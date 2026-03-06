"""
Message Bus Metrics Instrumentation

Tracks message bus event processing and performance.
"""

import time
from typing import Optional
from contextlib import contextmanager

from opentelemetry import metrics

_message_duration = None
_message_counter = None
_backlog_gauge = None


def _ensure_instruments():
    global _message_duration, _message_counter, _backlog_gauge

    if _message_duration is not None:
        return

    meter = metrics.get_meter("aico.messagebus")

    _message_duration = meter.create_histogram(
        name="aico.messagebus.message.duration",
        description="Message processing duration in seconds",
        unit="s",
    )
    _message_counter = meter.create_counter(
        name="aico.messagebus.message.count",
        description="Total number of messages processed",
        unit="1",
    )
    _backlog_gauge = meter.create_up_down_counter(
        name="aico.messagebus.backlog.depth",
        description="Current message backlog depth",
        unit="1",
    )


@contextmanager
def track_message(
    topic: str,
    **extra_attributes
):
    """
    Context manager for tracking message bus metrics.
    
    Usage:
        with track_message("conversation.input") as tracker:
            process_message(msg)
            tracker.set_backlog_depth(5)
            tracker.set_consumer_count(2)
    
    Args:
        topic: Message topic
        **extra_attributes: Additional attributes
    """
    start_time = time.perf_counter()
    
    tracker_state = {
        "backlog_depth": 0,
        "consumer_count": 0
    }
    
    class MessageTracker:
        def set_backlog_depth(self, depth: int):
            tracker_state["backlog_depth"] = depth
        
        def set_consumer_count(self, count: int):
            tracker_state["consumer_count"] = count
    
    tracker = MessageTracker()
    
    try:
        yield tracker
    finally:
        _ensure_instruments()
        duration = time.perf_counter() - start_time
        
        attributes = {
            "topic": topic,
            "backlog.depth": tracker_state["backlog_depth"],
            "consumer.count": tracker_state["consumer_count"],
            **extra_attributes
        }
        
        _message_duration.record(duration, attributes)
        _message_counter.add(1, attributes)


def record_message(
    topic: str,
    duration_seconds: float,
    backlog_depth: int = 0,
    consumer_count: int = 0,
    **extra_attributes
):
    """
    Record message bus metrics directly.
    
    Args:
        topic: Message topic
        duration_seconds: Processing duration in seconds
        backlog_depth: Current backlog depth
        consumer_count: Number of consumers
        **extra_attributes: Additional attributes
    """
    attributes = {
        "topic": topic,
        "backlog.depth": backlog_depth,
        "consumer.count": consumer_count,
        **extra_attributes
    }
    
    _ensure_instruments()
    _message_duration.record(duration_seconds, attributes)
    _message_counter.add(1, attributes)
