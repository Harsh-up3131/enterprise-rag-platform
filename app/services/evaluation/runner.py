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


def run_eval(
    db: Session,
    organization_id: str,
    user_id: str,
    eval_set_path: str = _SAMPLE_EVAL_PATH,
    cases: list[dict] | None = None,
    *,
    # If True, cases that don't include `relevant_chunk_ids` are scored as
    # recall=0.0 instead of being excluded (so Recall@K won't show as "n/a").
    score_missing_recall_as_zero: bool = False,
    # When True, try to auto-annotate missing `relevant_chunk_ids` by
    # searching the organization's chunks for n-gram matches against the
    # question text. This attempts to recover ground-truth when the eval
    # author omitted it, avoiding spurious "n/a" reports.
    auto_annotate_missing: bool = True,
) -> dict:
    """Runs each case through the live pipeline and aggregates the scores.

    `cases` lets a caller supply an eval set inline (the Evaluation panel
    posts one) instead of reading the on-disk sample. The sample set is
    deliberately generic, so it only produces meaningful citation/recall
    numbers against a corpus that happens to contain those answers —
    grading your own documents means supplying your own questions.
    """
    if cases is None:
        cases = load_eval_set(eval_set_path)

    results: list[EvalCaseResult] = []

    for case in cases:
        result = answer_question(db, case["question"], organization_id, user_id)
        # Use retrieval-stage evidence (reranked candidates) for Recall@K
        # rather than the post-generation validated citations. This matches
        # the metric's intent: did retrieval find the expected chunks?
        retrieved_ids = getattr(result, "retrieved_chunk_ids", []) or []
        expected_abstain = case.get("expect_abstain", False)

        # If the case has no explicit ground-truth chunk ids, try to
        # auto-annotate using a simple n-gram substring search over the
        # organization's chunk texts. This is a best-effort heuristic and
        # should be reviewed by a human when possible.
        relevant_ids = case.get("relevant_chunk_ids", []) or []
        auto_annotated = False
        if not relevant_ids and auto_annotate_missing:
            import re
            from app.models import Chunk, Document

            words = [w for w in re.findall(r"\w+", case["question"].lower()) if len(w) > 1]
            ngrams = []
            max_n = min(6, len(words))
            for n in range(max_n, 0, -1):
                for i in range(0, len(words) - n + 1):
                    ngrams.append(" ".join(words[i : i + n]))

            found = []
            for phrase in ngrams[:50]:
                if found:
                    break
                q = (
                    db.query(Chunk.id)
                    .join(Document, Document.id == Chunk.document_id)
                    .filter(Chunk.organization_id == organization_id)
                    .filter(Chunk.text.ilike(f"%{phrase}%"))
                )
                if case.get("knowledge_base_id"):
                    q = q.filter(Document.knowledge_base_id == case.get("knowledge_base_id"))
                rows = q.limit(10).all()
                found.extend([r[0] for r in rows])

            if found:
                relevant_ids = [str(r) for r in found]
                auto_annotated = True

        results.append(EvalCaseResult(
            question=case["question"],
            recall_at_k=recall_at_k(retrieved_ids, relevant_ids, treat_missing_as_zero=score_missing_recall_as_zero),
            num_verified_citations=len(result.citations),
            abstained=result.abstained,
            expected_abstain=expected_abstain,
            correct_abstention_behavior=(result.abstained == expected_abstain),
            suggested_relevant_ids=relevant_ids or None,
            auto_annotated=auto_annotated,
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
