"""
Agency System Data Models

Dataclasses for agency-related entities (goals, plans, lessons, events).
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Dict, Any, List


@dataclass
class AgencyEvent:
    """Agency event model - matches agency_events table."""
    id: int
    user_id: str
    event_type: str
    source: str
    payload_json: Dict[str, Any]
    goal_id: Optional[str] = None
    plan_id: Optional[str] = None
    created_at: Optional[datetime] = None


@dataclass
class AgencyEventLog:
    """Agency event log model - matches agency_events_log table."""
    event_id: str
    user_id: str
    event_type: str
    event_category: str
    source_component: str
    event_data: str
    created_at: str
    entity_type: Optional[str] = None
    entity_id: Optional[str] = None
    workflow_trace_id: Optional[str] = None
    parent_event_id: Optional[str] = None
    severity: str = 'info'


@dataclass
class AgencyFollowup:
    """Agency followup model - matches agency_followups table."""
    followup_id: str
    user_id: str
    followup_type: str
    content: str
    scheduled_at: str
    status: str
    created_at: str
    updated_at: str
    goal_id: Optional[str] = None
    related_message_id: Optional[str] = None
    delivered_at: Optional[str] = None
    user_response: Optional[str] = None
    response_sentiment: Optional[float] = None
    priority: int = 50
    policy_approved: int = 1
    relationship_context: Optional[str] = None
    values_alignment: Optional[float] = None


@dataclass
class AgencyReflectionNote:
    """Agency reflection note model - matches agency_reflection_notes table."""
    note_id: str
    user_id: str
    title: str
    content: str
    related_goal_id: Optional[str] = None
    related_plan_id: Optional[str] = None
    tags_json: Optional[Dict[str, Any]] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


@dataclass
class AgencyReminder:
    """Agency reminder model - matches agency_reminders table."""
    reminder_id: str
    user_id: str
    title: str
    scheduled_at: str
    status: str
    priority: str
    created_at: str
    updated_at: str
    goal_id: Optional[str] = None
    description: Optional[str] = None
    delivered_at: Optional[str] = None
    snoozed_until: Optional[str] = None
    snooze_count: int = 0
    urgency_score: float = 0.5
    recurrence_rule: Optional[str] = None
    cluster_id: Optional[str] = None
    adaptation_data: Optional[str] = None


@dataclass
class Goal:
    """Agency goal model."""
    goal_id: str
    user_id: str
    origin: str
    title: str
    status: str
    priority: str
    goal_type: Optional[str] = None
    description: Optional[str] = None
    metadata_json: Optional[Dict[str, Any]] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


@dataclass
class Plan:
    """Agency plan model."""
    plan_id: str
    goal_id: str
    status: str
    steps_json: List[Dict[str, Any]]
    metadata_json: Optional[Dict[str, Any]] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


@dataclass
class Lesson:
    """Agency lesson model."""
    lesson_id: str
    user_id: str
    lesson_type: str
    content: str
    confidence: float
    status: str
    source_data: Optional[Dict[str, Any]] = None
    superseded_by: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


@dataclass
class Policy:
    """Agency policy rule model."""
    rule_id: str
    rule_name: str
    target_type: str
    conditions: str
    effect: str
    scope: str
    user_id: Optional[str] = None
    user_message_template: Optional[str] = None
    priority: int = 50
    version: int = 1
    active: bool = True
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
