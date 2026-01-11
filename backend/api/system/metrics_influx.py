"""
System Metrics Collection from InfluxDB

Provides comprehensive metrics for the Studio Metrics dashboard by querying
InfluxDB directly. Replaces LibSQL-based metrics with InfluxDB Flux queries.

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

from aico.data.influx.connection import InfluxDBConnection
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
    """Get API Gateway performance metrics from InfluxDB."""
    
    try:
        conn = InfluxDBConnection()
        
        # Total requests in last 24h
        query_24h = '''
            from(bucket: "aico_telemetry")
            |> range(start: -24h)
            |> filter(fn: (r) => r._measurement == "api_request")
            |> filter(fn: (r) => r.service == "aico-backend")
            |> count()
        '''
        results = conn.query(query_24h)
        total_requests_24h = sum(r.get('value', 0) for r in results)
        
        # Requests per second (last 1 minute)
        query_rps = '''
            from(bucket: "aico_telemetry")
            |> range(start: -1m)
            |> filter(fn: (r) => r._measurement == "api_request")
            |> filter(fn: (r) => r.service == "aico-backend")
            |> count()
        '''
        results = conn.query(query_rps)
        recent_requests = sum(r.get('value', 0) for r in results)
        requests_per_second = recent_requests / 60.0
        
        # RPS sparkline (last 12 minutes, 1-minute intervals)
        rps_sparkline = []
        for i in range(12):
            start_offset = 12 - i
            end_offset = 11 - i
            query = f'''
                from(bucket: "aico_telemetry")
                |> range(start: -{start_offset}m, stop: -{end_offset}m)
                |> filter(fn: (r) => r._measurement == "api_request")
                |> filter(fn: (r) => r.service == "aico-backend")
                |> count()
            '''
            results = conn.query(query)
            count = sum(r.get('value', 0) for r in results)
            rps_sparkline.append(count / 60.0)
        
        # Average response time (last 1 minute)
        query_latency = '''
            from(bucket: "aico_telemetry")
            |> range(start: -1m)
            |> filter(fn: (r) => r._measurement == "api_request")
            |> filter(fn: (r) => r.service == "aico-backend")
            |> filter(fn: (r) => r._field == "latency_ms_f")
            |> mean()
        '''
        results = conn.query(query_latency)
        avg_response_time = results[0].get('value', 0.0) if results else 0.0
        
        # Latency sparkline (last 12 minutes)
        latency_sparkline = []
        for i in range(12):
            start_offset = 12 - i
            end_offset = 11 - i
            query = f'''
                from(bucket: "aico_telemetry")
                |> range(start: -{start_offset}m, stop: -{end_offset}m)
                |> filter(fn: (r) => r._measurement == "api_request")
                |> filter(fn: (r) => r.service == "aico-backend")
                |> filter(fn: (r) => r._field == "latency_ms_f")
                |> mean()
            '''
            results = conn.query(query)
            latency_sparkline.append(results[0].get('value', 0.0) if results else 0.0)
        
        # P95 and P99 latencies (last 24h)
        query_latencies = '''
            from(bucket: "aico_telemetry")
            |> range(start: -24h)
            |> filter(fn: (r) => r._measurement == "api_request")
            |> filter(fn: (r) => r.service == "aico-backend")
            |> filter(fn: (r) => r._field == "latency_ms_f")
        '''
        results = conn.query(query_latencies)
        latencies = [r.get('value', 0.0) for r in results]
        p95_response_time = calculate_percentile(latencies, 0.95)
        p99_response_time = calculate_percentile(latencies, 0.99)
        
        # Status code distribution (last 24h)
        query_status = '''
            from(bucket: "aico_telemetry")
            |> range(start: -24h)
            |> filter(fn: (r) => r._measurement == "api_request")
            |> filter(fn: (r) => r.service == "aico-backend")
            |> filter(fn: (r) => r._field == "status_code_i")
            |> group(columns: ["status_class"])
            |> count()
        '''
        results = conn.query(query_status)
        status_distribution = {}
        for r in results:
            status_class = r.get('status_class', 'other')
            count = r.get('value', 0)
            status_distribution[status_class] = status_distribution.get(status_class, 0) + count
        
        # Error rate (last 1 minute)
        # Count total and 4xx/5xx separately
        query_errors = '''
            from(bucket: "aico_telemetry")
            |> range(start: -1m)
            |> filter(fn: (r) => r._measurement == "api_request")
            |> filter(fn: (r) => r.service == "aico-backend")
            |> filter(fn: (r) => r.status_class == "4xx" or r.status_class == "5xx")
            |> count()
        '''
        results = conn.query(query_errors)
        error_count = sum(r.get('value', 0) for r in results)
        error_rate = (error_count / recent_requests * 100) if recent_requests > 0 else 0.0
        success_rate = 100.0 - error_rate
        
        # Error rate sparkline
        error_rate_sparkline = []
        for i in range(12):
            start_offset = 12 - i
            end_offset = 11 - i
            
            # Total requests in interval
            query_total = f'''
                from(bucket: "aico_telemetry")
                |> range(start: -{start_offset}m, stop: -{end_offset}m)
                |> filter(fn: (r) => r._measurement == "api_request")
                |> filter(fn: (r) => r.service == "aico-backend")
                |> count()
            '''
            total_results = conn.query(query_total)
            interval_total = sum(r.get('value', 0) for r in total_results)
            
            # Error requests in interval
            query_errors_interval = f'''
                from(bucket: "aico_telemetry")
                |> range(start: -{start_offset}m, stop: -{end_offset}m)
                |> filter(fn: (r) => r._measurement == "api_request")
                |> filter(fn: (r) => r.service == "aico-backend")
                |> filter(fn: (r) => r.status_class == "4xx" or r.status_class == "5xx")
                |> count()
            '''
            error_results = conn.query(query_errors_interval)
            interval_errors = sum(r.get('value', 0) for r in error_results)
            
            interval_error_rate = (interval_errors / interval_total * 100) if interval_total > 0 else 0.0
            error_rate_sparkline.append(interval_error_rate)
        
        # Top endpoints (last 24h)
        query_endpoints = '''
            from(bucket: "aico_telemetry")
            |> range(start: -24h)
            |> filter(fn: (r) => r._measurement == "api_request")
            |> filter(fn: (r) => r.service == "aico-backend")
            |> group(columns: ["path"])
            |> count()
            |> sort(desc: true)
            |> limit(n: 5)
        '''
        results = conn.query(query_endpoints)
        top_endpoints = []
        for r in results:
            path = r.get('path', 'unknown')
            requests = r.get('value', 0)
            
            # Get avg latency for this path
            query_path_latency = f'''
                from(bucket: "aico_telemetry")
                |> range(start: -24h)
                |> filter(fn: (r) => r._measurement == "api_request")
                |> filter(fn: (r) => r.service == "aico-backend")
                |> filter(fn: (r) => r.path == "{path}")
                |> filter(fn: (r) => r._field == "latency_ms_f")
                |> mean()
            '''
            latency_results = conn.query(query_path_latency)
            avg_latency = latency_results[0].get('value', 0.0) if latency_results else 0.0
            
            top_endpoints.append({
                "path": path,
                "requests": requests,
                "avg_latency": round(avg_latency, 2),
                "error_rate": 0.0  # Would need separate query
            })
        
        # Protocol distribution (last 24h)
        query_protocol = '''
            from(bucket: "aico_telemetry")
            |> range(start: -24h)
            |> filter(fn: (r) => r._measurement == "api_request")
            |> filter(fn: (r) => r.service == "aico-backend")
            |> group(columns: ["protocol"])
            |> count()
        '''
        results = conn.query(query_protocol)
        protocol_distribution = {}
        for r in results:
            protocol = r.get('protocol', 'unknown')
            count = r.get('value', 0)
            protocol_distribution[protocol] = count
        
        conn.close()
        
        return GatewayMetrics(
            requests_per_second=MetricValue(
                value=round(requests_per_second, 2),
                unit="req/s",
                trend=0.0,
                status="healthy" if requests_per_second < 1000 else "warning",
                sparkline_data=rps_sparkline
            ),
            avg_response_time=MetricValue(
                value=round(avg_response_time, 2),
                unit="ms",
                trend=0.0,
                status=get_metric_status(avg_response_time, {"warning": 500, "critical": 1000}),
                sparkline_data=latency_sparkline
            ),
            p95_response_time=MetricValue(
                value=round(p95_response_time, 2),
                unit="ms",
                trend=0.0,
                status=get_metric_status(p95_response_time, {"warning": 1000, "critical": 2000})
            ),
            p99_response_time=MetricValue(
                value=round(p99_response_time, 2),
                unit="ms",
                trend=0.0,
                status=get_metric_status(p99_response_time, {"warning": 2000, "critical": 5000})
            ),
            error_rate=MetricValue(
                value=round(error_rate, 2),
                unit="%",
                trend=0.0,
                status=get_metric_status(error_rate, {"warning": 5, "critical": 10}),
                sparkline_data=error_rate_sparkline
            ),
            success_rate=MetricValue(
                value=round(success_rate, 2),
                unit="%",
                trend=0.0,
                status="healthy" if success_rate > 95 else "warning",
                sparkline_data=[100 - x for x in error_rate_sparkline]
            ),
            total_requests_24h=total_requests_24h,
            status_code_distribution=status_distribution,
            top_endpoints=top_endpoints,
            protocol_distribution=protocol_distribution
        )
        
    except Exception as e:
        logger.error(f"Failed to fetch gateway metrics from InfluxDB: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to fetch metrics: {str(e)}")
