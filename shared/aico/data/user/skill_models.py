"""
User Skill Confidence Data Models

Dataclasses for user skill confidence entities.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class UserSkillConfidence:
    """User skill confidence model - matches user_skill_confidence table."""
    user_id: str
    skill_id: str
    confidence_score: float = 0.5
    usage_count: int = 0
    positive_count: int = 0
    negative_count: int = 0
    last_used_at: Optional[datetime] = None
