"""Lightweight answer-quality monitoring helpers.

These helpers turn the existing RetrievalTrace rows into an interpretable
quality dashboard without requiring a heavy LLM judge dependency.
"""
from __future__ import annotations

from typing import Any


def summarize_trace_metrics(traces: list[dict[str, Any]]) -> dict[str, Any]:
    """Summarize recent query traces into a simple quality dashboard.

    Metrics are intentionally deterministic and cheap to compute so they can
    power a local dashboard or CI report without external services.
    """
    total_queries = len(traces)
    if not total_queries:
        return {
            "total_queries": 0,
            "abstention_rate": 0.0,
            "citation_success_rate": 0.0,
            "avg_latency_ms": 0.0,
            "answer_quality_score": 0.0,
            "recent_queries": [],
        }

    abstentions = sum(1 for trace in traces if trace.get("abstained"))
    successful_citations = sum(
        1 for trace in traces if not trace.get("abstained") and trace.get("selected_chunk_ids")
    )

    latencies = []
    for trace in traces:
        latency_values = trace.get("latency_ms", {})
        latencies.append(
            float(latency_values.get("lexical", 0.0) or 0.0)
            + float(latency_values.get("dense", 0.0) or 0.0)
            + float(latency_values.get("rerank", 0.0) or 0.0)
        )

    recent_queries = [
        {
            "query": trace.get("query"),
            "abstained": trace.get("abstained", False),
            "selected_chunk_ids": trace.get("selected_chunk_ids", []),
        }
        for trace in traces[-5:]
    ]

    return {
        "total_queries": total_queries,
        "abstention_rate": abstentions / total_queries,
        "citation_success_rate": successful_citations / total_queries,
        "avg_latency_ms": round(sum(latencies) / total_queries, 2),
        "answer_quality_score": round(
            (1.0 - (abstentions / total_queries)) * 0.7
            + (successful_citations / total_queries) * 0.3,
            4,
        ),
        "recent_queries": recent_queries,
    }
