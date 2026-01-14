"""
Agency Arbiter Data Models

Dataclasses for agency arbiter adjustments.
"""

from dataclasses import dataclass
from typing import Optional
from datetime import datetime


@dataclass
class AgencyArbiterAdjustment:
    """Agency arbiter adjustment model - matches agency_arbiter_adjustments table."""
    adjustment_key: str
    adjustment_value: float
    lesson_id: str
    applied_at: datetime
    confidence: float
    user_id: Optional[str] = None
    active: bool = True
    notes: Optional[str] = None
