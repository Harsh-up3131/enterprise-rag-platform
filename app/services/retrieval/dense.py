"""
Dense retrieval: pgvector cosine similarity over `chunks.embedding`.

Mirrors the same ACL join as lexical.py — dense retrieval is exactly as
permission-aware as lexical retrieval, not an afterthought.
"""
from dataclasses import dataclass

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.services.ingestion.embedder import embed_text


@dataclass
class Candidate:
    chunk_id: str
    score: float  # cosine similarity, higher is better


_DENSE_SQL = text("""
    SELECT c.id, 1 - (c.embedding <=> CAST(:query_embedding AS vector)) AS score
    FROM chunks c
    JOIN documents d ON d.id = c.document_id
    WHERE c.organization_id = :organization_id
      AND (CAST(:knowledge_base_id AS uuid) IS NULL OR d.knowledge_base_id = CAST(:knowledge_base_id AS uuid))
      AND EXISTS (
            SELECT 1 FROM document_acl acl
            WHERE acl.document_id = d.id
              AND (
                    (acl.principal_type = 'organization' AND acl.principal_id = CAST(:organization_id AS text))
                 OR (acl.principal_type = 'user' AND acl.principal_id = CAST(:user_id AS text))
                 OR (acl.principal_type = 'group' AND acl.principal_id IN (
                        SELECT group_id::text FROM group_members WHERE user_id = CAST(:user_id AS uuid)
                    ))
              )
      )
    ORDER BY c.embedding <=> CAST(:query_embedding AS vector) ASC
    LIMIT :top_k
""")


def dense_search(
    db: Session,
    query: str,
    organization_id: str,
    user_id: str,
    top_k: int,
    knowledge_base_id: str | None = None,
) -> list[Candidate]:
    query_embedding = embed_text(query)
    rows = db.execute(_DENSE_SQL, {
        "query_embedding": query_embedding,
        "organization_id": organization_id,
        "user_id": user_id,
        "knowledge_base_id": knowledge_base_id,
        "top_k": top_k,
    }).fetchall()
    return [Candidate(chunk_id=str(r[0]), score=float(r[1])) for r in rows]
