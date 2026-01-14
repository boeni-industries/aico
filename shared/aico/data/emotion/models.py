"""
Emotion Data Models

Dataclasses for emotion entities (state, history).
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class EmotionState:
    """Emotion state model - matches emotion_state table."""
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


@dataclass
class EmotionHistory:
    """Emotion history model - matches emotion_history table."""
    id: int
    user_id: str
    timestamp: str
    feeling: str
    valence: float
    arousal: float
    intensity: float
    created_at: Optional[str] = None
