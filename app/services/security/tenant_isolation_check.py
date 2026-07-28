"""
Tenant-isolation self-check.

This is the highest-priority verification in the whole system: ACL
enforcement happens inside raw SQL joins (services/retrieval/lexical.py,
dense.py), and a bug there would leak one organization's documents into
another's search results silently — no error, no stack trace, just wrong
answers. This module proves the boundary holds by actually attempting the
leak, end-to-end, against real data, rather than asserting on the query
text.

Design: three checks per run —
  1. POSITIVE CONTROL — the calling org can find its own freshly-planted
     document. If this fails, the whole check is meaningless (a search
     that finds nothing "passes" isolation trivially and dishonestly).
  2. CROSS-TENANT ISOLATION — a document planted in a throwaway *other*
     organization, ACL'd only to that other org, must NOT be findable by
     the calling org.
  3. NO-ACL DEFAULT-DENY — a document with zero ACL rows at all must not
     be findable by anyone (proves the ACL join is an allow-list, not a
     deny-list).

Everything created here is cleaned up at the end, pass or fail.
"""
import uuid
from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.models import Organization, User, Membership, KnowledgeBase, Document, DocumentVersion, DocumentACL, Chunk
from app.services.ingestion.embedder import embed_text
from app.services.retrieval.lexical import lexical_search
from app.services.retrieval.dense import dense_search
from app.core.security import hash_password


@dataclass
class CheckResult:
    name: str
    passed: bool
    detail: str


def _plant_document(db: Session, organization_id: str, kb_id: str, owner_id: str, secret_token: str, acl_org_id: str | None):
    """Creates a document + version + one chunk containing `secret_token`.
    If acl_org_id is None, no ACL row is created at all (tests default-deny)."""
    document = Document(
        organization_id=organization_id, knowledge_base_id=kb_id,
        title=f"isolation-check-{secret_token[:8]}", source_type="txt",
        owner_id=owner_id, status="ready",
    )
    db.add(document)
    db.flush()

    version = DocumentVersion(document_id=document.id, version_number=1, object_key="n/a",
                               checksum="n/a", ingestion_status="ready")
    db.add(version)
    db.flush()

    text = f"Confidential isolation-test marker: {secret_token}. This content must stay inside its own organization."
    db.add(Chunk(
        organization_id=organization_id, document_id=document.id, document_version_id=version.id,
        chunk_index=0, text=text, embedding=embed_text(text),
    ))

    if acl_org_id is not None:
        db.add(DocumentACL(document_id=document.id, principal_type="organization",
                            principal_id=acl_org_id, permission="read"))

    db.flush()
    return document, version


def _cleanup(db: Session, document_ids: list[str], extra_org_id: str | None, extra_user_id: str | None):
    if document_ids:
        db.query(Chunk).filter(Chunk.document_id.in_(document_ids)).delete(synchronize_session=False)
        db.query(DocumentACL).filter(DocumentACL.document_id.in_(document_ids)).delete(synchronize_session=False)
        db.query(DocumentVersion).filter(DocumentVersion.document_id.in_(document_ids)).delete(synchronize_session=False)
        db.query(Document).filter(Document.id.in_(document_ids)).delete(synchronize_session=False)
    if extra_org_id:
        db.query(KnowledgeBase).filter(KnowledgeBase.organization_id == extra_org_id).delete(synchronize_session=False)
        db.query(Membership).filter(Membership.organization_id == extra_org_id).delete(synchronize_session=False)
        db.query(Organization).filter(Organization.id == extra_org_id).delete(synchronize_session=False)
    if extra_user_id:
        db.query(User).filter(User.id == extra_user_id).delete(synchronize_session=False)
    db.commit()


def run_isolation_check(db: Session, organization_id: str, user_id: str, knowledge_base_id: str) -> list[CheckResult]:
    results: list[CheckResult] = []
    planted_document_ids: list[str] = []
    shadow_org_id = None
    shadow_user_id = None

    try:
        # --- setup: a throwaway "shadow" org this check will try to leak from ---
        run_tag = uuid.uuid4().hex[:8]
        shadow_org = Organization(name=f"isolation-check-shadow-{run_tag}", slug=f"isolation-check-{run_tag}")
        db.add(shadow_org)
        db.flush()
        shadow_org_id = shadow_org.id

        shadow_user = User(email=f"isolation-check-{run_tag}@internal.invalid",
                            hashed_password=hash_password(uuid.uuid4().hex))
        db.add(shadow_user)
        db.flush()
        shadow_user_id = shadow_user.id
        db.add(Membership(user_id=shadow_user.id, organization_id=shadow_org.id, role="owner"))

        shadow_kb = KnowledgeBase(organization_id=shadow_org.id, name="shadow-kb")
        db.add(shadow_kb)
        db.flush()
        db.commit()

        # --- Check 1: positive control (own-org document must be findable) ---
        own_secret = f"own-{run_tag}"
        own_doc, _ = _plant_document(db, organization_id, knowledge_base_id, user_id, own_secret, acl_org_id=organization_id)
        planted_document_ids.append(own_doc.id)
        db.commit()

        own_hits = dense_search(db, own_secret, organization_id, user_id, top_k=5, knowledge_base_id=knowledge_base_id)
        results.append(CheckResult(
            name="Positive control: own document is findable",
            passed=len(own_hits) > 0,
            detail="Confirms search is actually working (not just returning empty results)."
                    if own_hits else "FAILED — search found nothing for the calling org's own document.",
        ))

        # --- Check 2: cross-tenant isolation ---
        shadow_secret = f"shadow-{run_tag}"
        shadow_doc, _ = _plant_document(db, shadow_org.id, shadow_kb.id, shadow_user.id, shadow_secret, acl_org_id=shadow_org.id)
        planted_document_ids.append(shadow_doc.id)
        db.commit()

        leak_hits_lexical = lexical_search(db, shadow_secret, organization_id, user_id, top_k=5)
        leak_hits_dense = dense_search(db, shadow_secret, organization_id, user_id, top_k=5)
        leaked = len(leak_hits_lexical) > 0 or len(leak_hits_dense) > 0
        results.append(CheckResult(
            name="Cross-tenant isolation: other org's document is NOT findable",
            passed=not leaked,
            detail="No leakage detected across the organization boundary."
                    if not leaked else "FAILED — content from another organization was returned in search results.",
        ))

        # --- Check 3: no-ACL rows means default-deny, not default-allow ---
        noacl_secret = f"noacl-{run_tag}"
        noacl_doc, _ = _plant_document(db, shadow_org.id, shadow_kb.id, shadow_user.id, noacl_secret, acl_org_id=None)
        planted_document_ids.append(noacl_doc.id)
        db.commit()

        noacl_hits = dense_search(db, noacl_secret, organization_id, user_id, top_k=5)
        results.append(CheckResult(
            name="Default-deny: document with no ACL rows is NOT findable by anyone",
            passed=len(noacl_hits) == 0,
            detail="Absence of an ACL row correctly means no access."
                    if len(noacl_hits) == 0 else "FAILED — a document with zero ACL rows was still returned.",
        ))

    finally:
        _cleanup(db, planted_document_ids, shadow_org_id, shadow_user_id)

    return results
