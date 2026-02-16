"""
Modelservice Metrics Endpoint

Provides inference metrics for all model types:
- LLM (Large Language Models)
- NER (Named Entity Recognition)
- Sentiment Analysis
- Embeddings Generation

All metrics sourced from InfluxDB (model_inference measurement).
"""

from fastapi import APIRouter, HTTPException

from ..models import ModelserviceMetrics, LLMMetrics, NERMetrics, SentimentMetrics, EmbeddingsMetrics, MetricValue
from ..influx_client import MetricsInfluxClient, get_metric_status
from aico.core.logging import get_logger

logger = get_logger("backend.api.metrics.modelservice")

router = APIRouter()


@router.get("/modelservice", response_model=ModelserviceMetrics)
async def get_modelservice_metrics():
    """
    Get comprehensive modelservice inference metrics from InfluxDB.
    
    Aggregates metrics across all model types (LLM, NER, sentiment, embeddings).
    """
    try:
        with MetricsInfluxClient() as client:
            filters = {"service": "modelservice"}
            
            # LLM Metrics
            llm_filters = {**filters, "task_type": "chat_streaming"}
            llm_count = client.count_points("model_inference", "-24h", llm_filters)
            llm_latency_ms = client.mean_field("model_inference", "duration_ms_f", "-24h", llm_filters)
            llm_latency = llm_latency_ms / 1000  # Convert ms to seconds
            
            # Calculate trend: compare current 24h to previous 24h (24-48h ago)
            prev_latency_query = f'''
                from(bucket: "aico_telemetry")
                |> range(start: -48h, stop: -24h)
                |> filter(fn: (r) => r._measurement == "model_inference")
                |> filter(fn: (r) => r._field == "duration_ms_f")
                |> filter(fn: (r) => r.service == "modelservice")
                |> filter(fn: (r) => r.task_type == "chat_streaming")
                |> mean()
            '''
            prev_results = client.query(prev_latency_query)
            llm_latency_prev_ms = prev_results[0].get('value', llm_latency_ms) if prev_results else llm_latency_ms
            llm_latency_prev = llm_latency_prev_ms / 1000
            llm_latency_trend = ((llm_latency - llm_latency_prev) / llm_latency_prev * 100) if llm_latency_prev > 0 else 0
            
            llm_ttft_ms = client.mean_field("model_inference", "ttft_ms_f", "-24h", llm_filters)
            llm_ttft = llm_ttft_ms / 1000  # Convert ms to seconds for better UX
            
            # Calculate RPS (requests per second) - use max to avoid 0
            rps_value = max(llm_count / 86400, 0.01) if llm_count > 0 else 0.0
            
            # Calculate TPS (tokens per second) from tokens_generated and duration
            total_tokens_query = f'''
                from(bucket: "aico_telemetry")
                |> range(start: -24h)
                |> filter(fn: (r) => r._measurement == "model_inference")
                |> filter(fn: (r) => r._field == "tokens_generated_i")
                |> filter(fn: (r) => r.service == "modelservice")
                |> filter(fn: (r) => r.task_type == "chat_streaming")
                |> sum()
            '''
            total_duration_query = f'''
                from(bucket: "aico_telemetry")
                |> range(start: -24h)
                |> filter(fn: (r) => r._measurement == "model_inference")
                |> filter(fn: (r) => r._field == "duration_ms_f")
                |> filter(fn: (r) => r.service == "modelservice")
                |> filter(fn: (r) => r.task_type == "chat_streaming")
                |> sum()
            '''
            total_tokens_results = client.query(total_tokens_query)
            total_duration_results = client.query(total_duration_query)
            
            total_tokens = total_tokens_results[0].get('value', 0) if total_tokens_results else 0
            total_duration_ms = total_duration_results[0].get('value', 0) if total_duration_results else 0
            
            # TPS = total_tokens / (total_duration_ms / 1000)
            tps_value = round((total_tokens / (total_duration_ms / 1000)), 2) if total_duration_ms > 0 else 0.0
            
            # Calculate success rate from success_b field
            success_query = f'''
                from(bucket: "aico_telemetry")
                |> range(start: -24h)
                |> filter(fn: (r) => r._measurement == "model_inference")
                |> filter(fn: (r) => r._field == "success_b")
                |> filter(fn: (r) => r.service == "modelservice")
                |> filter(fn: (r) => r.task_type == "chat_streaming")
                |> group()
                |> count()
            '''
            success_results = client.query(success_query)
            
            # Count successes (where success_b == true)
            success_count = sum(1 for r in success_results if r.get('value', False))
            total_count = len(success_results) if success_results else llm_count
            
            success_rate_value = round((success_count / total_count * 100), 2) if total_count > 0 else 100.0
            
            # Query average prompt and response lengths
            avg_prompt_tokens = client.mean_field("model_inference", "prompt_tokens_i", "-24h", llm_filters)
            avg_response_tokens = client.mean_field("model_inference", "tokens_generated_i", "-24h", llm_filters)
            
            # Generate sparkline data for E2E latency (24 hourly data points)
            e2e_sparkline = client.sparkline(
                measurement="model_inference",
                field="duration_ms_f",
                intervals=24,
                interval_duration="1h",
                aggregation="mean",
                filters=llm_filters
            )
            # Convert sparkline from ms to seconds
            e2e_sparkline_seconds = [round(val / 1000, 2) if val > 0 else 0 for val in e2e_sparkline]
            
            # Get model usage from InfluxDB (models that have been used in last 24h)
            # Note: This shows models with actual usage, not necessarily all loaded models
            # Modelservice manages Ollama directly - we only observe metrics here
            model_usage_dict = client.group_count("model_inference", "model_name", "-24h", llm_filters)
            active_models_count = len(model_usage_dict) if model_usage_dict else 0
            
            llm = LLMMetrics(
                active_models=MetricValue(
                    value=active_models_count, 
                    unit="models", 
                    status="healthy"
                ),
                ttft=MetricValue(value=round(llm_ttft, 2) if llm_ttft > 0 else 0, unit="s", status="healthy"),
                tps=MetricValue(value=tps_value, unit="tokens/s", status="healthy"),
                e2e_latency=MetricValue(
                    value=round(llm_latency, 2) if llm_latency > 0 else 0, 
                    unit="s", 
                    status="healthy",
                    trend=round(llm_latency_trend, 2),
                    sparkline_data=e2e_sparkline_seconds
                ),
                rps=MetricValue(value=round(rps_value, 2), unit="req/s", status="healthy"),
                success_rate=MetricValue(value=success_rate_value, unit="%", status="healthy"),
                total_tokens_24h=int(total_tokens) if total_tokens > 0 else 0,
                total_requests_24h=llm_count,
                avg_prompt_length=MetricValue(value=round(avg_prompt_tokens, 1) if avg_prompt_tokens > 0 else 0, unit="tokens", status="healthy"),
                avg_response_length=MetricValue(value=round(avg_response_tokens, 1) if avg_response_tokens > 0 else 0, unit="tokens", status="healthy"),
                model_usage=model_usage_dict
            )
            
            # NER Metrics
            ner_filters = {**filters, "task_type": "ner"}
            ner_count_24h = client.count_points("model_inference", "-24h", ner_filters)
            ner_count_1h = client.count_points("model_inference", "-1h", ner_filters)
            ner_count_7d = client.count_points("model_inference", "-7d", ner_filters)
            
            # Latency metrics with averages
            ner_latency_current = client.mean_field("model_inference", "duration_ms_f", "-1h", ner_filters)
            ner_latency_1h = client.mean_field("model_inference", "duration_ms_f", "-1h", ner_filters)
            ner_latency_24h = client.mean_field("model_inference", "duration_ms_f", "-24h", ner_filters)
            ner_latency_7d = client.mean_field("model_inference", "duration_ms_f", "-7d", ner_filters)
            
            # P99 latency
            ner_p99 = client.percentile_field("model_inference", "duration_ms_f", 0.99, "-24h", ner_filters)
            
            # Total entities extracted (sum of entities_count_i field)
            total_entities_query = f'''
                from(bucket: "aico_telemetry")
                |> range(start: -24h)
                |> filter(fn: (r) => r._measurement == "model_inference")
                |> filter(fn: (r) => r._field == "entities_count_i")
                |> filter(fn: (r) => r.service == "modelservice")
                |> filter(fn: (r) => r.task_type == "ner")
                |> sum()
            '''
            entities_result = client.query(total_entities_query)
            total_entities_24h = int(entities_result[0].get('value', 0)) if entities_result else 0
            
            # Average entities per request
            avg_entities = (total_entities_24h / ner_count_24h) if ner_count_24h > 0 else 0.0
            
            # Success rate (count success_b=true vs total)
            success_query = f'''
                from(bucket: "aico_telemetry")
                |> range(start: -24h)
                |> filter(fn: (r) => r._measurement == "model_inference")
                |> filter(fn: (r) => r._field == "success_b")
                |> filter(fn: (r) => r.service == "modelservice")
                |> filter(fn: (r) => r.task_type == "ner")
                |> filter(fn: (r) => r._value == true)
                |> count()
            '''
            success_result = client.query(success_query)
            success_count = int(success_result[0].get('value', 0)) if success_result else 0
            success_rate = (success_count / ner_count_24h * 100) if ner_count_24h > 0 else 100.0
            
            # Entity type distribution (parse entity_types_s field)
            # This would require more complex parsing - for now use aggregated counts
            entity_types_query = f'''
                from(bucket: "aico_telemetry")
                |> range(start: -24h)
                |> filter(fn: (r) => r._measurement == "model_inference")
                |> filter(fn: (r) => r._field == "entity_types_s")
                |> filter(fn: (r) => r.service == "modelservice")
                |> filter(fn: (r) => r.task_type == "ner")
                |> count()
            '''
            # Simplified: return empty dict if no data, would need proper parsing
            entity_type_distribution = {}
            
            ner = NERMetrics(
                inference_rate=MetricValue(
                    value=round(ner_count_24h / 86400, 4),
                    unit="req/s",
                    status="healthy",
                    avg_1h=round(ner_count_1h / 3600, 4),
                    avg_24h=round(ner_count_24h / 86400, 4),
                    avg_7d=round(ner_count_7d / 604800, 4)
                ),
                avg_latency=MetricValue(
                    value=round(ner_latency_current / 1000, 3),  # Convert ms to seconds
                    unit="s",
                    status=get_metric_status(ner_latency_current, {"warning": 500, "critical": 1000}),
                    avg_1h=round(ner_latency_1h / 1000, 3),
                    avg_24h=round(ner_latency_24h / 1000, 3),
                    avg_7d=round(ner_latency_7d / 1000, 3)
                ),
                p99_latency=round(ner_p99 / 1000, 3) if ner_p99 else None,  # Convert to seconds
                total_entities_24h=total_entities_24h,
                total_requests_24h=ner_count_24h,
                avg_entities_per_request=MetricValue(
                    value=round(avg_entities, 1),
                    unit="entities",
                    status="healthy"
                ),
                success_rate=MetricValue(
                    value=round(success_rate, 1),
                    unit="%",
                    status="healthy" if success_rate > 95 else "warning"
                ),
                entity_type_distribution=entity_type_distribution
            )
            
            # Sentiment Metrics
            sentiment_filters = {**filters, "task_type": "sentiment"}
            sentiment_count_24h = client.count_points("model_inference", "-24h", sentiment_filters)
            sentiment_count_1h = client.count_points("model_inference", "-1h", sentiment_filters)
            sentiment_count_7d = client.count_points("model_inference", "-7d", sentiment_filters)
            
            # Latency metrics with averages
            sentiment_latency_current = client.mean_field("model_inference", "duration_ms_f", "-1m", sentiment_filters)
            sentiment_latency_1h = client.mean_field("model_inference", "duration_ms_f", "-1h", sentiment_filters)
            sentiment_latency_24h = client.mean_field("model_inference", "duration_ms_f", "-24h", sentiment_filters)
            sentiment_latency_7d = client.mean_field("model_inference", "duration_ms_f", "-7d", sentiment_filters)
            
            # P99 latency
            sentiment_p99 = client.percentile_field("model_inference", "duration_ms_f", 0.99, "-24h", sentiment_filters)
            
            # Average confidence score
            avg_confidence_query = f'''
                from(bucket: "aico_telemetry")
                |> range(start: -24h)
                |> filter(fn: (r) => r._measurement == "model_inference")
                |> filter(fn: (r) => r._field == "confidence_score_f")
                |> filter(fn: (r) => r.service == "modelservice")
                |> filter(fn: (r) => r.task_type == "sentiment")
                |> mean()
            '''
            confidence_result = client.query(avg_confidence_query)
            avg_confidence = confidence_result[0].get('value', 0.0) if confidence_result else 0.0
            
            # Success rate
            sentiment_success_query = f'''
                from(bucket: "aico_telemetry")
                |> range(start: -24h)
                |> filter(fn: (r) => r._measurement == "model_inference")
                |> filter(fn: (r) => r._field == "success_b")
                |> filter(fn: (r) => r.service == "modelservice")
                |> filter(fn: (r) => r.task_type == "sentiment")
                |> filter(fn: (r) => r._value == "true")
                |> count()
            '''
            sentiment_success_result = client.query(sentiment_success_query)
            sentiment_success_count = int(sentiment_success_result[0].get('value', 0)) if sentiment_success_result else 0
            sentiment_success_rate = (sentiment_success_count / sentiment_count_24h * 100) if sentiment_count_24h > 0 else 100.0
            
            # Sentiment distribution (count by sentiment_result_s field)
            # Note: We need to get all values and count them in Python since Flux doesn't
            # support grouping by field values directly for string fields
            sentiment_dist_query = f'''
                from(bucket: "aico_telemetry")
                |> range(start: -24h)
                |> filter(fn: (r) => r._measurement == "model_inference")
                |> filter(fn: (r) => r._field == "sentiment_result_s")
                |> filter(fn: (r) => r.service == "modelservice")
                |> filter(fn: (r) => r.task_type == "sentiment")
            '''
            sentiment_dist_results = client.query(sentiment_dist_query)
            sentiment_distribution = {}
            for result in sentiment_dist_results:
                sentiment_label = result.get('_value', 'unknown')
                if isinstance(sentiment_label, str):
                    sentiment_label = sentiment_label.strip('"')  # Remove quotes from string field
                sentiment_distribution[sentiment_label] = sentiment_distribution.get(sentiment_label, 0) + 1
            
            sentiment = SentimentMetrics(
                inference_rate=MetricValue(
                    value=round(sentiment_count_24h / 86400, 4),
                    unit="req/s",
                    status="healthy",
                    avg_1h=round(sentiment_count_1h / 3600, 4),
                    avg_24h=round(sentiment_count_24h / 86400, 4),
                    avg_7d=round(sentiment_count_7d / 604800, 4)
                ),
                avg_latency=MetricValue(
                    value=round(sentiment_latency_current / 1000, 3),  # Convert ms to seconds
                    unit="s",
                    status=get_metric_status(sentiment_latency_current, {"warning": 500, "critical": 1000}),
                    avg_1h=round(sentiment_latency_1h / 1000, 3),
                    avg_24h=round(sentiment_latency_24h / 1000, 3),
                    avg_7d=round(sentiment_latency_7d / 1000, 3)
                ),
                p99_latency=round(sentiment_p99 / 1000, 3) if sentiment_p99 else None,  # Convert to seconds
                total_analyses_24h=sentiment_count_24h,
                avg_confidence=MetricValue(
                    value=round(avg_confidence, 2),
                    unit="score",
                    status="healthy" if avg_confidence > 0.7 else "warning"
                ),
                success_rate=MetricValue(
                    value=round(sentiment_success_rate, 1),
                    unit="%",
                    status="healthy" if sentiment_success_rate > 95 else "warning"
                ),
                sentiment_distribution=sentiment_distribution
            )
            
            # Embeddings Metrics
            embeddings_filters = {**filters, "task_type": "embedding"}
            embeddings_count_24h = client.count_points("model_inference", "-24h", embeddings_filters)
            embeddings_count_1h = client.count_points("model_inference", "-1h", embeddings_filters)
            
            # Latency metrics
            embeddings_latency_current = client.mean_field("model_inference", "duration_ms_f", "-1h", embeddings_filters)
            embeddings_latency_24h = client.mean_field("model_inference", "duration_ms_f", "-24h", embeddings_filters)
            
            # P99 latency
            embeddings_p99 = client.percentile_field("model_inference", "duration_ms_f", 0.99, "-24h", embeddings_filters)
            
            # Success rate
            embeddings_success_query = f'''
                from(bucket: "aico_telemetry")
                |> range(start: -24h)
                |> filter(fn: (r) => r._measurement == "model_inference")
                |> filter(fn: (r) => r._field == "success_b")
                |> filter(fn: (r) => r.service == "modelservice")
                |> filter(fn: (r) => r.task_type == "embedding")
                |> filter(fn: (r) => r._value == true)
                |> count()
            '''
            embeddings_success_result = client.query(embeddings_success_query)
            embeddings_success_count = int(embeddings_success_result[0].get('value', 0)) if embeddings_success_result else 0
            embeddings_success_rate = (embeddings_success_count / embeddings_count_24h * 100) if embeddings_count_24h > 0 else 100.0
            
            # Calculate throughput (embeddings per second in last hour)
            embeddings_throughput = round(embeddings_count_1h / 3600, 4) if embeddings_count_1h > 0 else 0.0
            
            embeddings = EmbeddingsMetrics(
                inference_rate=MetricValue(
                    value=round(embeddings_count_24h / 86400, 6) if embeddings_count_24h > 0 else 0.0,
                    unit="emb/s",
                    status="healthy",
                    avg_1h=round(embeddings_count_1h / 3600, 6) if embeddings_count_1h > 0 else 0.0,
                    avg_24h=round(embeddings_count_24h / 86400, 6) if embeddings_count_24h > 0 else 0.0
                ),
                avg_latency=MetricValue(
                    value=round(embeddings_latency_current, 2),
                    unit="ms",
                    status=get_metric_status(embeddings_latency_current, {"warning": 100, "critical": 500}),
                    avg_1h=round(embeddings_latency_current, 2),
                    avg_24h=round(embeddings_latency_24h, 2)
                ),
                p99_latency=round(embeddings_p99, 2) if embeddings_p99 else None,
                throughput=MetricValue(
                    value=embeddings_throughput,
                    unit="emb/s",
                    status="healthy"
                ),
                total_embeddings_24h=embeddings_count_24h,
                avg_input_length=MetricValue(
                    value=0,
                    unit="tokens",
                    status="healthy"
                ),
                success_rate=MetricValue(
                    value=round(embeddings_success_rate, 1),
                    unit="%",
                    status="healthy" if embeddings_success_rate > 95 else "warning"
                ),
                vector_dimension=768
            )
            
            return ModelserviceMetrics(
                llm=llm,
                ner=ner,
                sentiment=sentiment,
                embeddings=embeddings
            )
    
    except Exception as e:
        # If InfluxDB is empty or has no data, return zero metrics instead of failing
        logger.error(f"InfluxDB query failed, returning zero metrics: {e}", exc_info=True)
        
        # Return empty/zero metrics matching the schema
        return ModelserviceMetrics(
            llm=LLMMetrics(
                active_models=MetricValue(value=0.0, unit="models", status="healthy"),
                ttft=MetricValue(value=0.0, unit="ms", status="healthy"),
                tps=MetricValue(value=0.0, unit="tokens/s", status="healthy"),
                e2e_latency=MetricValue(value=0.0, unit="ms", status="healthy"),
                rps=MetricValue(value=0.0, unit="req/s", status="healthy"),
                success_rate=MetricValue(value=100.0, unit="%", status="healthy"),
                total_tokens_24h=0,
                total_requests_24h=0,
                avg_prompt_length=MetricValue(value=0.0, unit="tokens", status="healthy"),
                avg_response_length=MetricValue(value=0.0, unit="tokens", status="healthy"),
                model_usage={}
            ),
            ner=NERMetrics(
                inference_rate=MetricValue(value=0.0, unit="req/s", status="healthy"),
                avg_latency=MetricValue(value=0.0, unit="s", status="healthy"),
                total_entities_24h=0,
                total_requests_24h=0,
                avg_entities_per_request=MetricValue(value=0.0, unit="entities", status="healthy"),
                success_rate=MetricValue(value=100.0, unit="%", status="healthy"),
                entity_type_distribution={}
            ),
            sentiment=SentimentMetrics(
                inference_rate=MetricValue(value=0.0, unit="req/s", status="healthy"),
                avg_latency=MetricValue(value=0.0, unit="s", status="healthy"),
                total_analyses_24h=0,
                avg_confidence=MetricValue(value=0.0, unit="score", status="healthy"),
                success_rate=MetricValue(value=100.0, unit="%", status="healthy"),
                sentiment_distribution={}
            ),
            embeddings=EmbeddingsMetrics(
                inference_rate=MetricValue(value=0.0, unit="emb/s", status="healthy"),
                avg_latency=MetricValue(value=0.0, unit="ms", status="healthy"),
                throughput=MetricValue(value=0.0, unit="tokens/s", status="healthy"),
                total_embeddings_24h=0,
                avg_input_length=MetricValue(value=0.0, unit="tokens", status="healthy"),
                success_rate=MetricValue(value=100.0, unit="%", status="healthy"),
                vector_dimension=768
            )
        )
