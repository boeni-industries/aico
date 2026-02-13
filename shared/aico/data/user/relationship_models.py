from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class UserRelationship(BaseModel):
    uuid: str
    user_uuid: str
    related_user_uuid: str
    relationship_type: str
    is_active: bool = True
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class UserSkillConfidence(BaseModel):
    user_id: str
    skill_id: str
    confidence_score: float = 0.5
    usage_count: int = 0
    positive_count: int = 0
    negative_count: int = 0
    last_used_at: Optional[datetime] = None


class UserTimePreference(BaseModel):
    preference_id: str
    user_id: str
    time_period: str
    productivity_score: float = 1.0
    active: bool = True
    created_at: datetime
    updated_at: datetime
