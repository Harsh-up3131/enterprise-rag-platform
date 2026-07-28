"""
Evaluation runner: loads a hand-written eval set and runs each case through
the SAME retrieval/generation pipeline used in production (not a mocked
shortcut), so results reflect real system behavior. This is the seed of
the "CI evaluation gate" from blueprint §6.1 — wire this into CI and fail
the build if aggregate metrics regress below a threshold.

RAGAS integration (faithfulness/answer-relevancy scored by an LLM judge)
is left as `run_ragas_eval` stub — POC keeps to deterministic metrics only,
per the instruction not to go deep into any one subsystem.
"""
import json
import os

from sqlalchemy.orm import Session

from app.services.query_service import answer_question
from app.services.evaluation.metrics import recall_at_k, EvalCaseResult, aggregate

_SAMPLE_EVAL_PATH = os.path.join(os.path.dirname(__file__), "sample_eval_set.json")


def load_eval_set(path: str = _SAMPLE_EVAL_PATH) -> list[dict]:
    with open(path) as f:
        return json.load(f)


def run_eval(db: Session, organization_id: str, user_id: str, eval_set_path: str = _SAMPLE_EVAL_PATH) -> dict:
    cases = load_eval_set(eval_set_path)
    results: list[EvalCaseResult] = []

    for case in cases:
        result = answer_question(db, case["question"], organization_id, user_id)
        retrieved_ids = [c.chunk_id for c in result.citations]
        expected_abstain = case.get("expect_abstain", False)

        results.append(EvalCaseResult(
            question=case["question"],
            recall_at_k=recall_at_k(retrieved_ids, case.get("relevant_chunk_ids", [])),
            any_citation_correct=len(result.citations) > 0,
            abstained=result.abstained,
            expected_abstain=expected_abstain,
            correct_abstention_behavior=(result.abstained == expected_abstain),
        ))

    return aggregate(results)


def run_ragas_eval(*args, **kwargs) -> dict:
    """
    TODO(prod): wire in RAGAS (faithfulness, answer_relevancy, context_precision)
    using an LLM judge over (question, evidence, answer) triples collected
    from run_eval(). Left as a stub so the eval interface/shape is settled
    without adding an LLM-judge dependency to the POC's CI path.
    """
    raise NotImplementedError("RAGAS evaluation is a production-phase addition; see blueprint §6.2")
