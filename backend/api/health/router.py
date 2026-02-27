"""
Health Management API Router

REST API endpoints for system health monitoring, readiness checks, and diagnostics.
"""

from fastapi import APIRouter, HTTPException
from datetime import datetime, UTC
from typing import Dict, Any, List

import psutil
import time
from pydantic import BaseModel

from aico.core.logging import get_logger
from aico.core.version import get_backend_version, get_modelservice_version
from .schemas import (
    HealthResponse, DetailedHealthResponse, ReadinessResponse, 
    LivenessResponse, SystemMetrics, ComponentHealth, 
    DatabaseHealth, MessageBusHealth
)
from aico.core.bus import MessageBusClient

logger = get_logger("aico.api.health.router")

router = APIRouter()

# These will be injected during app initialization
gateway = None
start_time = time.time()

# Get version from canonical VERSIONS file via shared module
try:
    BACKEND_VERSION = get_backend_version()
except Exception as e:
    logger.warning(f"Failed to read backend version from VERSIONS file: {e}")
    BACKEND_VERSION = "unknown"

try:
    MODELSERVICE_VERSION = get_modelservice_version()
except Exception as e:
    logger.warning(f"Failed to read modelservice version from VERSIONS file: {e}")
    MODELSERVICE_VERSION = "unknown"


# Removed initialize_router - using proper FastAPI dependency injection


@router.get("/", response_model=HealthResponse)
async def health_check():
    """Basic health check endpoint"""
    logger.info("Health check endpoint called")
    return HealthResponse(
        status="healthy",
        version=BACKEND_VERSION,
        service="aico-backend",
        timestamp=datetime.now(UTC).isoformat(),
        components={
            "api": "healthy",
            "gateway": "healthy" if gateway and gateway.running else "unavailable",
            "message_bus": "healthy"
        }
    )


@router.get("/detailed", response_model=DetailedHealthResponse)
async def detailed_health():
    """Detailed health check with system metrics"""
    current_time = datetime.now(UTC)
    uptime = time.time() - start_time
    
    # Get system metrics
    try:
        cpu_percent = psutil.cpu_percent(interval=0)  # Non-blocking, instant measurement
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        load_avg = psutil.getloadavg() if hasattr(psutil, 'getloadavg') else None
    except Exception as e:
        logger.warning(f"Failed to get system metrics: {e}")
        cpu_percent = 0.0
        memory = type('obj', (object,), {'percent': 0.0})()
        disk = type('obj', (object,), {'percent': 0.0})()
        load_avg = None
    
    system_metrics = SystemMetrics(
        cpu_usage=cpu_percent,
        memory_usage=memory.percent,
        disk_usage=disk.percent,
        uptime=uptime,
        load_average=list(load_avg) if load_avg else None
    )
    
    # Check component health
    components = {}
    
    # API Gateway health - if we're responding, the gateway is running
    components["api_gateway"] = ComponentHealth(
        status="healthy",
        uptime=uptime,
        last_check=current_time.isoformat(),
        version=BACKEND_VERSION,
        details={"note": "Gateway is serving this request"}
    )
    
    # Message Bus health - external NATS
    bus_status = "running"
    try:
        client = MessageBusClient("backend_health_probe")
        await client.connect()
        await client.disconnect()
        bus_status = "healthy"
    except Exception as e:
        bus_status = "unavailable"

    components["message_bus"] = ComponentHealth(
        status=bus_status,
        uptime=uptime,
        last_check=current_time.isoformat(),
        version=BACKEND_VERSION,
        details={"note": "NATS is external"}
    )
    
    # Modelservice health
    modelservice_uptime = None
    modelservice_status = "healthy"
    try:
        from backend.services import get_modelservice_client
        from aico.core.config import ConfigurationManager
        
        config = ConfigurationManager()
        modelservice_client = get_modelservice_client(config)
        
        health_data = await modelservice_client.get_health()
        if health_data and health_data.get('success') and health_data.get('uptime_seconds'):
            modelservice_uptime = health_data['uptime_seconds']
    except Exception as e:
        logger.debug(f"Could not poll modelservice uptime: {e}")
        modelservice_status = "unavailable"
    
    components["modelservice"] = ComponentHealth(
        status=modelservice_status,
        uptime=modelservice_uptime,
        last_check=current_time.isoformat(),
        version=MODELSERVICE_VERSION,
        details={"note": "Modelservice is a separate process"}
    )

    # vLLM health - OpenAI-compatible HTTP server
    vllm_version = "unknown"
    vllm_status = "healthy"
    try:
        from aico.core.config import ConfigurationManager
        import httpx

        config = ConfigurationManager()
        vllm_cfg = config.get("llm.vllm", {})

        host = vllm_cfg.get("host", "localhost")
        port = int(vllm_cfg.get("port", 8774))
        base_url = f"http://{host}:{port}"

        async with httpx.AsyncClient(timeout=2.0) as client:
            # Prefer /health if available
            resp = await client.get(f"{base_url}/health")
            if resp.status_code != 200:
                # Fallback to OpenAI models list
                resp = await client.get(f"{base_url}/v1/models")
                if resp.status_code != 200:
                    vllm_status = "unavailable"
    except Exception as e:
        logger.debug(f"Could not detect vLLM availability: {e}")
        vllm_status = "unavailable"

    components["vllm"] = ComponentHealth(
        status=vllm_status,
        uptime=None,
        last_check=current_time.isoformat(),
        version=vllm_version,
        details={"note": "OpenAI-compatible LLM server"}
    )
    
    # Determine overall status
    component_statuses = [comp.status for comp in components.values()]
    if all(status in ["healthy", "running"] for status in component_statuses):
        overall_status = "healthy"
    elif any(status == "error" for status in component_statuses):
        overall_status = "degraded"
    else:
        overall_status = "starting"
    
    return DetailedHealthResponse(
        overall_status=overall_status,
        timestamp=current_time.isoformat(),
        system_metrics=system_metrics,
        components=components
    )


