"""
Auth Domain Models

Rich domain models for authentication entities.
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class Session(BaseModel):
    """User session domain model."""
    session_id: str
    user_id: str
    device_id: Optional[str] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    is_active: bool = True
    expires_at: Optional[datetime] = None
    last_activity: Optional[datetime] = None
    jwt_token_hash: Optional[str] = None
    session_type: str = "web"
    metadata: dict = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now())


class UserCredentials(BaseModel):
    """User credentials domain model."""
    user_id: str
    password_hash: str
    salt: str
    algorithm: str = "bcrypt"
    last_password_change: Optional[datetime] = None
    failed_attempts: int = 0
    locked_until: Optional[datetime] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now())
    updated_at: datetime = Field(default_factory=lambda: datetime.now())


class Device(BaseModel):
    """User device domain model."""
    device_id: str
    user_id: str
    device_name: str
    device_type: str
    platform: Optional[str] = None
    is_trusted: bool = False
    last_used: Optional[datetime] = None
    metadata: dict = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now())


class AuthAccessPolicy(BaseModel):
    """Auth access policy domain model."""
    uuid: str
    user_uuid: str
    resource_type: str
    permission: str
    resource_uuid: Optional[str] = None
    is_active: bool = True
    created_at: Optional[datetime] = None
