"""
Conversation Domain Models

Rich domain models for conversation entities.
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field
from enum import Enum


class InitiationStatus(str, Enum):
    """Conversation initiation status."""
    PENDING = "pending"
    SENT = "sent"
    DELIVERED = "delivered"
    FAILED = "failed"


class ConversationInitiation(BaseModel):
    """Conversation initiation domain model."""
    initiation_id: str
    user_id: str
    trigger_type: str
    trigger_reason: str
    status: InitiationStatus = InitiationStatus.PENDING
    scheduled_at: Optional[datetime] = None
    sent_at: Optional[datetime] = None
    conversation_id: Optional[str] = None
    metadata: dict = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now())
    updated_at: datetime = Field(default_factory=lambda: datetime.now())
