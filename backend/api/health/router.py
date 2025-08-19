"""
Health Management API Router

REST API endpoints for system health monitoring, readiness checks, and diagnostics.
"""

from fastapi import APIRouter, HTTPException
from datetime import datetime
import psutil
import time
from aico.core.logging import get_logger
from .schemas import (
    HealthResponse, DetailedHealthResponse, ReadinessResponse, 
    LivenessResponse, SystemMetrics, ComponentHealth, 
    DatabaseHealth, MessageBusHealth
)

router = APIRouter()
logger = get_logger("api", "health_router")

# These will be injected during app initialization
gateway = None
message_bus_host = None
start_time = time.time()


def initialize_router(gw, msg_bus):
    """Initialize router with dependencies from main.py"""
    global gateway, message_bus_host
    gateway = gw
    message_bus_host = msg_bus


@router.get("/", response_model=HealthResponse)
async def health_check():
    """Basic health check endpoint"""
    return HealthResponse(
        status="healthy",
        version="0.2.0",
        service="aico-backend",
        timestamp=datetime.utcnow().isoformat(),
        components={
            "api": "healthy",
            "gateway": "healthy" if gateway and gateway.running else "unavailable",
            "message_bus": "healthy" if message_bus_host and message_bus_host.running else "unavailable"
        }
    )


@router.get("/detailed", response_model=DetailedHealthResponse)
async def detailed_health():
    """Detailed health check with system metrics"""
    current_time = datetime.utcnow()
    uptime = time.time() - start_time
    
    # Get system metrics
    try:
        cpu_percent = psutil.cpu_percent(interval=1)
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
    
    # API Gateway health
    if gateway:
        try:
            gateway_status = gateway.get_health_status()
            components["api_gateway"] = ComponentHealth(
                status=gateway_status.get("status", "unknown"),
                uptime=gateway_status.get("uptime", 0),
                last_check=current_time.isoformat(),
                details=gateway_status
            )
        except Exception as e:
            components["api_gateway"] = ComponentHealth(
                status="error",
                last_check=current_time.isoformat(),
                details={"error": str(e)}
            )
    else:
        components["api_gateway"] = ComponentHealth(
            status="unavailable",
            last_check=current_time.isoformat()
        )
    
    # Message Bus health
    if message_bus_host:
        components["message_bus"] = ComponentHealth(
            status="running" if message_bus_host.running else "stopped",
            uptime=uptime if message_bus_host.running else 0,
            last_check=current_time.isoformat(),
            details={
                "modules": len(message_bus_host.modules),
                "address": message_bus_host.bind_address
            }
        )
    else:
        components["message_bus"] = ComponentHealth(
            status="unavailable",
            last_check=current_time.isoformat()
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


