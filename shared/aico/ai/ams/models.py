"""
AMS (Adaptive Memory System) Domain Models

Rich domain models for behavioral and adaptive memory entities.
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class AMSTrajectory(BaseModel):
    """AMS trajectory domain model."""
    trajectory_id: str
    user_id: str
    trajectory_type: str
    content: str
    context: Optional[dict] = Field(default_factory=dict)
    metadata: dict = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now())


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
    """AMS user memory domain model."""
    memory_id: str
    user_id: str
    memory_type: str
    content: str
    importance: float = 0.5
    metadata: dict = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now())
    updated_at: datetime = Field(default_factory=lambda: datetime.now())


# Aliases for backward compatibility
Trajectory = AMSTrajectory
BehavioralFeedback = AMSBehavioralFeedback
