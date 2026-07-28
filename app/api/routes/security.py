"""
Admin/security routes. Owner/admin only — these either touch cross-tenant
data (isolation check plants a throwaway shadow org) or expose access
control details (ACL listing) that regular members shouldn't need to see.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.core.deps import require_role, RequestContext
from app.models import KnowledgeBase
from app.services.security.tenant_isolation_check import run_isolation_check

router = APIRouter(prefix="/admin/security", tags=["security"])


class CheckOut(BaseModel):
    name: str
    passed: bool
    detail: str


class IsolationCheckResponse(BaseModel):
    all_passed: bool
    checks: list[CheckOut]


@router.post("/isolation-check", response_model=IsolationCheckResponse)
def isolation_check(
    ctx: RequestContext = Depends(require_role("owner", "admin")),
    db: Session = Depends(get_db),
):
    # Needs at least one knowledge base in the org to plant a test document into.
    kb = db.query(KnowledgeBase).filter(KnowledgeBase.organization_id == ctx.organization_id).first()
    if not kb:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Create a knowledge base before running this check")

    results = run_isolation_check(db, ctx.organization_id, ctx.user.id, kb.id)
    return IsolationCheckResponse(
        all_passed=all(r.passed for r in results),
        checks=[CheckOut(name=r.name, passed=r.passed, detail=r.detail) for r in results],
    )
