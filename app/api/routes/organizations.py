"""
Organization-scoped resource routes: knowledge bases. Kept minimal for the
POC — invite/remove members, group management, and plan/billing are
natural next additions but aren't needed to demonstrate the RAG core.
"""
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.core.deps import get_current_context, RequestContext
from app.models import KnowledgeBase

router = APIRouter(prefix="/knowledge-bases", tags=["knowledge-bases"])


class KnowledgeBaseIn(BaseModel):
    name: str
    description: str | None = None


class KnowledgeBaseOut(BaseModel):
    id: str
    name: str
    description: str | None = None
    status: str

    class Config:
        from_attributes = True


@router.post("", response_model=KnowledgeBaseOut)
def create_knowledge_base(
    payload: KnowledgeBaseIn,
    ctx: RequestContext = Depends(get_current_context),
    db: Session = Depends(get_db),
):
    kb = KnowledgeBase(organization_id=ctx.organization_id, name=payload.name, description=payload.description)
    db.add(kb)
    db.commit()
    db.refresh(kb)
    return kb


@router.get("", response_model=list[KnowledgeBaseOut])
def list_knowledge_bases(
    ctx: RequestContext = Depends(get_current_context),
    db: Session = Depends(get_db),
):
    return db.query(KnowledgeBase).filter(KnowledgeBase.organization_id == ctx.organization_id).all()
