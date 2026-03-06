"""
Emotion API Schemas

Pydantic models for emotion API request/response validation.
"""

from pydantic import BaseModel, Field, model_validator
from typing import List, Dict, Any, Optional
from datetime import datetime


class EmotionStateResponse(BaseModel):
    """Current emotional state response"""
    timestamp: str = Field(..., description="ISO 8601 timestamp of emotional state")
    primary: str = Field(..., description="Primary emotion label")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence level")
    valence: float = Field(..., ge=-1.0, le=1.0, description="Pleasure/displeasure dimension")
    arousal: float = Field(..., ge=0.0, le=1.0, description="Activation/energy level")
    dominance: float = Field(..., ge=0.0, le=1.0, description="Control/power dimension")
    
    class Config:
        json_schema_extra = {
            "example": {
                "timestamp": "2024-11-19T15:30:00Z",
                "primary": "calm",
                "confidence": 0.85,
                "valence": 0.3,
                "arousal": 0.4,
                "dominance": 0.5
            }
        }


class EmotionHistoryItem(BaseModel):
    """Single emotional state history entry"""
    timestamp: str = Field(..., description="ISO 8601 timestamp")
    feeling: Optional[str] = Field(default=None, description="Subjective feeling label")
    valence: Optional[float] = Field(default=None, ge=-1.0, le=1.0, description="Mood valence")
    arousal: Optional[float] = Field(default=None, ge=0.0, le=1.0, description="Mood arousal")
    intensity: Optional[float] = Field(default=None, ge=0.0, le=1.0, description="Emotional intensity")

    mood: Optional[Dict[str, Any]] = Field(default=None, description="Optional compact mood projection")
    label: Optional[Dict[str, Any]] = Field(default=None, description="Optional compact label projection")

    @model_validator(mode="before")
    @classmethod
    def _normalize_compact_projection(cls, data: Any):
        if not isinstance(data, dict):
            return data

        feeling = data.get("feeling")
        valence = data.get("valence")
        arousal = data.get("arousal")
        intensity = data.get("intensity")

        label = data.get("label") or {}
        mood = data.get("mood") or {}

        if feeling is None and isinstance(label, dict):
            feeling = label.get("primary")
        if intensity is None and isinstance(label, dict):
            intensity = label.get("intensity")
        if valence is None and isinstance(mood, dict):
            valence = mood.get("valence")
        if arousal is None and isinstance(mood, dict):
            arousal = mood.get("arousal")

        data["feeling"] = feeling
        data["valence"] = valence
        data["arousal"] = arousal
        data["intensity"] = intensity

        return data
    
    class Config:
        json_schema_extra = {
            "example": {
                "timestamp": "2024-11-19T15:30:00Z",
                "feeling": "warm_concern",
                "valence": 0.3,
                "arousal": 0.5,
                "intensity": 0.7
            }
        }


class EmotionHistoryResponse(BaseModel):
    """Emotional state history response"""
    count: int = Field(..., description="Number of history entries")
    history: List[EmotionHistoryItem] = Field(..., description="List of emotional states")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Optional metadata about data age and quality")
    
    class Config:
        json_schema_extra = {
            "example": {
                "count": 2,
                "history": [
                    {
                        "timestamp": "2024-11-19T15:30:00Z",
                        "feeling": "warm_concern",
                        "valence": 0.3,
                        "arousal": 0.5,
                        "intensity": 0.7
                    },
                    {
                        "timestamp": "2024-11-19T15:29:00Z",
                        "feeling": "neutral",
                        "valence": 0.0,
                        "arousal": 0.5,
                        "intensity": 0.5
                    }
                ]
            }
        }
