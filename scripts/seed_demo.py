"""
Seeds a demo organization + user so you can immediately try the API
without going through /auth/signup manually.

Usage:
    python scripts/seed_demo.py
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import SessionLocal
from app.models import User, Organization, Membership, KnowledgeBase
from app.core.security import hash_password

DEMO_EMAIL = "demo@ekip.local"
DEMO_PASSWORD = "demo-password-123"


def main():
    db = SessionLocal()
    try:
        existing = db.query(User).filter(User.email == DEMO_EMAIL).first()
        if existing:
            print(f"Demo user already exists: {DEMO_EMAIL}")
            return

        user = User(email=DEMO_EMAIL, hashed_password=hash_password(DEMO_PASSWORD), display_name="Demo User")
        db.add(user)
        db.flush()

        org = Organization(name="Demo Org", slug="demo-org")
        db.add(org)
        db.flush()

        db.add(Membership(user_id=user.id, organization_id=org.id, role="owner"))

        kb = KnowledgeBase(organization_id=org.id, name="General Knowledge Base",
                            description="Default KB created by seed script")
        db.add(kb)
        db.commit()

        print("Seeded demo data:")
        print(f"  email:    {DEMO_EMAIL}")
        print(f"  password: {DEMO_PASSWORD}")
        print(f"  org_id:   {org.id}")
        print(f"  kb_id:    {kb.id}")
        print("Login via POST /auth/login to get a JWT, then use kb_id for uploads/queries.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
