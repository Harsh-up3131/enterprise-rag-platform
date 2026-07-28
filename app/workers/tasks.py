"""
Celery tasks. Thin wrappers around service-layer functions — the task just
owns the DB session lifecycle and retry policy; all real logic lives in
app/services so it stays testable without Celery running.
"""
from app.workers.celery_app import celery_app
from app.database import SessionLocal
from app.services.ingestion.pipeline import run_ingestion


@celery_app.task(bind=True, max_retries=2, default_retry_delay=10)
def ingest_document_version_task(self, document_version_id: str):
    """
    Queued after a document upload. Retries twice on transient failures
    (e.g. a flaky embedding call); a permanent failure (bad file, unsupported
    content) marks the DocumentVersion as 'failed' rather than retrying
    forever — see run_ingestion's except block.
    """
    db = SessionLocal()
    try:
        run_ingestion(db, document_version_id)
    except Exception as exc:  # noqa: BLE001
        # Only retry if we haven't already exhausted attempts; run_ingestion
        # has already persisted the failure state either way, so a retry
        # here is safe/idempotent (pipeline re-parses + replaces chunks).
        raise self.retry(exc=exc)
    finally:
        db.close()
