from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class ArbiterBanditArm(BaseModel):
    arm_id: str
    weights_json: Dict[str, Any] = Field(default_factory=dict)

    pulls: int = 0
    total_reward: float = 0.0
    success_count: int = 0
    failure_count: int = 0

    last_pulled: Optional[datetime] = None
    active: bool = True

    created_at: datetime
    updated_at: datetime
