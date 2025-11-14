"""
Behavioral Learning Data Models

Pydantic models for skill-based interaction learning with RLHF.
"""

from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Any
from datetime import datetime


class Skill(BaseModel):
    """
    Skill definition for behavioral learning.
    
    Skills are context-aware procedures that guide AI interaction style.
    Base skills are shared templates; user-created skills are personalized.
    """
    skill_id: str
    skill_name: str
    skill_type: str = Field(..., pattern="^(base|user_created)$")
    trigger_context: Dict[str, Any]  # JSON: {intent: [...], time_of_day: ...}
    procedure_template: str  # Prompt template to inject
    dimension_vector: List[float] = Field(..., min_length=16, max_length=16)  # 16 explicit dimensions
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class UserSkillConfidence(BaseModel):
    """User-specific confidence score for a skill."""
    user_id: str
    skill_id: str
    confidence_score: float = Field(default=0.5, ge=0.0, le=1.0)
    usage_count: int = 0
    positive_count: int = 0
    negative_count: int = 0
    last_used_at: Optional[datetime] = None


class FeedbackEvent(BaseModel):
    """User feedback on AI response."""
    event_id: str
    user_id: str
    message_id: str
    skill_id: Optional[str] = None
    reward: int = Field(..., ge=-1, le=1)  # -1 (negative), 0 (neutral), 1 (positive)
    reason: Optional[str] = None  # Dropdown selection
    free_text: Optional[str] = Field(None, max_length=300)  # User's free text
    classified_categories: Optional[Dict[str, float]] = None  # {"too_verbose": 0.85, ...}
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    processed: bool = False


class Trajectory(BaseModel):
    """Conversation turn trajectory for learning."""
    trajectory_id: str
    user_id: str
    conversation_id: str
    turn_number: int
    user_input: str
    selected_skill_id: Optional[str] = None
    ai_response: str
    feedback_reward: Optional[int] = Field(None, ge=-1, le=1)
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    archived: bool = False


class ContextSkillStats(BaseModel):
    """Thompson Sampling statistics for (context, skill) pair."""
    user_id: str
    context_bucket: int = Field(..., ge=0, le=99)
    skill_id: str
    alpha: float = Field(default=1.0, ge=0.0)  # Beta distribution success parameter
    beta: float = Field(default=1.0, ge=0.0)  # Beta distribution failure parameter
    last_updated_at: datetime = Field(default_factory=datetime.utcnow)


class PreferenceVector(BaseModel):
    """Context-aware user preference vector (16 explicit dimensions)."""
    user_id: str
    context_bucket: int = Field(..., ge=0, le=99)
    dimensions: List[float] = Field(..., min_length=16, max_length=16)  # Each in [0.0, 1.0]
    last_updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    @classmethod
    def create_neutral(cls, user_id: str, context_bucket: int) -> "PreferenceVector":
        """Create neutral preference vector (all 0.5)."""
        return cls(
            user_id=user_id,
            context_bucket=context_bucket,
            dimensions=[0.5] * 16
        )
