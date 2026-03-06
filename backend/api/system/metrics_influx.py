"""
System Metrics Collection from InfluxDB

Provides comprehensive metrics for the Studio Metrics dashboard by querying
InfluxDB directly. Replaces PostgreSQL-based metrics with InfluxDB Flux queries.

All metrics are sourced from OpenTelemetry exporters writing to InfluxDB:
- API Gateway performance metrics (api_request measurement)
- Modelservice inference metrics (model_inference measurement)
- Memory system metrics (memory_query measurement)
- Task scheduler metrics (scheduler_job measurement)
- Message bus metrics (messagebus_event measurement)
"""

import time
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import statistics

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from aico.core.logging import get_logger

logger = get_logger("backend.api.system.metrics_influx")

router = APIRouter(prefix="/metrics", tags=["metrics"])


# Response Models (same as before)
class MetricValue(BaseModel):
    """Single metric value with metadata."""
    value: float
    unit: str
    trend: Optional[float] = None
    status: str = "healthy"
    sparkline_data: Optional[List[float]] = None
    avg_1h: Optional[float] = None
    avg_24h: Optional[float] = None
    avg_7d: Optional[float] = None


class GatewayMetrics(BaseModel):
    """API Gateway performance metrics."""
    requests_per_second: MetricValue
    avg_response_time: MetricValue
    p95_response_time: MetricValue
    p99_response_time: MetricValue
    error_rate: MetricValue
    success_rate: MetricValue
    total_requests_24h: int
    status_code_distribution: Dict[str, int]
    top_endpoints: List[Dict[str, Any]]
    protocol_distribution: Dict[str, int]


# Helper functions
def calculate_trend(current: float, previous: float) -> float:
    """Calculate percentage trend."""
    if previous == 0:
        return 0.0
    return ((current - previous) / previous) * 100


def get_metric_status(value: float, thresholds: Dict[str, float]) -> str:
    """Determine metric status based on thresholds."""
    if value >= thresholds.get("critical", float("inf")):
        return "critical"
    elif value >= thresholds.get("warning", float("inf")):
        return "warning"
    return "healthy"


def calculate_percentile(values: List[float], percentile: float) -> float:
    """Calculate percentile from list of values."""
    if not values:
        return 0.0
    sorted_values = sorted(values)
    index = int(len(sorted_values) * percentile)
    return sorted_values[min(index, len(sorted_values) - 1)]


# API Endpoints
@router.get("/gateway", response_model=GatewayMetrics)
async def get_gateway_metrics():
    raise HTTPException(
        status_code=410,
        detail="InfluxDB-backed system metrics have been retired; use /metrics/* Prometheus-backed endpoints",
    )
