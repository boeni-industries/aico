"""
Ethics Value Profile Data Models

Dataclasses for ethics value profile entities.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class EthicsValueProfile:
    """Ethics value profile model - matches ethics_value_profiles table."""
    profile_id: str
    user_id: str
    sensitive_life_areas: Optional[str] = None
    allowed_curiosity_domains: Optional[str] = None
    curiosity_intensity: float = 0.5
    proactive_behavior_level: str = 'balanced'
    storage_preferences: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
