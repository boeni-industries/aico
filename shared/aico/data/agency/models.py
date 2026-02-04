from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field

from aico.data.agency.followup_models import AgencyFollowup
from aico.data.agency.goal_models import AgencyGoalSkillExecution
from aico.data.agency.skill_models import AgencySkillExecution
from aico.data.user.feedback_models import UserFeedbackRequest
from aico.data.conversation.models import ConversationInitiation
from aico.data.arbiter.models import ArbiterABTest, ArbiterBanditArm


class Goal(BaseModel):
    goal_id: str
    user_id: str
    origin: str
    goal_type: Optional[str] = None
    title: str
    description: Optional[str] = None
    status: str
    priority: str
    metadata: Optional[Dict[str, Any]] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class Plan(BaseModel):
    plan_id: str
    goal_id: str
    title: Optional[str] = None
    description: Optional[str] = None
    steps_json: Any
    status: str = "draft"
    metadata: Optional[Dict[str, Any]] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class AgencyEvent(BaseModel):
    id: Optional[int] = None
    user_id: str
    goal_id: Optional[str] = None
    plan_id: Optional[str] = None
    event_type: str
    source: str
    payload: Dict[str, Any] = Field(default_factory=dict)
    created_at: Optional[datetime] = None


class AgencyEventLog(BaseModel):
    event_id: str
    user_id: str
    event_type: str
    event_category: str
    source_component: str

    entity_type: Optional[str] = None
    entity_id: Optional[str] = None

    event_data: str
    workflow_trace_id: Optional[str] = None
    parent_event_id: Optional[str] = None
    severity: str = "info"
    created_at: str


class AgencyReflectionNote(BaseModel):
    note_id: str
    user_id: str
    related_goal_id: Optional[str] = None
    related_plan_id: Optional[str] = None
    title: str
    content: str
    tags: Optional[Dict[str, Any]] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class AgencyReminder(BaseModel):
    reminder_id: str
    user_id: str
    goal_id: Optional[str] = None

    title: str
    description: Optional[str] = None

    scheduled_at: str
    delivered_at: Optional[str] = None
    snoozed_until: Optional[str] = None
    snooze_count: int = 0

    status: str = "pending"
    priority: str = "normal"
    urgency_score: float = 0.5
    recurrence_rule: Optional[str] = None
    cluster_id: Optional[str] = None
    adaptation_data: Optional[str] = None

    created_at: str
    updated_at: str


class Policy(BaseModel):
    rule_id: str
    rule_name: str
    user_id: Optional[str] = None
    target_type: str
    conditions: str
    effect: str
    user_message_template: Optional[str] = None
    priority: int = 50
    scope: str
    version: int = 1
    active: bool = True
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


__all__ = [
    "Goal",
    "Plan",
    "AgencyEvent",
    "AgencyEventLog",
    "AgencyReflectionNote",
    "AgencyReminder",
    "Policy",
    "AgencyFollowup",
    "AgencyGoalSkillExecution",
    "AgencySkillExecution",
    "UserFeedbackRequest",
    "ConversationInitiation",
    "ArbiterBanditArm",
    "ArbiterABTest",
]
