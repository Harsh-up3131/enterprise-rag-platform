from app.services.evaluation.monitoring import summarize_trace_metrics


def test_quality_history_summarizes_recent_runs():
    history = [
        {"abstained": False, "selected_chunk_ids": ["a"], "latency_ms": {"lexical": 10.0, "dense": 5.0, "rerank": 2.0}, "query": "first"},
        {"abstained": True, "selected_chunk_ids": [], "latency_ms": {"lexical": 12.0, "dense": 6.0, "rerank": 2.0}, "query": "second"},
        {"abstained": False, "selected_chunk_ids": ["b"], "latency_ms": {"lexical": 14.0, "dense": 7.0, "rerank": 3.0}, "query": "third"},
    ]

    summary = summarize_trace_metrics(history)

    assert summary["total_queries"] == 3
    assert summary["abstention_rate"] == 1 / 3
    assert summary["citation_success_rate"] == 2 / 3
    assert summary["avg_latency_ms"] == 20.33
    assert summary["answer_quality_score"] == 0.6667
