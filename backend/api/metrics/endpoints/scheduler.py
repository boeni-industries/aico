"""
Task Scheduler Metrics Endpoint

Provides metrics for the task scheduler including:
- Job execution statistics
- Success/failure rates
- Queue utilization
- Job type distribution
- Recent failures

Metrics sourced from InfluxDB (scheduler_job measurement).
"""

from fastapi import APIRouter, HTTPException

from ..models import SchedulerMetrics, MetricValue
from ..influx_client import MetricsInfluxClient
from aico.core.logging import get_logger

logger = get_logger("backend.api.metrics.scheduler")

router = APIRouter()


@router.get("/scheduler", response_model=SchedulerMetrics)
async def get_scheduler_metrics():
    """Get task scheduler metrics from InfluxDB."""
    try:
        with MetricsInfluxClient() as client:
            # Jobs executed in last 24h - use duration_ms_f field and group before counting
            jobs_query = '''
                from(bucket: "aico_telemetry")
                |> range(start: -24h)
                |> filter(fn: (r) => r._measurement == "scheduler_job")
                |> filter(fn: (r) => r.service == "aico-backend")
                |> filter(fn: (r) => r._field == "duration_ms_f")
                |> group()
                |> count()
            '''
            jobs_results = client.query(jobs_query)
            jobs_today = jobs_results[0].get('value', 0) if jobs_results else 0
            
            # Success rate - count successful jobs (where success_b == true)
            success_query = '''
                from(bucket: "aico_telemetry")
                |> range(start: -24h)
                |> filter(fn: (r) => r._measurement == "scheduler_job")
                |> filter(fn: (r) => r.service == "aico-backend")
                |> filter(fn: (r) => r._field == "success_b")
                |> filter(fn: (r) => r._value == true)
                |> group()
                |> count()
            '''
            success_results = client.query(success_query)
            successful_jobs = success_results[0].get('value', 0) if success_results else 0
            success_rate = round((successful_jobs / jobs_today * 100), 1) if jobs_today > 0 else 100.0
            
            # Average job duration
            avg_query = '''
                from(bucket: "aico_telemetry")
                |> range(start: -24h)
                |> filter(fn: (r) => r._measurement == "scheduler_job")
                |> filter(fn: (r) => r.service == "aico-backend")
                |> filter(fn: (r) => r._field == "duration_ms_f")
                |> mean()
            '''
            avg_results = client.query(avg_query)
            avg_duration = avg_results[0].get('value', 0) if avg_results else 0
            
            # Job type distribution (top 10)
            job_distribution = client.group_count("scheduler_job", "job_type", "-24h", {"service": "aico-backend"}, limit=10)
            
            # Queue utilization by queue name
            queue_distribution = client.group_count("scheduler_job", "queue_name", "-24h", {"service": "aico-backend"})
            queue_utilization = {queue: round(count / 100, 1) for queue, count in queue_distribution.items()}
            
            return SchedulerMetrics(
                jobs_today=MetricValue(value=jobs_today, unit="jobs", status="healthy"),
                success_rate=MetricValue(value=success_rate, unit="%", status="healthy" if success_rate > 95 else "warning"),
                failed_jobs=MetricValue(value=jobs_today - successful_jobs, unit="jobs", status="healthy"),
                avg_job_duration=MetricValue(value=round(avg_duration / 1000, 2) if avg_duration else 0, unit="s", status="healthy"),
                queue_utilization=queue_utilization,
                job_type_distribution=job_distribution,
                failed_job_reasons=[]
            )
    
    except Exception as e:
        # If InfluxDB is empty or has no data, return zero metrics instead of failing
        logger.debug(f"InfluxDB query failed (likely no data yet), returning zero metrics: {e}")
        
        # Return empty/zero metrics
        return SchedulerMetrics(
            jobs_today=MetricValue(value=0, unit="jobs", status="healthy"),
            success_rate=MetricValue(value=100.0, unit="%", status="healthy"),
            failed_jobs=MetricValue(value=0, unit="jobs", status="healthy"),
            avg_job_duration=MetricValue(value=0.0, unit="s", status="healthy"),
            queue_utilization={},
            job_type_distribution={},
            failed_job_reasons=[]
        )
