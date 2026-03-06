"""
User Management API Schemas

Pydantic models for user-related API requests and responses.
"""

from typing import Optional, List
from pydantic import BaseModel, Field, validator
import uuid
from aico.core.config import ConfigurationManager


class CreateUserRequest(BaseModel):
    """Request schema for creating a new user"""
    full_name: str = Field(..., description="User's full name")
    nickname: Optional[str] = Field(None, description="Optional nickname")
    user_type: str = Field(
        default_factory=lambda: ConfigurationManager().get('core.user_profiles.default_user_type', 'person'),
        pattern=f'^{ConfigurationManager().get("core.user_profiles.default_user_type", "person")}$',
        description="User type"
    )
    password: Optional[str] = Field(None, description="Optional password for authentication")
    pin: Optional[str] = Field(None, description="Deprecated alias for password")
    primary_language: Optional[str] = Field("en", description="Primary language preference (ISO/BCP-47 code, e.g. 'en', 'de', 'fr')")
    
    @validator('full_name')
    def validate_full_name(cls, v):
        from .dependencies import validate_full_name
        return validate_full_name(v)
    
    @validator('nickname')
    def validate_nickname(cls, v):
        from .dependencies import validate_nickname
        return validate_nickname(v)
    
    @validator('password')
    def validate_password(cls, v):
        if v is not None:
            from .dependencies import validate_password
            return validate_password(v)
        return v

    @validator('pin')
    def validate_pin(cls, v):
        if v is not None:
            from .dependencies import validate_password
            return validate_password(v)
        return v


class UpdateUserRequest(BaseModel):
    """Request schema for updating user profile"""
    full_name: Optional[str] = Field(None, description="User's full name")
    nickname: Optional[str] = Field(None, description="Optional nickname")
    user_type: Optional[str] = Field(
        None,
        pattern=f'^{ConfigurationManager().get("core.user_profiles.default_user_type", "person")}$',
        description="User type"
    )
    primary_language: Optional[str] = Field(None, description="Primary language preference (ISO/BCP-47 code)")
    
    @validator('full_name')
    def validate_full_name(cls, v):
        if v is not None:
            from .dependencies import validate_full_name
            return validate_full_name(v)
        return v
    
    @validator('nickname')
    def validate_nickname(cls, v):
        from .dependencies import validate_nickname
        return validate_nickname(v)


class AuthenticateRequest(BaseModel):
    """Request schema for user authentication"""
    user_uuid: str = Field(..., pattern='^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$', description="User UUID")
    password: Optional[str] = Field(None, description="User password")
    pin: Optional[str] = Field(None, description="Deprecated alias for password")
    
    @validator('password')
    def validate_password(cls, v):
        if v is None:
            return v
        from .dependencies import validate_password
        return validate_password(v)

    @validator('pin')
    def validate_pin(cls, v):
        if v is None:
            return v
        from .dependencies import validate_password
        return validate_password(v)

    @validator('pin', always=True)
    def require_password_or_pin(cls, v, values):
        if (values.get('password') or '').strip():
            return v
        if (v or '').strip():
            return v
        raise ValueError('password is required')


class SetPasswordRequest(BaseModel):
    """Request schema for setting/updating user password"""
    new_password: str = Field(..., description="New password")
    new_pin: Optional[str] = Field(None, description="Deprecated alias for new_password")
    
    @validator('new_password')
    def validate_new_password(cls, v):
        from .dependencies import validate_password
        return validate_password(v)

    @validator('new_pin')
    def validate_new_pin(cls, v):
        if v is None:
            return v
        from .dependencies import validate_password
        return validate_password(v)


class UserResponse(BaseModel):
    """Response schema for user data"""
    uuid: str = Field(..., description="User UUID")
    full_name: str = Field(..., description="User's full name")
    nickname: Optional[str] = Field(None, description="User's nickname")
    user_type: str = Field(..., description="User type")
    is_active: bool = Field(..., description="Whether user is active")
    primary_language: Optional[str] = Field(None, description="Primary language preference (ISO/BCP-47 code)")
    created_at: Optional[str] = Field(None, description="Creation timestamp")
    updated_at: Optional[str] = Field(None, description="Last update timestamp")


class AuthenticationResponse(BaseModel):
    """Response schema for authentication attempts"""
    success: bool = Field(..., description="Whether authentication succeeded")
    user: Optional[UserResponse] = Field(None, description="User data if authentication successful")
    jwt_token: Optional[str] = Field(None, description="JWT access token if authentication successful")
    refresh_token: Optional[str] = Field(None, description="JWT refresh token if authentication successful")
    error: Optional[str] = Field(None, description="Error message if authentication failed")
    last_login: Optional[str] = Field(None, description="Last login timestamp")


class UserStatsResponse(BaseModel):
    """Response schema for user statistics"""
    total_users: int = Field(..., description="Total number of users")
    active_users: int = Field(..., description="Number of active users")
    users_by_type: dict = Field(..., description="User count by type")
    recent_logins: int = Field(..., description="Recent login count")


class UserListResponse(BaseModel):
    """Response schema for user list"""
    users: List[UserResponse] = Field(..., description="List of users")
    total: int = Field(..., description="Total number of users")
    limit: int = Field(..., description="Query limit used")
    user_type_filter: Optional[str] = Field(None, description="User type filter applied")
