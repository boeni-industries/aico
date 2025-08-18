"""
User Management API Schemas

Pydantic models for user-related API requests and responses.
"""

from typing import Optional, List
from pydantic import BaseModel, Field
import uuid


class CreateUserRequest(BaseModel):
    """Request schema for creating a new user"""
    full_name: str = Field(..., min_length=1, max_length=100, description="User's full name")
    nickname: Optional[str] = Field(None, max_length=50, description="Optional nickname")
    user_type: str = Field(default='parent', pattern='^(parent|child|admin)$', description="User type")
    pin: Optional[str] = Field(None, min_length=4, max_length=8, description="Optional PIN for authentication")


class UpdateUserRequest(BaseModel):
    """Request schema for updating user profile"""
    full_name: Optional[str] = Field(None, min_length=1, max_length=100, description="User's full name")
    nickname: Optional[str] = Field(None, max_length=50, description="Optional nickname")
    user_type: Optional[str] = Field(None, pattern='^(parent|child|admin)$', description="User type")


class AuthenticateRequest(BaseModel):
    """Request schema for user authentication"""
    user_uuid: str = Field(..., pattern='^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$', description="User UUID")
    pin: str = Field(..., min_length=4, max_length=8, description="User PIN")


class SetPinRequest(BaseModel):
    """Request schema for setting/updating user PIN"""
    new_pin: str = Field(..., min_length=4, max_length=8, description="New PIN")


class UserResponse(BaseModel):
    """Response schema for user data"""
    uuid: str = Field(..., description="User UUID")
    full_name: str = Field(..., description="User's full name")
    nickname: Optional[str] = Field(None, description="User's nickname")
    user_type: str = Field(..., description="User type")
    is_active: bool = Field(..., description="Whether user is active")
    created_at: Optional[str] = Field(None, description="Creation timestamp")
    updated_at: Optional[str] = Field(None, description="Last update timestamp")


class AuthenticationResponse(BaseModel):
    """Response schema for authentication attempts"""
    success: bool = Field(..., description="Whether authentication succeeded")
    user: Optional[UserResponse] = Field(None, description="User data if authentication successful")
    jwt_token: Optional[str] = Field(None, description="JWT token if authentication successful")
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
