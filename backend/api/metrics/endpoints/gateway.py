"""API Gateway Metrics Endpoint."""

from typing import Any, Dict, List

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter

from aico.core.logging import get_logger

from ..models import GatewayMetrics, MetricValue
from ..prometheus_client import PrometheusClient, prom_label_values, prom_scalar
from ..influx_client import get_metric_status

logger = get_logger("backend.api.metrics.gateway")

router = APIRouter()


@router.get("/gateway", response_model=GatewayMetrics)
async def get_gateway_metrics():
    """
    Get API Gateway performance metrics from Prometheus.
    
    Returns comprehensive metrics including throughput, latency,
    error rates, and endpoint statistics.
    
    The values are derived from the OpenTelemetry-exported Prometheus metrics
    exposed by the collector.
    """
    try:
        prom = PrometheusClient()

        base_selector = '{job="aico-backend"}'
        rps = await prom_scalar(prom, f"sum(rate(aico_api_request_count_total{base_selector}[5m]))")
        total_requests_24h = await prom_scalar(prom, f"sum(increase(aico_api_request_count_total{base_selector}[24h]))")

        avg_latency_ms = await prom_scalar(
            prom,
            "(" \
            f"sum(rate(aico_api_request_duration_seconds_sum{base_selector}[5m]))" \
            "/" \
            f"sum(rate(aico_api_request_duration_seconds_count{base_selector}[5m]))" \
            ") * 1000",
        )

        p95_ms = await prom_scalar(
            prom,
            "histogram_quantile(0.95, sum by (le) (rate(aico_api_request_duration_seconds_bucket" \
            f"{base_selector}[5m]))) * 1000",
        )
        p99_ms = await prom_scalar(
            prom,
            "histogram_quantile(0.99, sum by (le) (rate(aico_api_request_duration_seconds_bucket" \
            f"{base_selector}[5m]))) * 1000",
        )

        error_rps = await prom_scalar(
            prom,
            f"sum(rate(aico_api_request_count_total{{job=\"aico-backend\",status_code_class=~\"4xx|5xx\"}}[5m]))",
        )
        error_rate = (error_rps / rps * 100.0) if rps > 0 else 0.0
        success_rate = 100.0 - error_rate

        # Sparklines (5 points, 1-minute step)
        now = datetime.now(timezone.utc)
        end_ts = now.timestamp()
        start_ts = (now - timedelta(minutes=5)).timestamp()

        rps_range = await prom.query_range(
            f"sum(rate(aico_api_request_count_total{base_selector}[1m]))",
            start=start_ts,
            end=end_ts,
            step_seconds=60,
        )
        rps_sparkline = [round(v, 2) for v in (rps_range[0][1] if rps_range else [0.0] * 5)]

        latency_range = await prom.query_range(
            "(" \
            f"sum(rate(aico_api_request_duration_seconds_sum{base_selector}[1m]))" \
            "/" \
            f"sum(rate(aico_api_request_duration_seconds_count{base_selector}[1m]))" \
            ") * 1000",
            start=start_ts,
            end=end_ts,
            step_seconds=60,
        )
        latency_sparkline = [round(v, 2) for v in (latency_range[0][1] if latency_range else [0.0] * 5)]

        err_range = await prom.query_range(
            "(" \
            f"sum(rate(aico_api_request_count_total{{job=\\\"aico-backend\\\",status_code_class=~\\\"4xx|5xx\\\"}}[1m]))" \
            "/" \
            f"sum(rate(aico_api_request_count_total{base_selector}[1m]))" \
            ") * 100",
            start=start_ts,
            end=end_ts,
            step_seconds=60,
        )
        error_rate_sparkline = [round(v, 2) for v in (err_range[0][1] if err_range else [0.0] * 5)]

        status_distribution_f = await prom_label_values(
            prom,
            f"sum by (status_code_class) (increase(aico_api_request_count_total{base_selector}[24h]))",
            label="status_code_class",
        )
        status_distribution = {k: int(v) for k, v in status_distribution_f.items()}

        protocol_distribution_f = await prom_label_values(
            prom,
            f"sum by (http_scheme) (increase(aico_api_request_count_total{base_selector}[24h]))",
            label="http_scheme",
        )
        protocol_distribution = {k: int(v) for k, v in protocol_distribution_f.items()}

        # Top endpoints (by request volume)
        top_route_samples = await prom.query(
            f"topk(5, sum by (http_route) (increase(aico_api_request_count_total{base_selector}[24h])))"
        )

        top_endpoints: List[Dict[str, Any]] = []
        for s in top_route_samples:
            route = s.labels.get("http_route") or "unknown"
            reqs = int(s.value)
            route_selector = '{job="aico-backend",http_route="' + route.replace('"', '\\"') + '"}'
            route_avg_ms = await prom_scalar(
                prom,
                "(" \
                f"sum(rate(aico_api_request_duration_seconds_sum{route_selector}[5m]))" \
                "/" \
                f"sum(rate(aico_api_request_duration_seconds_count{route_selector}[5m]))" \
                ") * 1000",
            )
            top_endpoints.append(
                {
                    "path": route,
                    "requests": reqs,
                    "avg_latency": round(route_avg_ms, 2),
                    "error_rate": 0.0,
                }
            )

        return GatewayMetrics(
            requests_per_second=MetricValue(
                value=round(rps, 2),
                unit="req/s",
                status=get_metric_status(rps, {"warning": 50, "critical": 100}),
                sparkline_data=rps_sparkline,
            ),
            total_requests_24h=int(total_requests_24h),
            avg_response_time=MetricValue(
                value=round(avg_latency_ms, 2),
                unit="ms",
                status=get_metric_status(avg_latency_ms, {"warning": 500, "critical": 2000}),
                sparkline_data=latency_sparkline,
            ),
            p95_response_time=MetricValue(
                value=round(p95_ms, 2),
                unit="ms",
                status=get_metric_status(p95_ms, {"warning": 1000, "critical": 3000}),
            ),
            p99_response_time=MetricValue(
                value=round(p99_ms, 2),
                unit="ms",
                status=get_metric_status(p99_ms, {"warning": 2000, "critical": 5000}),
            ),
            error_rate=MetricValue(
                value=round(error_rate, 2),
                unit="%",
                status=get_metric_status(error_rate, {"warning": 1, "critical": 5}),
                sparkline_data=error_rate_sparkline,
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
    
    except Exception as e:
        logger.error(f"[GATEWAY_METRICS] Exception occurred, returning zero metrics: {e}", exc_info=True)
        
        # Return empty/zero metrics
        return GatewayMetrics(
            requests_per_second=MetricValue(value=0.0, unit="req/s", status="healthy", sparkline_data=[0.0] * 5),
            avg_response_time=MetricValue(value=0.0, unit="ms", status="healthy", sparkline_data=[0.0] * 5),
            p95_response_time=MetricValue(value=0.0, unit="ms", status="healthy"),
            p99_response_time=MetricValue(value=0.0, unit="ms", status="healthy"),
            error_rate=MetricValue(value=0.0, unit="%", status="healthy", sparkline_data=[0.0] * 5),
            success_rate=MetricValue(value=100.0, unit="%", status="healthy"),
            total_requests_24h=0,
            status_code_distribution={},
            top_endpoints=[],
            protocol_distribution={}
        )
