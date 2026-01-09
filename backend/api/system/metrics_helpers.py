"""
Helper functions for calculating modelservice metrics.

Separates LLM metrics from specialized inference model metrics.
"""

import time
from typing import Dict, Tuple, Optional, Any
import numpy as np
from aico.core.logging import get_logger

logger = get_logger("backend", "api.system.metrics_helpers")


def calculate_percentile(values: list, percentile: float) -> Optional[float]:
    """Calculate percentile from a list of values."""
    if not values:
        return None
    return float(np.percentile(values, percentile))


def calculate_llm_metrics(db_connection, cutoff_1h: float, cutoff_24h: float, cutoff_7d: float) -> Dict[str, Any]:
    """
    Calculate LLM (Ollama) specific metrics.
    
    Metrics include:
    - TTFT (Time to First Token)
    - TPS (Tokens Per Second)
    - E2E Latency
    - RPS (Requests Per Second)
    - Success Rate
    - Prompt/Response lengths
    - P95/P99 latencies
    """
    try:
        # Query LLM-specific data (task_type = 'completion' or 'chat')
        # Current period (1h)
        result = db_connection.execute(
            """SELECT 
                COUNT(*) as count,
                SUM(COALESCE(tokens_generated, 0)) as total_tokens,
                AVG(inference_time_ms) as avg_latency_ms,
                AVG(COALESCE(tokens_generated, 0)) as avg_response_length,
                SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as success_count,
                MIN(timestamp) as min_ts,
                MAX(timestamp) as max_ts
               FROM otel_model_inferences 
               WHERE timestamp > ? 
               AND task_type IN ('completion', 'chat', 'chat_streaming')""",
            (cutoff_1h,)
        ).fetchone()
        
        if result and result[0] > 0:
            count, total_tokens, avg_latency_ms, avg_response_length, success_count, min_ts, max_ts = result
            time_span = max_ts - min_ts if max_ts > min_ts else 3600.0
            
            # Core metrics
            tps = (total_tokens or 0) / time_span if time_span > 0 else 0.0
            rps = count / time_span if time_span > 0 else 0.0
            e2e_latency = (avg_latency_ms or 0) / 1000.0
            success_rate = (success_count / count * 100) if count > 0 else 0.0
            
            # Get latency distribution for P95/P99
            latencies = db_connection.execute(
                """SELECT inference_time_ms FROM otel_model_inferences 
                   WHERE timestamp > ? AND task_type IN ('completion', 'chat', 'chat_streaming')
                   AND inference_time_ms IS NOT NULL""",
                (cutoff_1h,)
            ).fetchall()
            latency_values = [row[0] / 1000.0 for row in latencies]  # Convert to seconds
            p95_latency = calculate_percentile(latency_values, 95)
            p99_latency = calculate_percentile(latency_values, 99)
            
            # TTFT - if we have it recorded (will be None initially)
            ttft_result = db_connection.execute(
                """SELECT AVG(ttft) FROM otel_model_inferences 
                   WHERE timestamp > ? AND ttft IS NOT NULL
                   AND task_type IN ('completion', 'chat', 'chat_streaming')""",
                (cutoff_1h,)
            ).fetchone()
            ttft = ttft_result[0] if ttft_result and ttft_result[0] else None
            
            # Prompt length (if recorded)
            prompt_result = db_connection.execute(
                """SELECT AVG(prompt_tokens) FROM otel_model_inferences 
                   WHERE timestamp > ? AND prompt_tokens > 0
                   AND task_type IN ('completion', 'chat', 'chat_streaming')""",
                (cutoff_1h,)
            ).fetchone()
            avg_prompt_length = prompt_result[0] if prompt_result and prompt_result[0] else 0.0
            
        else:
            tps = rps = e2e_latency = success_rate = 0.0
            ttft = p95_latency = p99_latency = None
            avg_prompt_length = avg_response_length = 0.0
            count = total_tokens = 0
        
        # 24h totals
        result_24h = db_connection.execute(
            """SELECT COUNT(*), SUM(COALESCE(tokens_generated, 0))
               FROM otel_model_inferences 
               WHERE timestamp > ? 
               AND task_type IN ('completion', 'chat', 'chat_streaming')""",
            (cutoff_24h,)
        ).fetchone()
        total_requests_24h = result_24h[0] if result_24h else 0
        total_tokens_24h = result_24h[1] if result_24h and result_24h[1] else 0
        
        # Model usage distribution (24h)
        model_usage_result = db_connection.execute(
            """SELECT model_name, COUNT(*) as count 
               FROM otel_model_inferences 
               WHERE timestamp > ? 
               AND task_type IN ('completion', 'chat', 'chat_streaming')
               GROUP BY model_name 
               ORDER BY count DESC""",
            (cutoff_24h,)
        )
        model_usage = {row[0]: row[1] for row in model_usage_result.fetchall()}
        
        # Historical averages (1h, 24h, 7d)
        def get_period_metrics(cutoff: float, period_seconds: float) -> Tuple[Optional[float], Optional[float], Optional[float], Optional[float]]:
            result = db_connection.execute(
                """SELECT COUNT(*), SUM(COALESCE(tokens_generated, 0)), 
                          AVG(inference_time_ms), MIN(timestamp), MAX(timestamp)
                   FROM otel_model_inferences 
                   WHERE timestamp > ? 
                   AND task_type IN ('completion', 'chat', 'chat_streaming')""",
                (cutoff,)
            ).fetchone()
            
            if result and result[0] > 0:
                cnt, tokens, avg_lat, min_ts, max_ts = result
                span = max_ts - min_ts if max_ts and min_ts and max_ts > min_ts else period_seconds
                return (
                    (tokens or 0) / span,  # TPS
                    cnt / span,  # RPS
                    (avg_lat or 0) / 1000.0,  # E2E latency
                    None  # TTFT (calculate separately if needed)
                )
            return None, None, None, None
        
        tps_1h, rps_1h, e2e_1h, _ = get_period_metrics(cutoff_1h, 3600.0)
        tps_24h, rps_24h, e2e_24h, _ = get_period_metrics(cutoff_24h, 86400.0)
        tps_7d, rps_7d, e2e_7d, _ = get_period_metrics(cutoff_7d, 604800.0)
        
        return {
            "tps": tps,
            "rps": rps,
            "e2e_latency": e2e_latency,
            "ttft": ttft or 0.0,  # Default to 0 if not available
            "success_rate": success_rate,
            "total_tokens_24h": total_tokens_24h,
            "total_requests_24h": total_requests_24h,
            "avg_prompt_length": avg_prompt_length,
            "avg_response_length": avg_response_length or 0.0,
            "model_usage": model_usage,
            "p95_latency": p95_latency,
            "p99_latency": p99_latency,
            "tps_1h": tps_1h,
            "tps_24h": tps_24h,
            "tps_7d": tps_7d,
            "rps_1h": rps_1h,
            "rps_24h": rps_24h,
            "rps_7d": rps_7d,
            "e2e_1h": e2e_1h,
            "e2e_24h": e2e_24h,
            "e2e_7d": e2e_7d,
        }
        
    except Exception as e:
        logger.exception(f"Error calculating LLM metrics: {e}")
        return {
            "tps": 0.0, "rps": 0.0, "e2e_latency": 0.0, "ttft": 0.0,
            "success_rate": 0.0, "total_tokens_24h": 0, "total_requests_24h": 0,
            "avg_prompt_length": 0.0, "avg_response_length": 0.0,
            "model_usage": {}, "p95_latency": None, "p99_latency": None,
            "tps_1h": None, "tps_24h": None, "tps_7d": None,
            "rps_1h": None, "rps_24h": None, "rps_7d": None,
            "e2e_1h": None, "e2e_24h": None, "e2e_7d": None,
        }


def calculate_ner_metrics(db_connection, cutoff_1h: float, cutoff_24h: float, cutoff_7d: float) -> Dict[str, Any]:
    """Calculate NER (Named Entity Recognition) specific metrics."""
    try:
        # Current period (1h)
        result = db_connection.execute(
            """SELECT 
                COUNT(*) as count,
                AVG(inference_time_ms) as avg_latency_ms,
                SUM(entities_count) as total_entities,
                SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as success_count,
                MIN(timestamp) as min_ts,
                MAX(timestamp) as max_ts
               FROM otel_model_inferences 
               WHERE timestamp > ? 
               AND task_type = 'ner'""",
            (cutoff_1h,)
        ).fetchone()
        
        if result and result[0] > 0:
            count, avg_latency_ms, total_entities, success_count, min_ts, max_ts = result
            time_span = max_ts - min_ts if max_ts > min_ts else 3600.0
            
            inference_rate = count / time_span if time_span > 0 else 0.0
            avg_latency = (avg_latency_ms or 0) / 1000.0
            avg_entities = (total_entities or 0) / count if count > 0 else 0.0
            success_rate = (success_count / count * 100) if count > 0 else 0.0
            
            # P95/P99 latencies
            latencies = db_connection.execute(
                """SELECT inference_time_ms FROM otel_model_inferences 
                   WHERE timestamp > ? AND task_type = 'ner'
                   AND inference_time_ms IS NOT NULL""",
                (cutoff_1h,)
            ).fetchall()
            latency_values = [row[0] / 1000.0 for row in latencies]
            p95_latency = calculate_percentile(latency_values, 95)
            p99_latency = calculate_percentile(latency_values, 99)
        else:
            inference_rate = avg_latency = avg_entities = success_rate = 0.0
            p95_latency = p99_latency = None
            total_entities = count = 0
        
        # 24h totals
        result_24h = db_connection.execute(
            """SELECT COUNT(*), SUM(entities_count)
               FROM otel_model_inferences 
               WHERE timestamp > ? AND task_type = 'ner'""",
            (cutoff_24h,)
        ).fetchone()
        total_requests_24h = result_24h[0] if result_24h else 0
        total_entities_24h = result_24h[1] if result_24h and result_24h[1] else 0
        
        # Entity type distribution (24h)
        # Note: entity_types stored as comma-separated string
        entity_types_result = db_connection.execute(
            """SELECT entity_types FROM otel_model_inferences 
               WHERE timestamp > ? AND task_type = 'ner'
               AND entity_types IS NOT NULL""",
            (cutoff_24h,)
        ).fetchall()
        
        entity_type_dist = {}
        for row in entity_types_result:
            if row[0]:
                types = row[0].split(',')
                for entity_type in types:
                    entity_type = entity_type.strip()
                    entity_type_dist[entity_type] = entity_type_dist.get(entity_type, 0) + 1
        
        # Historical averages
        def get_period_metrics(cutoff: float, period_seconds: float) -> Tuple[Optional[float], Optional[float]]:
            result = db_connection.execute(
                """SELECT COUNT(*), AVG(inference_time_ms), MIN(timestamp), MAX(timestamp)
                   FROM otel_model_inferences 
                   WHERE timestamp > ? AND task_type = 'ner'""",
                (cutoff,)
            ).fetchone()
            
            if result and result[0] > 0:
                cnt, avg_lat, min_ts, max_ts = result
                span = max_ts - min_ts if max_ts and min_ts and max_ts > min_ts else period_seconds
                return cnt / span, (avg_lat or 0) / 1000.0
            return None, None
        
        rate_1h, lat_1h = get_period_metrics(cutoff_1h, 3600.0)
        rate_24h, lat_24h = get_period_metrics(cutoff_24h, 86400.0)
        rate_7d, lat_7d = get_period_metrics(cutoff_7d, 604800.0)
        
        return {
            "inference_rate": inference_rate,
            "avg_latency": avg_latency,
            "p95_latency": p95_latency,
            "p99_latency": p99_latency,
            "total_entities_24h": total_entities_24h,
            "total_requests_24h": total_requests_24h,
            "avg_entities_per_request": avg_entities,
            "success_rate": success_rate,
            "entity_type_distribution": entity_type_dist,
            "rate_1h": rate_1h,
            "rate_24h": rate_24h,
            "rate_7d": rate_7d,
            "lat_1h": lat_1h,
            "lat_24h": lat_24h,
            "lat_7d": lat_7d,
        }
        
    except Exception as e:
        logger.exception(f"Error calculating NER metrics: {e}")
        return {
            "inference_rate": 0.0, "avg_latency": 0.0,
            "p95_latency": None, "p99_latency": None,
            "total_entities_24h": 0, "total_requests_24h": 0,
            "avg_entities_per_request": 0.0, "success_rate": 0.0,
            "entity_type_distribution": {},
            "rate_1h": None, "rate_24h": None, "rate_7d": None,
            "lat_1h": None, "lat_24h": None, "lat_7d": None,
        }


def calculate_sentiment_metrics(db_connection, cutoff_1h: float, cutoff_24h: float, cutoff_7d: float) -> Dict[str, Any]:
    """Calculate Sentiment Analysis specific metrics."""
    try:
        # Current period (1h)
        result = db_connection.execute(
            """SELECT 
                COUNT(*) as count,
                AVG(inference_time_ms) as avg_latency_ms,
                AVG(confidence_score) as avg_confidence,
                SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as success_count,
                MIN(timestamp) as min_ts,
                MAX(timestamp) as max_ts
               FROM otel_model_inferences 
               WHERE timestamp > ? 
               AND task_type = 'sentiment'""",
            (cutoff_1h,)
        ).fetchone()
        
        if result and result[0] > 0:
            count, avg_latency_ms, avg_confidence, success_count, min_ts, max_ts = result
            time_span = max_ts - min_ts if max_ts > min_ts else 3600.0
            
            inference_rate = count / time_span if time_span > 0 else 0.0
            avg_latency = (avg_latency_ms or 0) / 1000.0
            success_rate = (success_count / count * 100) if count > 0 else 0.0
            
            # P95/P99 latencies
            latencies = db_connection.execute(
                """SELECT inference_time_ms FROM otel_model_inferences 
                   WHERE timestamp > ? AND task_type = 'sentiment'
                   AND inference_time_ms IS NOT NULL""",
                (cutoff_1h,)
            ).fetchall()
            latency_values = [row[0] / 1000.0 for row in latencies]
            p95_latency = calculate_percentile(latency_values, 95)
            p99_latency = calculate_percentile(latency_values, 99)
        else:
            inference_rate = avg_latency = avg_confidence = success_rate = 0.0
            p95_latency = p99_latency = None
            count = 0
        
        # 24h totals
        result_24h = db_connection.execute(
            """SELECT COUNT(*) FROM otel_model_inferences 
               WHERE timestamp > ? AND task_type = 'sentiment'""",
            (cutoff_24h,)
        ).fetchone()
        total_analyses_24h = result_24h[0] if result_24h else 0
        
        # Sentiment distribution (24h)
        sentiment_dist_result = db_connection.execute(
            """SELECT sentiment_result, COUNT(*) as count
               FROM otel_model_inferences 
               WHERE timestamp > ? AND task_type = 'sentiment'
               AND sentiment_result IS NOT NULL
               GROUP BY sentiment_result""",
            (cutoff_24h,)
        )
        sentiment_distribution = {row[0]: row[1] for row in sentiment_dist_result.fetchall()}
        
        # Historical averages
        def get_period_metrics(cutoff: float, period_seconds: float) -> Tuple[Optional[float], Optional[float]]:
            result = db_connection.execute(
                """SELECT COUNT(*), AVG(inference_time_ms), MIN(timestamp), MAX(timestamp)
                   FROM otel_model_inferences 
                   WHERE timestamp > ? AND task_type = 'sentiment'""",
                (cutoff,)
            ).fetchone()
            
            if result and result[0] > 0:
                cnt, avg_lat, min_ts, max_ts = result
                span = max_ts - min_ts if max_ts and min_ts and max_ts > min_ts else period_seconds
                return cnt / span, (avg_lat or 0) / 1000.0
            return None, None
        
        rate_1h, lat_1h = get_period_metrics(cutoff_1h, 3600.0)
        rate_24h, lat_24h = get_period_metrics(cutoff_24h, 86400.0)
        rate_7d, lat_7d = get_period_metrics(cutoff_7d, 604800.0)
        
        return {
            "inference_rate": inference_rate,
            "avg_latency": avg_latency,
            "p95_latency": p95_latency,
            "p99_latency": p99_latency,
            "total_analyses_24h": total_analyses_24h,
            "avg_confidence": avg_confidence or 0.0,
            "success_rate": success_rate,
            "sentiment_distribution": sentiment_distribution,
            "rate_1h": rate_1h,
            "rate_24h": rate_24h,
            "rate_7d": rate_7d,
            "lat_1h": lat_1h,
            "lat_24h": lat_24h,
            "lat_7d": lat_7d,
        }
        
    except Exception as e:
        logger.exception(f"Error calculating sentiment metrics: {e}")
        return {
            "inference_rate": 0.0, "avg_latency": 0.0,
            "p95_latency": None, "p99_latency": None,
            "total_analyses_24h": 0, "avg_confidence": 0.0,
            "success_rate": 0.0, "sentiment_distribution": {},
            "rate_1h": None, "rate_24h": None, "rate_7d": None,
            "lat_1h": None, "lat_24h": None, "lat_7d": None,
        }


def calculate_embeddings_metrics(db_connection, cutoff_1h: float, cutoff_24h: float, cutoff_7d: float) -> Dict[str, Any]:
    """Calculate Embeddings generation specific metrics."""
    try:
        # Current period (1h)
        result = db_connection.execute(
            """SELECT 
                COUNT(*) as count,
                AVG(inference_time_ms) as avg_latency_ms,
                AVG(prompt_tokens) as avg_input_length,
                SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as success_count,
                MIN(timestamp) as min_ts,
                MAX(timestamp) as max_ts
               FROM otel_model_inferences 
               WHERE timestamp > ? 
               AND task_type = 'embedding'""",
            (cutoff_1h,)
        ).fetchone()
        
        if result and result[0] > 0:
            count, avg_latency_ms, avg_input_length, success_count, min_ts, max_ts = result
            time_span = max_ts - min_ts if max_ts > min_ts else 3600.0
            
            inference_rate = count / time_span if time_span > 0 else 0.0
            avg_latency = (avg_latency_ms or 0) / 1000.0
            success_rate = (success_count / count * 100) if count > 0 else 0.0
            
            # Throughput (input tokens/s)
            total_input_tokens = db_connection.execute(
                """SELECT SUM(prompt_tokens) FROM otel_model_inferences 
                   WHERE timestamp > ? AND task_type = 'embedding'
                   AND prompt_tokens > 0""",
                (cutoff_1h,)
            ).fetchone()[0] or 0
            throughput = total_input_tokens / time_span if time_span > 0 else 0.0
            
            # P95/P99 latencies
            latencies = db_connection.execute(
                """SELECT inference_time_ms FROM otel_model_inferences 
                   WHERE timestamp > ? AND task_type = 'embedding'
                   AND inference_time_ms IS NOT NULL""",
                (cutoff_1h,)
            ).fetchall()
            latency_values = [row[0] / 1000.0 for row in latencies]
            p95_latency = calculate_percentile(latency_values, 95)
            p99_latency = calculate_percentile(latency_values, 99)
        else:
            inference_rate = avg_latency = throughput = success_rate = 0.0
            avg_input_length = 0.0
            p95_latency = p99_latency = None
            count = 0
        
        # 24h totals
        result_24h = db_connection.execute(
            """SELECT COUNT(*) FROM otel_model_inferences 
               WHERE timestamp > ? AND task_type = 'embedding'""",
            (cutoff_24h,)
        ).fetchone()
        total_embeddings_24h = result_24h[0] if result_24h else 0
        
        # Historical averages
        def get_period_metrics(cutoff: float, period_seconds: float) -> Tuple[Optional[float], Optional[float]]:
            result = db_connection.execute(
                """SELECT COUNT(*), AVG(inference_time_ms), MIN(timestamp), MAX(timestamp)
                   FROM otel_model_inferences 
                   WHERE timestamp > ? AND task_type = 'embedding'""",
                (cutoff,)
            ).fetchone()
            
            if result and result[0] > 0:
                cnt, avg_lat, min_ts, max_ts = result
                span = max_ts - min_ts if max_ts and min_ts and max_ts > min_ts else period_seconds
                return cnt / span, (avg_lat or 0) / 1000.0
            return None, None
        
        rate_1h, lat_1h = get_period_metrics(cutoff_1h, 3600.0)
        rate_24h, lat_24h = get_period_metrics(cutoff_24h, 86400.0)
        rate_7d, lat_7d = get_period_metrics(cutoff_7d, 604800.0)
        
        return {
            "inference_rate": inference_rate,
            "avg_latency": avg_latency,
            "p95_latency": p95_latency,
            "p99_latency": p99_latency,
            "throughput": throughput,
            "total_embeddings_24h": total_embeddings_24h,
            "avg_input_length": avg_input_length or 0.0,
            "success_rate": success_rate,
            "vector_dimension": 768,  # Standard for sentence-transformers
            "rate_1h": rate_1h,
            "rate_24h": rate_24h,
            "rate_7d": rate_7d,
            "lat_1h": lat_1h,
            "lat_24h": lat_24h,
            "lat_7d": lat_7d,
        }
        
    except Exception as e:
        logger.exception(f"Error calculating embeddings metrics: {e}")
        return {
            "inference_rate": 0.0, "avg_latency": 0.0,
            "p95_latency": None, "p99_latency": None,
            "throughput": 0.0, "total_embeddings_24h": 0,
            "avg_input_length": 0.0, "success_rate": 0.0,
            "vector_dimension": 768,
            "rate_1h": None, "rate_24h": None, "rate_7d": None,
            "lat_1h": None, "lat_24h": None, "lat_7d": None,
        }
