from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class AgencyReflectionRun(BaseModel):
    run_id: str
    user_id: str
    run_type: str
    trigger_reason: Optional[str] = None
    analysis_window_start: datetime
    analysis_window_end: datetime
    lessons_generated: int = 0
    lessons_applied: int = 0
    started_at: datetime
    completed_at: Optional[datetime] = None
    duration_seconds: Optional[float] = None
    status: str
    error_message: Optional[str] = None
    created_at: Optional[datetime] = None


class AgencySelfModel(BaseModel):
    model_id: str
    user_id: str
    entity_type: str
    entity_id: str
    performance_summary: str
    window_start: datetime
    window_end: datetime
    sample_size: int
    confidence: float
    last_updated: Optional[datetime] = None
    created_at: Optional[datetime] = None
