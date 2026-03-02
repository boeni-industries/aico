"""
Memory System Metrics Instrumentation

Tracks memory query performance across working, episodic, and semantic memory.
"""

import time
from typing import Optional
from contextlib import contextmanager

from opentelemetry import metrics

_query_duration = None
_query_counter = None
_results_count = None


def _ensure_instruments():
    global _query_duration, _query_counter, _results_count

    if _query_duration is not None:
        return

    meter = metrics.get_meter("aico.memory")

    _query_duration = meter.create_histogram(
        name="aico.memory.query.duration",
        description="Memory query duration in seconds",
        unit="s",
    )
    _query_counter = meter.create_counter(
        name="aico.memory.query.count",
        description="Total number of memory queries",
        unit="1",
    )
    _results_count = meter.create_histogram(
        name="aico.memory.results.count",
        description="Number of results returned from memory query",
        unit="1",
    )


@contextmanager
def track_query(
    query_type: str,
    memory_layer: str = "unknown",
    **extra_attributes
):
    """
    Context manager for tracking memory query metrics.
    
    Usage:
        with track_query("semantic_search", memory_layer="semantic") as tracker:
            results = semantic_memory.search(query)
            tracker.set_results_count(len(results))
            tracker.set_success(True)
    
    Args:
        query_type: Type of query (semantic_search, episodic_retrieval, working_context, etc.)
        memory_layer: Memory layer (working, episodic, semantic)
        **extra_attributes: Additional attributes
    """
    start_time = time.perf_counter()
    
    tracker_state = {
        "results_count": 0,
        "success": True
    }
    
    class QueryTracker:
        def set_results_count(self, count: int):
            tracker_state["results_count"] = count
        
        def set_success(self, success: bool):
            tracker_state["success"] = success
    
    tracker = QueryTracker()
    
    try:
        yield tracker
    finally:
        _ensure_instruments()
        duration = time.perf_counter() - start_time
        
        attributes = {
            "query.type": query_type,
            "memory.layer": memory_layer,
            "success": tracker_state["success"],
            **extra_attributes
        }
        
        _query_duration.record(duration, attributes)
        _query_counter.add(1, attributes)
        _results_count.record(tracker_state["results_count"], attributes)


def record_query(
    query_type: str,
    duration_seconds: float,
    results_count_value: int = 0,
    success: bool = True,
    memory_layer: str = "unknown",
    **extra_attributes
):
    """
    Record memory query metrics directly.
    
    Args:
        query_type: Type of query
        duration_seconds: Query duration in seconds
        results_count_value: Number of results returned
        success: Whether query succeeded
        memory_layer: Memory layer
        **extra_attributes: Additional attributes
    """
    attributes = {
        "query.type": query_type,
        "memory.layer": memory_layer,
        "success": success,
        **extra_attributes
    }
    
    _ensure_instruments()
    _query_duration.record(duration_seconds, attributes)
    _query_counter.add(1, attributes)
    _results_count.record(results_count_value, attributes)
