"""
Ethics Cache Data Models

Dataclasses for ethics decision cache entities.
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class EthicsDecisionsCache:
    """Ethics decisions cache model - matches ethics_decisions_cache table."""
    cache_id: str
    user_id: str
    target_type: str
    target_id: str
    decision: str
    cached_at: str
    reasoning: Optional[str] = None
    policy_rules_applied: Optional[str] = None
    confidence: float = 1.0
    expires_at: Optional[str] = None
    hit_count: int = 0
    last_hit_at: Optional[str] = None
