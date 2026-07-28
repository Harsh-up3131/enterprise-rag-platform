"""
Retrieval orchestrator: runs the full pipeline described in blueprint §8.2
(lexical + dense -> fusion -> rerank -> evidence selection) and returns an
EvidencePack plus the raw stage data needed to persist a RetrievalTrace.
"""
import time
from dataclasses import dataclass, field

from langsmith import traceable
from sqlalchemy.orm import Session

from app.config import settings
from app.models import Chunk, Document
from app.services.retrieval import lexical, dense, fusion, reranker


@dataclass
class EvidenceItem:
    chunk_id: str
    text: str
    document_id: str
    document_title: str
    heading_path: str | None
    page_start: int | None
    score: float


@dataclass
class RetrievalResult:
    evidence: list[EvidenceItem]
    top_score: float
    stage_data: dict = field(default_factory=dict)  # for RetrievalTrace persistence
    latency_ms: dict = field(default_factory=dict)


@traceable(name="hybrid_retrieve", run_type="retriever")
def retrieve(
    db: Session,
    query: str,
    organization_id: str,
    user_id: str,
    knowledge_base_id: str | None = None,
) -> RetrievalResult:
    latency_ms: dict[str, float] = {}

    t0 = time.perf_counter()
    lexical_candidates = lexical.lexical_search(
        db, query, organization_id, user_id, settings.lexical_top_k, knowledge_base_id
    )
    latency_ms["lexical"] = (time.perf_counter() - t0) * 1000

    t0 = time.perf_counter()
    dense_candidates = dense.dense_search(
        db, query, organization_id, user_id, settings.dense_top_k, knowledge_base_id
    )
    latency_ms["dense"] = (time.perf_counter() - t0) * 1000

    fused = fusion.reciprocal_rank_fusion(lexical_candidates, dense_candidates, settings.fusion_top_k)

    if not fused:
        return RetrievalResult(
            evidence=[],
            top_score=0.0,
            stage_data={
                "lexical_candidates": [c.__dict__ for c in lexical_candidates],
                "dense_candidates": [c.__dict__ for c in dense_candidates],
                "fused_candidates": [],
                "reranked_candidates": [],
            },
            latency_ms=latency_ms,
        )

    # Fetch chunk text/document metadata for the fused candidates only
    # (rerank needs text; earlier stages only need chunk_id + score).
    fused_ids = [c.chunk_id for c in fused]
    chunk_rows = (
        db.query(Chunk, Document)
        .join(Document, Document.id == Chunk.document_id)
        .filter(Chunk.id.in_(fused_ids))
        .all()
    )
    chunk_by_id = {str(c.id): (c, d) for c, d in chunk_rows}

    t0 = time.perf_counter()
    rerank_input = [(cid, chunk_by_id[cid][0].text) for cid in fused_ids if cid in chunk_by_id]
    reranked = reranker.rerank(query, rerank_input, settings.rerank_top_k)
    latency_ms["rerank"] = (time.perf_counter() - t0) * 1000

    evidence: list[EvidenceItem] = []
    for r in reranked:
        chunk, doc = chunk_by_id[r.chunk_id]
        evidence.append(EvidenceItem(
            chunk_id=r.chunk_id,
            text=chunk.text,
            document_id=str(doc.id),
            document_title=doc.title,
            heading_path=chunk.heading_path,
            page_start=chunk.page_start,
            score=r.rerank_score,
        ))

    top_score = evidence[0].score if evidence else 0.0

    return RetrievalResult(
        evidence=evidence,
        top_score=top_score,
        stage_data={
            "lexical_candidates": [c.__dict__ for c in lexical_candidates],
            "dense_candidates": [c.__dict__ for c in dense_candidates],
            "fused_candidates": [c.__dict__ for c in fused],
            "reranked_candidates": [r.__dict__ for r in reranked],
        },
        latency_ms=latency_ms,
    )
