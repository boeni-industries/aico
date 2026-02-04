"""
Agency API Router

REST API endpoints for agency system - intentions, goals, values, policies, and consents.
Based on agency-metrics.md user-facing metrics.
"""

import asyncio
import importlib
import json
import pkgutil
from datetime import datetime, UTC, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, status
from typing import Annotated, Optional, List, Dict, Any, Tuple
from pydantic import BaseModel
from sqlalchemy import select, func, case

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
    Event,
    EventType,
    EventsListResponse,
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
    # Studio-facing plan/execution models
    GoalDetailResponse,
    PlanResponse,
    PlanStepResponse,
    PlanExecutionSummary,
    StepExecutionSummary,
    PlanStatusAPI,
    ExecutionStatusAPI,
    StepExecutionStatusAPI,
    ReflectionRunResponse,
    ReflectionRunsListResponse,
    LessonResponse,
    LessonListResponse,
    SelfModelResponse,
    SelfModelListResponse,
    SkillPerformanceResponse,
    ReflectionSummaryResponse,
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
from aico.data.tables import agency_lessons, agency_reflection_runs
from backend.core.postgres_dependencies import get_uow

logger = get_logger("backend.api.agency")
router = APIRouter()


def _reflection_run_to_api(run) -> ReflectionRunResponse:
    return ReflectionRunResponse(
        run_id=run.run_id,
        user_id=run.user_id,
        run_type=run.run_type,
        trigger_reason=getattr(run, "trigger_reason", None),
        analysis_window_start=run.analysis_window_start,
        analysis_window_end=run.analysis_window_end,
        lessons_generated=int(getattr(run, "lessons_generated", 0) or 0),
        lessons_applied=int(getattr(run, "lessons_applied", 0) or 0),
        started_at=run.started_at,
        completed_at=getattr(run, "completed_at", None),
        duration_seconds=getattr(run, "duration_seconds", None),
        status=str(getattr(run, "status", "")),
        error_message=getattr(run, "error_message", None),
        created_at=getattr(run, "created_at", None),
    )


def _lesson_to_api(lesson) -> LessonResponse:
    proposed_change = getattr(lesson, "proposed_change", None)
    if proposed_change is None:
        proposed_change = {}
    if isinstance(proposed_change, str):
        try:
            proposed_change = json.loads(proposed_change)
        except Exception:
            proposed_change = {}

    metrics_basis = getattr(lesson, "metrics_basis", None)
    if isinstance(metrics_basis, str):
        try:
            metrics_basis = json.loads(metrics_basis)
        except Exception:
            metrics_basis = None

    return LessonResponse(
        lesson_id=lesson.lesson_id,
        user_id=lesson.user_id,
        lesson_type=str(getattr(lesson, "lesson_type", "")),
        target_kind=str(getattr(lesson, "target_kind", "")),
        target_id=getattr(lesson, "target_id", None),
        summary_text=getattr(lesson, "summary_text", ""),
        proposed_change=proposed_change if isinstance(proposed_change, dict) else {},
        confidence=float(getattr(lesson, "confidence", 0.0) or 0.0),
        metrics_basis=metrics_basis if isinstance(metrics_basis, dict) else None,
        scope=str(getattr(lesson, "scope", "")),
        status=str(getattr(lesson, "status", "")),
        superseded_by=getattr(lesson, "superseded_by", None),
        applied_at=getattr(lesson, "applied_at", None),
        applied_by=getattr(lesson, "applied_by", None),
        source_reflection_run_id=getattr(lesson, "source_reflection_run_id", None),
        evidence_window_start=getattr(lesson, "evidence_window_start", None),
        evidence_window_end=getattr(lesson, "evidence_window_end", None),
        created_at=getattr(lesson, "created_at", datetime.now(UTC)),
        updated_at=getattr(lesson, "updated_at", datetime.now(UTC)),
    )


def _self_model_to_api(model) -> SelfModelResponse:
    summary = getattr(model, "performance_summary", None)
    parsed: Dict[str, Any] = {}
    if isinstance(summary, str) and summary:
        try:
            loaded = json.loads(summary)
            if isinstance(loaded, dict):
                parsed = loaded
        except Exception:
            parsed = {}

    return SelfModelResponse(
        model_id=model.model_id,
        user_id=model.user_id,
        entity_type=model.entity_type,
        entity_id=model.entity_id,
        performance_summary=parsed,
        window_start=model.window_start,
        window_end=model.window_end,
        sample_size=int(getattr(model, "sample_size", 0) or 0),
        confidence=float(getattr(model, "confidence", 0.0) or 0.0),
        last_updated=getattr(model, "last_updated", None),
        created_at=getattr(model, "created_at", None),
    )

# ============================================================================
# Caching
# ============================================================================

# Simple in-memory cache for agency endpoints
_agency_cache: Dict[str, Tuple[Any, datetime]] = {}

async def _get_cached(key: str, ttl_seconds: int = 30) -> Optional[Any]:
    """Get cached value if not expired."""
    if key in _agency_cache:
        value, cached_at = _agency_cache[key]
        age = (datetime.now(UTC) - cached_at).total_seconds()
        
        if age < ttl_seconds:
            logger.info(f"[AGENCY_CACHE] Cache HIT for {key} (age: {age:.1f}s)")
            return value
        else:
            logger.info(f"[AGENCY_CACHE] Cache EXPIRED for {key} (age: {age:.1f}s)")
            del _agency_cache[key]
    else:
        logger.info(f"[AGENCY_CACHE] Cache MISS for {key}")
    
    return None

async def _set_cached(key: str, value: Any):
    """Store value in cache."""
    _agency_cache[key] = (value, datetime.now(UTC))
    logger.debug(f"[AGENCY_CACHE] Cached {key}")


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
        # Exclude technical/users used for internal instrumentation from
        # Studio-facing agency event streams.
        if user.get("is_technical"):
            raise HTTPException(status_code=403, detail="Technical users are excluded from agency events")

        user_id = user["user_uuid"]
        
        # Get intention set from engine
        intention_set = await engine.get_intention_set(user_id)
        
        # DEBUG: Log intention set data
        logger.debug(f"[DEBUG] get_intention_set for user {user_id}")
        logger.debug(f"[DEBUG] intention_set.intentions count: {len(intention_set.intentions)}")
        logger.debug(f"[DEBUG] intention_set raw: {intention_set}")
        
        # Limit results
        intentions = intention_set.intentions[:limit]
        logger.debug(f"[DEBUG] intentions after limit: {len(intentions)}")
        
        # Optimized: Fetch all Goal objects in a single bulk query instead of N+1 queries
        active_intentions = []
        if intentions:
            goal_ids = [intention.goal_id for intention in intentions]
            goals = await engine.agency_service.get_goals_bulk(goal_ids)
            
            # Create lookup dict for O(1) access
            goals_by_id = {goal.goal_id: goal for goal in goals}
            logger.debug(f"[DEBUG] Fetched {len(goals)} goals in single bulk query")
            
            for intention in intentions:
                goal = goals_by_id.get(intention.goal_id)
                if goal:
                    logger.debug(f"[DEBUG] Found goal: {goal.title} (status={goal.status.value})")
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
                    logger.debug(f"[DEBUG] Goal not found for intention: {intention.goal_id}")
        
        logger.debug(f"[DEBUG] active_intentions final count: {len(active_intentions)}")
        
        # Get hobby goals
        hobby_goals = [g for g in active_intentions if g.origin == GoalOrigin.HOBBY]
        
        # Count all open goals
        all_goals = await engine.list_goals_for_user(user_id)
        open_goals = [g for g in all_goals if g.status in [GoalStatus.PENDING, GoalStatus.ACTIVE]]
        
        logger.debug(f"[DEBUG] all_goals count: {len(all_goals)}, open_goals count: {len(open_goals)}")
        
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
# Events Endpoints
# ============================================================================


@router.get("/events", response_model=EventsListResponse)
async def list_events(
    user: Annotated[dict, Depends(get_current_user)],
    uow: Annotated[UnitOfWork, Depends(get_uow)],
    limit: int = Query(50, ge=1, le=200, description="Maximum number of events to return"),
    processed: Optional[bool] = Query(
        None,
        description="Optional filter by processed flag (derived from related_goal_id)",
    ),
    event_type: Optional[EventType] = Query(
        None,
        description="Optional filter by high-level event type",
    ),
) -> EventsListResponse:
    """List perception events driving autonomous behaviour.

    This endpoint exposes a unified event stream for the Execution Chain
    dashboard, projecting the internal agency_events_log table into the
    simplified Event model.
    """

    try:
        # Exclude technical/system users from Studio-facing agency event streams
        if user.get("is_technical"):
            raise HTTPException(status_code=403, detail="Technical users are excluded from agency events")

        user_id = user["user_uuid"]

        filters: Dict[str, Any] = {"user_id": user_id}
        if event_type is not None:
            filters["event_type"] = event_type.value

        rows = await uow.agency_events_log.list(filters=filters, limit=limit)

        events = [_event_log_to_api(row) for row in rows]

        if processed is not None:
            events = [e for e in events if e.processed == processed]

        count_filters: Dict[str, Any] = {"user_id": user_id}
        if event_type is not None:
            count_filters["event_type"] = event_type.value
        total = await uow.agency_events_log.count(filters=count_filters)

        return EventsListResponse(events=events, total=total)

    except Exception as e:
        logger.error(f"Failed to list agency events: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


def _build_goal_response(goal) -> GoalResponse:
    """Map domain Goal to API GoalResponse.

    This helper keeps goal-to-API mapping consistent across endpoints.
    """

    return GoalResponse(
        goal_id=goal.goal_id,
        user_id=goal.user_id,
        origin=GoalOrigin(goal.origin),
        goal_type=goal.goal_type,
        title=goal.title,
        description=goal.description or "",
        status=GoalStatus(goal.status),
        priority=GoalPriority(goal.priority),
        metadata=goal.metadata or {},
        created_at=goal.created_at,
        updated_at=goal.updated_at,
    )


def _map_plan_status(status_value: str) -> PlanStatusAPI:
    """Map stored plan status string to PlanStatusAPI with safe fallback."""

    try:
        return PlanStatusAPI(status_value)
    except Exception:
        # Fallback to DRAFT for unknown legacy statuses
        return PlanStatusAPI.DRAFT


def _map_execution_status(status_value: str) -> ExecutionStatusAPI:
    """Map stored execution status string to ExecutionStatusAPI with fallback."""

    try:
        return ExecutionStatusAPI(status_value)
    except Exception:
        return ExecutionStatusAPI.PENDING


def _map_step_execution_status(status_value: str) -> StepExecutionStatusAPI:
    """Map stored step execution status string to StepExecutionStatusAPI."""

    try:
        return StepExecutionStatusAPI(status_value)
    except Exception:
        return StepExecutionStatusAPI.PENDING


_KNOWN_EVENT_TYPE_MAP: Dict[str, EventType] = {
    # Curiosity / intrinsic motivation pipeline
    "curiosity_signal_detected": EventType.CURIOSITY_SIGNAL,
    "opportunities_scanned": EventType.CURIOSITY_SIGNAL,
    "goal_generated_from_curiosity": EventType.CURIOSITY_SIGNAL,
    "hobby_created": EventType.CURIOSITY_SIGNAL,
    "curiosity_signal_blocked": EventType.CURIOSITY_SIGNAL,
    "curiosity_signal_needs_consent": EventType.CURIOSITY_SIGNAL,
    "curiosity_signal_warning": EventType.CURIOSITY_SIGNAL,

    # Goal / plan lifecycle and ethics
    "goal_created": EventType.SYSTEM_OBSERVATION,
    "goal_updated": EventType.SYSTEM_OBSERVATION,
    "goal_blocked": EventType.SYSTEM_OBSERVATION,
    "plan_generation_started": EventType.SYSTEM_OBSERVATION,
    "plan_execution_started": EventType.SYSTEM_OBSERVATION,
    "feedback_collection_started": EventType.SYSTEM_OBSERVATION,
    "plan_executed": EventType.SYSTEM_OBSERVATION,

    # Workflows and world model updates
    "workflow_started": EventType.SYSTEM_OBSERVATION,
    "outcomes_analyzed": EventType.SYSTEM_OBSERVATION,
    "lessons_generated": EventType.SYSTEM_OBSERVATION,
    "adjustments_applied": EventType.SYSTEM_OBSERVATION,
    "changes_validated": EventType.SYSTEM_OBSERVATION,
    "hypothesis_generated": EventType.SYSTEM_OBSERVATION,
    "evidence_collected": EventType.SYSTEM_OBSERVATION,
    "hypothesis_validated": EventType.SYSTEM_OBSERVATION,
    "world_model_updated": EventType.SYSTEM_OBSERVATION,
}


def _map_event_type(raw_type: str) -> EventType:
    """Map low-level event_type strings to high-level EventType.

    Prefer explicit mappings for known event types and only fall back to
    minimal heuristics to keep the Execution Chain buckets stable.
    """

    normalized = (raw_type or "").strip().lower()
    if not normalized:
        return EventType.EXTERNAL_STIMULUS

    # 1) Exact mapping for known event types
    if normalized in _KNOWN_EVENT_TYPE_MAP:
        return _KNOWN_EVENT_TYPE_MAP[normalized]

    # 2) Narrow heuristics for "obvious" cases
    if normalized.startswith("user_") or normalized.startswith("manual_"):
        return EventType.USER_TRIGGER

    if "curiosity" in normalized:
        return EventType.CURIOSITY_SIGNAL

    if any(k in normalized for k in ("reflection", "maintenance", "workflow", "world_model")):
        return EventType.SYSTEM_OBSERVATION

    # 3) Fallback bucket for everything else (external/scheduled stimuli)
    return EventType.EXTERNAL_STIMULUS


def _event_log_to_api(row) -> Event:
    """Project AgencyEventLog row to public Event API model.

    The internal schema stores a flexible JSON payload; here we derive
    stable title/description/intensity fields with sensible fallbacks.
    """

    try:
        payload = json.loads(row.event_data) if row.event_data else {}
    except Exception:
        payload = {}

    title = payload.get("title") or payload.get("topic") or row.event_type
    description = payload.get("message") or payload.get("description") or ""

    raw_intensity = payload.get("intensity")
    if raw_intensity is None:
        raw_intensity = payload.get("curiosity_score") or payload.get("novelty_score")
    try:
        intensity = float(raw_intensity) if raw_intensity is not None else 0.5
    except (TypeError, ValueError):
        intensity = 0.5

    # Try to resolve a related goal from structured fields first
    related_goal_id = None
    if getattr(row, "entity_type", None) == "goal":
        related_goal_id = getattr(row, "entity_id", None)

    # Fallback: many events encode goal linkage in the JSON payload
    if not related_goal_id:
        related_goal_id = payload.get("goal_id")

    # Mark as processed if we can associate the event to a concrete goal
    processed = bool(related_goal_id)

    return Event(
        event_id=row.event_id,
        user_id=row.user_id,
        event_type=_map_event_type(row.event_type),
        source=row.source_component,
        title=title,
        description=description,
        intensity=max(0.0, min(1.0, intensity)),
        metadata=payload,
        created_at=row.created_at,
        processed=processed,
        related_goal_id=related_goal_id,
    )


@router.get("/goals/{goal_id}/plans", response_model=GoalDetailResponse)
async def get_goal_plans(
    goal_id: str,
    user: Annotated[dict, Depends(get_current_user)],
    engine: Annotated[AgencyEngine, Depends(get_agency_engine)],
):
    """Get a goal with all plans and their latest execution state.

    This is the Studio-facing read model:
    Goal → Plan(s) → PlanExecution → StepExecution.
    """

    try:
        user_id = user["user_uuid"]

        # Load goal from AgencyEngine and enforce ownership
        goal = await engine.get_goal(goal_id)
        if not goal:
            raise HTTPException(status_code=404, detail=f"Goal {goal_id} not found")

        if goal.user_id != user_id:
            raise HTTPException(status_code=403, detail="Not authorized to view this goal")

        goal_response = _build_goal_response(goal)

        # Get all plans for this goal via AgencyService (PostgreSQL-backed)
        agency_service = engine.agency_service
        plans = await agency_service.list_plans(goal_id=goal.goal_id)

        plan_responses: List[PlanResponse] = []

        for plan in plans:
            # Map plan steps (static plan definition)
            step_responses: List[PlanStepResponse] = []
            for step in plan.steps:
                # Enrich with implementation_tools from SkillRegistry
                implementation_tools: List[str] = []
                if step.skill_id and engine.skill_registry:
                    skill = engine.skill_registry.get(step.skill_id)
                    if skill:
                        implementation_tools = skill.implementation_tools
                
                step_responses.append(
                    PlanStepResponse(
                        step_id=step.step_id,
                        order=step.order,
                        description=step.description,
                        status=getattr(step.status, "value", str(step.status)),
                        tool_id=step.tool_id,
                        skill_id=step.skill_id,
                        scheduled_for=step.scheduled_for,
                        depends_on=step.depends_on or [],
                        metadata=step.metadata or {},
                        implementation_tools=implementation_tools,
                    )
                )

            latest_execution: Optional[PlanExecutionSummary] = None
            all_executions: List[PlanExecutionSummary] = []

            try:
                # Only fetch a bounded number of recent executions per plan
                executions = await agency_service.get_plan_executions(plan.plan_id, limit=10)
                if executions:
                    # Use PlanExecutor helper to get detailed status + steps for each execution
                    executor = engine.executor
                    if executor:
                        # Parse timestamps safely (they may already be datetime or ISO strings)
                        def _parse_dt(val: Any) -> Optional[datetime]:
                            if val is None:
                                return None
                            if isinstance(val, datetime):
                                return val
                            try:
                                return datetime.fromisoformat(val)
                            except Exception:
                                return None

                        for exec_row in executions:
                            try:
                                status_dict = await executor.get_execution_status(exec_row.execution_id)
                                if not status_dict:
                                    continue

                                step_execs: List[StepExecutionSummary] = []

                                def _step_field(step_obj: Any, field: str, default: Any = None) -> Any:
                                    if isinstance(step_obj, dict):
                                        return step_obj.get(field, default)
                                    if hasattr(step_obj, field):
                                        return getattr(step_obj, field)
                                    # Pydantic BaseModel (v1/v2) fallback
                                    if hasattr(step_obj, "model_dump"):
                                        try:
                                            return step_obj.model_dump().get(field, default)
                                        except Exception:
                                            return default
                                    if hasattr(step_obj, "dict"):
                                        try:
                                            return step_obj.dict().get(field, default)
                                        except Exception:
                                            return default
                                    return default

                                for s in status_dict.get("steps", []):
                                    step_execs.append(
                                        StepExecutionSummary(
                                            step_execution_id=str(_step_field(s, "step_execution_id", "")),
                                            step_id=str(_step_field(s, "step_id", "")),
                                            step_order=int(_step_field(s, "step_order", 0) or 0),
                                            status=_map_step_execution_status(str(_step_field(s, "status", "pending"))),
                                            duration_ms=_step_field(s, "duration_ms"),
                                            error_message=_step_field(s, "error_message"),
                                            skill_id=_step_field(s, "skill_id"),
                                            skill_invocation_id=_step_field(s, "skill_invocation_id"),
                                        )
                                    )

                                exec_summary = PlanExecutionSummary(
                                    execution_id=status_dict["execution_id"],
                                    plan_id=status_dict["plan_id"],
                                    goal_id=status_dict["goal_id"],
                                    status=_map_execution_status(status_dict.get("status", "pending")),
                                    steps_completed=status_dict.get("steps_completed", 0),
                                    steps_total=status_dict.get("steps_total", 0),
                                    progress_percentage=status_dict.get("progress_percentage", 0.0),
                                    started_at=_parse_dt(status_dict.get("started_at")),
                                    completed_at=_parse_dt(status_dict.get("completed_at")),
                                    last_error=status_dict.get("error_message"),
                                    last_updated_at=_parse_dt(status_dict.get("completed_at"))
                                    or _parse_dt(status_dict.get("started_at")),
                                    steps=step_execs,
                                )

                                all_executions.append(exec_summary)
                            except Exception as single_exec_err:
                                logger.error(
                                    f"[AGENCY_API] Failed to map execution {getattr(exec_row, 'execution_id', '?')} for plan {plan.plan_id}: {single_exec_err}",
                                    exc_info=True,
                                )

                        # Determine latest execution (by last_updated_at) for convenience
                        if all_executions:
                            latest_execution = max(
                                all_executions,
                                key=lambda e: e.last_updated_at or e.started_at or datetime.min,
                            )
            except Exception as exec_err:
                # Log but do not fail the entire response if execution data is missing/broken
                logger.error(
                    f"[AGENCY_API] Failed to attach executions for plan {plan.plan_id}: {exec_err}",
                    exc_info=True,
                )

            plan_responses.append(
                PlanResponse(
                    plan_id=plan.plan_id,
                    goal_id=plan.goal_id,
                    title=plan.title,
                    description=plan.description,
                    status=_map_plan_status(getattr(plan.status, "value", str(plan.status))),
                    metadata=plan.metadata or {},
                    created_at=plan.created_at,
                    updated_at=plan.updated_at,
                    steps=step_responses,
                    execution=latest_execution,
                    executions=all_executions,
                )
            )

        return GoalDetailResponse(goal=goal_response, plans=plan_responses)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get goal plans: {e}", exc_info=True)
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
    Cached for 20 seconds to reduce database load.
    """
    try:
        user_id = user["user_uuid"]
        
        # Check cache first (20s TTL, includes filter params in key)
        cache_key = f"goals_list:{user_id}:{status}:{origin}:{priority}:{limit}:{page}"
        cached_response = await _get_cached(cache_key, ttl_seconds=20)
        if cached_response is not None:
            return cached_response
        
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
        
        response = GoalListResponse(
            goals=goal_responses,
            total=total,
            page=page,
            page_size=limit
        )
        
        # Cache the response
        await _set_cached(cache_key, response)
        
        return response
        
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
    uow: Annotated[UnitOfWork, Depends(get_uow)],
):
    """Get complete agency state - intentions, curiosity, profile, and pending consents.

    This is a convenience endpoint that combines multiple agency metrics.
    Cached for 15 seconds to handle rapid-fire Studio requests.
    """
    try:
        # Agency state is a user-facing construct; do not compute it for
        # technical/system users.
        if user.get("is_technical"):
            raise HTTPException(status_code=403, detail="Technical users are excluded from agency state")

        user_id = user["user_uuid"]
        
        # Check cache first (15s TTL for rapid-fire requests)
        cache_key = f"agency_state:{user_id}"
        cached_response = await _get_cached(cache_key, ttl_seconds=15)
        if cached_response is not None:
            return cached_response
        
        # Get all components in parallel
        intention_set_task = get_intention_set(user, engine, limit=10)
        curiosity_task = get_curiosity_status(user, engine)
        profile_task = get_value_profile(user, uow)
        
        intention_set, curiosity_status, value_profile = await asyncio.gather(
            intention_set_task,
            curiosity_task,
            profile_task,
        )

        # Build recent_events goal-centrically: we care about events for the
        # goals that currently have active intentions, not an arbitrary
        # time-slice over all events.
        # Note: intention_set.active_intentions contains GoalSummary objects
        active_goal_ids = {
            goal_summary.goal_id
            for goal_summary in intention_set.active_intentions
        }
        
        logger.info(
            f"[AGENCY_API] Building recent_events for user {user_id}: "
            f"{len(active_goal_ids)} active goals"
        )

        # Optimized: Fetch all events in a single bulk query instead of N+1 queries
        projected_events: list[Event] = []
        if active_goal_ids:
            try:
                rows = await uow.agency_events_log.get_by_entities_bulk(
                    entity_type="goal",
                    entity_ids=list(active_goal_ids),
                    limit_per_entity=20,
                )
                logger.info(
                    f"[AGENCY_API] Fetched {len(rows)} events for {len(active_goal_ids)} goals in single query"
                )
                projected_events = [_event_log_to_api(row) for row in rows]
            except Exception as e:
                logger.error(
                    f"[AGENCY_API] Failed to fetch events in bulk: {e}",
                    exc_info=True,
                )

        # Deduplicate by event_id so each raw event is only represented once
        seen_ids: set[str] = set()
        goal_events: list[Event] = []
        for ev in projected_events:
            if ev.event_id in seen_ids:
                continue
            seen_ids.add(ev.event_id)
            goal_events.append(ev)

        # Group events by related_goal_id; any goal-linked event (including
        # goal_created, plan_generated, user_requested_goal, etc.)
        # contributes to that goal's aggregate.
        groups: Dict[str, list[Event]] = {}
        for ev in goal_events:
            if not ev.related_goal_id:
                continue
            groups.setdefault(ev.related_goal_id, []).append(ev)

        aggregated_events: list[Event] = []
        for goal_id, group in groups.items():
            # Pick the most recent event as the master for display, and use
            # strength to indicate how many underlying events contributed.
            master = max(group, key=lambda e: e.created_at)
            master.strength = len(group)
            aggregated_events.append(master)

        # Sort by recency and cap to last 10 summaries
        aggregated_events.sort(key=lambda e: e.created_at, reverse=True)
        recent_events = aggregated_events[:10]
        
        logger.info(
            f"[AGENCY_API] Event aggregation complete: "
            f"{len(projected_events)} raw events → "
            f"{len(goal_events)} deduplicated → "
            f"{len(aggregated_events)} aggregated → "
            f"{len(recent_events)} in recent_events"
        )
        
        # Get pending consent actions (goals/signals that need consent)
        # This would require querying for blocked actions - placeholder for now
        consent_required_actions = []
        
        response = AgencyStateResponse(
            user_id=user_id,
            intention_set=intention_set,
            curiosity_status=curiosity_status,
            value_profile=value_profile,
            consent_required_actions=consent_required_actions,
            recent_events=recent_events,
            timestamp=datetime.utcnow(),
        )
        
        # Cache the response
        await _set_cached(cache_key, response)
        
        return response
        
    except Exception as e:
        logger.error(f"Failed to get agency state: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==========================================================================
# Self-Reflection Transparency Endpoints (Studio-facing)
# ==========================================================================


@router.get("/reflection/runs", response_model=ReflectionRunsListResponse)
async def list_reflection_runs(
    user: Annotated[dict, Depends(get_current_user)],
    uow: Annotated[UnitOfWork, Depends(get_uow)],
    limit: int = Query(50, ge=1, le=200),
):
    try:
        user_id = user["user_uuid"]
        runs = await uow.agency_reflection_runs.get_user_runs(user_id)
        runs = runs[:limit]
        return ReflectionRunsListResponse(runs=[_reflection_run_to_api(r) for r in runs], total=len(runs))
    except Exception as e:
        logger.error(f"Failed to list reflection runs: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/reflection/lessons", response_model=LessonListResponse)
async def list_reflection_lessons(
    user: Annotated[dict, Depends(get_current_user)],
    uow: Annotated[UnitOfWork, Depends(get_uow)],
    active_only: bool = Query(True),
    lesson_type: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=500),
):
    try:
        user_id = user["user_uuid"]
        if active_only:
            lessons = await uow.lessons.get_active_lessons_for_user(user_id=user_id, lesson_type=lesson_type)
        else:
            filters: Dict[str, Any] = {"user_id": user_id}
            if lesson_type:
                filters["lesson_type"] = lesson_type
            lessons = await uow.lessons.list(filters=filters, limit=limit)
        lessons = lessons[:limit]
        return LessonListResponse(lessons=[_lesson_to_api(l) for l in lessons], total=len(lessons))
    except Exception as e:
        logger.error(f"Failed to list reflection lessons: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/reflection/self-model", response_model=SelfModelListResponse)
async def list_self_model(
    user: Annotated[dict, Depends(get_current_user)],
    uow: Annotated[UnitOfWork, Depends(get_uow)],
    entity_type: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=500),
):
    try:
        user_id = user["user_uuid"]
        models = await uow.agency_self_model.get_user_models(user_id=user_id, entity_type=entity_type)
        models = models[:limit]
        return SelfModelListResponse(models=[_self_model_to_api(m) for m in models], total=len(models))
    except Exception as e:
        logger.error(f"Failed to list self model: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/reflection/skills/{skill_id}/performance", response_model=SkillPerformanceResponse)
async def get_skill_performance(
    skill_id: str,
    user: Annotated[dict, Depends(get_current_user)],
    uow: Annotated[UnitOfWork, Depends(get_uow)],
):
    try:
        user_id = user["user_uuid"]
        model = await uow.agency_self_model.get_by_entity(user_id=user_id, entity_type="skill", entity_id=skill_id)
        if not model:
            return SkillPerformanceResponse(user_id=user_id, skill_id=skill_id, performance_summary=None)
        return SkillPerformanceResponse(
            user_id=user_id,
            skill_id=skill_id,
            performance_summary=_self_model_to_api(model).performance_summary,
        )
    except Exception as e:
        logger.error(f"Failed to get skill performance: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/reflection/summary", response_model=ReflectionSummaryResponse)
async def get_reflection_summary(
    user: Annotated[dict, Depends(get_current_user)],
    uow: Annotated[UnitOfWork, Depends(get_uow)],
    days: int = Query(7, ge=1, le=365),
    recent_lessons_limit: int = Query(10, ge=1, le=100),
):
    try:
        user_id = user["user_uuid"]
        window_end = datetime.now(UTC)
        window_start = window_end - timedelta(days=days)

        runs_stmt = (
            select(func.count())
            .select_from(agency_reflection_runs)
            .where(
                (agency_reflection_runs.c.user_id == user_id)
                & (agency_reflection_runs.c.started_at >= window_start)
                & (agency_reflection_runs.c.started_at <= window_end)
            )
        )
        runs_res = await uow._session.execute(runs_stmt)
        reflections = int(runs_res.scalar() or 0)

        lessons_agg_stmt = (
            select(
                func.count().label("lessons_total"),
                func.coalesce(
                    func.sum(case((agency_lessons.c.applied_at.is_not(None), 1), else_=0)),
                    0,
                ).label("lessons_applied"),
                func.avg(agency_lessons.c.confidence).label("avg_confidence"),
            )
            .select_from(agency_lessons)
            .where(
                (agency_lessons.c.user_id == user_id)
                & (agency_lessons.c.created_at >= window_start)
                & (agency_lessons.c.created_at <= window_end)
            )
        )
        lessons_agg_res = await uow._session.execute(lessons_agg_stmt)
        lessons_agg_row = lessons_agg_res.fetchone()
        lessons_total = int(getattr(lessons_agg_row, "lessons_total", 0) or 0) if lessons_agg_row else 0
        lessons_applied = int(getattr(lessons_agg_row, "lessons_applied", 0) or 0) if lessons_agg_row else 0
        avg_confidence_raw = getattr(lessons_agg_row, "avg_confidence", None) if lessons_agg_row else None
        avg_confidence = float(avg_confidence_raw) if avg_confidence_raw is not None else None

        recent_stmt = (
            select(agency_lessons)
            .where(
                (agency_lessons.c.user_id == user_id)
                & (agency_lessons.c.created_at >= window_start)
                & (agency_lessons.c.created_at <= window_end)
            )
            .order_by(agency_lessons.c.created_at.desc())
            .limit(recent_lessons_limit)
        )
        recent_res = await uow._session.execute(recent_stmt)
        recent_rows = recent_res.fetchall()
        recent_lessons = []
        for row in recent_rows:
            try:
                recent_lessons.append(_lesson_to_api(row[0]))
            except Exception:
                try:
                    recent_lessons.append(_lesson_to_api(row))
                except Exception:
                    pass

        return ReflectionSummaryResponse(
            user_id=user_id,
            window_days=days,
            window_start=window_start,
            window_end=window_end,
            reflections=reflections,
            lessons_total=lessons_total,
            lessons_applied=lessons_applied,
            avg_confidence=avg_confidence,
            recent_lessons=recent_lessons,
        )
    except Exception as e:
        logger.error(f"Failed to get reflection summary: {e}")
        raise HTTPException(status_code=500, detail=str(e))
