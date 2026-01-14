from __future__ import annotations

from typing import Optional
from datetime import datetime

from pydantic import BaseModel


class EmotionState(BaseModel):
    id: int
    user_id: str
    timestamp: str

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
    
    updated_at: Optional[str] = None


class EmotionHistory(BaseModel):
    id: int = 0
    user_id: str
    timestamp: str

    feeling: str
    valence: float
    arousal: float
    intensity: float

    created_at: Optional[str] = None
    updated_at: Optional[str] = None
