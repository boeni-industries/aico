from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class AgencyArbiterAdjustment(BaseModel):
    adjustment_key: str
    adjustment_value: float
    lesson_id: str
    user_id: Optional[str] = None
    applied_at: datetime
    confidence: float
    active: bool = True
    notes: Optional[str] = None
