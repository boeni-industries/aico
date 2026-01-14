from __future__ import annotations

from typing import Optional

from pydantic import BaseModel


class UserFeedbackRequest(BaseModel):
    request_id: str
    user_id: str

    goal_id: Optional[str] = None
    skill_id: Optional[str] = None
    execution_id: Optional[str] = None

    feedback_type: str
    question: str

    response: Optional[str] = None
    rating: Optional[float] = None
    responded_at: Optional[str] = None

    created_at: str
