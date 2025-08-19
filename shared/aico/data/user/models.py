"""
User Management Data Models

Defines data structures for user profiles and authentication data.
Used by both CLI and API Gateway components.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class UserProfile:
    """User profile data structure"""
    uuid: str
    full_name: str
    nickname: Optional[str] = None
    user_type: str = 'parent'
    is_active: bool = True
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


@dataclass
class AuthenticationData:
    """User authentication data"""
    uuid: str
    user_uuid: str
    pin_hash: str
    failed_attempts: int = 0
    locked_until: Optional[datetime] = None
    last_login: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
