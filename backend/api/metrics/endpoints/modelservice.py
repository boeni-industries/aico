"""
Modelservice Metrics Endpoint

Provides inference metrics for all model types:
- LLM (Large Language Models)
- NER (Named Entity Recognition)
- Sentiment Analysis
- Embeddings Generation

Metrics sourced from Prometheus when available (OpenTelemetry-exported metrics).
"""

from fastapi import APIRouter

from ..models import ModelserviceMetrics, LLMMetrics, NERMetrics, SentimentMetrics, EmbeddingsMetrics, MetricValue
from aico.core.logging import get_logger

logger = get_logger("backend.api.metrics.modelservice")

router = APIRouter()


@router.get("/modelservice", response_model=ModelserviceMetrics)
async def get_modelservice_metrics():
    """
    Get comprehensive modelservice inference metrics.

    Note: dedicated modelservice inference metrics are not yet exported to Prometheus.
    This endpoint returns schema-stable default values (zeros) to keep Studio compatible
    until OTLP instruments are wired to produce aico_modelservice_* series.
    """
    return ModelserviceMetrics(
        llm=LLMMetrics(
            active_models=MetricValue(value=0.0, unit="models", status="healthy"),
            ttft=MetricValue(value=0.0, unit="s", status="healthy"),
            tps=MetricValue(value=0.0, unit="tokens/s", status="healthy"),
            e2e_latency=MetricValue(value=0.0, unit="s", status="healthy"),
            rps=MetricValue(value=0.0, unit="req/s", status="healthy"),
            success_rate=MetricValue(value=100.0, unit="%", status="healthy"),
            total_tokens_24h=0,
            total_requests_24h=0,
            avg_prompt_length=MetricValue(value=0.0, unit="tokens", status="healthy"),
            avg_response_length=MetricValue(value=0.0, unit="tokens", status="healthy"),
            model_usage={},
        ),
        ner=NERMetrics(
            inference_rate=MetricValue(value=0.0, unit="req/s", status="healthy"),
            avg_latency=MetricValue(value=0.0, unit="s", status="healthy"),
            total_entities_24h=0,
            total_requests_24h=0,
            avg_entities_per_request=MetricValue(value=0.0, unit="entities", status="healthy"),
            success_rate=MetricValue(value=100.0, unit="%", status="healthy"),
            entity_type_distribution={},
        ),
        sentiment=SentimentMetrics(
            inference_rate=MetricValue(value=0.0, unit="req/s", status="healthy"),
            avg_latency=MetricValue(value=0.0, unit="s", status="healthy"),
            total_analyses_24h=0,
            avg_confidence=MetricValue(value=0.0, unit="score", status="healthy"),
            success_rate=MetricValue(value=100.0, unit="%", status="healthy"),
            sentiment_distribution={},
        ),
        embeddings=EmbeddingsMetrics(
            inference_rate=MetricValue(value=0.0, unit="emb/s", status="healthy"),
            avg_latency=MetricValue(value=0.0, unit="ms", status="healthy"),
            throughput=MetricValue(value=0.0, unit="emb/s", status="healthy"),
            total_embeddings_24h=0,
            avg_input_length=MetricValue(value=0.0, unit="tokens", status="healthy"),
            success_rate=MetricValue(value=100.0, unit="%", status="healthy"),
            vector_dimension=768,
        ),
    )
