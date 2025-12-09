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
