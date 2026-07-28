"""
The query route: this is the main RAG endpoint tying retrieval and
generation together via services/query_service.py.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.core.deps import get_current_context, RequestContext
from app.schemas.query import QueryRequest, QueryResponse, CitationOut
from app.services.query_service import answer_question

router = APIRouter(prefix="/query", tags=["query"])


@router.post("", response_model=QueryResponse)
def ask(
    payload: QueryRequest,
    ctx: RequestContext = Depends(get_current_context),
    db: Session = Depends(get_db),
):
    try:
        result = answer_question(
            db,
            question=payload.question,
            organization_id=ctx.organization_id,
            user_id=ctx.user.id,
            knowledge_base_id=payload.knowledge_base_id,
            conversation_id=payload.conversation_id,
        )
    except ValueError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc))

    return QueryResponse(
        answer=result.answer,
        abstained=result.abstained,
        citations=[
            CitationOut(
                chunk_id=c.chunk_id,
                document_title=c.document_title,
                heading_path=c.heading_path,
                page=c.page,
                score=c.score,
            )
            for c in result.citations
        ],
        trace_id=result.trace_id,
        conversation_id=result.conversation_id,
    )
