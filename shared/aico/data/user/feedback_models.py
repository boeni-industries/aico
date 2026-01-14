"""
User Feedback Request Data Models

Dataclasses for user feedback requests.
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class UserFeedbackRequest:
    """User feedback request model - matches user_feedback_requests table."""
    request_id: str
    user_id: str
    feedback_type: str
    question: str
    created_at: str
    goal_id: Optional[str] = None
    skill_id: Optional[str] = None
    execution_id: Optional[str] = None
    response: Optional[str] = None
    rating: Optional[float] = None
    responded_at: Optional[str] = None
