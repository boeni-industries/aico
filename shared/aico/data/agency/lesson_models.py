from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Optional, List

from pydantic import BaseModel


class Lesson(BaseModel):
    lesson_id: str
    user_id: str

    # Classification
    lesson_type: str
    target_kind: str
    target_id: Optional[str] = None

    # Content
    summary_text: str
    proposed_change: Optional[Dict[str, Any]] = None

    # Evidence
    confidence: float
    metrics_basis: Optional[Dict[str, Any]] = None

    # Scope and status
    scope: str
    status: str
    superseded_by: Optional[str] = None

    # Application tracking
    applied_at: Optional[datetime] = None
    applied_by: Optional[str] = None

    # Provenance
    source_reflection_run_id: Optional[str] = None
    evidence_window_start: Optional[datetime] = None
    evidence_window_end: Optional[datetime] = None

    # Related entities (stored as comma-separated strings in DB; repositories may normalize)
    related_goal_ids: List[str] = []
    related_trajectory_ids: List[str] = []
    related_event_ids: List[str] = []

    # Arbitrary metadata (not a DB column in current schema, kept for forward compatibility)
    metadata: Optional[Dict[str, Any]] = None

    created_at: datetime
    updated_at: datetime
