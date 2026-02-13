from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class UserProfile(BaseModel):
    uuid: str
    full_name: str
    nickname: Optional[str] = None
    user_type: str
    is_active: bool = True
    primary_language: Optional[str] = "en"
    created_at: datetime
    updated_at: datetime


class UserSkillConfidence(BaseModel):
    user_id: str
    skill_id: str
    confidence_score: float = 0.5
    usage_count: int = 0
    positive_count: int = 0
    negative_count: int = 0
    last_used_at: Optional[datetime] = None


class UserFeedbackRequest(BaseModel):
    request_id: str
    user_id: str
    goal_id: Optional[str] = None
    skill_id: Optional[str] = None
    execution_id: Optional[str] = None
    feedback_type: str
    question: str
    response: Optional[str] = None
    rating: Optional[float] = None
    responded_at: Optional[datetime] = None
    created_at: datetime


class UserProactivePreferences(BaseModel):
    user_id: str
    followup_enabled: bool = True
    reminder_enabled: bool = True
    preferred_followup_times: Optional[str] = None
    preferred_reminder_times: Optional[str] = None
    max_followups_per_day: int = 3
    max_reminders_per_day: int = 5
    min_hours_between_followups: int = 4
    min_hours_between_reminders: int = 2
    cluster_reminders: int = 1
    auto_snooze_duration_minutes: int = 60
    updated_at: datetime


class UserRelationship(BaseModel):
    uuid: str
    user_uuid: str
    related_user_uuid: str
    relationship_type: str
    is_active: bool = True
    created_at: datetime
    updated_at: datetime


class UserTimePreference(BaseModel):
    preference_id: str
    user_id: str
    time_period: str
    productivity_score: float = 1.0
    active: bool = True
    created_at: datetime
    updated_at: datetime


class AuthenticationData(BaseModel):
    """Persistence-facing auth metadata associated with a user profile.

    This is used by the historical user data layer; keep minimal fields and extend only
    when the repository/schema requires it.
    """

    user_uuid: str
    pin_hash: str
    failed_attempts: int = 0
    locked_until: Optional[datetime] = None
    last_login: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
