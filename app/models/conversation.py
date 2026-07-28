import uuid
from datetime import datetime, timezone

from sqlalchemy import String, ForeignKey, DateTime, Text, Float, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


def _uuid():
    return str(uuid.uuid4())


class Conversation(Base):
    """
    Chat history is stored for UX continuity but — per blueprint principle
    4.1/4.5 — is NEVER treated as authoritative knowledge; each turn
    re-runs retrieval against the knowledge base, not against prior chat.
    """
    __tablename__ = "conversations"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    organization_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("organizations.id"), nullable=False, index=True)
    user_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("users.id"), nullable=False)
    title: Mapped[str] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    conversation_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("conversations.id"), nullable=False, index=True)
    role: Mapped[str] = mapped_column(String, nullable=False)  # user|assistant
    content: Mapped[str] = mapped_column(Text, nullable=False)
    trace_id: Mapped[str] = mapped_column(UUID(as_uuid=False), nullable=True)  # links to RetrievalTrace
    abstained: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class Citation(Base):
    """One resolvable evidence pointer backing part of an assistant answer."""
    __tablename__ = "citations"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    message_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("messages.id"), nullable=False, index=True)
    chunk_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("chunks.id"), nullable=False)
    document_version_id: Mapped[str] = mapped_column(UUID(as_uuid=False), nullable=True)
    quoted_span: Mapped[str] = mapped_column(Text, nullable=True)
    page: Mapped[int] = mapped_column(Integer, nullable=True)
    score: Mapped[float] = mapped_column(Float, nullable=True)
    # verification_status: verified|unverified|rejected
    # set by services/generation/citation_validator.py
    verification_status: Mapped[str] = mapped_column(String, default="unverified")
