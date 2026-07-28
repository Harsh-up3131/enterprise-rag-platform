from datetime import datetime
from pydantic import BaseModel


class DocumentOut(BaseModel):
    id: str
    knowledge_base_id: str
    title: str
    source_type: str
    status: str
    sensitivity: str
    created_at: datetime
    # Finer-grained than `status` — drives the upload progress bar in the UI.
    # One of: pending | parsing | chunking | embedding | ready | failed | None
    ingestion_status: str | None = None

    class Config:
        from_attributes = True


class DocumentACLIn(BaseModel):
    principal_type: str  # user|group|role|organization
    principal_id: str
    permission: str = "read"


class DocumentACLOut(BaseModel):
    id: str
    principal_type: str
    principal_id: str
    permission: str

    class Config:
        from_attributes = True
