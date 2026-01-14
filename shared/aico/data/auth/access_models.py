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
    uuid: str
    user_uuid: str
    resource_type: str
    permission: str
    resource_uuid: Optional[str] = None
    is_active: bool = True
    created_at: Optional[datetime] = None
