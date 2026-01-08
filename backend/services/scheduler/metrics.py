"""
Scheduler Metrics Instrumentation

Tracks job execution performance for the task scheduler.
"""

import time
from typing import Optional
from contextlib import contextmanager

from opentelemetry import metrics

# Get OpenTelemetry meter
meter = metrics.get_meter("aico.scheduler")

# Create metrics instruments
job_duration = meter.create_histogram(
    name="aico.scheduler.job.duration",
    description="Scheduler job execution duration in seconds",
    unit="s"
)

job_counter = meter.create_counter(
    name="aico.scheduler.job.count",
    description="Total number of scheduler jobs executed",
    unit="1"
)


@contextmanager
def track_job(
    job_type: str,
    queue_name: str = "default",
    **extra_attributes
):
    """
    Context manager for tracking scheduler job metrics.
    
    Usage:
        with track_job("maintenance.database_vacuum", queue_name="maintenance") as tracker:
            perform_vacuum()
            tracker.set_success(True)
    
    Args:
        job_type: Type of job (e.g., "maintenance.database_vacuum")
        queue_name: Queue name
        **extra_attributes: Additional attributes
    """
    start_time = time.perf_counter()
    
    tracker_state = {
        "success": True,
        "error": None
    }
    
    class JobTracker:
        def set_success(self, success: bool):
            tracker_state["success"] = success
        
        def set_error(self, error: str):
            tracker_state["error"] = error
            tracker_state["success"] = False
    
    tracker = JobTracker()
    
    try:
        yield tracker
    finally:
        duration = time.perf_counter() - start_time
        
        attributes = {
            "job.type": job_type,
            "queue.name": queue_name,
            "success": tracker_state["success"],
            **extra_attributes
        }
        
        job_duration.record(duration, attributes)
        job_counter.add(1, attributes)


def record_job(
    job_type: str,
    duration_seconds: float,
    success: bool = True,
    queue_name: str = "default",
    error_message: Optional[str] = None,
    **extra_attributes
):
    """
    Record scheduler job metrics directly.
    
    Args:
        job_type: Type of job
        duration_seconds: Job duration in seconds
        success: Whether job succeeded
        queue_name: Queue name
        error_message: Error message if failed
        **extra_attributes: Additional attributes
    """
    attributes = {
        "job.type": job_type,
        "queue.name": queue_name,
        "success": success,
        **extra_attributes
    }
    
    if error_message:
        attributes["error.message"] = error_message
    
    job_duration.record(duration_seconds, attributes)
    job_counter.add(1, attributes)
