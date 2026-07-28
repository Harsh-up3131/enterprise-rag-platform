"""
Ingestion pipeline orchestrator (per blueprint §8.1).

Runs parse -> chunk -> embed -> persist for one DocumentVersion, and only
flips the version/document status to "ready" once every chunk is
successfully embedded and committed — a document must never become
searchable while only partially indexed.

Called from a Celery task (app/workers/tasks.py) so it runs off the
request path; this function itself is transport-agnostic and could equally
be called from a script or a different queue.
"""
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models import DocumentVersion, Document, Chunk
from app.services.ingestion.parser import parse_document, PARSER_VERSION
from app.services.ingestion.chunker import chunk_elements, CHUNKER_VERSION
from app.services.ingestion.embedder import embed_texts, EMBEDDING_MODEL_VERSION
from app.services.ingestion.storage import get_object_path


def run_ingestion(db: Session, document_version_id: str) -> None:
    version = db.get(DocumentVersion, document_version_id)
    if version is None:
        raise ValueError(f"DocumentVersion {document_version_id} not found")

    document = db.get(Document, version.document_id)

    try:
        version.ingestion_status = "parsing"
        db.commit()

        file_path = get_object_path(version.object_key)
        elements = parse_document(file_path, document.source_type)

        version.ingestion_status = "chunking"
        version.parser_version = PARSER_VERSION
        db.commit()

        drafts = chunk_elements(elements)
        if not drafts:
            raise ValueError("No content extracted from document (empty or unsupported layout)")

        version.ingestion_status = "embedding"
        version.chunker_version = CHUNKER_VERSION
        db.commit()

        vectors = embed_texts([d.text for d in drafts])

        # Remove any partial chunks from a previous failed attempt at this version
        # (retry-safety per blueprint §12.4 idempotency rule).
        db.query(Chunk).filter(Chunk.document_version_id == version.id).delete()

        for idx, (draft, vector) in enumerate(zip(drafts, vectors)):
            db.add(Chunk(
                organization_id=document.organization_id,
                document_id=document.id,
                document_version_id=version.id,
                chunk_index=idx,
                text=draft.text,
                heading_path=draft.heading_path,
                page_start=draft.page_start,
                page_end=draft.page_end,
                token_count=draft.token_count,
                embedding=vector,
                metadata_json={},
            ))

        version.embedding_model_version = EMBEDDING_MODEL_VERSION
        version.ingestion_status = "ready"
        version.indexed_at = datetime.now(timezone.utc)
        document.current_version_id = version.id
        document.status = "ready"
        db.commit()

    except Exception as exc:  # noqa: BLE001 - top-level pipeline guard
        db.rollback()
        version.ingestion_status = "failed"
        version.error_message = str(exc)[:2000]
        document.status = "failed"
        db.commit()
        raise
