"""
Emotion API Schemas

Pydantic models for emotion API request/response validation.
"""

from pydantic import BaseModel, Field
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
    feeling: str = Field(..., description="Subjective feeling label")
    valence: float = Field(..., ge=-1.0, le=1.0, description="Mood valence")
    arousal: float = Field(..., ge=0.0, le=1.0, description="Mood arousal")
    intensity: float = Field(..., ge=0.0, le=1.0, description="Emotional intensity")
    
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
