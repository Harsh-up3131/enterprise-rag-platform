from pydantic import BaseModel


class QueryRequest(BaseModel):
    question: str
    knowledge_base_id: str | None = None  # None = search all KBs the user can access
    conversation_id: str | None = None


class CitationOut(BaseModel):
    chunk_id: str
    document_title: str
    heading_path: str | None = None
    page: int | None = None
    quoted_span: str | None = None
    score: float | None = None


class QueryResponse(BaseModel):
    answer: str
    abstained: bool
    citations: list[CitationOut]
    trace_id: str
    conversation_id: str
