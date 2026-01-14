"""
Auth System Data Models

Dataclasses for authentication-related entities (sessions, credentials, devices).
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class Device:
    """Device model - matches auth_devices table."""
    uuid: str
    device_name: str
    device_type: str
    platform: str
    is_active: bool = True
    last_seen: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


@dataclass
class Session:
    """User session model."""
    uuid: str
    user_uuid: str
    device_uuid: str
    jwt_token_hash: str
    expires_at: datetime
    created_at: datetime
    is_active: bool = True
    session_type: str = 'unified'


@dataclass
class UserCredentials:
    """User credentials model."""
    uuid: str
    user_uuid: str
    pin_hash: str
    failed_attempts: int = 0
    locked_until: Optional[datetime] = None
    last_login: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
