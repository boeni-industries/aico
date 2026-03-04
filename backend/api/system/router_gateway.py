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

# Include config router for direct access to configuration endpoints
from backend.api.system.config.router import router as config_router
router.include_router(config_router, prefix="/config", tags=["system-config"])


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
async def get_system_health():
    """Get system health (gateway→core NATS proxy)"""
    try:
        from backend.api_gateway.core.nats_client import get_gateway_nats_client
        nats_client = get_gateway_nats_client()
        return await nats_client.request_system_health()
    except Exception as e:
        raise_api_error(status_code=500, error_code="SYSTEM_HEALTH_FAILED", message=str(e))


@router.get("/health/services")
async def get_health_services():
    """Get health services (gateway→core NATS proxy)"""
    try:
        from backend.api_gateway.core.nats_client import get_gateway_nats_client
        nats_client = get_gateway_nats_client()
        return await nats_client.request_health_services()
    except Exception as e:
        raise_api_error(status_code=500, error_code="HEALTH_SERVICES_FAILED", message=str(e))


@router.get("/health/issues")
async def get_health_issues():
    """Get system health issues (gateway→core NATS proxy)"""
    try:
        from backend.api_gateway.core.nats_client import get_gateway_nats_client
        nats_client = get_gateway_nats_client()
        return await nats_client.request_health_issues()
    except Exception as e:
        raise_api_error(status_code=500, error_code="HEALTH_ISSUES_FAILED", message=str(e))


@router.get("/remediate/available")
async def get_available_remediations():
    """Get available remediation actions (gateway→core NATS proxy)"""
    try:
        from backend.api_gateway.core.nats_client import get_gateway_nats_client
        nats_client = get_gateway_nats_client()
        return await nats_client.request_remediate_available()
    except Exception as e:
        raise_api_error(status_code=500, error_code="REMEDIATE_AVAILABLE_FAILED", message=str(e))


@router.get("/remediate/history")
async def get_remediation_history(
    limit: int = 20
):
    """Get remediation history (gateway→core NATS proxy)"""
    try:
        from backend.api_gateway.core.nats_client import get_gateway_nats_client
        nats_client = get_gateway_nats_client()
        return await nats_client.request_remediate_history(limit=limit)
    except Exception as e:
        raise_api_error(status_code=500, error_code="REMEDIATE_HISTORY_FAILED", message=str(e))


@router.post("/remediate/{skill_id}")
async def trigger_remediation(
    skill_id: str,
    payload: Dict[str, Any],
    _auth: dict = Depends(get_current_user),
):
    """Trigger a remediation skill (gateway→core NATS proxy)"""
    try:
        from backend.api_gateway.core.nats_client import get_gateway_nats_client

        nats_client = get_gateway_nats_client()
        return await nats_client.request_remediate_trigger(skill_id=skill_id, payload=payload)
    except Exception as e:
        raise_api_error(status_code=500, error_code="REMEDIATE_TRIGGER_FAILED", message=str(e))


@router.post("/health/check/connectivity")
async def run_connectivity_check(_auth: dict = Depends(get_current_user)):
    """Run connectivity health check (gateway→core NATS proxy)"""
    try:
        from backend.api_gateway.core.nats_client import get_gateway_nats_client
        nats_client = get_gateway_nats_client()
        return await nats_client.request_health_check_connectivity()
    except Exception as e:
        raise_api_error(status_code=500, error_code="HEALTH_CHECK_FAILED", message=str(e))


@router.post("/health/check/resources")
async def run_resources_check(_auth: dict = Depends(get_current_user)):
    """Run resources health check (gateway→core NATS proxy)"""
    try:
        from backend.api_gateway.core.nats_client import get_gateway_nats_client
        nats_client = get_gateway_nats_client()
        return await nats_client.request_health_check_resources()
    except Exception as e:
        raise_api_error(status_code=500, error_code="HEALTH_CHECK_FAILED", message=str(e))


@router.post("/health/check/models")
async def run_models_check(_auth: dict = Depends(get_current_user)):
    """Run models health check (gateway→core NATS proxy)"""
    try:
        from backend.api_gateway.core.nats_client import get_gateway_nats_client
        nats_client = get_gateway_nats_client()
        return await nats_client.request_health_check_models()
    except Exception as e:
        raise_api_error(status_code=500, error_code="HEALTH_CHECK_FAILED", message=str(e))


@router.post("/health/check/ai-behaviour")
async def run_ai_behaviour_check(_auth: dict = Depends(get_current_user)):
    """Run AI behaviour health check (gateway→core NATS proxy)"""
    try:
        from backend.api_gateway.core.nats_client import get_gateway_nats_client
        nats_client = get_gateway_nats_client()
        return await nats_client.request_health_check_ai_behaviour()
    except Exception as e:
        raise_api_error(status_code=500, error_code="HEALTH_CHECK_FAILED", message=str(e))


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
