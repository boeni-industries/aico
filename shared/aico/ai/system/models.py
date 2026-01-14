"""
System Domain Models

Rich domain models for system entities.
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field
from enum import Enum


class EventSeverity(str, Enum):
    """Event severity enumeration."""
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class SystemEvent(BaseModel):
    """System event domain model."""
    event_id: str
    event_type: str
    event_category: str
    source_component: str
    severity: EventSeverity = EventSeverity.INFO
    event_data: dict = Field(default_factory=dict)
    user_id: Optional[str] = None
    entity_type: Optional[str] = None
    entity_id: Optional[str] = None
    workflow_trace_id: Optional[str] = None
    parent_event_id: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now())


class SystemEventMetrics(BaseModel):
    """System event metrics domain model."""
    metric_id: str
    event_type: str
    metric_name: str
    metric_value: float
    aggregation_period: str
    metadata: dict = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now())


class SystemEventReplaySession(BaseModel):
    """System event replay session domain model."""
    session_id: str
    start_event_id: str
    end_event_id: str
    status: str
    created_at: datetime = Field(default_factory=lambda: datetime.now())
    completed_at: Optional[datetime] = None
