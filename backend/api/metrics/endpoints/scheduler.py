"""
Task Scheduler Metrics Endpoint

Provides metrics for the task scheduler including:
- Job execution statistics
- Success/failure rates
- Queue utilization
- Job type distribution
- Recent failures

Metrics sourced from Prometheus (OpenTelemetry-exported metrics).
"""

from fastapi import APIRouter

from ..models import SchedulerMetrics, MetricValue
from ..prometheus_client import PrometheusClient, prom_label_values, prom_scalar
from aico.core.logging import get_logger

logger = get_logger("backend.api.metrics.scheduler")

router = APIRouter()


@router.get("/scheduler", response_model=SchedulerMetrics)
async def get_scheduler_metrics():
    """Get task scheduler metrics from Prometheus."""
    try:
        prom = PrometheusClient()
        base_selector = '{job="aico-backend"}'

        jobs_today = await prom_scalar(prom, f"sum(increase(aico_scheduler_job_count_total{base_selector}[24h]))")
        successful_jobs = await prom_scalar(
            prom,
            f"sum(increase(aico_scheduler_job_count_total{base_selector},success=\"true\"[24h]))",
        )
        failed_jobs = max(0.0, jobs_today - successful_jobs)
        success_rate = round((successful_jobs / jobs_today * 100.0), 1) if jobs_today > 0 else 100.0

        avg_duration_s = await prom_scalar(
            prom,
            "(" \
            f"sum(increase(aico_scheduler_job_duration_seconds_sum{base_selector}[24h]))" \
            "/" \
            f"sum(increase(aico_scheduler_job_duration_seconds_count{base_selector}[24h]))" \
            ")",
        )

        job_type_distribution_f = await prom_label_values(
            prom,
            f"sum by (job_type) (increase(aico_scheduler_job_count_total{base_selector}[24h]))",
            label="job_type",
        )
        job_type_distribution = {k: int(v) for k, v in job_type_distribution_f.items()}

        queue_distribution_f = await prom_label_values(
            prom,
            f"sum by (queue_name) (increase(aico_scheduler_job_count_total{base_selector}[24h]))",
            label="queue_name",
        )
        total_queue = sum(queue_distribution_f.values())
        queue_utilization = {
            k: round((v / total_queue * 100.0), 1) if total_queue > 0 else 0.0
            for k, v in queue_distribution_f.items()
        }

        return SchedulerMetrics(
            jobs_today=MetricValue(value=float(jobs_today), unit="jobs", status="healthy"),
            success_rate=MetricValue(
                value=float(success_rate),
                unit="%",
                status="healthy" if success_rate > 95 else "warning",
            ),
            failed_jobs=MetricValue(value=float(failed_jobs), unit="jobs", status="healthy"),
            avg_job_duration=MetricValue(value=round(float(avg_duration_s), 2), unit="s", status="healthy"),
            queue_utilization=queue_utilization,
            job_type_distribution=job_type_distribution,
            failed_job_reasons=[],
        )
    
    except Exception as e:
        logger.debug(f"Prometheus query failed (likely no data yet), returning zero metrics: {e}")
        
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
