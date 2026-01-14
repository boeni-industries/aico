"""
Agency Goal Data Models

Dataclasses for goal-related entities.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class AgencyGoalDependency:
    """Agency goal dependency model - matches agency_goal_dependencies table."""
    dependency_id: str
    goal_id: str
    prerequisite_goal_id: str
    created_at: str
    dependency_type: str = 'hard'
    active: bool = True


@dataclass
class AgencyGoalOutcome:
    """Agency goal outcome model - matches agency_goal_outcomes table."""
    outcome_id: str
    goal_id: str
    user_id: str
    outcome: str
    created_at: str
    arm_id: Optional[str] = None
    success: int = 0
    reward: Optional[float] = None
    completion_time_minutes: Optional[int] = None
    user_satisfaction: Optional[float] = None
    metadata_json: Optional[dict] = None


@dataclass
class AgencyGoalSkillExecution:
    """Agency goal skill execution model - matches agency_goal_skill_executions table."""
    link_id: str
    goal_id: str
    skill_id: str
    execution_id: str
    created_at: str
    execution_order: Optional[int] = None


@dataclass
class AgencyIntentionSet:
    """Agency intention set model - matches agency_intention_set table."""
    intention_id: str
    goal_id: str
    user_id: str
    status: str
    arbiter_score: float
    priority_band: str
    created_at: datetime
    updated_at: datetime
    reasons_json: Optional[dict] = None
    activated_at: Optional[datetime] = None
    deactivated_at: Optional[datetime] = None
