"""
Rank fusion: combine lexical + dense candidate lists into one ranking.

Uses Reciprocal Rank Fusion (RRF) — simple, has no score-scale issues
(lexical ts_rank and cosine similarity aren't comparable magnitudes), and
is a defensible, explicitly-named baseline per blueprint §6.1
("RRF or another explicitly evaluated fusion strategy").
"""
from dataclasses import dataclass

from app.config import settings


@dataclass
class FusedCandidate:
    chunk_id: str
    fused_score: float
    lexical_rank: int | None = None
    dense_rank: int | None = None


def reciprocal_rank_fusion(
    lexical_candidates: list,  # list[lexical.Candidate], ordered best-first
    dense_candidates: list,    # list[dense.Candidate], ordered best-first
    top_k: int,
    k: int = None,
) -> list[FusedCandidate]:
    k = k or settings.rrf_k
    scores: dict[str, float] = {}
    lex_rank: dict[str, int] = {}
    dense_rank: dict[str, int] = {}

    for rank, cand in enumerate(lexical_candidates, start=1):
        scores[cand.chunk_id] = scores.get(cand.chunk_id, 0.0) + 1.0 / (k + rank)
        lex_rank[cand.chunk_id] = rank

    for rank, cand in enumerate(dense_candidates, start=1):
        scores[cand.chunk_id] = scores.get(cand.chunk_id, 0.0) + 1.0 / (k + rank)
        dense_rank[cand.chunk_id] = rank

    fused = [
        FusedCandidate(
            chunk_id=chunk_id,
            fused_score=score,
            lexical_rank=lex_rank.get(chunk_id),
            dense_rank=dense_rank.get(chunk_id),
        )
        for chunk_id, score in scores.items()
    ]
    fused.sort(key=lambda c: c.fused_score, reverse=True)
    return fused[:top_k]
