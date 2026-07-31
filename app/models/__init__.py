"""
Import every model module here so that a single `import app.models`
registers all tables on `Base.metadata` (needed by scripts/init_db.py and
by Alembic autogeneration in a later phase).
"""
from app.models.organization import Organization, Membership, Group, GroupMember
from app.models.user import User
from app.models.knowledge_base import KnowledgeBase
from app.models.document import Document, DocumentVersion, DocumentACL
from app.models.chunk import Chunk
from app.models.conversation import Conversation, Message, Citation
from app.models.trace import RetrievalTrace, QualitySummarySnapshot
from app.models.audit import AuditEvent

__all__ = [
    "Organization", "Membership", "Group", "GroupMember",
    "User",
    "KnowledgeBase",
    "Document", "DocumentVersion", "DocumentACL",
    "Chunk",
    "Conversation", "Message", "Citation",
    "RetrievalTrace",
    "QualitySummarySnapshot",
    "AuditEvent",
]
