"""
AMS (Adaptive Memory System) Domain Models

Rich domain models for behavioral and adaptive memory entities.
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class AMSTrajectory(BaseModel):
    """AMS trajectory domain model matching PostgreSQL schema."""
    trajectory_id: str
    user_id: str
    conversation_id: Optional[str] = None
    selected_skill_id: Optional[str] = None
    context_bucket: Optional[str] = None
    feedback_reward: Optional[int] = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now())
    archived: bool = False
    agency_context: Optional[str] = None
    message_id: Optional[str] = None
    turn_number: Optional[int] = None
    user_input: Optional[str] = None
    ai_response: Optional[str] = None


class AMSBehavioralFeedback(BaseModel):
    """AMS behavioral feedback domain model."""
    feedback_id: str
    user_id: str
    feedback_type: str
    content: str
    sentiment: Optional[float] = None
    context: Optional[dict] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now())


class AMSBehavioralSkill(BaseModel):
    """AMS behavioral skill domain model."""
    skill_id: str
    user_id: str
    skill_name: str
    skill_type: str
    proficiency: float = 0.0
    usage_count: int = 0
    last_used: Optional[datetime] = None
    metadata: dict = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now())
    updated_at: datetime = Field(default_factory=lambda: datetime.now())


class AMSContextPreferenceVector(BaseModel):
    """AMS context preference vector domain model."""
    user_id: str
    context_bucket: int
    dimensions: str
    last_updated_at: datetime = Field(default_factory=lambda: datetime.now())


class AMSContextSkillStats(BaseModel):
    """AMS context skill stats domain model."""
    user_id: str
    context_bucket: int
    skill_id: str
    alpha: float
    beta: float
    last_updated_at: datetime = Field(default_factory=lambda: datetime.now())


class AMSUserMemory(BaseModel):
    """AMS user memory domain model matching PostgreSQL schema."""
    fact_id: str  # Primary key (not memory_id)
    user_id: str
    fact_type: str  # identity, preference, relationship, temporal
    category: str  # personal_info, preferences, relationships
    confidence: float
    is_immutable: bool = False
    valid_from: datetime
    valid_until: Optional[datetime] = None
    content: str
    entities_json: Optional[str] = None  # JSON array of extracted entities
    extraction_method: str
    source_conversation_id: str
    source_message_id: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now())
    updated_at: datetime = Field(default_factory=lambda: datetime.now())
    user_note: Optional[str] = None
    tags_json: Optional[str] = None  # JSON array
    is_favorite: bool = False
    revisit_count: int = 0
    last_revisited: Optional[datetime] = None
    emotional_tone: Optional[str] = None
    memory_type: Optional[str] = None
    content_type: str = "message"
    conversation_title: Optional[str] = None
    conversation_summary: Optional[str] = None
    turn_range: Optional[str] = None
    key_moments_json: Optional[str] = None  # JSON
    temporal_metadata: Optional[str] = None
    language: Optional[str] = None


# Aliases for backward compatibility
Trajectory = AMSTrajectory
BehavioralFeedback = AMSBehavioralFeedback
