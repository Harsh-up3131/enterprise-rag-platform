"""
Reranking stage: reorders fused candidates against the raw query text with
a finer-grained relevance model than lexical/dense retrieval alone.

POC scope: a lightweight lexical-overlap scorer standing in for a real
cross-encoder (e.g. BGE-reranker) — it's fast, dependency-free, and proves
the *interface* the real model will plug into. Swap `score_pair` for a
call to a hosted/local cross-encoder in production; nothing upstream
(fusion) or downstream (evidence selection) needs to change.
"""
import re
from dataclasses import dataclass


@dataclass
class RerankedCandidate:
    chunk_id: str
    rerank_score: float


_WORD_RE = re.compile(r"[a-z0-9]+")


def _tokenize(text: str) -> set[str]:
    return set(_WORD_RE.findall(text.lower()))


def score_pair(query: str, chunk_text: str) -> float:
    """
    TODO(prod): replace with a real cross-encoder, e.g.:
        from sentence_transformers import CrossEncoder
        model = CrossEncoder("BAAI/bge-reranker-base")
        return float(model.predict([(query, chunk_text)])[0])
    POC stand-in: normalized token-overlap (Jaccard-ish) score in [0, 1].
    """
    q_tokens = _tokenize(query)
    c_tokens = _tokenize(chunk_text)
    if not q_tokens or not c_tokens:
        return 0.0
    overlap = len(q_tokens & c_tokens)
    return overlap / len(q_tokens)


def rerank(query: str, candidates: list[tuple[str, str]], top_k: int) -> list[RerankedCandidate]:
    """`candidates` is a list of (chunk_id, chunk_text)."""
    scored = [
        RerankedCandidate(chunk_id=chunk_id, rerank_score=score_pair(query, text))
        for chunk_id, text in candidates
    ]
    scored.sort(key=lambda c: c.rerank_score, reverse=True)
    return scored[:top_k]
