from __future__ import annotations

from typing import Optional

from pydantic import BaseModel


class EthicsDecisionsCache(BaseModel):
    cache_id: str
    user_id: str
    target_type: str
    target_id: str
    decision: str

    reasoning: Optional[str] = None
    policy_rules_applied: Optional[str] = None
    confidence: float = 1.0

    cached_at: str
    expires_at: Optional[str] = None

    hit_count: int = 0
    last_hit_at: Optional[str] = None
