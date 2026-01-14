"""
Conversation Data Models

Dataclasses for conversation entities.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class ConversationInitiation:
    """Conversation initiation model - matches conversation_initiations table."""
    initiation_id: str
    user_id: str
    conversation_id: str
    trigger_source: str
    initiated_at: datetime
    trigger_reason: Optional[str] = None
    question: Optional[str] = None
    context: Optional[str] = None
    urgency: str = 'medium'
    expected_answer_type: str = 'text'
    resolved_at: Optional[datetime] = None
    resolution_status: str = 'pending'
    user_response_time: Optional[int] = None
    engagement_score: Optional[float] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
