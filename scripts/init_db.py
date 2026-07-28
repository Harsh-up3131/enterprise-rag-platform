"""
Initializes the database: enables the pgvector extension and creates all
tables via SQLAlchemy metadata. POC uses `create_all` for speed; a
production system should switch to Alembic migrations (see README "Next
steps") so schema changes are versioned and reversible.

Usage:
    python scripts/init_db.py
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text

from app.database import engine, Base
import app.models  # noqa: F401 - registers all models on Base.metadata


def main():
    with engine.begin() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
    Base.metadata.create_all(bind=engine)
    print("Database initialized: pgvector extension enabled, tables created.")


if __name__ == "__main__":
    main()
