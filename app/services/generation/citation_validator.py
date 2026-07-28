"""
Citation validation: extracts [chunk_id] tags the model emitted and checks
each one against the evidence pack that was actually provided. A claim
citing a chunk_id that wasn't in the evidence pack is a hallucinated
citation and is flagged "rejected" rather than trusted — the LLM cannot
be trusted to self-report which citations are real.
"""
import re
from dataclasses import dataclass

from app.services.retrieval.retriever import EvidenceItem

_CITATION_RE = re.compile(r"\[([0-9a-fA-F-]{36})\]")  # UUID chunk_id tags


@dataclass
class ValidatedCitation:
    chunk_id: str
    document_title: str
    heading_path: str | None
    page: int | None
    score: float
    verification_status: str  # "verified" | "rejected"


def extract_and_validate_citations(
    answer_text: str,
    evidence: list[EvidenceItem],
) -> list[ValidatedCitation]:
    evidence_by_id = {item.chunk_id: item for item in evidence}
    seen: set[str] = set()
    results: list[ValidatedCitation] = []

    for match in _CITATION_RE.finditer(answer_text):
        chunk_id = match.group(1)
        if chunk_id in seen:
            continue
        seen.add(chunk_id)

        item = evidence_by_id.get(chunk_id)
        if item is None:
            # Model cited a chunk_id that was never in the evidence pack —
            # reject rather than surface a fabricated source to the user.
            results.append(ValidatedCitation(
                chunk_id=chunk_id, document_title="unknown", heading_path=None,
                page=None, score=0.0, verification_status="rejected",
            ))
            continue

        results.append(ValidatedCitation(
            chunk_id=item.chunk_id,
            document_title=item.document_title,
            heading_path=item.heading_path,
            page=item.page_start,
            score=item.score,
            verification_status="verified",
        ))

    return results


def strip_citation_tags(answer_text: str) -> str:
    """Optional: produce a clean display string without inline [uuid] tags,
    for UIs that render citations as separate footnote chips instead."""
    return _CITATION_RE.sub("", answer_text).strip()
