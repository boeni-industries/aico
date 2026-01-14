"""
Auth Credentials Data Models

Dataclasses for user credentials entities.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class AuthUserCredentials:
    """Auth user credentials model - matches auth_user_credentials table."""
    uuid: str
    user_uuid: str
    pin_hash: str
    failed_attempts: int = 0
    locked_until: Optional[datetime] = None
    last_login: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
