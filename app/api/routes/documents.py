"""
Document routes: upload triggers async ingestion (Celery), status can be
polled, and ACLs can be granted per blueprint's document_acl model.
"""
import hashlib
import os

from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.core.deps import get_current_context, RequestContext
from app.models import Document, DocumentVersion, DocumentACL, KnowledgeBase, Chunk
from app.schemas.document import DocumentOut, DocumentACLIn, DocumentACLOut
from app.services.ingestion.storage import put_object
from app.workers.tasks import ingest_document_version_task

router = APIRouter(prefix="/documents", tags=["documents"])

_ALLOWED_EXTENSIONS = {"pdf": "pdf", "docx": "docx", "txt": "txt", "md": "md"}
_MAX_UPLOAD_BYTES = 25 * 1024 * 1024  # 25MB, per blueprint §12.2 "maximum size"


def _with_ingestion_status(db: Session, document: Document) -> DocumentOut:
    """Attaches the latest DocumentVersion's ingestion_status so the UI can
    render a progress bar (pending/parsing/chunking/embedding/ready/failed)
    even before the document as a whole is marked 'ready'."""
    latest_version = (
        db.query(DocumentVersion)
        .filter(DocumentVersion.document_id == document.id)
        .order_by(DocumentVersion.version_number.desc())
        .first()
    )
    out = DocumentOut.model_validate(document)
    out.ingestion_status = latest_version.ingestion_status if latest_version else None
    return out


@router.post("/upload", response_model=DocumentOut)
def upload_document(
    knowledge_base_id: str = Form(...),
    title: str = Form(...),
    sensitivity: str = Form("internal"),
    file: UploadFile = File(...),
    ctx: RequestContext = Depends(get_current_context),
    db: Session = Depends(get_db),
):
    kb = db.get(KnowledgeBase, knowledge_base_id)
    if not kb or kb.organization_id != ctx.organization_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Knowledge base not found")

    extension = (os.path.splitext(file.filename or "")[1] or "").lstrip(".").lower()
    if extension not in _ALLOWED_EXTENSIONS:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Unsupported file type: .{extension}")

    file_bytes = file.file.read()
    if len(file_bytes) == 0:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Uploaded file is empty")
    if len(file_bytes) > _MAX_UPLOAD_BYTES:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "File exceeds max upload size (25MB)")
    # NOTE(POC): real deployments must also do MIME sniffing (not just
    # extension) and malware scanning before this point — blueprint §12.2.

    checksum = hashlib.sha256(file_bytes).hexdigest()
    object_key = put_object(file_bytes, extension)

    document = Document(
        organization_id=ctx.organization_id,
        knowledge_base_id=knowledge_base_id,
        title=title,
        source_type=_ALLOWED_EXTENSIONS[extension],
        owner_id=ctx.user.id,
        sensitivity=sensitivity,
        status="processing",
    )
    db.add(document)
    db.flush()

    version = DocumentVersion(
        document_id=document.id,
        version_number=1,
        object_key=object_key,
        checksum=checksum,
        ingestion_status="pending",
    )
    db.add(version)
    db.flush()

    # POC default ACL: readable by anyone in the owning organization.
    # Callers can add finer-grained ACL rows via POST /documents/{id}/acl.
    db.add(DocumentACL(document_id=document.id, principal_type="organization",
                        principal_id=ctx.organization_id, permission="read"))
    db.commit()
    db.refresh(document)

    ingest_document_version_task.delay(version.id)

    return _with_ingestion_status(db, document)


@router.get("/{document_id}", response_model=DocumentOut)
def get_document(
    document_id: str,
    ctx: RequestContext = Depends(get_current_context),
    db: Session = Depends(get_db),
):
    document = db.get(Document, document_id)
    if not document or document.organization_id != ctx.organization_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Document not found")
    return _with_ingestion_status(db, document)


@router.get("", response_model=list[DocumentOut])
def list_documents(
    ctx: RequestContext = Depends(get_current_context),
    db: Session = Depends(get_db),
):
    documents = db.query(Document).filter(Document.organization_id == ctx.organization_id).all()
    return [_with_ingestion_status(db, d) for d in documents]


@router.delete("/{document_id}")
def delete_document(
    document_id: str,
    ctx: RequestContext = Depends(get_current_context),
    db: Session = Depends(get_db),
):
    document = db.get(Document, document_id)
    if not document or document.organization_id != ctx.organization_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Document not found")

    db.query(Chunk).filter(Chunk.document_id == document_id).delete()
    db.query(DocumentACL).filter(DocumentACL.document_id == document_id).delete()
    db.query(DocumentVersion).filter(DocumentVersion.document_id == document_id).delete()
    db.delete(document)
    db.commit()
    return {"status": "deleted"}


@router.get("/{document_id}/acl", response_model=list[DocumentACLOut])
def list_acl(
    document_id: str,
    ctx: RequestContext = Depends(get_current_context),
    db: Session = Depends(get_db),
):
    document = db.get(Document, document_id)
    if not document or document.organization_id != ctx.organization_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Document not found")
    return db.query(DocumentACL).filter(DocumentACL.document_id == document_id).all()


@router.post("/{document_id}/acl")
def grant_acl(
    document_id: str,
    payload: DocumentACLIn,
    ctx: RequestContext = Depends(get_current_context),
    db: Session = Depends(get_db),
):
    document = db.get(Document, document_id)
    if not document or document.organization_id != ctx.organization_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Document not found")
    if ctx.role not in ("owner", "admin"):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Only owner/admin can manage ACLs")

    db.add(DocumentACL(document_id=document_id, principal_type=payload.principal_type,
                        principal_id=payload.principal_id, permission=payload.permission))
    db.commit()
    return {"status": "granted"}
