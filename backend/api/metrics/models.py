"""
Pydantic Models for Metrics API

Type-safe response models for all metrics endpoints.
Centralized to ensure consistency and enable reuse.
"""

from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field


class MetricValue(BaseModel):
    """
    Single metric value with metadata.
    
    Provides rich context for each metric including:
    - Current value and unit
    - Trend analysis (percentage change)
    - Health status (healthy/warning/critical)
    - Historical sparkline data for visualization
    - Time-based averages (1h, 24h, 7d)
    """
    value: float = Field(..., description="Current metric value")
    unit: str = Field(..., description="Unit of measurement (req/s, ms, %, etc.)")
    trend: Optional[float] = Field(None, description="Percentage change from baseline")
    status: str = Field("healthy", description="Health status: healthy, warning, or critical")
    sparkline_data: Optional[List[float]] = Field(None, description="Historical data points for visualization")
    avg_1h: Optional[float] = Field(None, description="1-hour average")
    avg_24h: Optional[float] = Field(None, description="24-hour average")
    avg_7d: Optional[float] = Field(None, description="7-day average")


class GatewayMetrics(BaseModel):
    """API Gateway performance metrics."""
    requests_per_second: MetricValue = Field(..., description="Current request rate")
    avg_response_time: MetricValue = Field(..., description="Average response time")
    p95_response_time: MetricValue = Field(..., description="95th percentile latency")
    p99_response_time: MetricValue = Field(..., description="99th percentile latency")
    error_rate: MetricValue = Field(..., description="Error rate percentage")
    success_rate: MetricValue = Field(..., description="Success rate percentage")
    total_requests_24h: int = Field(..., description="Total requests in last 24 hours")
    status_code_distribution: Dict[str, int] = Field(..., description="Distribution by status code class")
    top_endpoints: List[Dict[str, Any]] = Field(..., description="Most frequently accessed endpoints")
    protocol_distribution: Dict[str, int] = Field(..., description="Distribution by protocol (HTTP, gRPC, etc.)")


class LLMMetrics(BaseModel):
    """LLM (Large Language Model) inference metrics."""
    active_models: MetricValue = Field(..., description="Number of active models")
    ttft: MetricValue = Field(..., description="Time to First Token (ms)")
    tps: MetricValue = Field(..., description="Tokens Per Second")
    e2e_latency: MetricValue = Field(..., description="End-to-end latency (ms)")
    rps: MetricValue = Field(..., description="Requests Per Second")
    success_rate: MetricValue = Field(..., description="Success rate percentage")
    total_tokens_24h: int = Field(..., description="Total tokens generated in 24h")
    total_requests_24h: int = Field(..., description="Total inference requests in 24h")
    avg_prompt_length: MetricValue = Field(..., description="Average prompt length in tokens")
    avg_response_length: MetricValue = Field(..., description="Average response length in tokens")
    model_usage: Dict[str, int] = Field(..., description="Request distribution by model")
    p95_latency: Optional[float] = Field(None, description="95th percentile latency")
    p99_latency: Optional[float] = Field(None, description="99th percentile latency")


class NERMetrics(BaseModel):
    """Named Entity Recognition metrics."""
    inference_rate: MetricValue = Field(..., description="Inferences per second")
    avg_latency: MetricValue = Field(..., description="Average inference latency")
    p95_latency: Optional[float] = Field(None, description="95th percentile latency")
    p99_latency: Optional[float] = Field(None, description="99th percentile latency")
    total_entities_24h: int = Field(..., description="Total entities extracted in 24h")
    total_requests_24h: int = Field(..., description="Total NER requests in 24h")
    avg_entities_per_request: MetricValue = Field(..., description="Average entities per request")
    success_rate: MetricValue = Field(..., description="Success rate percentage")
    entity_type_distribution: Dict[str, int] = Field(..., description="Distribution by entity type (PERSON, ORG, etc.)")


class SentimentMetrics(BaseModel):
    """Sentiment Analysis metrics."""
    inference_rate: MetricValue = Field(..., description="Analyses per second")
    avg_latency: MetricValue = Field(..., description="Average analysis latency")
    p95_latency: Optional[float] = Field(None, description="95th percentile latency")
    p99_latency: Optional[float] = Field(None, description="99th percentile latency")
    total_analyses_24h: int = Field(..., description="Total analyses in 24h")
    avg_confidence: MetricValue = Field(..., description="Average confidence score")
    success_rate: MetricValue = Field(..., description="Success rate percentage")
    sentiment_distribution: Dict[str, int] = Field(..., description="Distribution by sentiment (positive, negative, neutral)")


class EmbeddingsMetrics(BaseModel):
    """Embeddings generation metrics."""
    inference_rate: MetricValue = Field(..., description="Embeddings per second")
    avg_latency: MetricValue = Field(..., description="Average generation latency")
    p95_latency: Optional[float] = Field(None, description="95th percentile latency")
    p99_latency: Optional[float] = Field(None, description="99th percentile latency")
    throughput: MetricValue = Field(..., description="Input tokens per second")
    total_embeddings_24h: int = Field(..., description="Total embeddings generated in 24h")
    avg_input_length: MetricValue = Field(..., description="Average input length in tokens")
    success_rate: MetricValue = Field(..., description="Success rate percentage")
    vector_dimension: int = Field(..., description="Embedding vector dimension")


class ModelserviceMetrics(BaseModel):
    """Comprehensive modelservice metrics."""
    llm: LLMMetrics = Field(..., description="LLM inference metrics")
    ner: NERMetrics = Field(..., description="Named Entity Recognition metrics")
    sentiment: SentimentMetrics = Field(..., description="Sentiment analysis metrics")
    embeddings: EmbeddingsMetrics = Field(..., description="Embeddings generation metrics")


class MemoryMetrics(BaseModel):
    """Memory system metrics."""
    working_memory_size: MetricValue = Field(..., description="Working memory entries")
    semantic_queries_per_second: MetricValue = Field(..., description="Semantic search rate")
    kg_nodes: MetricValue = Field(..., description="Knowledge graph nodes")
    kg_relationships: MetricValue = Field(..., description="Knowledge graph edges")
    entity_type_distribution: Dict[str, int] = Field(..., description="Entity type distribution")
    relationship_type_distribution: Dict[str, int] = Field(..., description="Relationship type distribution")
    storage_breakdown: Dict[str, float] = Field(..., description="Storage size by component (MB)")
    consolidation_health: MetricValue = Field(..., description="Consolidation health score")
    last_consolidation: Optional[str] = Field(None, description="Last consolidation timestamp")


class SchedulerMetrics(BaseModel):
    """Task scheduler metrics."""
    jobs_today: MetricValue = Field(..., description="Jobs executed today")
    success_rate: MetricValue = Field(..., description="Job success rate")
    failed_jobs: MetricValue = Field(..., description="Failed jobs count")
    avg_job_duration: MetricValue = Field(..., description="Average job duration")
    queue_utilization: Dict[str, float] = Field(..., description="Utilization by queue (%)")
    job_type_distribution: Dict[str, int] = Field(..., description="Distribution by job type")
    failed_job_reasons: List[Dict[str, Any]] = Field(..., description="Recent failure reasons")


class MessageBusMetrics(BaseModel):
    """Message bus metrics."""
    messages_per_second: MetricValue = Field(..., description="Message throughput")
    backlog_depth: MetricValue = Field(..., description="Current backlog size")
    topic_count: MetricValue = Field(..., description="Number of active topics")
    consumer_groups: MetricValue = Field(..., description="Number of consumer groups")
    top_topics: List[Dict[str, Any]] = Field(..., description="Most active topics")
    message_type_distribution: Dict[str, int] = Field(..., description="Distribution by message type")
    latency_by_topic: Dict[str, float] = Field(..., description="Average latency by topic (ms)")


class SystemHealthMetrics(BaseModel):
    """Overall system health and quality metrics."""
    health_score: int = Field(..., ge=0, le=100, description="Overall health score (0-100)")
    component_status: Dict[str, Dict[str, Any]] = Field(..., description="Status of each component")
    cpu_percent: float = Field(..., description="CPU utilization percentage")
    memory_percent: float = Field(..., description="RAM utilization percentage")
    disk_percent: float = Field(..., description="Disk utilization percentage")
    uptime_seconds: int = Field(..., description="System uptime in seconds")
    active_sessions: int = Field(..., description="Active user sessions")
    total_throughput: float = Field(..., description="Total requests/sec across all endpoints")
    system_error_rate: float = Field(..., description="System-wide error rate percentage")
    avg_latency_ms: float = Field(..., description="Average system latency (ms)")
    queue_backlog: int = Field(..., description="Total messages in all queues")
    storage_size_mb: float = Field(..., description="Total storage size (MB)")
    critical_alerts: int = Field(..., description="Number of critical alerts")
    warnings: int = Field(..., description="Number of warnings")


class AllMetrics(BaseModel):
    """Complete metrics response combining all subsystems."""
    timestamp: str = Field(..., description="Metrics collection timestamp (ISO 8601)")
    gateway: GatewayMetrics = Field(..., description="API Gateway metrics")
    modelservice: ModelserviceMetrics = Field(..., description="Modelservice metrics")
    memory: MemoryMetrics = Field(..., description="Memory system metrics")
    scheduler: SchedulerMetrics = Field(..., description="Scheduler metrics")
    message_bus: MessageBusMetrics = Field(..., description="Message bus metrics")
    system_health: SystemHealthMetrics = Field(..., description="System health metrics")
