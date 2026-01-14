"""
Arbiter Bandit Arms Data Models

Dataclasses for arbiter bandit arms.
"""

from dataclasses import dataclass
from typing import Optional, Dict, Any


@dataclass
class ArbiterBanditArm:
    """Arbiter bandit arm model - matches arbiter_bandit_arms table."""
    arm_id: str
    weights_json: Dict[str, Any]
    created_at: str
    updated_at: str
    pulls: int = 0
    total_reward: float = 0.0
    success_count: int = 0
    failure_count: int = 0
    last_pulled: Optional[str] = None
    active: bool = True
