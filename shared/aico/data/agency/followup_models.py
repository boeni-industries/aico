from __future__ import annotations

from typing import Optional

from pydantic import BaseModel


class AgencyFollowup(BaseModel):
    followup_id: str
    user_id: str

    goal_id: Optional[str] = None
    related_message_id: Optional[str] = None

    followup_type: str
    content: str
    scheduled_at: str

    delivered_at: Optional[str] = None
    user_response: Optional[str] = None
    response_sentiment: Optional[float] = None

    status: str = "pending"
    priority: int = 50
    policy_approved: int = 1

    relationship_context: Optional[str] = None
    values_alignment: Optional[float] = None

    created_at: str
    updated_at: str
