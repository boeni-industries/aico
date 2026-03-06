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

from aico.core.logging import get_logger

from ..models import ModelserviceMetrics, LLMMetrics, NERMetrics, SentimentMetrics, EmbeddingsMetrics, MetricValue
from ..prometheus_client import PrometheusClient, prom_label_values, prom_scalar

logger = get_logger("backend.api.metrics.modelservice")

router = APIRouter()


@router.get("/modelservice", response_model=ModelserviceMetrics)
async def get_modelservice_metrics():
    """
    Get comprehensive modelservice inference metrics.

    vLLM exposes a native Prometheus /metrics endpoint. Prometheus scrapes it under job="vllm".
    This endpoint queries vllm:* series to provide real inference metrics.
    """

    def _defaults() -> ModelserviceMetrics:
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

    try:
        prom = PrometheusClient()

        selector = '{job="vllm"}'

        model_names = await prom_label_values(prom, "vllm:num_requests_running", "model_name")
        active_models = float(len(model_names))

        # Requests/sec (successful requests only; vLLM does not expose a total-with-fail counter by default)
        rps = await prom_scalar(prom, f"sum(rate(vllm:request_success_total{selector}[5m]))")

        # Tokens/sec (generated/output tokens)
        tps = await prom_scalar(prom, f"sum(rate(vllm:generation_tokens_total{selector}[5m]))")

        # Averages from histograms
        ttft_s = await prom_scalar(
            prom,
            "(" \
            f"sum(rate(vllm:time_to_first_token_seconds_sum{selector}[5m]))" \
            "/" \
            f"sum(rate(vllm:time_to_first_token_seconds_count{selector}[5m]))" \
            ")",
        )
        e2e_latency_s = await prom_scalar(
            prom,
            "(" \
            f"sum(rate(vllm:e2e_request_latency_seconds_sum{selector}[5m]))" \
            "/" \
            f"sum(rate(vllm:e2e_request_latency_seconds_count{selector}[5m]))" \
            ")",
        )

        # Percentiles from buckets
        p95_latency_s = await prom_scalar(
            prom,
            "histogram_quantile(0.95, "
            f"sum by (le) (rate(vllm:e2e_request_latency_seconds_bucket{selector}[5m]))"
            ")",
        )
        p99_latency_s = await prom_scalar(
            prom,
            "histogram_quantile(0.99, "
            f"sum by (le) (rate(vllm:e2e_request_latency_seconds_bucket{selector}[5m]))"
            ")",
        )

        # Prompt/response sizes (tokens)
        avg_prompt_tokens = await prom_scalar(
            prom,
            "(" \
            f"sum(rate(vllm:request_prompt_tokens_sum{selector}[5m]))" \
            "/" \
            f"sum(rate(vllm:request_prompt_tokens_count{selector}[5m]))" \
            ")",
        )
        avg_response_tokens = await prom_scalar(
            prom,
            "(" \
            f"sum(rate(vllm:request_generation_tokens_sum{selector}[5m]))" \
            "/" \
            f"sum(rate(vllm:request_generation_tokens_count{selector}[5m]))" \
            ")",
        )

        total_requests_24h = int(
            await prom_scalar(prom, f"sum(increase(vllm:request_success_total{selector}[24h]))")
        )
        total_tokens_24h = int(
            await prom_scalar(prom, f"sum(increase(vllm:generation_tokens_total{selector}[24h]))")
        )

        llm = LLMMetrics(
            active_models=MetricValue(value=active_models, unit="models", status="healthy"),
            ttft=MetricValue(value=ttft_s, unit="s", status="healthy"),
            tps=MetricValue(value=tps, unit="tokens/s", status="healthy"),
            e2e_latency=MetricValue(value=e2e_latency_s, unit="s", status="healthy"),
            rps=MetricValue(value=rps, unit="req/s", status="healthy"),
            success_rate=MetricValue(value=100.0, unit="%", status="healthy"),
            total_tokens_24h=total_tokens_24h,
            total_requests_24h=total_requests_24h,
            avg_prompt_length=MetricValue(value=avg_prompt_tokens, unit="tokens", status="healthy"),
            avg_response_length=MetricValue(value=avg_response_tokens, unit="tokens", status="healthy"),
            model_usage={},
            p95_latency=p95_latency_s,
            p99_latency=p99_latency_s,
        )

        # Non-LLM modelservice metrics are not yet mapped to vLLM.
        d = _defaults()
        d.llm = llm
        return d
    except Exception as exc:
        logger.warning("[MODELSERVICE_METRICS] Exception occurred, returning default values: %s", exc)
        return _defaults()
