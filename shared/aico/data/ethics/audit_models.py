from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class EthicsGateAudit(BaseModel):
    audit_id: str
    user_id: str
    target_type: str
    target_id: str
    decision: str

    reasoning: Optional[str] = None
    policy_rules_applied: Optional[str] = None

    check_level: int = 1
    cached: int = 0
    processing_time_ms: Optional[int] = None

    created_at: datetime
