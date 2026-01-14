from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import BaseModel


class Lesson(BaseModel):
    lesson_id: str
    user_id: Optional[str] = None
    lesson_type: str
    target_kind: str
    target_id: str
    
    scope: str
    status: str
    
    observation: str
    proposed_change: Optional[Dict[str, Any]] = None
    rationale: str
    
    confidence: float
    impact_estimate: Optional[float] = None
    
    approved_at: Optional[datetime] = None
    rejected_at: Optional[datetime] = None
    applied_at: Optional[datetime] = None
    
    metadata: Optional[Dict[str, Any]] = None
    
    created_at: datetime
    updated_at: datetime
