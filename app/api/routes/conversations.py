"""
Conversation history routes.

Chat history is a UX affordance only — per blueprint principle 4.1/4.5 it is
never fed back in as authoritative knowledge; every turn re-runs retrieval
against the knowledge base. These routes exist so the UI can list past
conversations and replay one, nothing more.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.core.deps import get_current_context, RequestContext
from app.models import Conversation, Message, Citation, Chunk, Document

router = APIRouter(prefix="/conversations", tags=["conversations"])


class ConversationOut(BaseModel):
    id: str
    title: str | None = None
    created_at: str
    updated_at: str
    message_count: int


class CitationOut(BaseModel):
    chunk_id: str
    document_title: str
    heading_path: str | None = None
    page: int | None = None
    score: float | None = None


class MessageOut(BaseModel):
    id: str
    role: str
    content: str
    abstained: bool
    trace_id: str | None = None
    created_at: str
    citations: list[CitationOut] = []


class ConversationDetailOut(BaseModel):
    id: str
    title: str | None = None
    messages: list[MessageOut]


@router.get("", response_model=list[ConversationOut])
def list_conversations(
    limit: int = 50,
    ctx: RequestContext = Depends(get_current_context),
    db: Session = Depends(get_db),
):
    """Conversations belonging to the caller, most recently active first."""
    last_activity = func.coalesce(func.max(Message.created_at), Conversation.created_at)

    rows = (
        db.query(Conversation, last_activity.label("updated_at"), func.count(Message.id).label("message_count"))
        .outerjoin(Message, Message.conversation_id == Conversation.id)
        .filter(Conversation.organization_id == ctx.organization_id)
        .filter(Conversation.user_id == ctx.user.id)
        .group_by(Conversation.id)
        .order_by(last_activity.desc())
        .limit(min(limit, 200))
        .all()
    )

    return [
        ConversationOut(
            id=str(conv.id),
            title=conv.title,
            created_at=conv.created_at.isoformat(),
            updated_at=updated_at.isoformat(),
            message_count=message_count,
        )
        for conv, updated_at, message_count in rows
    ]


@router.get("/{conversation_id}", response_model=ConversationDetailOut)
def get_conversation(
    conversation_id: str,
    ctx: RequestContext = Depends(get_current_context),
    db: Session = Depends(get_db),
):
    """Full transcript of one conversation, with each answer's verified citations."""
    conversation = db.get(Conversation, conversation_id)
    # Tenant + ownership check before anything is read back.
    if (
        conversation is None
        or conversation.organization_id != ctx.organization_id
        or conversation.user_id != ctx.user.id
    ):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Conversation not found")

    messages = (
        db.query(Message)
        .filter(Message.conversation_id == conversation.id)
        .order_by(Message.created_at.asc())
        .all()
    )

    message_ids = [m.id for m in messages]
    citations_by_message: dict[str, list[CitationOut]] = {}
    if message_ids:
        rows = (
            db.query(Citation, Document.title)
            .join(Chunk, Chunk.id == Citation.chunk_id)
            .join(Document, Document.id == Chunk.document_id)
            .filter(Citation.message_id.in_(message_ids))
            .filter(Citation.verification_status == "verified")
            .all()
        )
        for citation, document_title in rows:
            citations_by_message.setdefault(str(citation.message_id), []).append(
                CitationOut(
                    chunk_id=str(citation.chunk_id),
                    document_title=document_title,
                    page=citation.page,
                    score=citation.score,
                )
            )

    return ConversationDetailOut(
        id=str(conversation.id),
        title=conversation.title,
        messages=[
            MessageOut(
                id=str(m.id),
                role=m.role,
                content=m.content,
                abstained=m.abstained,
                trace_id=str(m.trace_id) if m.trace_id else None,
                created_at=m.created_at.isoformat(),
                citations=citations_by_message.get(str(m.id), []),
            )
            for m in messages
        ],
    )


@router.delete("/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_conversation(
    conversation_id: str,
    ctx: RequestContext = Depends(get_current_context),
    db: Session = Depends(get_db),
):
    conversation = db.get(Conversation, conversation_id)
    if (
        conversation is None
        or conversation.organization_id != ctx.organization_id
        or conversation.user_id != ctx.user.id
    ):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Conversation not found")

    message_ids = [m.id for m in db.query(Message).filter(Message.conversation_id == conversation.id).all()]
    if message_ids:
        db.query(Citation).filter(Citation.message_id.in_(message_ids)).delete(synchronize_session=False)
    db.query(Message).filter(Message.conversation_id == conversation.id).delete(synchronize_session=False)
    db.delete(conversation)
    db.commit()
    return None
