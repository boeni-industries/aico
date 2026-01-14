from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class ProactiveAnalytics(BaseModel):
    id: str
    user_id: str
    event_type: str

    event_data: Optional[str] = None
    confidence_score: Optional[float] = None
    triggered_action: Optional[str] = None

    created_at: datetime


class ProactiveReminderCluster(BaseModel):
    cluster_id: str
    user_id: str
    cluster_name: str

    pattern_description: Optional[str] = None
    reminder_ids: Optional[str] = None
    confidence_score: Optional[float] = None

    created_at: datetime
    updated_at: Optional[datetime] = None
