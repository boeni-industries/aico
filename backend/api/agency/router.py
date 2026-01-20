"""
Agency API Router

REST API endpoints for agency system - intentions, goals, values, policies, and consents.
Based on agency-metrics.md user-facing metrics.
"""

import asyncio
import importlib
import json
import pkgutil
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from typing import Annotated, Optional, List, Dict, Any
from pydantic import BaseModel

from backend.api.conversation.dependencies import get_current_user
from backend.api.agency.models import (
    IntentionSetResponse,
    CuriosityStatusResponse,
    ValueProfileResponse,
    UpdateValueProfileRequest,
    PolicyListResponse,
    PolicyRuleResponse,
    ConsentRequest,
    ConsentResponse,
    ConsentListResponse,
    AgencyStateResponse,
    CreateGoalRequest,
    GoalResponse,
    GoalListResponse,
    UpdateGoalRequest,
    GoalSummary,
    CuriosityOpportunity,
    CuriosityLevel,
    GoalOrigin,
    GoalStatus,
    GoalPriority,
    PolicyEffect,
)
from aico.core.logging import get_logger
from aico.core.config import ConfigurationManager
from aico.ai.agency import AgencyEngine
from aico.ai.agency.skills.registry import SkillRegistry
from aico.ai.agency.tools.registry import get_tool_registry, ToolDefinition
import aico.ai.agency.tools as tools_package
from aico.ai.agency.values_ethics import ValuesEthicsService, ProactiveBehaviorLevel
from aico.ai import ai_registry
from aico.data.uow import UnitOfWork
from backend.core.postgres_dependencies import get_uow

logger = get_logger("backend.api.agency")
router = APIRouter()


# ============================================================================
# Dependencies
# ============================================================================

async def get_agency_engine() -> AgencyEngine:
    """Get AgencyEngine instance from global ai_registry (with LLM client injected)"""
    try:
        # Get the global AgencyEngine instance that has LLM client injected during startup
        engine = ai_registry.get("agency")
        
        if not engine:
            raise HTTPException(
                status_code=500,
                detail="AgencyEngine not available in ai_registry - backend may not be fully initialized"
            )
        
        return engine
        
    except Exception as e:
        logger.error(f"Failed to get AgencyEngine from registry: {e}")
        raise HTTPException(status_code=500, detail=f"Agency service unavailable: {str(e)}")


# Removed get_values_ethics_service - using repositories via UnitOfWork instead


# ============================================================================
# Intention Set Endpoints
# ============================================================================

@router.get("/intentions", response_model=IntentionSetResponse)
async def get_intention_set(
    user: Annotated[dict, Depends(get_current_user)],
    engine: Annotated[AgencyEngine, Depends(get_agency_engine)],
    limit: int = Query(10, ge=1, le=50, description="Maximum number of intentions to return")
):
    """
    Get the active intention set - what AICO is currently working on.
    
    Returns the primary focus intention and list of active intentions with scores.
    """
    try:
        user_id = user["user_uuid"]
        
        # Get intention set from engine
        intention_set = await engine.get_intention_set(user_id)
        
        # DEBUG: Log intention set data
        logger.info(f"[DEBUG] get_intention_set for user {user_id}")
        logger.info(f"[DEBUG] intention_set.intentions count: {len(intention_set.intentions)}")
        logger.info(f"[DEBUG] intention_set raw: {intention_set}")
        
        # Limit results
        intentions = intention_set.intentions[:limit]
        logger.info(f"[DEBUG] intentions after limit: {len(intentions)}")
        
        # Fetch actual Goal objects for each intention
        active_intentions = []
        for intention in intentions:
            logger.info(f"[DEBUG] Processing intention: goal_id={intention.goal_id}, score={intention.arbiter_score}")
            goal = await engine.get_goal(intention.goal_id)
            if goal:
                logger.info(f"[DEBUG] Found goal: {goal.title} (status={goal.status.value})")
                active_intentions.append(
                    GoalSummary(
                        goal_id=goal.goal_id,
                        title=goal.title,
                        description=goal.description,
                        origin=GoalOrigin(goal.origin.value),
                        priority=GoalPriority(goal.priority.value),
                        status=GoalStatus(goal.status.value),
                        score=intention.arbiter_score,
                        priority_band=intention.priority_band.value,
                        created_at=goal.created_at,
                        metadata=goal.metadata
                    )
                )
            else:
                logger.warning(f"[DEBUG] Goal not found for intention: {intention.goal_id}")
        
        logger.info(f"[DEBUG] active_intentions final count: {len(active_intentions)}")
        
        # Get hobby goals
        hobby_goals = [g for g in active_intentions if g.origin == GoalOrigin.HOBBY]
        
        # Count all open goals
        all_goals = await engine.list_goals_for_user(user_id)
        open_goals = [g for g in all_goals if g.status in [GoalStatus.PENDING, GoalStatus.ACTIVE]]
        
        logger.info(f"[DEBUG] all_goals count: {len(all_goals)}, open_goals count: {len(open_goals)}")
        
        return IntentionSetResponse(
            user_id=user_id,
            primary_focus=active_intentions[0] if active_intentions else None,
            active_intentions=active_intentions,
            open_goals_total=len(open_goals),
            hobby_goals_active=hobby_goals,
            timestamp=datetime.utcnow()
        )
        
    except Exception as e:
        logger.error(f"Failed to get intention set: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Skills & Tools Introspection / Invocation
# ============================================================================


class SkillInvokeRequest(BaseModel):
    skill_id: str
    input: Dict[str, Any] | None = None
    context: Dict[str, Any] | None = None


class SkillInfoResponse(BaseModel):
    skill_id: str
    name: str
    description: str
    category: str
    timeout_seconds: int
    capability_tags: List[str]
    side_effect_tags: List[str]
    safety_level: str
    implementation_tools: List[str]
    parameters: List[Dict[str, Any]]


class ToolInfoResponse(BaseModel):
    tool_id: str
    name: str
    description: str
    domain: str
    backend: str
    runtime_context: str
    capability_tags: List[str]
    side_effect_tags: List[str]
    safety_level: str
    resource_profile: str
    default_timeout_seconds: int
    parameters: List[Dict[str, Any]]


class ConnectivityScanRequest(BaseModel):
    targets: List[str] | None = None


def _get_skill_registry_from_engine(engine: AgencyEngine) -> SkillRegistry:
    registry = None
    skill_invoker = getattr(engine, "skill_invoker", None)
    if skill_invoker is not None:
        registry = getattr(skill_invoker, "skill_registry", None)
    if registry is None:
        registry = getattr(engine, "skill_registry", None)
    if registry is None or not isinstance(registry, SkillRegistry):
        logger.error("AgencyEngine does not expose a valid SkillRegistry instance")
        raise HTTPException(status_code=500, detail="SkillRegistry not available on AgencyEngine")
    return registry


def _tool_to_info(tool: ToolDefinition) -> ToolInfoResponse:
    return ToolInfoResponse(
        tool_id=tool.tool_id,
        name=tool.name,
        description=tool.description,
        domain=tool.domain,
        backend=tool.backend,
        runtime_context=tool.runtime_context,
        capability_tags=tool.capability_tags,
        side_effect_tags=tool.side_effect_tags,
        safety_level=tool.safety_level,
        resource_profile=tool.resource_profile,
        default_timeout_seconds=tool.default_timeout_seconds,
        parameters=[
            {
                "name": p.name,
                "type": p.type.value,
                "description": p.description,
                "required": p.required,
                "default": p.default,
            }
            for p in tool.parameters
        ],
    )


def _load_all_tool_modules() -> None:
    """Import all submodules under aico.ai.agency.tools.

    Ensures that modules which register tools at import time are loaded in
    the backend process before ToolRegistry is queried.
    """

    for finder, name, ispkg in pkgutil.iter_modules(
        tools_package.__path__, tools_package.__name__ + "."
    ):
        try:
            importlib.import_module(name)
        except Exception as exc:  # pragma: no cover - defensive
            logger.warning(f"[AGENCY_API] Failed to import tool module '{name}': {exc}")


@router.post("/skills/list", response_model=List[SkillInfoResponse])
async def list_skills(
    user: Annotated[dict, Depends(get_current_user)],
    engine: Annotated[AgencyEngine, Depends(get_agency_engine)],
) -> List[SkillInfoResponse]:
    """List all registered Agency skills.

    Authenticated via standard agency security.
    """

    registry = _get_skill_registry_from_engine(engine)
    skills = registry.list_all()
    return [SkillInfoResponse(**(registry.get_skill_info(s.skill_id) or {})) for s in skills]


@router.post("/skills/info", response_model=SkillInfoResponse)
async def get_skill_info(
    request: SkillInvokeRequest,
    user: Annotated[dict, Depends(get_current_user)],
    engine: Annotated[AgencyEngine, Depends(get_agency_engine)],
) -> SkillInfoResponse:
    """Get detailed metadata for a single skill."""

    registry = _get_skill_registry_from_engine(engine)
    info: Optional[Dict[str, Any]] = registry.get_skill_info(request.skill_id)
    if not info:
        raise HTTPException(status_code=404, detail=f"Skill not found: {request.skill_id}")
    return SkillInfoResponse(**info)


@router.post("/skills/invoke")
async def invoke_skill(
    request: SkillInvokeRequest,
    user: Annotated[dict, Depends(get_current_user)],
    engine: Annotated[AgencyEngine, Depends(get_agency_engine)],
):
    """Invoke a registered Agency skill via SkillInvoker."""

    try:
        result = await engine.skill_invoker.invoke_skill(
            skill_id=request.skill_id,
            user_id=user["user_uuid"],
            input_data=request.input or {},
            context=(request.context or {}) | {
                "trigger": "agency_skill_invoke",
                "initiator_type": "user",
                "source": "agency_api",
                "user_id": user["user_uuid"],
            },
        )
    except Exception as exc:
        logger.error(f"Skill invocation failed: {exc}")
        raise HTTPException(status_code=500, detail="Skill invocation failed")

    if not result.get("success"):
        raise HTTPException(status_code=500, detail=result.get("error") or "Skill reported failure")

    return result.get("output")


@router.post("/connectivity/scan")
async def connectivity_scan(
    request: ConnectivityScanRequest,
    user: Annotated[dict, Depends(get_current_user)],
    engine: Annotated[AgencyEngine, Depends(get_agency_engine)],
):
    """Run the maint.connectivity.full_scan maintenance skill."""

    input_data: Dict[str, Any] = {}
    if request.targets is not None:
        input_data["targets"] = request.targets

    try:
        result = await engine.skill_invoker.invoke_skill(
            skill_id="maint.connectivity.full_scan",
            user_id=user["user_uuid"],
            input_data=input_data,
            context={
                "trigger": "agency_connectivity_scan",
                "initiator_type": "user",
                "source": "agency_api",
                "user_id": user["user_uuid"],
            },
        )
    except Exception as exc:
        logger.error(f"Connectivity scan skill invocation failed: {exc}")
        raise HTTPException(status_code=500, detail="Connectivity scan failed")

    if not result.get("success"):
        raise HTTPException(status_code=500, detail=result.get("error") or "Connectivity scan reported failure")

    return result.get("output")


@router.post("/tools/list", response_model=List[ToolInfoResponse])
async def list_tools(
    user: Annotated[dict, Depends(get_current_user)],
) -> List[ToolInfoResponse]:
    """List all registered Agency tools from the ToolRegistry."""
    _load_all_tool_modules()
    registry = get_tool_registry()
    tools = registry.list_all()
    return [_tool_to_info(t) for t in tools]


class ToolInvokeRequest(BaseModel):
    tool_id: str
    input: Dict[str, Any] | None = None


@router.post("/tools/info", response_model=ToolInfoResponse)
async def get_tool_info(
    request: ToolInvokeRequest,
    user: Annotated[dict, Depends(get_current_user)],
) -> ToolInfoResponse:
    """Get detailed metadata for a single tool."""
    _load_all_tool_modules()
    registry = get_tool_registry()
    tool = registry.get(request.tool_id)
    if not tool:
        raise HTTPException(status_code=404, detail=f"Tool not found: {request.tool_id}")
    return _tool_to_info(tool)


@router.post("/tools/invoke")
async def invoke_tool(
    request: ToolInvokeRequest,
    user: Annotated[dict, Depends(get_current_user)],
):
    """Invoke a registered Agency tool directly via ToolRegistry."""
    _load_all_tool_modules()
    registry = get_tool_registry()
    tool = registry.get(request.tool_id)
    if not tool:
        raise HTTPException(status_code=404, detail=f"Tool not found: {request.tool_id}")

    kwargs = request.input or {}

    try:
        # NOTE: For now we only support tools whose handlers accept kwargs
        # matching the input dict; connectivity tools are parameterless.
        result = await tool.handler(**kwargs)
    except TypeError as exc:
        logger.error(f"Tool invocation failed (argument mismatch) for {request.tool_id}: {exc}")
        raise HTTPException(status_code=400, detail="Tool invocation argument mismatch")
    except Exception as exc:
        logger.error(f"Tool invocation failed for {request.tool_id}: {exc}")
        raise HTTPException(status_code=500, detail="Tool invocation failed")

    return result


# ============================================================================
# Curiosity Endpoints
# ============================================================================

@router.get("/curiosity", response_model=CuriosityStatusResponse)
async def get_curiosity_status(
    user: Annotated[dict, Depends(get_current_user)],
    engine: Annotated[AgencyEngine, Depends(get_agency_engine)]
):
    """
    Get current curiosity status - what AICO is curious about.
    
    Returns curiosity level and top curiosity opportunities.
    """
    try:
        user_id = user["user_uuid"]
        
        # Get intention set to analyze curiosity goals
        intention_set = await engine.get_intention_set(user_id)
        
        # Fetch goals and filter for curiosity-driven ones
        curiosity_goals = []
        for intention in intention_set.intentions:
            goal = await engine.get_goal(intention.goal_id)
            if goal and goal.origin.value == "curiosity":
                curiosity_goals.append((intention, goal))
        
        # Determine curiosity level based on active curiosity goals
        if len(curiosity_goals) >= 3:
            curiosity_level = CuriosityLevel.HIGH
        elif len(curiosity_goals) >= 1:
            curiosity_level = CuriosityLevel.MEDIUM
        else:
            curiosity_level = CuriosityLevel.LOW
        
        # Extract curiosity opportunities from metadata
        opportunities = []
        for intention, goal in curiosity_goals[:3]:  # Top 3
            if "curiosity_type" in goal.metadata:
                opportunities.append(
                    CuriosityOpportunity(
                        theme=goal.title,
                        description=goal.description or "",
                        intensity=goal.metadata.get("curiosity_score", 0.5),
                        signal_type=goal.metadata.get("curiosity_type", "unknown")
                    )
                )
        
        return CuriosityStatusResponse(
            user_id=user_id,
            curiosity_level=curiosity_level,
            curiosity_opportunities=opportunities,
            curiosity_goals_active=len(curiosity_goals),
            timestamp=datetime.utcnow()
        )
        
    except Exception as e:
        logger.error(f"Failed to get curiosity status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Value Profile Endpoints
# ============================================================================

@router.get("/profile", response_model=ValueProfileResponse)
async def get_value_profile(
    user: Annotated[dict, Depends(get_current_user)],
    uow: Annotated[UnitOfWork, Depends(get_uow)]
):
    """
    Get user value profile - curiosity settings, proactive level, sensitive areas.
    """
    try:
        user_id = user["user_uuid"]
        
        # Get profile from repository
        profiles = await uow.ethics_value_profiles.list(filters={"user_id": user_id}, limit=1)
        
        if not profiles:
            # Create default profile
            from aico.data.ethics.models import EthicsValueProfile
            import uuid as uuid_lib
            
            profile = EthicsValueProfile(
                profile_id=str(uuid_lib.uuid4()),
                user_id=user_id,
                curiosity_intensity=0.5,
                proactive_behavior_level="balanced",
                sensitive_life_areas=None,
                allowed_curiosity_domains=None,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            profile = await uow.ethics_value_profiles.create(profile)
            await uow.commit()
        else:
            profile = profiles[0]
        
        return ValueProfileResponse(
            profile_id=profile.profile_id,
            user_id=profile.user_id,
            curiosity_intensity=profile.curiosity_intensity,
            proactive_behavior_level=profile.proactive_behavior_level,
            sensitive_life_areas=profile.sensitive_life_areas if profile.sensitive_life_areas else [],
            allowed_curiosity_domains=profile.allowed_curiosity_domains if profile.allowed_curiosity_domains else []
        )
        
    except Exception as e:
        logger.error(f"Failed to get value profile: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/profile", response_model=ValueProfileResponse)
async def update_value_profile(
    request: UpdateValueProfileRequest,
    user: Annotated[dict, Depends(get_current_user)],
    uow: Annotated[UnitOfWork, Depends(get_uow)]
):
    """
    Update user value profile settings.
    """
    try:
        user_id = user["user_uuid"]
        
        # Get existing profile
        profiles = await uow.ethics_value_profiles.list(filters={"user_id": user_id}, limit=1)
        if not profiles:
            raise HTTPException(status_code=404, detail="Value profile not found")
        
        profile = profiles[0]
        
        # Apply updates
        if request.curiosity_intensity is not None:
            profile.curiosity_intensity = request.curiosity_intensity
        
        if request.proactive_behavior_level is not None:
            profile.proactive_behavior_level = request.proactive_behavior_level
        
        # Handle sensitive areas as list
        sensitive_areas = profile.sensitive_life_areas if profile.sensitive_life_areas else []
        if isinstance(sensitive_areas, str):
            sensitive_areas = json.loads(sensitive_areas)
        
        if request.add_sensitive_areas:
            for area in request.add_sensitive_areas:
                if area not in sensitive_areas:
                    sensitive_areas.append(area)
        
        if request.remove_sensitive_areas:
            sensitive_areas = [
                area for area in sensitive_areas
                if area not in request.remove_sensitive_areas
            ]
        
        profile.sensitive_life_areas = sensitive_areas
        profile.updated_at = datetime.utcnow()
        
        # Update via repository
        profile = await uow.ethics_value_profiles.update(profile)
        await uow.commit()
        
        return ValueProfileResponse(
            profile_id=profile.profile_id,
            user_id=profile.user_id,
            curiosity_intensity=profile.curiosity_intensity,
            proactive_behavior_level=profile.proactive_behavior_level,
            sensitive_life_areas=profile.sensitive_life_areas if profile.sensitive_life_areas else [],
            allowed_curiosity_domains=profile.allowed_curiosity_domains if profile.allowed_curiosity_domains else []
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update value profile: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Policy Endpoints
# ============================================================================

@router.get("/policies", response_model=PolicyListResponse)
async def list_policies(
    user: Annotated[dict, Depends(get_current_user)],
    uow: Annotated[UnitOfWork, Depends(get_uow)],
    target_type: Optional[str] = Query(None, description="Filter by target type")
):
    """
    List policy rules - what's allowed, warned, or blocked.
    """
    try:
        # Build filters
        filters = {"enabled": True}
        if target_type:
            filters["target_type"] = target_type
        
        # Get policies from repository
        policies = await uow.ethics_policy_rules.list(filters=filters, limit=1000)
        
        # Sort by priority
        policies.sort(key=lambda p: p.priority if p.priority else 999)
        
        policy_list = [
            PolicyRuleResponse(
                rule_id=p.rule_id,
                rule_name=p.rule_name,
                target_type=p.target_type,
                effect=PolicyEffect(p.effect),
                scope=p.scope,
                priority=p.priority,
                conditions=json.loads(p.conditions) if p.conditions and isinstance(p.conditions, str) else (p.conditions if p.conditions else {}),
                user_message=p.user_message,
                enabled=p.enabled
            )
            for p in policies
        ]
        
        return PolicyListResponse(
            policies=policy_list,
            total=len(policy_list)
        )
        
    except Exception as e:
        logger.error(f"Failed to list policies: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Consent Endpoints
# ============================================================================

@router.post("/consent", response_model=ConsentResponse, status_code=status.HTTP_201_CREATED)
async def grant_consent(
    request: ConsentRequest,
    user: Annotated[dict, Depends(get_current_user)],
    uow: Annotated[UnitOfWork, Depends(get_uow)]
):
    """
    Grant or deny consent for a specific action.
    """
    try:
        from aico.data.consent.models import ConsentRecord
        import uuid as uuid_lib
        
        user_id = user["user_uuid"]
        consent_id = f"consent-{user_id}-{datetime.utcnow().timestamp()}"
        
        # Create consent record
        consent = ConsentRecord(
            consent_id=consent_id,
            user_id=user_id,
            consent_scope=json.dumps(request.scope),
            decision=request.decision,
            granted_at=datetime.utcnow()
        )
        
        consent = await uow.consent_records.create(consent)
        await uow.commit()
        
        return ConsentResponse(
            consent_id=consent.consent_id,
            user_id=consent.user_id,
            scope=request.scope,
            decision=consent.decision,
            granted_at=consent.granted_at
        )
        
    except Exception as e:
        logger.error(f"Failed to grant consent: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/consent", response_model=ConsentListResponse)
async def list_consents(
    user: Annotated[dict, Depends(get_current_user)],
    uow: Annotated[UnitOfWork, Depends(get_uow)]
):
    """
    List user's consents.
    """
    try:
        user_id = user["user_uuid"]
        
        # Get consents from repository
        consents = await uow.consent_records.list(filters={"user_id": user_id}, limit=1000)
        
        # Sort by granted_at descending
        consents.sort(key=lambda c: c.granted_at if c.granted_at else datetime.min, reverse=True)
        
        consent_list = [
            ConsentResponse(
                consent_id=c.consent_id,
                user_id=c.user_id,
                scope=json.loads(c.consent_scope) if c.consent_scope and isinstance(c.consent_scope, str) else {},
                decision=c.decision,
                granted_at=c.granted_at if c.granted_at else datetime.utcnow()
            )
            for c in consents
        ]
        
        return ConsentListResponse(
            consents=consent_list,
            total=len(consent_list)
        )
        
    except Exception as e:
        logger.error(f"Failed to list consents: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/consent/{consent_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_consent(
    consent_id: str,
    user: Annotated[dict, Depends(get_current_user)],
    uow: Annotated[UnitOfWork, Depends(get_uow)]
):
    """
    Revoke a consent.
    """
    try:
        user_id = user["user_uuid"]
        
        # Get consent
        consent = await uow.consent_records.get_by_id(consent_id)
        if not consent:
            raise HTTPException(status_code=404, detail="Consent not found")
        
        # Verify ownership
        if consent.user_id != user_id:
            raise HTTPException(status_code=403, detail="Not authorized")
        
        # Update decision to denied
        consent.decision = "denied"
        await uow.consent_records.update(consent)
        await uow.commit()
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to revoke consent: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Goal Management Endpoints
# ============================================================================

@router.get("/goals", response_model=GoalListResponse)
async def list_goals(
    user: Annotated[dict, Depends(get_current_user)],
    engine: Annotated[AgencyEngine, Depends(get_agency_engine)],
    status: Optional[GoalStatus] = None,
    origin: Optional[GoalOrigin] = None,
    priority: Optional[GoalPriority] = None,
    limit: int = Query(50, ge=1, le=200),
    page: int = Query(1, ge=1)
):
    """
    List goals for the current user with optional filters.
    """
    try:
        user_id = user["user_uuid"]
        
        # Get all goals for user
        all_goals = await engine.list_goals_for_user(user_id)
        
        # Apply filters
        filtered_goals = all_goals
        if status:
            filtered_goals = [g for g in filtered_goals if g.status == status]
        if origin:
            filtered_goals = [g for g in filtered_goals if g.origin == origin]
        if priority:
            filtered_goals = [g for g in filtered_goals if g.priority == priority]
        
        # Pagination
        total = len(filtered_goals)
        start_idx = (page - 1) * limit
        end_idx = start_idx + limit
        paginated_goals = filtered_goals[start_idx:end_idx]
        
        # Convert to response format
        goal_responses = [
            GoalResponse(
                goal_id=g.goal_id,
                user_id=g.user_id,
                origin=GoalOrigin(g.origin),
                goal_type=g.goal_type,
                title=g.title,
                description=g.description or "",
                status=GoalStatus(g.status),
                priority=GoalPriority(g.priority),
                metadata=g.metadata or {},
                created_at=g.created_at.isoformat() if g.created_at else None,
                updated_at=g.updated_at.isoformat() if g.updated_at else None,
            )
            for g in paginated_goals
        ]
        
        return GoalListResponse(
            goals=goal_responses,
            total=total,
            page=page,
            page_size=limit
        )
        
    except Exception as e:
        logger.error(f"Failed to list goals: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/goals/{goal_id}", response_model=GoalResponse)
async def get_goal(
    goal_id: str,
    user: Annotated[dict, Depends(get_current_user)],
    engine: Annotated[AgencyEngine, Depends(get_agency_engine)]
):
    """
    Get a specific goal by ID with full details including plan, provenance, and execution history.
    """
    try:
        user_id = user["user_uuid"]
        
        goal = await engine.get_goal(goal_id)
        if not goal:
            raise HTTPException(status_code=404, detail=f"Goal {goal_id} not found")
        
        # Verify ownership
        if goal.user_id != user_id:
            raise HTTPException(status_code=403, detail="Not authorized to view this goal")
        
        # Enrich metadata with plan details
        enriched_metadata = goal.metadata.copy() if goal.metadata else {}
        
        # Fetch plan if exists (wrapped in try-except to handle missing methods gracefully)
        try:
            if hasattr(engine, 'plan_store') and engine.plan_store:
                plans = await engine.plan_store.list_plans_for_goal(goal_id)
                if plans:
                    active_plan = plans[0]  # Get most recent plan
                    enriched_metadata["plan_id"] = active_plan.plan_id
                    enriched_metadata["plan_title"] = active_plan.title or "Untitled Plan"
                    enriched_metadata["plan_strategy"] = active_plan.metadata.get("plan_strategy", "llm_refined") if active_plan.metadata else "llm_refined"
                    
                    # Fetch plan steps
                    try:
                        steps = await engine.plan_store.list_steps_for_plan(active_plan.plan_id)
                        enriched_metadata["plan_steps"] = [
                            {
                                "title": step.title,
                                "status": step.status.value,
                                "skill": step.skill_name,
                                "duration": step.metadata.get("estimated_duration") if step.metadata else None,
                            }
                            for step in steps
                        ]
                    except Exception as step_err:
                        logger.debug(f"Could not fetch plan steps: {step_err}")
        except Exception as plan_err:
            logger.debug(f"Could not fetch plan details: {plan_err}")
        
        # Add provenance information
        if goal.metadata and any(k in goal.metadata for k in ["conversation_id", "memory_id", "emotion_state"]):
            enriched_metadata["provenance"] = {
                "conversation": goal.metadata.get("conversation_id"),
                "memory": goal.metadata.get("memory_id"),
                "emotion": goal.metadata.get("emotion_state"),
            }
        
        # Add execution statistics (placeholder - would need execution tracking)
        enriched_metadata["executions"] = {
            "completed": 0,
            "running": 0,
            "total_time": None,
            "last_run": None,
        }
        
        return GoalResponse(
            goal_id=goal.goal_id,
            user_id=goal.user_id,
            origin=GoalOrigin(goal.origin.value),
            goal_type=goal.goal_type,
            title=goal.title,
            description=goal.description or "",
            status=GoalStatus(goal.status.value),
            priority=GoalPriority(goal.priority.value),
            metadata=enriched_metadata,
            created_at=goal.created_at,
            updated_at=goal.updated_at
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get goal: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/goals/{goal_id}/replan", response_model=dict)
async def replan_goal(
    goal_id: str,
    user: Annotated[dict, Depends(get_current_user)],
    engine: Annotated[AgencyEngine, Depends(get_agency_engine)],
    force: bool = False
):
    """
    Regenerate plan for a goal.
    
    Deletes existing plan and generates a new one using the planner.
    """
    try:
        user_id = user["user_uuid"]
        
        # Get goal
        goal = await engine.get_goal(goal_id)
        if not goal:
            raise HTTPException(status_code=404, detail=f"Goal {goal_id} not found")
        
        # Verify ownership
        if goal.user_id != user_id:
            raise HTTPException(status_code=403, detail="Not authorized to replan this goal")
        
        # Check if plan is active
        existing_plans = await engine.plan_store.list_plans_for_goal(goal_id)
        existing_plan = existing_plans[0] if existing_plans else None
        if existing_plan and existing_plan.status.value == "active" and not force:
            raise HTTPException(
                status_code=400,
                detail="Plan is currently active. Use force=true to replan anyway."
            )
        
        # Delete existing plan steps (if any) - plans are soft-deleted by status change
        if existing_plan:
            # Update plan status to abandoned
            from aico.ai.agency.models import PlanStatus
            await engine.plan_store.update_plan_status(existing_plan.plan_id, PlanStatus.ABANDONED)
        
        # Generate new plan
        new_plan = await engine._generate_and_store_plan(goal)
        
        # Build response with plan details
        metadata = new_plan.metadata.copy() if new_plan and new_plan.metadata else {}
        if new_plan:
            metadata["plan_id"] = new_plan.plan_id
            metadata["plan_strategy"] = new_plan.metadata.get("plan_strategy", "llm_refined")
        
        return {
            "goal_id": goal.goal_id,
            "title": goal.title,
            "description": goal.description,
            "status": goal.status.value,
            "metadata": metadata
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to replan goal: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {e}")


@router.get("/state", response_model=AgencyStateResponse)
async def get_agency_state(
    user: Annotated[dict, Depends(get_current_user)],
    engine: Annotated[AgencyEngine, Depends(get_agency_engine)],
    uow: Annotated[UnitOfWork, Depends(get_uow)]
):
    """
    Get complete agency state - intentions, curiosity, profile, and pending consents.
    
    This is a convenience endpoint that combines multiple agency metrics.
    """
    try:
        user_id = user["user_uuid"]
        
        # Get all components in parallel
        intention_set_task = get_intention_set(user, engine, limit=10)
        curiosity_task = get_curiosity_status(user, engine)
        profile_task = get_value_profile(user, uow)
        
        intention_set, curiosity_status, value_profile = await asyncio.gather(
            intention_set_task,
            curiosity_task,
            profile_task
        )
        
        # Get pending consent actions (goals/signals that need consent)
        # This would require querying for blocked actions - placeholder for now
        consent_required_actions = []
        
        return AgencyStateResponse(
            user_id=user_id,
            intention_set=intention_set,
            curiosity_status=curiosity_status,
            value_profile=value_profile,
            consent_required_actions=consent_required_actions,
            timestamp=datetime.utcnow()
        )
        
    except Exception as e:
        logger.error(f"Failed to get agency state: {e}")
        raise HTTPException(status_code=500, detail=str(e))
