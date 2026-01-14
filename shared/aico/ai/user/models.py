"""
User Domain Models

Rich domain models for user entities with validation and business logic.
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, EmailStr
from enum import Enum


class UserType(str, Enum):
    """User type enumeration."""
    HUMAN = "human"
    PARENT = "parent"
    CHILD = "child"
    ADMIN = "admin"
    SYSTEM = "system"


class UserProfile(BaseModel):
    """User profile domain model."""
    uuid: str
    full_name: str
    nickname: Optional[str] = None
    user_type: UserType
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    primary_language: str = "en"
    timezone: str = "UTC"
    is_active: bool = True
    preferences: dict = Field(default_factory=dict)
    metadata: dict = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now())
    updated_at: datetime = Field(default_factory=lambda: datetime.now())


class UserProactivePreferences(BaseModel):
    """User proactive preferences domain model."""
    user_id: str
    preference_type: str
    preference_value: str
    context: Optional[str] = None
    priority: int = 50
    active: bool = True
    created_at: datetime = Field(default_factory=lambda: datetime.now())
    updated_at: datetime = Field(default_factory=lambda: datetime.now())


class UserFeedbackRequest(BaseModel):
    """User feedback request domain model."""
    request_id: str
    user_id: str
    request_type: str
    content: str
    status: str = "pending"
    priority: int = 50
    scheduled_at: Optional[datetime] = None
    delivered_at: Optional[datetime] = None
    response: Optional[str] = None
    response_sentiment: Optional[float] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now())
    updated_at: datetime = Field(default_factory=lambda: datetime.now())


class UserTimePreferences(BaseModel):
    """User time preferences domain model."""
    user_id: str
    preference_key: str
    time_value: str
    context: Optional[str] = None
    active: bool = True
    created_at: datetime = Field(default_factory=lambda: datetime.now())
    updated_at: datetime = Field(default_factory=lambda: datetime.now())


class UserRelationship(BaseModel):
    """User relationship domain model."""
    relationship_id: str
    user_id: str
    related_user_id: str
    relationship_type: str
    strength: float = 0.5
    metadata: dict = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now())
    updated_at: datetime = Field(default_factory=lambda: datetime.now())


class UserSkillConfidence(BaseModel):
    """User skill confidence domain model."""
    user_id: str
    skill_id: str
    confidence_level: float
    usage_count: int = 0
    last_used: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now())
    updated_at: datetime = Field(default_factory=lambda: datetime.now())
