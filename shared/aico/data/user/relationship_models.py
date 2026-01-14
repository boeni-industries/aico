"""
User Relationship Data Models

Dataclasses for user relationships.
"""

from dataclasses import dataclass
from typing import Optional
from datetime import datetime


@dataclass
class UserRelationship:
    """User relationship model - matches user_relationships table."""
    uuid: str
    user_uuid: str
    related_user_uuid: str
    relationship_type: str
    is_active: bool = True
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


@dataclass
class UserSkillConfidence:
    """User skill confidence model - matches user_skill_confidence table."""
    user_id: str
    skill_id: str
    confidence_level: float
    last_used: Optional[str] = None
    usage_count: int = 0
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


@dataclass
class UserTimePreference:
    """User time preference model - matches user_time_preferences table."""
    preference_id: str
    user_id: str
    time_period: str
    productivity_score: float
    created_at: str
    updated_at: str
    active: bool = True
