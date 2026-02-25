from __future__ import annotations

from typing import Optional
from datetime import datetime

from pydantic import BaseModel, field_validator


class EmotionState(BaseModel):
    id: int
    user_id: str
    timestamp: datetime

    subjective_feeling: str
    mood_valence: float
    mood_arousal: float
    intensity: float

    warmth: float
    directness: float
    formality: float
    engagement: float
    closeness: float
    care_focus: float
    
    updated_at: Optional[datetime] = None
    
    @field_validator('timestamp', 'updated_at', mode='before')
    @classmethod
    def normalize_datetime(cls, v):
        """Normalize PostgreSQL datetime strings."""
        if isinstance(v, str):
            # Remove trailing Z if there's already a timezone offset
            if '+' in v and v.endswith('Z'):
                v = v[:-1]
            # Normalize +00 to +00:00
            elif v.endswith('+00'):
                v = v + ':00'
        return v


class EmotionHistory(BaseModel):
    id: int = 0
    user_id: str
    timestamp: datetime

    feeling: str
    valence: float
    arousal: float
    intensity: float

    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    @field_validator('timestamp', 'created_at', 'updated_at', mode='before')
    @classmethod
    def normalize_datetime(cls, v):
        """Normalize PostgreSQL datetime strings."""
        if isinstance(v, str):
            # Remove trailing Z if there's already a timezone offset
            if '+' in v and v.endswith('Z'):
                v = v[:-1]
            # Normalize +00 to +00:00
            elif v.endswith('+00'):
                v = v + ':00'
        return v
