"""
Arbiter Data Models

Dataclasses for arbiter A/B testing.
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class ArbiterABTest:
    """Arbiter A/B test model - matches arbiter_ab_tests table."""
    test_id: str
    test_name: str
    arm_a_id: str
    arm_b_id: str
    start_date: str
    end_date: str
    created_at: str
    status: str = 'active'
    winner_arm_id: Optional[str] = None
    confidence_score: Optional[float] = None
    notes: Optional[str] = None
    updated_at: Optional[str] = None
