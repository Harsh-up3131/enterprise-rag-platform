"""
Celery app definition. Ingestion is asynchronous (blueprint §8.1) so
uploads return immediately and processing happens off the request path,
recoverable independently via task retries.
"""
from celery import Celery

from app.config import settings

celery_app = Celery(
    "ekip",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=["app.workers.tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    task_track_started=True,
    # TODO(prod): tune retry/backoff policy, dead-letter handling, and
    # concurrency per worker for real ingestion volumes.
)
