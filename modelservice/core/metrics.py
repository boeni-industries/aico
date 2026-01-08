"""
Modelservice Metrics Instrumentation

Lightweight OpenTelemetry metrics for model inference tracking.
Records inference time, tokens generated, and success/failure.
"""

import time
from typing import Optional, Dict, Any
from contextlib import contextmanager

from opentelemetry import metrics

# Get OpenTelemetry meter for modelservice
meter = metrics.get_meter("aico.modelservice")

# Create metrics instruments
inference_duration = meter.create_histogram(
    name="aico.modelservice.inference.duration",
    description="Model inference duration in seconds",
    unit="s"
)

inference_counter = meter.create_counter(
    name="aico.modelservice.inference.count",
    description="Total number of model inferences",
    unit="1"
)

tokens_generated = meter.create_histogram(
    name="aico.modelservice.tokens.generated",
    description="Number of tokens generated per inference",
    unit="1"
)


@contextmanager
def track_inference(
    model_name: str,
    task_type: str = "completion",
    **extra_attributes
):
    """
    Context manager for tracking model inference metrics.
    
    Usage:
        with track_inference("llama-3.2-3b", task_type="completion") as tracker:
            result = model.generate(prompt)
            tracker.set_tokens(len(result.tokens))
            tracker.set_success(True)
    
    Args:
        model_name: Name of the model being used
        task_type: Type of task (completion, embedding, sentiment, etc.)
        **extra_attributes: Additional attributes to record
    """
    start_time = time.perf_counter()
    
    # Tracker state
    tracker_state = {
        "tokens": 0,
        "success": True,
        "error": None
    }
    
    class InferenceTracker:
        def set_tokens(self, count: int):
            tracker_state["tokens"] = count
        
        def set_success(self, success: bool):
            tracker_state["success"] = success
        
        def set_error(self, error: str):
            tracker_state["error"] = error
            tracker_state["success"] = False
    
    tracker = InferenceTracker()
    
    try:
        yield tracker
    finally:
        # Calculate duration
        duration = time.perf_counter() - start_time
        
        # Build attributes
        attributes = {
            "model.name": model_name,
            "task.type": task_type,
            "success": tracker_state["success"],
            **extra_attributes
        }
        
        # Record metrics
        inference_duration.record(duration, attributes)
        inference_counter.add(1, attributes)
        
        if tracker_state["tokens"] > 0:
            tokens_generated.record(tracker_state["tokens"], attributes)


def record_inference(
    model_name: str,
    duration_seconds: float,
    tokens: Optional[int] = None,
    success: bool = True,
    task_type: str = "completion",
    **extra_attributes
):
    """
    Record inference metrics directly (without context manager).
    
    Args:
        model_name: Name of the model
        duration_seconds: Inference duration in seconds
        tokens: Number of tokens generated (optional)
        success: Whether inference succeeded
        task_type: Type of task
        **extra_attributes: Additional attributes
    """
    attributes = {
        "model.name": model_name,
        "task.type": task_type,
        "success": success,
        **extra_attributes
    }
    
    inference_duration.record(duration_seconds, attributes)
    inference_counter.add(1, attributes)
    
    if tokens is not None:
        tokens_generated.record(tokens, attributes)
