"""
Tenant-isolation integration test.

Unlike tests/test_retrieval.py, this needs a REAL Postgres with pgvector —
the ACL joins and vector similarity queries can't run against SQLite/mocks.
Run it against the docker-compose stack:

    docker compose exec api python scripts/init_db.py   # if not already run
    docker compose exec api pytest tests/test_tenant_isolation.py -v

This exercises the exact same code path as the "Run isolation check" button
in the Security tab of the frontend (app/services/security/tenant_isolation_check.py)
— this file is here so the same guarantee is enforced in CI, not just
available as a manual UI action.
"""
import uuid

import pytest
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import Organization, User, Membership, KnowledgeBase
from app.core.security import hash_password
from app.services.security.tenant_isolation_check import run_isolation_check


@pytest.fixture
def db():
    session = SessionLocal()
    yield session
    session.close()


@pytest.fixture
def org_with_kb(db: Session):
    """A throwaway org + owner + knowledge base to run the check as."""
    tag = uuid.uuid4().hex[:8]
    org = Organization(name=f"test-org-{tag}", slug=f"test-org-{tag}")
    db.add(org)
    db.flush()

    user = User(email=f"test-{tag}@internal.invalid", hashed_password=hash_password("x"))
    db.add(user)
    db.flush()
    db.add(Membership(user_id=user.id, organization_id=org.id, role="owner"))

    kb = KnowledgeBase(organization_id=org.id, name="test-kb")
    db.add(kb)
    db.commit()

    yield org, user, kb

    # cleanup
    db.query(Membership).filter(Membership.organization_id == org.id).delete()
    db.query(KnowledgeBase).filter(KnowledgeBase.organization_id == org.id).delete()
    db.query(Organization).filter(Organization.id == org.id).delete()
    db.query(User).filter(User.id == user.id).delete()
    db.commit()


def test_tenant_isolation_all_checks_pass(db: Session, org_with_kb):
    org, user, kb = org_with_kb

    results = run_isolation_check(db, org.id, user.id, kb.id)

    by_name = {r.name: r for r in results}
    assert len(results) == 3, "Expected all three isolation checks to run"

    for result in results:
        assert result.passed, f"SECURITY FAILURE — {result.name}: {result.detail}"

    # Sanity: the positive control specifically must be the reason the other
    # two checks are meaningful (a search that finds nothing "passes"
    # isolation trivially and dishonestly).
    assert any("Positive control" in name for name in by_name)
