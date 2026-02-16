from __future__ import annotations

from datetime import datetime
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
    responded_at: Optional[datetime] = None

    created_at: datetime
