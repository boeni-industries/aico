from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class AMSContextPreferenceVector(BaseModel):
    user_id: str
    context_bucket: int
    dimensions: str
    last_updated_at: datetime


class AMSContextSkillStats(BaseModel):
    user_id: str
    context_bucket: int
    skill_id: str
    alpha: float = 1.0
    beta: float = 1.0
    last_updated_at: datetime
