from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class SystemEventMetric(BaseModel):
    metric_id: str
    metric_name: str
    metric_type: str

    event_type: Optional[str] = None
    event_category: Optional[str] = None

    time_bucket: str
    bucket_start: str

    value: float
    count: int = 1
    metadata: Optional[str] = None
    created_at: datetime


class SystemEventReplaySession(BaseModel):
    session_id: str
    user_id: str

    replay_name: Optional[str] = None

    start_time: str
    end_time: str

    event_filters: Optional[str] = None
    replay_speed: float = 1.0

    status: str
    started_at: datetime

    events_replayed: int = 0
    completed_at: Optional[datetime] = None

    created_at: datetime
