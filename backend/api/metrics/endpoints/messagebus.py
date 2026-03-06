"""
Message Bus Metrics Endpoint

Provides metrics for the message bus including:
- Message throughput
- Backlog depth
- Topic statistics
- Consumer groups
- Latency by topic

Metrics sourced from Prometheus (OpenTelemetry-exported metrics).
"""

from fastapi import APIRouter

from ..models import MessageBusMetrics, MetricValue
from ..prometheus_client import PrometheusClient, prom_label_values, prom_scalar
from aico.core.logging import get_logger

logger = get_logger("backend.api.metrics.messagebus")

router = APIRouter()


@router.get("/messagebus", response_model=MessageBusMetrics)
async def get_messagebus_metrics():
    """Get message bus metrics from Prometheus."""
    try:
        prom = PrometheusClient()
        base_selector = '{exported_job="aico-backend"}'

        messages_per_second = await prom_scalar(
            prom,
            f"sum(rate(aico_messagebus_message_duration_seconds_count{base_selector}[5m]))",
        )

        backlog_depth = await prom_scalar(
            prom,
            f"max(aico_messagebus_message_backlog_depth{base_selector})",
        )

        topic_distribution_f = await prom_label_values(
            prom,
            f"sum by (topic) (increase(aico_messagebus_message_duration_seconds_count{base_selector}[1h]))",
            label="topic",
        )
        topic_distribution = {k: int(v) for k, v in topic_distribution_f.items()}

        # Top topics by volume (up to 10)
        top_topics_samples = await prom.query(
            f"topk(10, sum by (topic) (increase(aico_messagebus_message_duration_seconds_count{base_selector}[1h])))"
        )

        top_topics = []
        latency_by_topic: dict[str, float] = {}

        for s in top_topics_samples:
            topic = s.labels.get("topic") or "unknown"
            msgs_1h = float(s.value)
            topic_selector = '{exported_job="aico-backend",topic="' + topic.replace('"', '\\"') + '"}'
            avg_latency_s = await prom_scalar(
                prom,
                "(" \
                f"sum(rate(aico_messagebus_message_duration_seconds_sum{topic_selector}[5m]))" \
                "/" \
                f"sum(rate(aico_messagebus_message_duration_seconds_count{topic_selector}[5m]))" \
                ")",
            )
            avg_consumer_count = await prom_scalar(
                prom,
                f"avg(aico_messagebus_message_consumer_count{topic_selector})",
            )

            top_topics.append(
                {
                    "topic": topic,
                    "msg_per_sec": round(msgs_1h / 3600.0, 4),
                    "backlog": 0,
                    "consumers": int(avg_consumer_count) if avg_consumer_count > 0 else 1,
                }
            )

            if avg_latency_s > 0:
                latency_by_topic[topic] = round(avg_latency_s * 1000.0, 2)

        return MessageBusMetrics(
            messages_per_second=MetricValue(value=round(messages_per_second, 4), unit="msg/s", status="healthy"),
            backlog_depth=MetricValue(value=int(backlog_depth) if backlog_depth > 0 else 0, unit="messages", status="healthy"),
            topic_count=MetricValue(value=len(topic_distribution), unit="topics", status="healthy"),
            consumer_groups=MetricValue(value=len(top_topics), unit="groups", status="healthy"),
            top_topics=top_topics,
            message_type_distribution=topic_distribution,
            latency_by_topic=latency_by_topic,
        )
    
    except Exception as e:
        logger.debug(f"Prometheus query failed (likely no data yet), returning zero metrics: {e}")
        
        # Return empty/zero metrics
        return MessageBusMetrics(
            messages_per_second=MetricValue(value=0.0, unit="msg/s", status="healthy"),
            backlog_depth=MetricValue(value=0, unit="messages", status="healthy"),
            topic_count=MetricValue(value=0, unit="topics", status="healthy"),
            consumer_groups=MetricValue(value=0, unit="groups", status="healthy"),
            top_topics=[],
            message_type_distribution={},
            latency_by_topic={}
        )
