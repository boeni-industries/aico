"""
Modelservice Metrics API

Provides aggregated metrics for modelservice:
- Active models count
- Inference throughput (tokens/s)
- Average inference time
- CPU utilization
"""

import time
import psutil
from typing import Optional
from fastapi import APIRouter, Depends
from pydantic import BaseModel

from aico.data.libsql.encrypted import EncryptedLibSQLConnection
from backend.api.system.dependencies import get_db_connection

router = APIRouter()


class ModelserviceMetrics(BaseModel):
    """Modelservice metrics response model"""
    active_models: int
    inference_throughput: float  # tokens per second
    avg_inference_time: float  # seconds
    cpu_utilization: float  # percentage
    
    # Time window averages
    throughput_1h: Optional[float] = None
    throughput_24h: Optional[float] = None
    throughput_7d: Optional[float] = None
    
    avg_time_1h: Optional[float] = None
    avg_time_24h: Optional[float] = None
    avg_time_7d: Optional[float] = None


@router.get("/modelservice", response_model=ModelserviceMetrics)
async def get_modelservice_metrics(
    db_connection: EncryptedLibSQLConnection = Depends(get_db_connection)
):
    """
    Get aggregated modelservice metrics.
    
    Returns:
        ModelserviceMetrics with current and historical averages
    """
    now = time.time()
    cutoff_1m = now - 60  # Last 1 minute for current metrics
    cutoff_1h = now - 3600
    cutoff_24h = now - 86400
    cutoff_7d = now - 604800
    
    with db_connection.get_connection() as conn:
        # Get active models (distinct models with inferences in last 5 minutes)
        result = conn.execute(
            """SELECT COUNT(DISTINCT model_name) 
               FROM otel_model_inferences 
               WHERE timestamp > ?""",
            (now - 300,)
        ).fetchone()
        active_models = result[0] if result else 0
        
        # Current metrics (last 1 minute)
        result = conn.execute(
            """SELECT 
                COUNT(*) as count,
                SUM(tokens_generated) as total_tokens,
                AVG(inference_time_ms) as avg_time_ms,
                MIN(timestamp) as min_ts,
                MAX(timestamp) as max_ts
               FROM otel_model_inferences 
               WHERE timestamp > ? AND tokens_generated IS NOT NULL""",
            (cutoff_1m,)
        ).fetchone()
        
        if result and result[0] > 0:
            count, total_tokens, avg_time_ms, min_ts, max_ts = result
            time_span = max_ts - min_ts if max_ts > min_ts else 1.0
            inference_throughput = (total_tokens or 0) / time_span if time_span > 0 else 0.0
            avg_inference_time = (avg_time_ms or 0) / 1000.0  # Convert to seconds
        else:
            inference_throughput = 0.0
            avg_inference_time = 0.0
        
        # 1h averages
        result = conn.execute(
            """SELECT 
                SUM(tokens_generated) as total_tokens,
                AVG(inference_time_ms) as avg_time_ms,
                MIN(timestamp) as min_ts,
                MAX(timestamp) as max_ts
               FROM otel_model_inferences 
               WHERE timestamp > ? AND tokens_generated IS NOT NULL""",
            (cutoff_1h,)
        ).fetchone()
        
        if result and result[0]:
            total_tokens, avg_time_ms, min_ts, max_ts = result
            time_span = max_ts - min_ts if max_ts and min_ts and max_ts > min_ts else 3600.0
            throughput_1h = (total_tokens or 0) / time_span if time_span > 0 else None
            avg_time_1h = (avg_time_ms or 0) / 1000.0 if avg_time_ms else None
        else:
            throughput_1h = None
            avg_time_1h = None
        
        # 24h averages
        result = conn.execute(
            """SELECT 
                SUM(tokens_generated) as total_tokens,
                AVG(inference_time_ms) as avg_time_ms,
                MIN(timestamp) as min_ts,
                MAX(timestamp) as max_ts
               FROM otel_model_inferences 
               WHERE timestamp > ? AND tokens_generated IS NOT NULL""",
            (cutoff_24h,)
        ).fetchone()
        
        if result and result[0]:
            total_tokens, avg_time_ms, min_ts, max_ts = result
            time_span = max_ts - min_ts if max_ts and min_ts and max_ts > min_ts else 86400.0
            throughput_24h = (total_tokens or 0) / time_span if time_span > 0 else None
            avg_time_24h = (avg_time_ms or 0) / 1000.0 if avg_time_ms else None
        else:
            throughput_24h = None
            avg_time_24h = None
        
        # 7d averages
        result = conn.execute(
            """SELECT 
                SUM(tokens_generated) as total_tokens,
                AVG(inference_time_ms) as avg_time_ms,
                MIN(timestamp) as min_ts,
                MAX(timestamp) as max_ts
               FROM otel_model_inferences 
               WHERE timestamp > ? AND tokens_generated IS NOT NULL""",
            (cutoff_7d,)
        ).fetchone()
        
        if result and result[0]:
            total_tokens, avg_time_ms, min_ts, max_ts = result
            time_span = max_ts - min_ts if max_ts and min_ts and max_ts > min_ts else 604800.0
            throughput_7d = (total_tokens or 0) / time_span if time_span > 0 else None
            avg_time_7d = (avg_time_ms or 0) / 1000.0 if avg_time_ms else None
        else:
            throughput_7d = None
            avg_time_7d = None
    
    # Get CPU utilization
    try:
        cpu_utilization = psutil.cpu_percent(interval=0.1)
    except:
        cpu_utilization = 0.0
    
    return ModelserviceMetrics(
        active_models=active_models,
        inference_throughput=inference_throughput,
        avg_inference_time=avg_inference_time,
        cpu_utilization=cpu_utilization,
        throughput_1h=throughput_1h,
        throughput_24h=throughput_24h,
        throughput_7d=throughput_7d,
        avg_time_1h=avg_time_1h,
        avg_time_24h=avg_time_24h,
        avg_time_7d=avg_time_7d
    )
