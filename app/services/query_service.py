"""
Query orchestration: implements the full query flow from blueprint §8.2 —
guardrails -> retrieval -> evidence sufficiency check -> generation ->
citation validation -> output guardrails -> trace persistence.

This is the single place that stitches together retrieval + generation so
routes stay thin and the flow is testable independent of FastAPI.
"""
from dataclasses import dataclass

from langsmith import traceable
from sqlalchemy.orm import Session

from app.config import settings
from app.models import RetrievalTrace, Conversation, Message, Citation
from app.services.retrieval.retriever import retrieve
from app.services.generation.prompt import build_prompt
from app.services.generation.llm_client import generate
from app.services.generation.citation_validator import extract_and_validate_citations, strip_citation_tags
from app.services.generation import guardrails

ABSTENTION_MESSAGE = (
    "I don't have enough reliable evidence in the connected knowledge base "
    "to answer that confidently. Try rephrasing, or check that the relevant "
    "documents have been uploaded and finished indexing."
)


@dataclass
class AnswerResult:
    answer: str
    abstained: bool
    citations: list
    trace_id: str
    conversation_id: str


@traceable(name="answer_question", run_type="chain")
def answer_question(
    db: Session,
    question: str,
    organization_id: str,
    user_id: str,
    knowledge_base_id: str | None = None,
    conversation_id: str | None = None,
) -> AnswerResult:
    ok, reason = guardrails.check_input(question)
    if not ok:
        raise ValueError(reason)

    if conversation_id:
        conversation = db.get(Conversation, conversation_id)
    else:
        conversation = Conversation(organization_id=organization_id, user_id=user_id, title=question[:80])
        db.add(conversation)
        db.flush()

    result = retrieve(db, question, organization_id, user_id, knowledge_base_id)

    abstained = result.top_score < settings.min_evidence_score or not result.evidence
    validated_citations = []

    if abstained:
        answer_text = ABSTENTION_MESSAGE
    else:
        system_prompt, user_prompt = build_prompt(question, result.evidence)
        raw_answer = generate(system_prompt, user_prompt)

        ok, reason = guardrails.check_output(raw_answer)
        if not ok:
            abstained = True
            answer_text = ABSTENTION_MESSAGE
        else:
            validated_citations = extract_and_validate_citations(raw_answer, result.evidence)
            answer_text = strip_citation_tags(raw_answer)
            # Safe-abstention fallback: a grounded-generation answer with zero
            # verified citations is treated as insufficiently evidenced.
            if not any(c.verification_status == "verified" for c in validated_citations):
                abstained = True
                answer_text = ABSTENTION_MESSAGE

    trace = RetrievalTrace(
        organization_id=organization_id,
        user_id=user_id,
        query=question,
        normalized_query=question.strip().lower(),
        retriever_config_version=settings.retriever_config_version,
        lexical_candidates=result.stage_data.get("lexical_candidates", []),
        dense_candidates=result.stage_data.get("dense_candidates", []),
        fused_candidates=result.stage_data.get("fused_candidates", []),
        reranked_candidates=result.stage_data.get("reranked_candidates", []),
        selected_chunk_ids=[c.chunk_id for c in validated_citations if c.verification_status == "verified"],
        abstained=abstained,
        top_evidence_score=result.top_score,
        latency_ms=result.latency_ms,
    )
    db.add(trace)
    db.flush()

    message = Message(
        conversation_id=conversation.id,
        role="assistant",
        content=answer_text,
        trace_id=trace.trace_id,
        abstained=abstained,
    )
    db.add(message)
    db.flush()

    for c in validated_citations:
        if c.verification_status == "verified":
            db.add(Citation(
                message_id=message.id,
                chunk_id=c.chunk_id,
                quoted_span=None,
                page=c.page,
                score=c.score,
                verification_status=c.verification_status,
            ))

    db.commit()

    return AnswerResult(
        answer=answer_text,
        abstained=abstained,
        citations=[c for c in validated_citations if c.verification_status == "verified"],
        trace_id=trace.trace_id,
        conversation_id=conversation.id,
    )
