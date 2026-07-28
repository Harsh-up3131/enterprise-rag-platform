"""
Lexical retrieval: Postgres full-text search (`ts_rank`) over `chunks.search_vector`.

Authorization is enforced INSIDE this query (join to document_acl) rather
than filtering results afterward — per blueprint §4.3, unauthorized content
must never even be fetched, let alone reach the LLM context.
"""
from dataclasses import dataclass

from sqlalchemy import text
from sqlalchemy.orm import Session


@dataclass
class Candidate:
    chunk_id: str
    score: float


# NOTE(POC): ACL check here is simplified to "org member can read any
# document in their org, OR the document has an explicit ACL row granting
# this user/one of their groups/'organization' access". A production
# version would also weigh `role` and `sensitivity` explicitly.
_LEXICAL_SQL = text("""
    SELECT c.id, ts_rank(c.search_vector, plainto_tsquery('english', :query)) AS score
    FROM chunks c
    JOIN documents d ON d.id = c.document_id
    WHERE c.organization_id = :organization_id
      AND (CAST(:knowledge_base_id AS uuid) IS NULL OR d.knowledge_base_id = CAST(:knowledge_base_id AS uuid))
      AND c.search_vector @@ plainto_tsquery('english', :query)
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
    ORDER BY score DESC
    LIMIT :top_k
""")


def lexical_search(
    db: Session,
    query: str,
    organization_id: str,
    user_id: str,
    top_k: int,
    knowledge_base_id: str | None = None,
) -> list[Candidate]:
    rows = db.execute(_LEXICAL_SQL, {
        "query": query,
        "organization_id": organization_id,
        "user_id": user_id,
        "knowledge_base_id": knowledge_base_id,
        "top_k": top_k,
    }).fetchall()
    return [Candidate(chunk_id=str(r[0]), score=float(r[1])) for r in rows]
