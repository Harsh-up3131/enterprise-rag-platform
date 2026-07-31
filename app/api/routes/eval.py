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
from app.services.evaluation.monitoring import summarize_trace_metrics
from app.services.evaluation.runner import run_eval, load_eval_set
from app.services.evaluation.runner import get_suggested_chunks_for_cases
from app.services.evaluation.history import load_quality_history
from app.models import RetrievalTrace

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


@router.get("/quality")
def get_quality_dashboard(
    ctx: RequestContext = Depends(get_current_context),
    db: Session = Depends(get_db),
):
    """Return a lightweight quality summary for recent queries."""
    traces = (
        db.query(RetrievalTrace)
        .filter(RetrievalTrace.organization_id == ctx.organization_id)
        .order_by(RetrievalTrace.created_at.desc())
        .limit(50)
        .all()
    )
    payload = []
    for trace in traces:
        payload.append({
            "abstained": trace.abstained,
            "selected_chunk_ids": trace.selected_chunk_ids or [],
            "latency_ms": trace.latency_ms or {},
            "query": trace.query,
        })
    summary = summarize_trace_metrics(payload)
    history = load_quality_history(db, ctx.organization_id, limit=10)
    summary["history"] = [
        {
            "created_at": snapshot.created_at.isoformat() if snapshot.created_at else None,
            "total_queries": snapshot.total_queries,
            "abstention_rate": snapshot.abstention_rate,
            "citation_success_rate": snapshot.citation_success_rate,
            "avg_latency_ms": snapshot.avg_latency_ms,
            "answer_quality_score": snapshot.answer_quality_score,
        }
        for snapshot in history
    ]
    return summary
