from app.services.evaluation.monitoring import summarize_trace_metrics


def test_summarize_trace_metrics_returns_quality_dashboard():
    traces = [
        {
            "abstained": False,
            "selected_chunk_ids": ["chunk-1"],
            "latency_ms": {"lexical": 100.0, "dense": 50.0},
            "query": "What is the policy?",
        },
        {
            "abstained": True,
            "selected_chunk_ids": [],
            "latency_ms": {"lexical": 80.0, "dense": 20.0},
            "query": "What about security?",
        },
    ]

    summary = summarize_trace_metrics(traces)

    assert summary["total_queries"] == 2
    assert summary["abstention_rate"] == 0.5
    assert summary["citation_success_rate"] == 0.5
    assert summary["avg_latency_ms"] == 125.0
    assert summary["answer_quality_score"] == 0.5
    assert summary["recent_queries"][0]["query"] == "What is the policy?"
