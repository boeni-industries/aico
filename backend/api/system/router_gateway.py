"""
System API Gateway Router

Gateway router that proxies system/metrics requests to core via NATS.
All system endpoints require database access and must run on core.
"""

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import Any, Dict

from backend.api.errors import raise_api_error
from backend.api.system.dependencies import get_current_user

router = APIRouter(prefix="/system", tags=["system"])


class AllMetricsResponse(BaseModel):
    """Complete metrics response with all subsystems."""
    timestamp: str
    gateway: Dict[str, Any]
    modelservice: Dict[str, Any]
    memory: Dict[str, Any]
    scheduler: Dict[str, Any]
    message_bus: Dict[str, Any]
    system_health: Dict[str, Any]


@router.get("/overview")
async def get_system_overview(_auth: dict = Depends(get_current_user)):
    """Get system overview (gateway→core NATS proxy)"""
    try:
        from backend.api_gateway.core.nats_client import get_gateway_nats_client
        nats_client = get_gateway_nats_client()
        return await nats_client.request_system_overview()
    except Exception as e:
        raise_api_error(status_code=500, error_code="SYSTEM_OVERVIEW_FAILED", message=str(e))


@router.get("/health")
async def get_system_health(_auth: dict = Depends(get_current_user)):
    """Get system health (gateway→core NATS proxy)"""
    try:
        from backend.api_gateway.core.nats_client import get_gateway_nats_client
        nats_client = get_gateway_nats_client()
        return await nats_client.request_system_health()
    except Exception as e:
        raise_api_error(status_code=500, error_code="SYSTEM_HEALTH_FAILED", message=str(e))


@router.get("/health/services")
async def get_health_services(_auth: dict = Depends(get_current_user)):
    """Get health services (gateway→core NATS proxy)"""
    try:
        from backend.api_gateway.core.nats_client import get_gateway_nats_client
        nats_client = get_gateway_nats_client()
        return await nats_client.request_health_services()
    except Exception as e:
        raise_api_error(status_code=500, error_code="HEALTH_SERVICES_FAILED", message=str(e))


@router.get("/metrics/all", response_model=AllMetricsResponse)
async def get_all_metrics(
    _auth: dict = Depends(get_current_user)
):
    """
    Get all system metrics in a single request.
    
    Gateway proxies this request to core via NATS request/reply.
    """
    try:
        from backend.api_gateway.core.nats_client import get_gateway_nats_client
        
        nats_client = get_gateway_nats_client()
        data = await nats_client.request_system_metrics_all()
        
        return AllMetricsResponse(**data)
        
    except Exception as e:
        raise_api_error(
            status_code=500,
            error_code="SYSTEM_METRICS_FAILED",
            message=f"Failed to retrieve system metrics: {str(e)}",
        )
