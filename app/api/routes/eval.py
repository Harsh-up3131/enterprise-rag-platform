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
from app.services.evaluation.runner import run_eval

router = APIRouter(prefix="/eval", tags=["evaluation"])


@router.post("/run")
def run_evaluation(
    ctx: RequestContext = Depends(get_current_context),
    db: Session = Depends(get_db),
):
    return run_eval(db, organization_id=ctx.organization_id, user_id=ctx.user.id)
