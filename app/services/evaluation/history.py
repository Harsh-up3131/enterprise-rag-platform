from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.models import QualitySummarySnapshot


def save_quality_snapshot(db: Session, organization_id: str, summary: dict[str, Any], *, source: str = "eval") -> QualitySummarySnapshot:
    snapshot = QualitySummarySnapshot(
        organization_id=organization_id,
        source=source,
        total_queries=summary.get("total_queries", 0),
        abstention_rate=float(summary.get("abstention_rate", 0.0) or 0.0),
        citation_success_rate=float(summary.get("citation_success_rate", 0.0) or 0.0),
        avg_latency_ms=float(summary.get("avg_latency_ms", 0.0) or 0.0),
        answer_quality_score=float(summary.get("answer_quality_score", 0.0) or 0.0),
        payload={"recent_queries": summary.get("recent_queries", [])},
    )
    db.add(snapshot)
    db.commit()
    db.refresh(snapshot)
    return snapshot


def load_quality_history(db: Session, organization_id: str, *, limit: int = 20) -> list[QualitySummarySnapshot]:
    return (
        db.query(QualitySummarySnapshot)
        .filter(QualitySummarySnapshot.organization_id == organization_id)
        .order_by(QualitySummarySnapshot.created_at.desc())
        .limit(limit)
        .all()
    )
