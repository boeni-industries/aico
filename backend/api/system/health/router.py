"""System Health API Router

FastAPI router for system health monitoring endpoints.
"""

from typing import Annotated, Dict, Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Request

from aico.core.logging import get_logger
from aico.ai.agency.skills.registry import SkillRegistry
from aico.ai.agency.skill_invoker import SkillInvoker
from aico.data.postgres.connection import get_session_factory
from backend.api.dependencies import get_current_user

from . import schemas
from .schemas import (
    SystemHealthResponse,
    HealthCheckResult,
    SystemIssuesResponse,
    ServiceHealthResponse,
)
from .service import HealthService
from . import remediate


logger = get_logger("backend.api.system.health.router")

router = APIRouter()

# Include remediation sub-router
router.include_router(remediate.router)

# Global singleton health service instance
_health_service_instance: Optional[HealthService] = None


def get_health_service(
    request: Request,
    session_factory = Depends(get_session_factory),
) -> HealthService:
    """Dependency to get HealthService singleton instance."""
    global _health_service_instance
    
    if _health_service_instance is None:
        from aico.ai.agency.skills.registry import SkillRegistry
        from aico.ai.agency.skill_invoker import SkillInvoker
        from aico.ai.agency.skills.maintenance import (
            MaintenanceConnectivityFullScanSkill,
            MaintenanceSystemScanResourcesSkill,
            MaintenanceModelserviceScanHealthSkill,
            MaintenanceAgencyReEvaluateBehaviourHealthSkill,
            MaintenanceMessageBusCheckHealthSkill,
            MaintenanceSchedulerCheckHealthSkill,
        )
        from aico.ai.agency.skills.remediation.influx import RemediationInfluxGetMeasurementsSkill
        from aico.core.config import ConfigurationManager
        
        # Get backend start time from app state
        import time
        start_time = getattr(request.app.state, 'backend_start_time', time.time())
        
        # Get config for InfluxDB skill
        config = ConfigurationManager()
        
        skill_registry = SkillRegistry()
        skill_registry.register(MaintenanceConnectivityFullScanSkill(session_factory))
        skill_registry.register(MaintenanceSystemScanResourcesSkill())
        skill_registry.register(MaintenanceModelserviceScanHealthSkill())
        skill_registry.register(MaintenanceAgencyReEvaluateBehaviourHealthSkill(session_factory))
        skill_registry.register(MaintenanceMessageBusCheckHealthSkill())
        skill_registry.register(MaintenanceSchedulerCheckHealthSkill())
        skill_registry.register(RemediationInfluxGetMeasurementsSkill(config))
        
        skill_invoker = SkillInvoker(skill_registry, session_factory)
        
        _health_service_instance = HealthService(
            skill_registry=skill_registry,
            skill_invoker=skill_invoker,
            session_factory=session_factory,
            start_time=start_time,
        )
    
    return _health_service_instance


@router.get("/health", response_model=SystemHealthResponse)
async def get_system_health(
    current_user: Annotated[Dict[str, Any], Depends(get_current_user)],
    health_service: Annotated[HealthService, Depends(get_health_service)],
) -> SystemHealthResponse:
    """Get overall system health status.
    
    Aggregates results from all health check skills and returns summary.
    Cached for 30 seconds to avoid overload.
    """
    logger.debug("[HEALTH_API] Getting system health for user %s", current_user.get("user_uuid"))
    
    try:
        return await health_service.get_system_health()
    except Exception as exc:
        logger.error("[HEALTH_API] Failed to get system health: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to retrieve system health")


@router.get("/health/services", response_model=ServiceHealthResponse)
async def get_service_health(
    current_user: Annotated[Dict[str, Any], Depends(get_current_user)],
    health_service: Annotated[HealthService, Depends(get_health_service)],
) -> ServiceHealthResponse:
    """Get service health statuses with metrics.
    
    Returns current status and historical data for all services.
    """
    logger.debug("[HEALTH_API] Getting service health for user %s", current_user.get("user_uuid"))
    
    try:
        return await health_service.get_service_health()
    except Exception as exc:
        logger.error("[HEALTH_API] Failed to get service health: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to retrieve service health")


@router.get("/health/issues", response_model=SystemIssuesResponse)
async def get_system_issues(
    current_user: Annotated[Dict[str, Any], Depends(get_current_user)],
    health_service: Annotated[HealthService, Depends(get_health_service)],
) -> SystemIssuesResponse:
    """Get active system issues.
    
    Returns issues detected by health checks with remediation actions.
    """
    logger.debug("[HEALTH_API] Getting system issues for user %s", current_user.get("user_uuid"))
    
    try:
        return await health_service.get_active_issues()
    except Exception as exc:
        logger.error("[HEALTH_API] Failed to get system issues: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to retrieve system issues")


@router.post("/health/check/connectivity", response_model=HealthCheckResult)
async def run_connectivity_check(
    current_user: Annotated[Dict[str, Any], Depends(get_current_user)],
    health_service: Annotated[HealthService, Depends(get_health_service)],
) -> HealthCheckResult:
    """Run connectivity health check bundle.
    
    Tests connectivity to all core components (databases, modelservice, etc.).
    """
    logger.debug("[HEALTH_API] Running connectivity check for user %s", current_user.get("user_uuid"))
    
    try:
        return await health_service.run_connectivity_check()
    except Exception as exc:
        logger.error("[HEALTH_API] Connectivity check failed: %s", exc)
        raise HTTPException(status_code=500, detail="Connectivity check failed")


@router.post("/health/check/resources", response_model=HealthCheckResult)
async def run_resources_check(
    current_user: Annotated[Dict[str, Any], Depends(get_current_user)],
    health_service: Annotated[HealthService, Depends(get_health_service)],
) -> HealthCheckResult:
    """Run resource monitoring health check bundle.
    
    Monitors CPU, memory, and disk usage against thresholds.
    """
    logger.debug("[HEALTH_API] Running resources check for user %s", current_user.get("user_uuid"))
    
    try:
        return await health_service.run_resources_check()
    except Exception as exc:
        logger.error("[HEALTH_API] Resources check failed: %s", exc)
        raise HTTPException(status_code=500, detail="Resources check failed")


@router.post("/health/check/models", response_model=HealthCheckResult)
async def run_models_check(
    current_user: Annotated[Dict[str, Any], Depends(get_current_user)],
    health_service: Annotated[HealthService, Depends(get_health_service)],
) -> HealthCheckResult:
    """Run modelservice health check bundle.
    
    Tests modelservice connectivity and inference pipeline.
    """
    logger.debug("[HEALTH_API] Running models check for user %s", current_user.get("user_uuid"))
    
    try:
        return await health_service.run_models_check()
    except Exception as exc:
        logger.error("[HEALTH_API] Models check failed: %s", exc)
        raise HTTPException(status_code=500, detail="Models check failed")


@router.post("/health/check/ai-behaviour", response_model=HealthCheckResult)
async def run_ai_behaviour_check(
    current_user: Annotated[Dict[str, Any], Depends(get_current_user)],
    health_service: Annotated[HealthService, Depends(get_health_service)],
) -> HealthCheckResult:
    """Run AI behaviour health check bundle.
    
    Monitors agency goals, plans, and reflection activity.
    """
    logger.debug("[HEALTH_API] Running AI behaviour check for user %s", current_user.get("user_uuid"))
    
    try:
        return await health_service.run_ai_behaviour_check()
    except Exception as exc:
        logger.error("[HEALTH_API] AI behaviour check failed: %s", exc)
        raise HTTPException(status_code=500, detail="AI behaviour check failed")


# Phase 5: Advanced Features Endpoints

@router.post("/test/connection", response_model=schemas.ConnectionTestResult)
async def test_connection(
    current_user: Annotated[Dict[str, Any], Depends(get_current_user)],
    request: schemas.ConnectionTestRequest,
    health_service: Annotated[HealthService, Depends(get_health_service)],
) -> schemas.ConnectionTestResult:
    """Test connection to a specific component with detailed diagnostics.
    
    Tests connectivity and returns latency, status, and fix suggestions.
    """
    logger.debug(
        "[HEALTH_API] Testing connection to %s for user %s",
        request.component,
        current_user.get("user_uuid")
    )
    
    try:
        result = await health_service.test_connection(
            component=request.component,
            timeout_seconds=request.timeout_seconds or 5,
        )
        return schemas.ConnectionTestResult(**result)
    except Exception as exc:
        logger.error("[HEALTH_API] Connection test failed: %s", exc)
        raise HTTPException(status_code=500, detail="Connection test failed")


@router.get("/diagnostics", response_model=schemas.DiagnosticsResponse)
async def get_diagnostics(
    current_user: Annotated[Dict[str, Any], Depends(get_current_user)],
    health_service: Annotated[HealthService, Depends(get_health_service)],
) -> schemas.DiagnosticsResponse:
    """Get performance diagnostics and recommendations.
    
    Analyzes slow endpoints, slow queries, and error patterns.
    """
    logger.info("[HEALTH_API] Getting diagnostics for user %s", current_user.get("user_uuid"))
    
    try:
        result = await health_service.get_diagnostics()
        return schemas.DiagnosticsResponse(**result)
    except Exception as exc:
        logger.error("[HEALTH_API] Diagnostics failed: %s", exc)
        raise HTTPException(status_code=500, detail="Diagnostics failed")


# Phase 6: Remediation Actions Endpoints

@router.post("/actions/execute", response_model=schemas.ActionExecutionResponse)
async def execute_action(
    current_user: Annotated[Dict[str, Any], Depends(get_current_user)],
    request: schemas.ActionExecutionRequest,
    health_service: Annotated[HealthService, Depends(get_health_service)],
) -> schemas.ActionExecutionResponse:
    """Execute a remediation action.
    
    Invokes the appropriate maintenance skill to remediate an issue.
    Updates issue status to 'resolving' if issue_id is provided.
    """
    logger.info(
        "[HEALTH_API] Executing action %s for user %s",
        request.action_id,
        current_user.get("user_uuid")
    )
    
    try:
        result = await health_service.execute_action(
            action_id=request.action_id,
            params=request.params,
            issue_id=request.issue_id,
        )
        return schemas.ActionExecutionResponse(**result)
    except Exception as exc:
        logger.error("[HEALTH_API] Action execution failed: %s", exc)
        raise HTTPException(status_code=500, detail="Action execution failed")
