"""
Deterministic evaluation metrics — the "custom deterministic metrics" half
of blueprint §6.1 ("RAGAS plus deterministic/custom evaluation"). These
don't need an LLM judge, so they're fast/cheap enough to run in CI.

Scoring rule that matters: a metric is only averaged over the cases it can
actually be measured on, and reports `None` when that set is empty. The
alternative — folding unmeasurable cases in as 0.0 or 1.0 — produces
confident-looking numbers that mean nothing. Specifically:

  * recall@k is skipped for cases with no `relevant_chunk_ids` ground truth
    (there is nothing to recall, so a score of 1.0 would be vacuous).
  * citation accuracy is skipped for cases with `expect_abstain: true` —
    a correct abstention emits no citations *by design*, so counting it as
    a citation failure penalizes the system for behaving correctly.
"""
from dataclasses import dataclass


@dataclass
class EvalCaseResult:
    question: str
    abstained: bool
    expected_abstain: bool
    correct_abstention_behavior: bool
    num_verified_citations: int
    # None when the case carries no ground-truth chunk ids (not graded).
    recall_at_k: float | None = None

    @property
    def citation_scored(self) -> bool:
        """Citations are only meaningful on cases expected to produce an answer."""
        return not self.expected_abstain

    @property
    def cited_successfully(self) -> bool:
        return not self.abstained and self.num_verified_citations > 0


def recall_at_k(
    retrieved_chunk_ids: list[str],
    relevant_chunk_ids: list[str] | None,
    *,
    treat_missing_as_zero: bool = False,
) -> float | None:
    """Fraction of the expected chunks that were retrieved.

    Behavior when no ground truth is supplied:
      - default: return ``None`` so the case is excluded from aggregated averages
      - with ``treat_missing_as_zero=True``: return 0.0 so the case contributes
        as a zero to the aggregated average (useful when you want Recall@K to
        reflect all run cases even if some lack explicit ground truth).
    """
    if not relevant_chunk_ids:
        return 0.0 if treat_missing_as_zero else None
    retrieved_set = set(retrieved_chunk_ids)
    hits = sum(1 for cid in relevant_chunk_ids if cid in retrieved_set)
    return hits / len(relevant_chunk_ids)


def _mean(values: list[float]) -> float | None:
    return sum(values) / len(values) if values else None


def aggregate(results: list[EvalCaseResult]) -> dict:
    graded_recall = [r.recall_at_k for r in results if r.recall_at_k is not None]
    citation_cases = [r for r in results if r.citation_scored]

    return {
        "num_cases": len(results),
        "mean_recall_at_k": _mean(graded_recall),
        "recall_graded_cases": len(graded_recall),
        "citation_accuracy": _mean([1.0 if r.cited_successfully else 0.0 for r in citation_cases]),
        "citation_scored_cases": len(citation_cases),
        "abstention_accuracy": _mean([1.0 if r.correct_abstention_behavior else 0.0 for r in results]),
        "cases": [
            {
                "question": r.question,
                "abstained": r.abstained,
                "expected_abstain": r.expected_abstain,
                "abstention_ok": r.correct_abstention_behavior,
                "num_verified_citations": r.num_verified_citations,
                "recall_at_k": r.recall_at_k,
            }
            for r in results
        ],
    }
