"""
System Event Metrics Data Models

Dataclasses for system event metrics and replay sessions.
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class SystemEventMetric:
    """System event metric model - matches system_event_metrics table."""
    metric_id: str
    metric_name: str
    metric_type: str
    time_bucket: str
    bucket_start: str
    value: float
    created_at: str
    event_type: Optional[str] = None
    event_category: Optional[str] = None
    count: int = 1
    metadata: Optional[str] = None


@dataclass
class SystemEventReplaySession:
    """System event replay session model - matches system_event_replay_sessions table."""
    session_id: str
    user_id: str
    start_time: str
    end_time: str
    status: str
    started_at: str
    created_at: str
    replay_name: Optional[str] = None
    event_filters: Optional[str] = None
    replay_speed: float = 1.0
    events_replayed: int = 0
    completed_at: Optional[str] = None
