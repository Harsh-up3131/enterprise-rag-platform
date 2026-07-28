import uuid
from datetime import datetime, timezone

from sqlalchemy import String, ForeignKey, DateTime, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


def _uuid():
    return str(uuid.uuid4())


class Document(Base):
    """
    Logical document (stable identity across versions). The actual bytes and
    derived chunks live on DocumentVersion so re-uploads / edits are versioned
    rather than mutating history in place.
    """
    __tablename__ = "documents"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    organization_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("organizations.id"), nullable=False, index=True)
    knowledge_base_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("knowledge_bases.id"), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String, nullable=False)
    source_type: Mapped[str] = mapped_column(String, nullable=False)  # pdf|docx|txt|md|html
    owner_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("users.id"), nullable=False)
    current_version_id: Mapped[str] = mapped_column(UUID(as_uuid=False), nullable=True)
    sensitivity: Mapped[str] = mapped_column(String, default="internal")  # public|internal|confidential
    # status: uploading -> processing -> ready | failed
    status: Mapped[str] = mapped_column(String, default="uploading")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    versions: Mapped[list["DocumentVersion"]] = relationship(back_populates="document")
    acl_entries: Mapped[list["DocumentACL"]] = relationship(back_populates="document")


class DocumentVersion(Base):
    """
    An immutable, versioned snapshot of a document's content and how it was
    processed. `parser_version` / `chunker_version` / `embedding_model_version`
    make every index build reproducible, per the blueprint's provenance rule.
    """
    __tablename__ = "document_versions"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    document_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("documents.id"), nullable=False, index=True)
    version_number: Mapped[int] = mapped_column(Integer, default=1)
    object_key: Mapped[str] = mapped_column(String, nullable=False)  # path in object storage
    checksum: Mapped[str] = mapped_column(String, nullable=False)
    parser_version: Mapped[str] = mapped_column(String, nullable=True)
    chunker_version: Mapped[str] = mapped_column(String, nullable=True)
    embedding_model_version: Mapped[str] = mapped_column(String, nullable=True)
    # ingestion_status: pending -> parsing -> chunking -> embedding -> ready | failed
    ingestion_status: Mapped[str] = mapped_column(String, default="pending")
    error_message: Mapped[str] = mapped_column(String, nullable=True)
    indexed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    document: Mapped["Document"] = relationship(back_populates="versions")


class DocumentACL(Base):
    """
    Row-level authorization for a document. Checked BEFORE retrieval query
    execution (see services/retrieval/lexical.py / dense.py which both join
    against this table) — never after, and never delegated to the LLM.
    """
    __tablename__ = "document_acl"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    document_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("documents.id"), nullable=False, index=True)
    principal_type: Mapped[str] = mapped_column(String, nullable=False)  # user|group|role|organization
    principal_id: Mapped[str] = mapped_column(String, nullable=False)  # user_id/group_id/role name/org_id
    permission: Mapped[str] = mapped_column(String, default="read")

    document: Mapped["Document"] = relationship(back_populates="acl_entries")
