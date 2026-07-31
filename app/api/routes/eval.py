"""
Evaluation route: runs the sample eval set through the live pipeline. In
production this becomes a CI-gated job (blueprint §6.1) rather than an
on-demand API call, but exposing it here makes the eval harness easy to
poke at during development.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.core.deps import get_current_context, RequestContext
from app.schemas.eval import EvalRunRequest
from app.services.evaluation.runner import run_eval, load_eval_set
from app.services.evaluation.runner import get_suggested_chunks_for_cases

router = APIRouter(prefix="/eval", tags=["evaluation"])


@router.get("/sample-set")
def get_sample_eval_set():
    """The bundled starter questions, so the UI can prefill an editable set."""
    return load_eval_set()


@router.post("/run")
def run_evaluation(
    payload: EvalRunRequest | None = None,
    ctx: RequestContext = Depends(get_current_context),
    db: Session = Depends(get_db),
):
    cases = [c.model_dump() for c in payload.cases] if payload and payload.cases else None
    score_missing = payload.score_missing_recall_as_zero if payload is not None else False
    return run_eval(
        db,
        organization_id=ctx.organization_id,
        user_id=ctx.user.id,
        cases=cases,
        score_missing_recall_as_zero=score_missing,
    )


@router.post("/suggestions")
def suggested_chunks(
    payload: EvalRunRequest | None = None,
    ctx: RequestContext = Depends(get_current_context),
    db: Session = Depends(get_db),
):
    """Return suggested chunk texts for eval cases missing ground-truth.

    The request body mirrors `POST /eval/run` (an optional `cases` array).
    """
    cases = [c.model_dump() for c in payload.cases] if payload and payload.cases else load_eval_set()
    return get_suggested_chunks_for_cases(db, ctx.organization_id, cases)
