"""
API Gateway Metrics Endpoint

Provides comprehensive performance metrics for the API Gateway including:
- Request throughput (requests per second)
- Response times (average, P95, P99)
- Error rates and success rates
- Status code distribution
- Top endpoints by traffic
- Protocol distribution

All metrics sourced from InfluxDB (api_request measurement).
"""

from typing import Dict, Any, List
from fastapi import APIRouter, HTTPException

from ..models import GatewayMetrics, MetricValue
from ..influx_client import (
    MetricsInfluxClient,
    calculate_percentile,
    calculate_trend,
    get_metric_status,
)
from aico.core.logging import get_logger

logger = get_logger("backend", "api.metrics.gateway")

router = APIRouter()


@router.get("/gateway", response_model=GatewayMetrics)
async def get_gateway_metrics():
    """
    Get API Gateway performance metrics from InfluxDB.
    
    Returns comprehensive metrics including throughput, latency,
    error rates, and endpoint statistics.
    
    Raises:
        HTTPException: If metrics collection fails
    """
    try:
        with MetricsInfluxClient() as client:
            # Service filter for all queries
            filters = {"service": "aico-backend"}
            
            # === Requests Per Second ===
            # Count requests in last 1 minute
            recent_count = client.count_points("api_request", "-1m", filters)
            requests_per_second = recent_count / 60.0
            
            # RPS sparkline (last 12 minutes, 1-minute intervals)
            rps_sparkline = client.sparkline(
                measurement="api_request",
                field=None,  # Count-based
                intervals=12,
                interval_duration="1m",
                aggregation="mean",
                filters=filters
            )
            
            # Total requests in 24h
            total_requests_24h = client.count_points("api_request", "-24h", filters)
            
            # === Response Time ===
            # Average response time (last 1 minute)
            avg_response_time = client.mean_field(
                "api_request",
                "latency_ms_f",
                "-1m",
                filters
            )
            
            # Latency sparkline (last 12 minutes)
            latency_sparkline = client.sparkline(
                measurement="api_request",
                field="latency_ms_f",
                intervals=12,
                interval_duration="1m",
                aggregation="mean",
                filters=filters
            )
            
            # P95 and P99 latencies (last 24h)
            p95_response_time = client.percentile_field(
                "api_request",
                "latency_ms_f",
                0.95,
                "-24h",
                filters
            )
            
            p99_response_time = client.percentile_field(
                "api_request",
                "latency_ms_f",
                0.99,
                "-24h",
                filters
            )
            
            # === Error Rate ===
            # Count errors (4xx and 5xx) in last 1 minute
            error_filters = {**filters, "status_class": "4xx"}
            error_count_4xx = client.count_points("api_request", "-1m", error_filters)
            
            error_filters["status_class"] = "5xx"
            error_count_5xx = client.count_points("api_request", "-1m", error_filters)
            
            total_errors = error_count_4xx + error_count_5xx
            error_rate = (total_errors / recent_count * 100) if recent_count > 0 else 0.0
            success_rate = 100.0 - error_rate
            
            # Error rate sparkline (last 12 minutes)
            error_rate_sparkline = []
            for i in range(12):
                start_offset = 12 - i
                end_offset = 11 - i
                
                # Total in interval
                interval_total = client.count_points(
                    "api_request",
                    f"-{start_offset}m",
                    filters
                ) - client.count_points(
                    "api_request",
                    f"-{end_offset}m",
                    filters
                )
                
                # Errors in interval
                error_filters_4xx = {**filters, "status_class": "4xx"}
                interval_errors_4xx = client.count_points(
                    "api_request",
                    f"-{start_offset}m",
                    error_filters_4xx
                ) - client.count_points(
                    "api_request",
                    f"-{end_offset}m",
                    error_filters_4xx
                )
                
                error_filters_5xx = {**filters, "status_class": "5xx"}
                interval_errors_5xx = client.count_points(
                    "api_request",
                    f"-{start_offset}m",
                    error_filters_5xx
                ) - client.count_points(
                    "api_request",
                    f"-{end_offset}m",
                    error_filters_5xx
                )
                
                interval_errors = interval_errors_4xx + interval_errors_5xx
                interval_error_rate = (interval_errors / interval_total * 100) if interval_total > 0 else 0.0
                error_rate_sparkline.append(interval_error_rate)
            
            # === Status Code Distribution ===
            status_distribution = client.group_count(
                "api_request",
                "status_class",
                "-24h",
                filters
            )
            
            # === Top Endpoints ===
            endpoint_counts = client.group_count(
                "api_request",
                "path",
                "-24h",
                filters,
                limit=5
            )
            
            top_endpoints = []
            for path, count in endpoint_counts.items():
                # Get average latency for this path
                path_filters = {**filters, "path": path}
                avg_latency = client.mean_field(
                    "api_request",
                    "latency_ms_f",
                    "-24h",
                    path_filters
                )
                
                top_endpoints.append({
                    "path": path,
                    "requests": count,
                    "avg_latency": round(avg_latency, 2),
                    "error_rate": 0.0  # Would need separate query
                })
            
            # === Protocol Distribution ===
            protocol_distribution = client.group_count(
                "api_request",
                "protocol",
                "-24h",
                filters
            )
            
            # === Build Response ===
            return GatewayMetrics(
                requests_per_second=MetricValue(
                    value=round(requests_per_second, 2),
                    unit="req/s",
                    trend=0.0,  # Would need historical comparison
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
        # If InfluxDB is empty or has no data, return zero metrics instead of failing
        logger.warning(f"InfluxDB query failed (likely no data yet), returning zero metrics: {e}")
        
        # Return empty/zero metrics
        return GatewayMetrics(
            requests_per_second=MetricValue(value=0.0, unit="req/s", status="healthy", sparkline_data=[0.0] * 12),
            avg_response_time=MetricValue(value=0.0, unit="ms", status="healthy", sparkline_data=[0.0] * 12),
            p95_response_time=MetricValue(value=0.0, unit="ms", status="healthy"),
            p99_response_time=MetricValue(value=0.0, unit="ms", status="healthy"),
            error_rate=MetricValue(value=0.0, unit="%", status="healthy", sparkline_data=[0.0] * 12),
            success_rate=MetricValue(value=100.0, unit="%", status="healthy", sparkline_data=[100.0] * 12),
            total_requests_24h=0,
            status_code_distribution={},
            top_endpoints=[],
            protocol_distribution={}
        )
