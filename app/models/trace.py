import uuid
from datetime import datetime, timezone

from sqlalchemy import String, ForeignKey, DateTime, Text, Float, Integer
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class QualitySummarySnapshot(Base):
    """Persisted quality summary snapshots for trend tracking over time."""
    __tablename__ = "quality_summary_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    organization_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("organizations.id"), nullable=False, index=True)
    source: Mapped[str] = mapped_column(String(50), nullable=False, default="eval")
    total_queries: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    abstention_rate: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    citation_success_rate: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    avg_latency_ms: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    answer_quality_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    payload: Mapped[dict] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class RetrievalTrace(Base):
    """
    A reproducibility record for one query: what was asked, which config
    versions were active, what candidates/scores came back at each stage,
    and what was ultimately selected. This is deliberately a single wide
    row for the POC; a production system would emit per-stage spans to
    Langfuse/OpenTelemetry instead (see README "Next steps").
    """
    __tablename__ = "retrieval_traces"

    trace_id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4()))
    organization_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("organizations.id"), nullable=False, index=True)
    user_id: Mapped[str] = mapped_column(UUID(as_uuid=False), nullable=False)

    query: Mapped[str] = mapped_column(Text, nullable=False)
    normalized_query: Mapped[str] = mapped_column(Text, nullable=True)

    retriever_config_version: Mapped[str] = mapped_column(String, nullable=True)

    # Raw stage outputs, kept as JSON for POC simplicity/flexibility.
    lexical_candidates: Mapped[list] = mapped_column(JSONB, default=list)  # [{chunk_id, score}]
    dense_candidates: Mapped[list] = mapped_column(JSONB, default=list)
    fused_candidates: Mapped[list] = mapped_column(JSONB, default=list)
    reranked_candidates: Mapped[list] = mapped_column(JSONB, default=list)
    selected_chunk_ids: Mapped[list] = mapped_column(JSONB, default=list)

    abstained: Mapped[bool] = mapped_column(default=False)
    top_evidence_score: Mapped[float] = mapped_column(Float, nullable=True)

    latency_ms: Mapped[dict] = mapped_column(JSONB, default=dict)  # {"lexical": .., "dense": .., "rerank": .., "generation": ..}

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
