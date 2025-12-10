from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional
from datetime import datetime

from pydantic import BaseModel, Field


class GoalOrigin(str, Enum):
    USER = "user"
    CURIOSITY = "curiosity"
    HOBBY = "hobby"
    MAINTENANCE = "maintenance"
    SYSTEM = "system"


class GoalStatus(str, Enum):
    PENDING = "pending"
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    RETIRED = "retired"


class GoalPriority(str, Enum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"


class PlanStatus(str, Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    COMPLETED = "completed"
    ABANDONED = "abandoned"


class StepStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    DONE = "done"
    SKIPPED = "skipped"


class Goal(BaseModel):
    """Domain model for agency goals backed by agency_goals table."""

    goal_id: str
    user_id: str
    origin: GoalOrigin
    goal_type: str
    title: str
    description: Optional[str] = None
    status: GoalStatus = GoalStatus.PENDING
    priority: GoalPriority = GoalPriority.NORMAL
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class PlanStep(BaseModel):
    """Single step within a plan, stored inside agency_plans.steps_json."""

    step_id: str
    order: int
    description: str
    status: StepStatus = StepStatus.PENDING
    tool_id: Optional[str] = None
    skill_id: Optional[str] = None
    scheduled_for: Optional[datetime] = None
    depends_on: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class Plan(BaseModel):
    """Plan skeleton for a goal, backed by agency_plans table."""

    plan_id: str
    goal_id: str
    status: PlanStatus = PlanStatus.DRAFT
    steps: List[PlanStep] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class AgencyEvent(BaseModel):
    """Typed wrapper for agency_events telemetry."""

    id: Optional[int] = None
    user_id: str
    goal_id: Optional[str] = None
    plan_id: Optional[str] = None
    event_type: str
    source: str
    payload: Dict[str, Any]
    created_at: datetime = Field(default_factory=datetime.utcnow)


class ReflectionNote(BaseModel):
    """Self-reflection note backed by agency_reflection_notes table."""

    note_id: str
    user_id: str
    related_goal_id: Optional[str] = None
    related_plan_id: Optional[str] = None
    title: str
    content: str
    tags: List[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


# Phase 5: Self-Reflection & Behavioral Learning Models

class LessonType(str, Enum):
    """Type of behavioral lesson learned through self-reflection."""
    SKILL_TUNING = "skill_tuning"
    PLANNER_HEURISTIC = "planner_heuristic"
    CURIOSITY_FOCUS = "curiosity_focus"
    PERSONA_STYLE = "persona_style"
    POLICY_SUGGESTION = "policy_suggestion"


class TargetKind(str, Enum):
    """Kind of entity the lesson targets for modification."""
    SKILL = "skill"
    PLANNER_TEMPLATE = "planner_template"
    ARBITER_WEIGHT = "arbiter_weight"
    CURIOSITY_POLICY = "curiosity_policy"
    PERSONA_TRAIT = "persona_trait"
    POLICY_RULE = "policy_rule"


class ChangeType(str, Enum):
    """Type of change proposed in a lesson."""
    THRESHOLD_TWEAK = "threshold_tweak"
    WEIGHT_TWEAK = "weight_tweak"
    EXCEPTION_ADD = "exception_add"
    EXCEPTION_REMOVE = "exception_remove"
    TEMPLATE_UPDATE = "template_update"


class LessonScope(str, Enum):
    """Scope of lesson application."""
    THIS_USER = "this_user"
    GLOBAL_DEFAULT = "global_default"


class LessonStatus(str, Enum):
    """Status of a lesson in its lifecycle."""
    ACTIVE = "active"
    SUPERSEDED = "superseded"
    REJECTED = "rejected"


class ProposedChange(BaseModel):
    """Structured representation of a proposed behavioral change."""
    change_type: ChangeType
    field: str  # The parameter/config field being changed
    old: Any  # Previous value
    new: Any  # Proposed new value
    notes: Optional[str] = None  # Human-readable explanation


class MetricsBasis(BaseModel):
    """Evidence basis for a lesson."""
    time_span: str  # e.g., "7 days", "30 days"
    sample_size: int
    outcome_counts: Dict[str, int]  # e.g., {"success": 45, "failure": 5}
    additional_metrics: Dict[str, Any] = Field(default_factory=dict)


class Lesson(BaseModel):
    """
    Structured behavioral lesson from self-reflection.
    Backed by agency_lessons table.
    """
    lesson_id: str
    user_id: str
    
    # Classification
    lesson_type: LessonType
    target_kind: TargetKind
    target_id: Optional[str] = None  # ID of target entity
    
    # Content
    summary_text: str  # Human-readable summary
    proposed_change: ProposedChange
    
    # Evidence
    confidence: float  # 0.0 to 1.0
    metrics_basis: Optional[MetricsBasis] = None
    
    # Scope and status
    scope: LessonScope
    status: LessonStatus
    superseded_by: Optional[str] = None  # lesson_id that replaced this
    
    # Application tracking
    applied_at: Optional[datetime] = None
    applied_by: Optional[str] = None  # Component that applied it
    
    # Provenance
    source_reflection_run_id: Optional[str] = None
    evidence_window_start: Optional[datetime] = None
    evidence_window_end: Optional[datetime] = None
    
    # Related entities
    related_goal_ids: List[str] = Field(default_factory=list)
    related_trajectory_ids: List[str] = Field(default_factory=list)
    related_event_ids: List[str] = Field(default_factory=list)
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class EntityType(str, Enum):
    """Type of entity tracked in self-model."""
    SKILL = "skill"
    GOAL_TYPE = "goal_type"
    INTERACTION_PATTERN = "interaction_pattern"


class PerformanceSummary(BaseModel):
    """Performance metrics for an entity."""
    success_rate: float  # 0.0 to 1.0
    avg_duration_seconds: Optional[float] = None
    user_satisfaction: Optional[float] = None  # 0.0 to 1.0
    additional_metrics: Dict[str, Any] = Field(default_factory=dict)


class SelfModelEntry(BaseModel):
    """
    Self-model performance tracking entry.
    Backed by agency_self_model table.
    """
    model_id: str
    user_id: str
    
    # What this tracks
    entity_type: EntityType
    entity_id: str  # Specific skill_id, goal type name, etc.
    
    # Performance metrics
    performance_summary: PerformanceSummary
    
    # Temporal scope
    window_start: datetime
    window_end: datetime
    sample_size: int
    
    # Confidence and freshness
    confidence: float  # 0.0 to 1.0
    last_updated: datetime = Field(default_factory=datetime.utcnow)
    
    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)


class RunType(str, Enum):
    """Type of reflection run."""
    SCHEDULED = "scheduled"
    TRIGGERED = "triggered"
    MANUAL = "manual"


class RunStatus(str, Enum):
    """Status of a reflection run."""
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class ReflectionRun(BaseModel):
    """
    Reflection run tracking for audit trail.
    Backed by agency_reflection_runs table.
    """
    run_id: str
    user_id: str
    
    # Run metadata
    run_type: RunType
    trigger_reason: Optional[str] = None  # sleep_phase, goal_completion, user_request, etc.
    
    # Analysis scope
    analysis_window_start: datetime
    analysis_window_end: datetime
    
    # Results
    lessons_generated: int = 0
    lessons_applied: int = 0
    
    # Timing
    started_at: datetime
    completed_at: Optional[datetime] = None
    duration_seconds: Optional[float] = None
    
    # Status
    status: RunStatus
    error_message: Optional[str] = None
    
    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
