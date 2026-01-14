"""
AMS Context Data Models

Dataclasses for AMS context preference vectors and skill stats.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class AMSContextPreferenceVector:
    """AMS context preference vector model - matches ams_context_preference_vectors table."""
    user_id: str
    context_bucket: int
    dimensions: str
    last_updated_at: datetime


@dataclass
class AMSContextSkillStats:
    """AMS context skill stats model - matches ams_context_skill_stats table."""
    user_id: str
    context_bucket: int
    skill_id: str
    alpha: float
    beta: float
    last_updated_at: datetime
