"""
Auth Access Policy Data Models

Dataclasses for authentication access policy entities.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class AuthAccessPolicy:
    """Auth access policy model - matches auth_access_policies table."""
    policy_id: str
    resource_type: str
    action: str
    effect: str
    conditions_json: Optional[str] = None
    priority: int = 100
    enabled: bool = True
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
