from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class EthicsValueProfile(BaseModel):
    profile_id: str
    user_id: str

    sensitive_life_areas: Optional[str] = None
    allowed_curiosity_domains: Optional[str] = None

    curiosity_intensity: float = 0.5
    autonomy_level: str = "balanced"

    storage_preferences: Optional[str] = None

    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
