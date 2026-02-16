"""
Message Bus Metrics Endpoint

Provides metrics for the message bus including:
- Message throughput
- Backlog depth
- Topic statistics
- Consumer groups
- Latency by topic

Metrics sourced from InfluxDB (messagebus_event measurement).
"""

from fastapi import APIRouter, HTTPException

from ..models import MessageBusMetrics, MetricValue
from ..influx_client import MetricsInfluxClient
from aico.core.logging import get_logger

logger = get_logger("backend.api.metrics.messagebus")

router = APIRouter()


@router.get("/messagebus", response_model=MessageBusMetrics)
async def get_messagebus_metrics():
    """Get message bus metrics from InfluxDB."""
    try:
        with MetricsInfluxClient() as client:
            # Message throughput (last hour) - use downsampled data
            throughput_query = '''
                from(bucket: "aico_telemetry_downsampled")
                |> range(start: -1h)
                |> filter(fn: (r) => r._measurement == "messagebus_event_1m")
                |> filter(fn: (r) => r._field == "message_count_i")
                |> sum()
            '''
            
            throughput_results = client.query(throughput_query)
            throughput = 0
            for table in throughput_results:
                for record in table.records:
                    throughput += int(record.get_value())
            
            # Backlog depth - get latest backlog_depth_i value
            backlog = client.mean_field("messagebus_event", "backlog_depth_i", "-5m")
            backlog_value = int(backlog) if backlog else 0
            
            # Topic distribution (all topics by message count in last 1h - reduced from 24h)
            topic_query = '''
                from(bucket: "aico_telemetry_downsampled")
                |> range(start: -1h)
                |> filter(fn: (r) => r._measurement == "messagebus_event_1m")
                |> filter(fn: (r) => r._field == "message_count_i")
                |> group(columns: ["topic"])
                |> sum()
                |> group()
                |> sort(desc: true)
            '''
            topic_results = client.query(topic_query)
            
            # Build all topics with details
            top_topics = []
            latency_by_topic = {}
            topic_distribution = {}
            
            for result in topic_results:
                topic = result.get('topic', 'unknown')
                msg_count_24h = result.get('value', 0)
                topic_distribution[topic] = msg_count_24h
                
                topic_filters = {"topic": topic}
                avg_latency = client.mean_field("messagebus_event", "processing_time_ms_f", "-1h", topic_filters)
                consumer_count = client.mean_field("messagebus_event", "consumer_count_i", "-5m", topic_filters)
                
                top_topics.append({
                    "topic": topic,
                    "msg_per_sec": round(msg_count_24h / 86400, 4),
                    "backlog": 0,
                    "consumers": int(consumer_count) if consumer_count else 1
                })
                
                if avg_latency:
                    latency_by_topic[topic] = round(avg_latency, 2)
            
            return MessageBusMetrics(
                messages_per_second=MetricValue(value=messages_per_second, unit="msg/s", status="healthy"),
                backlog_depth=MetricValue(value=backlog_value, unit="messages", status="healthy"),
                topic_count=MetricValue(value=len(topic_distribution), unit="topics", status="healthy"),
                consumer_groups=MetricValue(value=len(top_topics), unit="groups", status="healthy"),
                top_topics=top_topics,
                message_type_distribution=topic_distribution,
                latency_by_topic=latency_by_topic
            )
    
    except Exception as e:
        # If InfluxDB is empty or has no data, return zero metrics instead of failing
        logger.debug(f"InfluxDB query failed (likely no data yet), returning zero metrics: {e}")
        
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
