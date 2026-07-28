"""
Smoke tests for pure-logic pieces that don't need a DB/LLM — good
candidates for fast CI. Retrieval SQL, ingestion, and generation are
integration-tested manually via the README's "Try the flow" walkthrough
for this POC; adding a docker-based pytest fixture DB is a natural next
step (see README "Next steps").
"""
from app.services.retrieval.fusion import reciprocal_rank_fusion
from app.services.retrieval import lexical, dense
from app.services.generation.citation_validator import extract_and_validate_citations
from app.services.retrieval.retriever import EvidenceItem


def test_rrf_prefers_items_ranked_highly_in_both_lists():
    lexical_candidates = [
        lexical.Candidate(chunk_id="a", score=0.9),
        lexical.Candidate(chunk_id="b", score=0.5),
        lexical.Candidate(chunk_id="c", score=0.3),
    ]
    dense_candidates = [
        dense.Candidate(chunk_id="b", score=0.95),
        dense.Candidate(chunk_id="a", score=0.4),
        dense.Candidate(chunk_id="d", score=0.2),
    ]

    fused = reciprocal_rank_fusion(lexical_candidates, dense_candidates, top_k=4)
    fused_ids = [c.chunk_id for c in fused]

    # 'a' and 'b' each appear near the top of both lists, so both should
    # outrank 'c' and 'd', which only appear in one list each.
    assert set(fused_ids[:2]) == {"a", "b"}
    assert "c" in fused_ids and "d" in fused_ids


def test_citation_validator_rejects_unknown_chunk_ids():
    evidence = [
        EvidenceItem(
            chunk_id="11111111-1111-1111-1111-111111111111",
            text="Deployments require a change ticket.",
            document_id="doc-1", document_title="Deployment SOP",
            heading_path="Release Process", page_start=3, score=0.8,
        )
    ]
    answer = (
        "Deployments require a change ticket [11111111-1111-1111-1111-111111111111]. "
        "Also the sky is blue [99999999-9999-9999-9999-999999999999]."
    )

    citations = extract_and_validate_citations(answer, evidence)
    statuses = {c.chunk_id: c.verification_status for c in citations}

    assert statuses["11111111-1111-1111-1111-111111111111"] == "verified"
    assert statuses["99999999-9999-9999-9999-999999999999"] == "rejected"
