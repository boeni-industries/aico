"""Health Remediation API Router

Provides HTTP endpoints for manually triggering remediation actions.
"""

from __future__ import annotations

from typing import Dict, Any, List, Optional, Annotated
from datetime import datetime, UTC

from fastapi import APIRouter, Depends, HTTPException, Body
from pydantic import BaseModel, Field

from aico.core.logging import get_logger
from aico.data.postgres.connection import get_session_factory
from aico.data.uow import UnitOfWork
from aico.ai.agency.skills.registry import SkillRegistry
from aico.ai.agency.skill_invoker import SkillInvoker
from backend.api.dependencies import get_current_user


logger = get_logger("backend.api.system.health.remediate")

router = APIRouter(prefix="/remediate", tags=["health", "remediation"])


# ============================================================================
# Dependencies
# ============================================================================

async def get_uow(session_factory = Depends(get_session_factory)) -> UnitOfWork:
    """Get Unit of Work for database operations."""
    async with UnitOfWork(session_factory) as uow:
        yield uow


# ============================================================================
# Request/Response Models
# ============================================================================

class RemediationRequest(BaseModel):
    """Request to trigger a remediation skill."""
    
    parameters: Dict[str, Any] = Field(
        default_factory=dict,
        description="Skill-specific parameters"
    )
    dry_run: bool = Field(
        default=True,
        description="If true, only report what would be done without executing"
    )


class RemediationResponse(BaseModel):
    """Response from remediation skill execution."""
    
    skill_id: str
    success: bool
    output: Dict[str, Any]
    error: Optional[str] = None
    executed_at: str
    execution_time_ms: int


class AvailableSkill(BaseModel):
    """Information about an available remediation skill."""
    
    skill_id: str
    name: str
    description: str
    category: str
    safety_level: str
    execution_policy: str
    capability_tags: List[str]
    side_effect_tags: List[str]
    parameters: List[Dict[str, Any]]


class RemediationHistoryEntry(BaseModel):
    """Historical remediation execution record."""
    
    id: str
    skill_id: str
    parameters: Dict[str, Any]
    success: bool
    dry_run: bool
    output: Dict[str, Any]
    error: Optional[str] = None
    executed_by: str
    executed_at: str
    execution_time_ms: int


# ============================================================================
# Dependency: Get Remediation Service
# ============================================================================

_remediation_registry: Optional[SkillRegistry] = None
_remediation_invoker: Optional[SkillInvoker] = None


async def get_remediation_service(
    session_factory = Depends(get_session_factory),
) -> tuple[SkillRegistry, SkillInvoker]:
    """Get or create remediation skill registry and invoker."""
    global _remediation_registry, _remediation_invoker
    
    if _remediation_registry is None or _remediation_invoker is None:
        from aico.ai.agency.skills.remediation import (
            RemediationPostgresVacuumSkill,
            RemediationPostgresArchiveSkill,
            RemediationDatabaseDiskPressureSkill,
            RemediationChromaCompactSkill,
            RemediationLmdbCompactSkill,
            RemediationLmdbCleanupSkill,
            RemediationInfluxGetMeasurementsSkill,
            RemediationInfluxApplyRetentionSkill,
            RemediationInfluxDropMeasurementSkill,
            RemediationModelserviceStabiliseSkill,
            RemediationAgencyRecoverPlansSkill,
            RemediationAgencyRebalanceLoadSkill,
        )
        from aico.core.config import ConfigurationManager
        
        registry = SkillRegistry()
        config = ConfigurationManager()
        
        # Register database remediation skills
        registry.register(RemediationPostgresVacuumSkill(session_factory))
        registry.register(RemediationPostgresArchiveSkill(session_factory))
        registry.register(RemediationDatabaseDiskPressureSkill(session_factory))
        registry.register(RemediationChromaCompactSkill())
        registry.register(RemediationLmdbCompactSkill())
        registry.register(RemediationLmdbCleanupSkill())
        
        # Register InfluxDB remediation skills
        registry.register(RemediationInfluxGetMeasurementsSkill(config))
        registry.register(RemediationInfluxApplyRetentionSkill(config))
        registry.register(RemediationInfluxDropMeasurementSkill(config))
        
        # Register service remediation skills
        registry.register(RemediationModelserviceStabiliseSkill())
        registry.register(RemediationAgencyRecoverPlansSkill(session_factory))
        registry.register(RemediationAgencyRebalanceLoadSkill(session_factory))
        
        invoker = SkillInvoker(registry, session_factory)
        
        _remediation_registry = registry
        _remediation_invoker = invoker
    
    return _remediation_registry, _remediation_invoker


# ============================================================================
# Endpoints
# ============================================================================

@router.get("/available", response_model=List[AvailableSkill])
async def list_available_remediations(
    current_user: Annotated[Dict[str, Any], Depends(get_current_user)],
    service: tuple = Depends(get_remediation_service),
) -> List[AvailableSkill]:
    """List all available remediation skills.
    
    Returns:
        List of available remediation skills with metadata
    """
    registry, _ = service
    
    skills = []
    for skill_obj in registry.list_by_category("remediation"):
        skills.append(AvailableSkill(
            skill_id=skill_obj.skill_id,
            name=skill_obj.name,
            description=skill_obj.description,
            category=skill_obj.category,
            safety_level=skill_obj.safety_level,
            execution_policy=getattr(skill_obj, "execution_policy", None).value
            if getattr(skill_obj, "execution_policy", None) is not None
            else "auto",
            capability_tags=skill_obj.capability_tags,
            side_effect_tags=skill_obj.side_effect_tags,
            parameters=[
                {
                    "name": p.name,
                    "type": p.type.value,
                    "description": p.description,
                    "required": p.required,
                    "default": p.default,
                }
                for p in skill_obj.parameters
            ],
        ))
    
    return skills


@router.post("/{skill_id}", response_model=RemediationResponse)
async def trigger_remediation(
    skill_id: str,
    current_user: Annotated[Dict[str, Any], Depends(get_current_user)],
    request: RemediationRequest = Body(...),
    service: tuple = Depends(get_remediation_service),
    uow: UnitOfWork = Depends(get_uow),
) -> RemediationResponse:
    """Trigger a specific remediation skill.
    
    Args:
        skill_id: ID of the remediation skill to execute
        request: Remediation request with parameters
        uow: Unit of work for database operations
    
    Returns:
        Remediation execution result
    
    Raises:
        HTTPException: If skill not found or execution fails
    """
    # Skill trigger - no logging (executes frequently)
    registry, invoker = service
    
    # Verify skill exists
    skill = registry.get(skill_id)
    if not skill:
        raise HTTPException(
            status_code=404,
            detail=f"Remediation skill '{skill_id}' not found"
        )
    
    # Ensure dry_run is set in parameters.
    # Safety-first: the request-level dry_run flag must never be overridden to False.
    # (Some clients may still send a legacy `parameters.dry_run=false` field.)
    input_data = request.parameters.copy()
    effective_dry_run = bool(request.dry_run) or bool(input_data.get("dry_run", False))
    input_data["dry_run"] = effective_dry_run
    
    print(f"\n{'='*80}")
    print(f"[REMEDIATION ENDPOINT] Skill Execution Request")
    print(f"{'='*80}")
    print(f"Skill ID: {skill_id}")
    print(f"Request body - parameters: {request.parameters}")
    print(f"Request body - dry_run: {request.dry_run} (type: {type(request.dry_run).__name__})")
    print(f"Merged input_data: {input_data}")
    print(f"input_data['dry_run']: {input_data.get('dry_run')} (type: {type(input_data.get('dry_run')).__name__})")
    print(f"{'='*80}\n")
    
    # Validate parameters
    is_valid, error = skill.validate_inputs(input_data)
    if not is_valid:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid parameters: {error}"
        )
    
    # Execute skill
    start_time = datetime.now(UTC)
    # Skill execution - no logging
    
    try:
        result = await invoker.invoke_skill(
            skill_id=skill_id,
            user_id="system",  # Manual trigger from UI
            input_data=input_data,
            context={"origin": "manual_remediation"},
        )
        
        execution_time_ms = int((datetime.now(UTC) - start_time).total_seconds() * 1000)
        
        success = result.get("success", False)
        output = result.get("output", {})
        error = result.get("error")
        
        # Skill completion - no logging
        
        # Persist execution to database
        try:
            from sqlalchemy import text
            import json
            
            query = text("""
                INSERT INTO aico_core.remediation_executions 
                (skill_id, parameters, success, dry_run, output, error, executed_by, executed_at, execution_time_ms)
                VALUES (:skill_id, :parameters, :success, :dry_run, :output, :error, :executed_by, :executed_at, :execution_time_ms)
            """)
            
            await uow._session.execute(query, {
                "skill_id": skill_id,
                "parameters": json.dumps(request.parameters),
                "success": success,
                "dry_run": input_data.get("dry_run", request.dry_run),
                "output": json.dumps(output),
                "error": error,
                "executed_by": "manual_ui",
                "executed_at": start_time,
                "execution_time_ms": execution_time_ms,
            })
            await uow.commit()
        except Exception as db_exc:
            logger.error("[REMEDIATION] Failed to persist execution history: %s", db_exc)
            # Don't fail the request if history persistence fails
        
        # Skill executed - no logging
        
        response = RemediationResponse(
            skill_id=skill_id,
            success=success,
            output=output,
            error=error,
            executed_at=start_time.isoformat(),
            execution_time_ms=execution_time_ms,
        )
        # Response - no logging
        return response
    
    except Exception as exc:
        logger.error(f"[REMEDIATION] Skill '{skill_id}' execution failed: {exc}")
        execution_time_ms = int((datetime.now(UTC) - start_time).total_seconds() * 1000)
        
        # Persist failed execution
        try:
            from sqlalchemy import text
            import json
            
            query = text("""
                INSERT INTO aico_core.remediation_executions 
                (skill_id, parameters, success, dry_run, output, error, executed_by, executed_at, execution_time_ms)
                VALUES (:skill_id, :parameters, :success, :dry_run, :output, :error, :executed_by, :executed_at, :execution_time_ms)
            """)
            
            await uow._session.execute(query, {
                "skill_id": skill_id,
                "parameters": json.dumps(request.parameters),
                "success": False,
                "dry_run": request.dry_run,
                "output": json.dumps({}),
                "error": str(exc),
                "executed_by": "manual_ui",
                "executed_at": start_time,
                "execution_time_ms": execution_time_ms,
            })
            await uow.commit()
        except Exception as db_exc:
            logger.error("[REMEDIATION] Failed to persist failed execution: %s", db_exc)
        
        return RemediationResponse(
            skill_id=skill_id,
            success=False,
            output={},
            error=str(exc),
            executed_at=start_time.isoformat(),
            execution_time_ms=execution_time_ms,
        )


@router.post("/{skill_id}/dry-run", response_model=RemediationResponse)
async def dry_run_remediation(
    skill_id: str,
    current_user: Annotated[Dict[str, Any], Depends(get_current_user)],
    request: RemediationRequest = Body(...),
    service: tuple = Depends(get_remediation_service),
    uow: UnitOfWork = Depends(get_uow),
) -> RemediationResponse:
    """Preview what a remediation would do without executing.
    
    This is a convenience endpoint that forces dry_run=True.
    
    Args:
        skill_id: ID of the remediation skill to preview
        request: Remediation request with parameters
    
    Returns:
        Dry-run execution result
    """
    # Force dry_run to True
    request.dry_run = True
    return await trigger_remediation(skill_id, current_user, request, service, uow)


@router.get("/history", response_model=List[RemediationHistoryEntry])
async def get_remediation_history(
    current_user: Annotated[Dict[str, Any], Depends(get_current_user)],
    limit: int = 50,
    skill_id: Optional[str] = None,
    uow: UnitOfWork = Depends(get_uow),
) -> List[RemediationHistoryEntry]:
    """Get remediation execution history.
    
    Args:
        limit: Maximum number of entries to return
        skill_id: Optional filter by skill ID
        uow: Unit of work for database operations
    
    Returns:
        List of historical remediation executions
    """
    try:
        from sqlalchemy import text
        import json
        
        # Build query with optional skill_id filter
        if skill_id:
            query = text("""
                SELECT id, skill_id, parameters, success, dry_run, output, error, 
                       executed_by, executed_at, execution_time_ms
                FROM aico_core.remediation_executions
                WHERE skill_id = :skill_id
                ORDER BY executed_at DESC
                LIMIT :limit
            """)
            result = await uow._session.execute(query, {"skill_id": skill_id, "limit": limit})
        else:
            query = text("""
                SELECT id, skill_id, parameters, success, dry_run, output, error, 
                       executed_by, executed_at, execution_time_ms
                FROM aico_core.remediation_executions
                ORDER BY executed_at DESC
                LIMIT :limit
            """)
            result = await uow._session.execute(query, {"limit": limit})
        
        rows = result.fetchall()
        
        history = []
        for row in rows:
            history.append(RemediationHistoryEntry(
                id=str(row.id),
                skill_id=row.skill_id,
                parameters=row.parameters if row.parameters else {},
                success=row.success,
                dry_run=row.dry_run,
                output=row.output if row.output else {},
                error=row.error,
                executed_by=row.executed_by,
                executed_at=row.executed_at.isoformat(),
                execution_time_ms=row.execution_time_ms,
            ))
        
        # History retrieved - no logging
        return history
        
    except Exception as exc:
        logger.error("[REMEDIATION] Failed to retrieve history: %s", exc)
        return []


@router.delete("/history/{execution_id}")
async def delete_history_entry(
    execution_id: str,
    current_user: Annotated[Dict[str, Any], Depends(get_current_user)],
    uow: UnitOfWork = Depends(get_uow),
) -> Dict[str, Any]:
    """Delete a single remediation execution history entry.
    
    Args:
        execution_id: UUID of the execution to delete
    
    Returns:
        Success message
    """
    try:
        from sqlalchemy import text
        
        query = text("""
            DELETE FROM aico_core.remediation_executions
            WHERE id = :execution_id
        """)
        
        result = await uow._session.execute(query, {"execution_id": execution_id})
        await uow.commit()
        
        if result.rowcount == 0:
            raise HTTPException(
                status_code=404,
                detail=f"Execution '{execution_id}' not found"
            )
        
        # History deleted - no logging
        return {"message": "History entry deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"[REMEDIATION] Failed to delete history entry: {exc}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to delete history entry: {str(exc)}"
        )


@router.delete("/history")
async def clear_history(
    current_user: Annotated[Dict[str, Any], Depends(get_current_user)],
    skill_id: Optional[str] = None,
    uow: UnitOfWork = Depends(get_uow),
) -> Dict[str, Any]:
    """Clear remediation execution history.
    
    Args:
        skill_id: Optional skill ID to clear history for specific skill only
    
    Returns:
        Number of entries deleted
    """
    try:
        from sqlalchemy import text
        
        if skill_id:
            query = text("""
                DELETE FROM aico_core.remediation_executions
                WHERE skill_id = :skill_id
            """)
            result = await uow._session.execute(query, {"skill_id": skill_id})
        else:
            query = text("DELETE FROM aico_core.remediation_executions")
            result = await uow._session.execute(query)
        
        await uow.commit()
        
        deleted_count = result.rowcount
        # History cleared - no logging
        
        return {
            "message": f"Deleted {deleted_count} history entries",
            "deleted_count": deleted_count
        }
        
    except Exception as exc:
        logger.error(f"[REMEDIATION] Failed to clear history: {exc}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to clear history: {str(exc)}"
        )


@router.get("/{skill_id}/info", response_model=AvailableSkill)
async def get_skill_info(
    skill_id: str,
    current_user: Annotated[Dict[str, Any], Depends(get_current_user)],
    service: tuple = Depends(get_remediation_service),
) -> AvailableSkill:
    """Get detailed information about a specific remediation skill.
    
    Args:
        skill_id: ID of the remediation skill
    
    Returns:
        Detailed skill information
    
    Raises:
        HTTPException: If skill not found
    """
    registry, _ = service
    
    skill = registry.get(skill_id)
    if not skill:
        raise HTTPException(
            status_code=404,
            detail=f"Remediation skill '{skill_id}' not found"
        )
    
    return AvailableSkill(
        skill_id=skill.skill_id,
        name=skill.name,
        description=skill.description,
        category=skill.category,
        safety_level=skill.safety_level,
        execution_policy=getattr(skill, "execution_policy", None).value
        if getattr(skill, "execution_policy", None) is not None
        else "auto",
        capability_tags=skill.capability_tags,
        side_effect_tags=skill.side_effect_tags,
        parameters=[
            {
                "name": p.name,
                "type": p.type.value,
                "description": p.description,
                "required": p.required,
                "default": p.default,
            }
            for p in skill.parameters
        ],
    )
