"""
Behavioral Learning API Schemas

Pydantic models for feedback API requests and responses.
"""

from pydantic import BaseModel, Field
from typing import Optional


class FeedbackRequest(BaseModel):
    """Request schema for user feedback on AI response."""
    message_id: str = Field(..., description="ID of the AI message being rated")
    skill_id: Optional[str] = Field(None, description="ID of skill that was applied (if known)")
    reward: int = Field(..., ge=-1, le=1, description="Feedback reward: 1 (positive), 0 (neutral), -1 (negative)")
    reason: Optional[str] = Field(None, description="Optional dropdown reason: too_verbose, too_brief, wrong_tone, not_helpful, incorrect_info")
    free_text: Optional[str] = Field(None, max_length=300, description="Optional free text feedback (max 300 chars)")


class FeedbackResponse(BaseModel):
    """Response schema for feedback submission."""
    status: str = "success"
    skill_updated: bool = Field(..., description="Whether skill confidence was updated")
    new_confidence: Optional[float] = Field(None, description="New confidence score if skill was updated")
    event_id: str = Field(..., description="ID of created feedback event")
