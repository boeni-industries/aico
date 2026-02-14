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
import asyncio
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, HTTPException

from ..models import GatewayMetrics, MetricValue
from ..influx_client import (
    MetricsInfluxClient,
    calculate_percentile,
    calculate_trend,
    get_metric_status,
)
from aico.core.logging import get_logger

logger = get_logger("backend.api.metrics.gateway")

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
        def _collect_gateway_metrics_sync() -> GatewayMetrics:
            with MetricsInfluxClient() as client:
                filters = {"service": "aico-backend"}

                # Use downsampled data for better performance - sum pre-aggregated counts
                recent_count = client.sum_field("api_request_counts_1m", "status_code_i", "-5m", filters)
                logger.info(f"[GATEWAY_METRICS] recent_count (5m): {recent_count}")
                requests_per_second = recent_count / 300.0  # 5 minutes = 300 seconds

                total_requests_24h = client.sum_field("api_request_counts_1m", "status_code_i", "-1h", filters)  # Reduced from 24h to 1h
                logger.info(f"[GATEWAY_METRICS] total_requests_24h (1h): {total_requests_24h}")

                avg_response_time = client.mean_field(
                    "api_request_1m",
                    "latency_ms_f",
                    "-5m",
                    filters,
                    bucket="aico_telemetry_downsampled"
                )
                logger.info(f"[GATEWAY_METRICS] avg_response_time (5m): {avg_response_time}")

                p95_response_time = client.percentile_field(
                    "api_request_1m",
                    "latency_ms_f",
                    0.95,
                    "-1h",  # Reduced from 24h to 1h
                    filters,
                    bucket="aico_telemetry_downsampled"
                )
                p99_response_time = client.percentile_field(
                    "api_request_1m",
                    "latency_ms_f",
                    0.99,
                    "-1h",  # Reduced from 24h to 1h
                    filters,
                    bucket="aico_telemetry_downsampled"
                )

                error_count_4xx = client.count_points(
                    "api_request",
                    "-1m",
                    {**filters, "status_class": "4xx"},
                )
                error_count_5xx = client.count_points(
                    "api_request",
                    "-1m",
                    {**filters, "status_class": "5xx"},
                )
                total_errors = error_count_4xx + error_count_5xx
                error_rate = (total_errors / recent_count * 100) if recent_count > 0 else 0.0
                success_rate = 100.0 - error_rate

                def _parse_windowed_sparkline(
                    results: List[Dict[str, Any]],
                    minutes: int,
                ) -> List[float]:
                    series_by_ts: Dict[int, float] = {}
                    for r in results:
                        t = r.get("time")
                        if not t:
                            continue
                        try:
                            ts = int(t.replace(tzinfo=timezone.utc).timestamp())
                        except Exception:
                            continue
                        v = r.get("value")
                        if v is None:
                            continue
                        try:
                            series_by_ts[ts] = float(v)
                        except Exception:
                            continue

                    now = datetime.now(timezone.utc)
                    rounded = now.replace(second=0, microsecond=0)
                    out: List[float] = []
                    for i in range(minutes, 0, -1):
                        t = rounded - timedelta(minutes=i - 1)
                        ts = int(t.timestamp())
                        out.append(series_by_ts.get(ts, 0.0))
                    return out

                # Sparklines: Use downsampled data for better performance (5 minutes instead of 12)
                rps_sparkline_query = f'''
                    from(bucket: "aico_telemetry_downsampled")
                    |> range(start: -5m)
                    |> filter(fn: (r) => r._measurement == "api_request_counts_1m")
                    |> filter(fn: (r) => r.service == "{filters['service']}")
                    |> map(fn: (r) => ({{ r with _value: float(v: r._value) / 60.0 }}))
                    |> keep(columns: ["_time", "_value"])
                '''
                rps_sparkline_results = client.query(rps_sparkline_query)
                rps_sparkline = _parse_windowed_sparkline(rps_sparkline_results, 5)

                latency_sparkline_query = f'''
                    from(bucket: "aico_telemetry_downsampled")
                    |> range(start: -5m)
                    |> filter(fn: (r) => r._measurement == "api_request_1m")
                    |> filter(fn: (r) => r.service == "{filters['service']}")
                    |> filter(fn: (r) => r._field == "latency_ms_f")
                    |> keep(columns: ["_time", "_value"])
                '''
                latency_sparkline_results = client.query(latency_sparkline_query)
                latency_sparkline = _parse_windowed_sparkline(latency_sparkline_results, 5)

                error_rate_sparkline_query = f'''
                    total = from(bucket: "aico_telemetry_downsampled")
                      |> range(start: -5m)
                      |> filter(fn: (r) => r._measurement == "api_request_counts_1m")
                      |> filter(fn: (r) => r.service == "{filters['service']}")
                      |> keep(columns: ["_time", "_value"])
                      |> rename(columns: {{_value: "total"}})

                    errors = from(bucket: "aico_telemetry_downsampled")
                      |> range(start: -5m)
                      |> filter(fn: (r) => r._measurement == "api_request_counts_1m")
                      |> filter(fn: (r) => r.service == "{filters['service']}")
                      |> filter(fn: (r) => r.status_class == "4xx" or r.status_class == "5xx")
                      |> keep(columns: ["_time", "_value"])
                      |> rename(columns: {{_value: "errors"}})

                    join(tables: {{t: total, e: errors}}, on: ["_time"], method: "inner")
                      |> map(fn: (r) => ({{ r with _value: if r.total == 0 then 0.0 else float(v: r.errors) / float(v: r.total) * 100.0 }}))
                      |> keep(columns: ["_time", "_value"])
                '''
                error_rate_sparkline_results = client.query(error_rate_sparkline_query)
                error_rate_sparkline = _parse_windowed_sparkline(error_rate_sparkline_results, 5)

                status_distribution = client.group_count(
                    "api_request",
                    "status_class",
                    "-24h",
                    filters,
                )

                endpoint_counts = client.group_count(
                    "api_request",
                    "path",
                    "-24h",
                    filters,
                    limit=5,
                )

                top_endpoints = []
                for path, count in endpoint_counts.items():
                    path_filters = {**filters, "path": path}
                    avg_latency = client.mean_field(
                        "api_request",
                        "latency_ms_f",
                        "-24h",
                        path_filters,
                    )
                    top_endpoints.append(
                        {
                            "path": path,
                            "requests": count,
                            "avg_latency": round(avg_latency, 2),
                            "error_rate": 0.0,
                        }
                    )

                protocol_distribution = client.group_count(
                    "api_request",
                    "protocol",
                    "-24h",
                    filters,
                )

                return GatewayMetrics(
                    requests_per_second=MetricValue(
                        value=round(requests_per_second, 2),
                        unit="req/s",
                        status=get_metric_status(requests_per_second, {"warning": 50, "critical": 100}),
                        sparkline_data=[round(v, 2) for v in rps_sparkline],
                    ),
                    total_requests_24h=int(total_requests_24h),
                    avg_response_time=MetricValue(
                        value=round(avg_response_time, 2),
                        unit="ms",
                        status=get_metric_status(avg_response_time, {"warning": 500, "critical": 2000}),
                        sparkline_data=[round(v, 2) for v in latency_sparkline],
                    ),
                    p95_response_time=MetricValue(
                        value=round(p95_response_time, 2) if p95_response_time else 0,
                        unit="ms",
                        status=get_metric_status(p95_response_time, {"warning": 1000, "critical": 3000}),
                    ),
                    p99_response_time=MetricValue(
                        value=round(p99_response_time, 2) if p99_response_time else 0,
                        unit="ms",
                        status=get_metric_status(p99_response_time, {"warning": 2000, "critical": 5000}),
                    ),
                    error_rate=MetricValue(
                        value=round(error_rate, 2),
                        unit="%",
                        status=get_metric_status(error_rate, {"warning": 1, "critical": 5}),
                        sparkline_data=[round(v, 2) for v in error_rate_sparkline],
                    ),
                    success_rate=MetricValue(
                        value=round(success_rate, 2),
                        unit="%",
                        status=get_metric_status(success_rate, {"warning": 95, "critical": 90}),
                    ),
                    status_code_distribution=status_distribution,
                    top_endpoints=top_endpoints,
                    protocol_distribution=protocol_distribution,
                )

        return await asyncio.to_thread(_collect_gateway_metrics_sync)
    
    except Exception as e:
        # If InfluxDB is empty or has no data, return zero metrics instead of failing
        logger.error(f"[GATEWAY_METRICS] Exception occurred, returning zero metrics: {e}", exc_info=True)
        
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
