"""
Deterministic evaluation metrics — the "custom deterministic metrics" half
of blueprint §6.1 ("RAGAS plus deterministic/custom evaluation"). These
don't need an LLM judge, so they're fast/cheap enough to run in CI.
"""
from dataclasses import dataclass


@dataclass
class EvalCaseResult:
    question: str
    recall_at_k: float
    any_citation_correct: bool
    abstained: bool
    expected_abstain: bool
    correct_abstention_behavior: bool


def recall_at_k(retrieved_chunk_ids: list[str], relevant_chunk_ids: list[str]) -> float:
    if not relevant_chunk_ids:
        return 1.0  # nothing to find, trivially satisfied
    retrieved_set = set(retrieved_chunk_ids)
    hits = sum(1 for cid in relevant_chunk_ids if cid in retrieved_set)
    return hits / len(relevant_chunk_ids)


def aggregate(results: list[EvalCaseResult]) -> dict:
    n = len(results) or 1
    return {
        "num_cases": len(results),
        "mean_recall_at_k": sum(r.recall_at_k for r in results) / n,
        "citation_accuracy": sum(1 for r in results if r.any_citation_correct) / n,
        "abstention_accuracy": sum(1 for r in results if r.correct_abstention_behavior) / n,
    }
