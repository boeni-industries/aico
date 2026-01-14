from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class ArbiterBanditArm(BaseModel):
    arm_id: str
    weights_json: dict
    pulls: int = 0
    total_reward: float = 0.0
    success_count: int = 0
    failure_count: int = 0
    last_pulled: Optional[str] = None
    active: bool = True
    created_at: str
    updated_at: str


class ArbiterABTest(BaseModel):
    test_id: str
    test_name: str
    arm_a_id: str
    arm_b_id: str
    start_date: str
    end_date: str

    status: str = "active"
    winner_arm_id: Optional[str] = None
    confidence_score: Optional[float] = None
    notes: Optional[str] = None

    created_at: str
    updated_at: Optional[str] = None
