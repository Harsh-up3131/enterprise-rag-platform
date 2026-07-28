import uuid

from sqlalchemy import String, ForeignKey, Integer, Computed, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB, TSVECTOR
from sqlalchemy.orm import Mapped, mapped_column
from pgvector.sqlalchemy import Vector

from app.database import Base
from app.config import settings


class Chunk(Base):
    """
    The atomic retrieval unit. Carries both a dense embedding (pgvector) and
    a generated tsvector column (Postgres full-text) so lexical and dense
    retrieval can both query this single table — keeping the POC simple
    while still demonstrating true hybrid retrieval (see blueprint §9 on
    why Postgres+pgvector is the recommended starting point).
    """
    __tablename__ = "chunks"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4()))
    organization_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("organizations.id"), nullable=False, index=True)
    document_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("documents.id"), nullable=False, index=True)
    document_version_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("document_versions.id"), nullable=False, index=True)

    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    heading_path: Mapped[str] = mapped_column(String, nullable=True)  # e.g. "Security > Secrets"
    page_start: Mapped[int] = mapped_column(Integer, nullable=True)
    page_end: Mapped[int] = mapped_column(Integer, nullable=True)
    token_count: Mapped[int] = mapped_column(Integer, nullable=True)
    checksum: Mapped[str] = mapped_column(String, nullable=True)
    metadata_json: Mapped[dict] = mapped_column(JSONB, default=dict)

    embedding: Mapped[list[float]] = mapped_column(Vector(settings.embedding_dim), nullable=True)

    # Postgres-generated tsvector, auto-maintained by the DB — this is the
    # "lexical index" referenced in the blueprint's ingestion flow.
    search_vector = mapped_column(
        TSVECTOR,
        Computed("to_tsvector('english', text)", persisted=True),
    )
