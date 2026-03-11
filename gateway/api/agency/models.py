"""
Agency API Models

Pydantic models for agency API requests and responses.
Based on agency-metrics.md user-facing metrics.
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum


# ============================================================================
# Enums
# ============================================================================

class GoalOrigin(str, Enum):
    """Goal origin types"""
    USER = "user"
    CURIOSITY = "curiosity"
    HOBBY = "hobby"
    MAINTENANCE = "maintenance"


class GoalStatus(str, Enum):
    """Goal status types"""
    PENDING = "pending"
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    RETIRED = "retired"


class GoalPriority(str, Enum):
    """Goal priority levels"""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"


class CuriosityLevel(str, Enum):
    """Curiosity intensity levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class AutonomyLevel(str, Enum):
    """Autonomy levels"""
    QUIET = "quiet"
    BALANCED = "balanced"
    PROACTIVE = "proactive"
    AUTONOMOUS = "autonomous"


class PolicyEffect(str, Enum):
    """Policy decision effects"""
    ALLOW = "allow"
    ALLOW_WITH_WARNING = "allow_with_warning"
    NEEDS_CONSENT = "needs_consent"
    BLOCK = "block"


# ============================================================================
# Self-Reflection Transparency Models (Studio-facing)
# ============================================================================


class ReflectionRunResponse(BaseModel):
    run_id: str
    user_id: str
    run_type: str
    trigger_reason: Optional[str] = None
    analysis_window_start: datetime
    analysis_window_end: datetime
    lessons_generated: int
    lessons_applied: int
    started_at: datetime
    completed_at: Optional[datetime] = None
    duration_seconds: Optional[float] = None
    status: str
    error_message: Optional[str] = None
    created_at: Optional[datetime] = None


class ReflectionRunsListResponse(BaseModel):
    runs: List[ReflectionRunResponse]
    total: int


class LessonResponse(BaseModel):
    lesson_id: str
    user_id: str
    lesson_type: str
    target_kind: str
    target_id: Optional[str] = None
    summary_text: str
    proposed_change: Dict[str, Any] = Field(default_factory=dict)
    confidence: float
    metrics_basis: Optional[Dict[str, Any]] = None
    scope: str
    status: str
    superseded_by: Optional[str] = None
    applied_at: Optional[datetime] = None
    applied_by: Optional[str] = None
    source_reflection_run_id: Optional[str] = None
    evidence_window_start: Optional[datetime] = None
    evidence_window_end: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime


class LessonListResponse(BaseModel):
    lessons: List[LessonResponse]
    total: int


class SelfModelResponse(BaseModel):
    model_id: str
    user_id: str
    entity_type: str
    entity_id: str
    performance_summary: Dict[str, Any] = Field(default_factory=dict)
    window_start: datetime
    window_end: datetime
    sample_size: int
    confidence: float
    last_updated: Optional[datetime] = None
    created_at: Optional[datetime] = None


class SelfModelListResponse(BaseModel):
    models: List[SelfModelResponse]
    total: int


class SkillPerformanceResponse(BaseModel):
    user_id: str
    skill_id: str
    performance_summary: Optional[Dict[str, Any]] = None


class ReflectionSummaryResponse(BaseModel):
    user_id: str
    window_days: int
    window_start: datetime
    window_end: datetime
    reflections: int
    lessons_total: int
    lessons_applied: int
    avg_confidence: Optional[float] = None
    recent_lessons: List[LessonResponse] = Field(default_factory=list)


# ============================================================================
# Goal & Intention Models
# ============================================================================

class GoalSummary(BaseModel):
    """Lightweight goal summary for intention set"""
    goal_id: str
    title: str
    description: Optional[str] = None
    origin: GoalOrigin
    priority: GoalPriority
    status: GoalStatus
    score: Optional[float] = None
    priority_band: Optional[str] = None
    created_at: datetime
    metadata: Dict[str, Any] = Field(default_factory=dict)


class IntentionSetResponse(BaseModel):
    """Active intention set - what AICO is currently working on"""
    user_id: str
    primary_focus: Optional[GoalSummary] = Field(
        None,
        description="The top-scored intention AICO is currently focused on"
    )
    active_intentions: List[GoalSummary] = Field(
        default_factory=list,
        description="List of active intentions being pursued"
    )
    open_goals_total: int = Field(
        0,
        description="Total number of open goals/projects"
    )
    hobby_goals_active: List[GoalSummary] = Field(
        default_factory=list,
        description="AICO's own hobbies and self-projects"
    )
    timestamp: datetime = Field(default_factory=datetime.utcnow)


# ============================================================================
# Curiosity Models
# ============================================================================

class CuriosityOpportunity(BaseModel):
    """A curiosity theme or topic AICO is interested in"""
    theme: str
    description: str
    intensity: float = Field(ge=0.0, le=1.0)
    signal_type: str


class CuriosityStatusResponse(BaseModel):
    """Current curiosity status"""
    user_id: str
    curiosity_level: CuriosityLevel
    curiosity_opportunities: List[CuriosityOpportunity] = Field(
        default_factory=list,
        description="What AICO is currently curious about (1-3 items)"
    )
    curiosity_goals_active: int = Field(
        0,
        description="Number of active curiosity-driven goals"
    )
    timestamp: datetime = Field(default_factory=datetime.utcnow)


# ============================================================================
# Value Profile Models
# ============================================================================

class ValueProfileResponse(BaseModel):
    """User value profile"""
    profile_id: str
    user_id: str
    curiosity_intensity: float = Field(
        ge=0.0,
        le=1.0,
        description="Curiosity intensity threshold (0.0-1.0)"
    )
    autonomy_level: AutonomyLevel
    sensitive_life_areas: List[str] = Field(
        default_factory=list,
        description="Life areas requiring consent"
    )
    allowed_curiosity_domains: List[str] = Field(
        default_factory=list,
        description="Domains where curiosity is allowed"
    )


class UpdateValueProfileRequest(BaseModel):
    """Request to update value profile"""
    curiosity_intensity: Optional[float] = Field(None, ge=0.0, le=1.0)
    autonomy_level: Optional[AutonomyLevel] = None
    add_sensitive_areas: Optional[List[str]] = None
    remove_sensitive_areas: Optional[List[str]] = None


# ============================================================================
# Policy Models
# ============================================================================

class PolicyRuleResponse(BaseModel):
    """Policy rule details"""
    rule_id: str
    rule_name: str
    target_type: str
    effect: PolicyEffect
    scope: str
    priority: int
    conditions: Dict[str, Any] = Field(default_factory=dict)
    user_message: Optional[str] = None
    enabled: bool = True


class PolicyListResponse(BaseModel):
    """List of policy rules"""
    policies: List[PolicyRuleResponse]
    total: int


# ============================================================================
# Consent Models
# ============================================================================

class ConsentRequest(BaseModel):
    """Request to grant consent"""
    scope: Dict[str, Any] = Field(
        ...,
        description="Scope of consent (e.g., {'target_type': 'curiosity_signal', 'rule_id': 'xyz'})"
    )
    decision: str = Field("granted", description="'granted' or 'denied'")


class ConsentResponse(BaseModel):
    """Consent record"""
    consent_id: str
    user_id: str
    scope: Dict[str, Any]
    decision: str
    granted_at: datetime


class ConsentListResponse(BaseModel):
    """List of user consents"""
    consents: List[ConsentResponse]
    total: int


# ============================================================================
# Event Models
# ============================================================================

class EventType(str, Enum):
    """High-level event types for agency perception system."""

    CURIOSITY_SIGNAL = "curiosity_signal"
    USER_TRIGGER = "user_trigger"
    SYSTEM_OBSERVATION = "system_observation"
    EXTERNAL_STIMULUS = "external_stimulus"


class Event(BaseModel):
    """API-level event model backing the Execution Chain Dashboard.

    This is a projection over the internal agency_events_log table and existing
    AgencyEvent logging, providing a stable, frontend-friendly view of
    perceptual triggers and signals that can lead to goal creation.
    """

    event_id: str
    user_id: str
    event_type: EventType
    source: str
    title: str
    description: str
    intensity: float = Field(ge=0.0, le=1.0)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    processed: bool = False
    related_goal_id: Optional[str] = None
    strength: int = Field(
        1,
        description=(
            "Number of underlying raw events contributing to this perception. "
            "For raw /agency/events responses this is 1; aggregated views like "
            "recent_events may increase this to reflect repeated signals."
        ),
        ge=1,
    )


class EventsListResponse(BaseModel):
    """Paginated list of events for /agency/events endpoint."""

    events: List[Event]
    total: int


# ============================================================================
# Agency State Models
# ============================================================================

class AgencyStateResponse(BaseModel):
    """Overall agency state for a user"""

    user_id: str
    intention_set: IntentionSetResponse
    curiosity_status: CuriosityStatusResponse
    value_profile: ValueProfileResponse
    consent_required_actions: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Actions waiting on explicit user approval",
    )
    recent_events: List[Event] = Field(
        default_factory=list,
        description="Last 10 unprocessed events driving autonomous behaviour",
    )
    timestamp: datetime = Field(default_factory=datetime.utcnow)


# ============================================================================
# Goal Management Models
# ============================================================================

class CreateGoalRequest(BaseModel):
    """Request to create a new goal"""
    title: str = Field(..., min_length=1, max_length=200)
    description: str = Field(..., min_length=1)
    goal_type: str = "project"
    priority: GoalPriority = GoalPriority.NORMAL
    auto_plan: bool = False
    metadata: Dict[str, Any] = Field(default_factory=dict)


class GoalResponse(BaseModel):
    """Detailed goal information"""
    goal_id: str
    user_id: str
    origin: GoalOrigin
    goal_type: str
    title: str
    description: str
    status: GoalStatus
    priority: GoalPriority
    metadata: Dict[str, Any]
    created_at: datetime
    updated_at: datetime


class GoalListResponse(BaseModel):
    """List of goals"""
    goals: List[GoalResponse]
    total: int
    page: int = 1
    page_size: int = 50


class UpdateGoalRequest(BaseModel):
    """Request to update a goal"""
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = Field(None, min_length=1)
    priority: Optional[GoalPriority] = None
    status: Optional[GoalStatus] = None
    metadata: Optional[Dict[str, Any]] = None


# ============================================================================
# Plan & Execution Models (Studio-facing read models)
# ============================================================================


class PlanStatusAPI(str, Enum):
    """Plan status exposed via API (mirrors domain PlanStatus)."""

    DRAFT = "draft"
    ACTIVE = "active"
    COMPLETED = "completed"
    PAUSED = "paused"
    ABANDONED = "abandoned"


class ExecutionStatusAPI(str, Enum):
    """Execution status for plan executions."""

    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class StepExecutionStatusAPI(str, Enum):
    """Execution status for individual plan steps."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"
    BLOCKED = "blocked"


class PlanStepResponse(BaseModel):
    """Single plan step as exposed to Studio.

    Parsed from agency_plans.steps_json and enriched in the domain PlanStep
    model. This ensures no double-encoded JSON is leaked to the frontend.
    """

    step_id: str
    order: int
    description: str
    status: str
    tool_id: Optional[str] = None
    skill_id: Optional[str] = None
    scheduled_for: Optional[datetime] = None
    depends_on: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    implementation_tools: List[str] = Field(default_factory=list)  # Tools used by this skill


class StepExecutionSummary(BaseModel):
    """Execution status for a single step within a plan execution."""

    step_execution_id: str
    step_id: str
    step_order: int
    status: StepExecutionStatusAPI
    duration_ms: Optional[int] = None
    error_message: Optional[str] = None
    skill_id: Optional[str] = None
    skill_invocation_id: Optional[str] = None


class PlanExecutionSummary(BaseModel):
    """High-level execution status for a plan.

    Aggregates step execution data as needed by Studio for progress bars
    and status badges.
    """

    execution_id: str
    plan_id: str
    goal_id: str
    status: ExecutionStatusAPI
    steps_completed: int
    steps_total: int
    progress_percentage: float
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    last_error: Optional[str] = None
    last_updated_at: Optional[datetime] = None
    steps: List[StepExecutionSummary] = Field(default_factory=list)


class PlanResponse(BaseModel):
    """Plan plus parsed steps and current execution summary for a goal."""

    plan_id: str
    goal_id: str
    title: Optional[str] = None
    description: Optional[str] = None
    status: PlanStatusAPI
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime
    steps: List[PlanStepResponse] = Field(default_factory=list)
    # Latest/most relevant execution for this plan (used for progress bar etc.)
    execution: Optional[PlanExecutionSummary] = None
    # All known executions for this plan (historical runs + current run)
    executions: List[PlanExecutionSummary] = Field(default_factory=list)


class GoalDetailResponse(BaseModel):
    """Rich goal detail view for Studio.

    Combines the core GoalResponse with all associated plans and their
    latest execution state. This is intentionally separate from
    GoalResponse to keep the basic goal API stable and focused.
    """

    goal: GoalResponse
    plans: List[PlanResponse] = Field(default_factory=list)

