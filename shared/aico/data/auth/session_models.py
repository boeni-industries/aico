"""
Auth Session Data Models

Dataclasses for session entities.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class AuthSession:
    """Auth session model - matches auth_sessions table."""
    uuid: str
    user_uuid: str
    device_uuid: str
    jwt_token_hash: str
    expires_at: datetime
    is_active: bool = True
    session_type: str = 'unified'
    created_at: Optional[datetime] = None
