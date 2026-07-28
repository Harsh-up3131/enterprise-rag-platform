import uuid
from datetime import datetime, timezone

from sqlalchemy import String, ForeignKey, DateTime
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class AuditEvent(Base):
    """Who did what, when — used to answer 'who accessed which knowledge'."""
    __tablename__ = "audit_events"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4()))
    organization_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("organizations.id"), nullable=False, index=True)
    actor_user_id: Mapped[str] = mapped_column(UUID(as_uuid=False), nullable=False)
    action: Mapped[str] = mapped_column(String, nullable=False)  # e.g. "document.upload", "query.ask"
    resource_type: Mapped[str] = mapped_column(String, nullable=True)
    resource_id: Mapped[str] = mapped_column(String, nullable=True)
    metadata_json: Mapped[dict] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
