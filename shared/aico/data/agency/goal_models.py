from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Optional, List

from pydantic import BaseModel, Field


class AgencyGoalDependency(BaseModel):
    dependency_id: str
    goal_id: str
    prerequisite_goal_id: str
    dependency_type: str = "hard"
    active: bool = True
    created_at: datetime


class AgencyGoalOutcome(BaseModel):
    outcome_id: str
    goal_id: str
    user_id: str
    arm_id: Optional[str] = None
    outcome: str
    success: int = 0
    reward: Optional[float] = None
    completion_time_minutes: Optional[int] = None
    user_satisfaction: Optional[float] = None
    metadata_json: Optional[Dict[str, Any]] = None
    created_at: datetime


class AgencyGoalSkillExecution(BaseModel):
    link_id: str
    goal_id: str
    skill_id: str
    execution_id: str
    execution_order: Optional[int] = None
    created_at: datetime


class AgencyIntentionSet(BaseModel):
    intention_id: str
    goal_id: str
    user_id: str
    status: str = "proposed"
    arbiter_score: float
    priority_band: str
    reasons_json: Optional[List[str]] = None
    activated_at: Optional[datetime] = None
    deactivated_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
