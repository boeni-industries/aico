from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class AgencySkillGap(BaseModel):
    gap_id: str
    step_description: str
    llm_suggested_skills: Optional[str] = None
    step_metadata: Optional[str] = None
    pattern_embedding: Optional[str] = None
    frequency_count: int = 1
    first_seen_at: str
    last_seen_at: str
    priority_score: float = 0.0
    suggested_skill_spec: Optional[str] = None
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class AgencySkillExecution(BaseModel):
    execution_id: str
    skill_id: str
    user_id: str
    message_id: Optional[str] = None
    goal_id: Optional[str] = None
    execution_time_ms: Optional[int] = None
    outcome: str
    error_message: Optional[str] = None
    context_json: Optional[dict] = None
    created_at: datetime


class AgencySkillLearningData(BaseModel):
    skill_id: str
    dimension_vector: str
    created_at: datetime
    updated_at: datetime
