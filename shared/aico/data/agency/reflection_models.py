"""
Agency Reflection Data Models

Dataclasses for reflection and self-model entities.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class AgencyReflectionRun:
    """Agency reflection run model - matches agency_reflection_runs table."""
    run_id: str
    user_id: str
    run_type: str
    analysis_window_start: datetime
    analysis_window_end: datetime
    started_at: datetime
    status: str
    created_at: datetime
    trigger_reason: Optional[str] = None
    lessons_generated: int = 0
    lessons_applied: int = 0
    completed_at: Optional[datetime] = None
    duration_seconds: Optional[float] = None
    error_message: Optional[str] = None


@dataclass
class AgencySelfModel:
    """Agency self model - matches agency_self_model table."""
    model_id: str
    user_id: str
    entity_type: str
    entity_id: str
    performance_summary: str
    window_start: datetime
    window_end: datetime
    sample_size: int
    confidence: float
    created_at: datetime
    last_updated: Optional[datetime] = None
