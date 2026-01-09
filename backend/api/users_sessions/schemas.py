"""
Users & Sessions API Schemas

Data models for user and session management endpoints.
"""

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class UserProfile(BaseModel):
    """User profile information"""
    uuid: str = Field(..., description="User UUID")
    full_name: str = Field(..., description="User full name")
    nickname: Optional[str] = Field(None, description="User nickname")
    user_type: str = Field(..., description="User type (person, system, admin)")
    is_active: bool = Field(..., description="User active status")
    primary_language: Optional[str] = Field(None, description="User's primary language")
    created_at: str = Field(..., description="Account creation timestamp")
    updated_at: str = Field(..., description="Last update timestamp")


class UserCredentials(BaseModel):
    """User authentication credentials information"""
    has_pin: bool = Field(..., description="Whether user has PIN set")
    failed_attempts: int = Field(..., description="Failed login attempts count")
    is_locked: bool = Field(..., description="Whether account is locked")
    locked_until: Optional[str] = Field(None, description="Lock expiration timestamp")
    last_login: Optional[str] = Field(None, description="Last successful login timestamp")


class DeviceInfo(BaseModel):
    """Device information"""
    uuid: str = Field(..., description="Device UUID")
    device_name: str = Field(..., description="Device name")
    device_type: str = Field(..., description="Device type")
    platform: str = Field(..., description="Platform")
    last_seen: Optional[str] = Field(None, description="Last seen timestamp")
    is_active: bool = Field(..., description="Device active status")


class SessionDetail(BaseModel):
    """Detailed session information"""
    uuid: str = Field(..., description="Session UUID")
    user_uuid: str = Field(..., description="User UUID")
    device_uuid: str = Field(..., description="Device UUID")
    session_type: str = Field(..., description="Session type")
    expires_at: str = Field(..., description="Session expiration timestamp")
    created_at: str = Field(..., description="Session creation timestamp")
    is_active: bool = Field(..., description="Session active status")
    time_remaining: Optional[str] = Field(None, description="Time until expiration (formatted)")


class SessionWithUser(SessionDetail):
    """Session with user information"""
    user_full_name: str = Field(..., description="User full name")
    user_nickname: Optional[str] = Field(None, description="User nickname")
    user_type: str = Field(..., description="User type")
    device_name: Optional[str] = Field(None, description="Device name")
    device_type: Optional[str] = Field(None, description="Device type")


class UserWithSessions(UserProfile):
    """User profile with session information"""
    active_session_count: int = Field(..., description="Number of active sessions")
    total_session_count: int = Field(..., description="Total number of sessions (lifetime)")
    last_activity: Optional[str] = Field(None, description="Last activity timestamp")
    credentials: Optional[UserCredentials] = Field(None, description="User credentials info")


class UsersListResponse(BaseModel):
    """Response model for users list"""
    users: List[UserWithSessions] = Field(..., description="List of users with session info")
    total_users: int = Field(..., description="Total number of users")
    active_users: int = Field(..., description="Number of users with active sessions")


class SessionsListResponse(BaseModel):
    """Response model for sessions list"""
    sessions: List[SessionWithUser] = Field(..., description="List of sessions with user info")
    total_sessions: int = Field(..., description="Total number of sessions")
    active_sessions: int = Field(..., description="Number of active sessions")


class UserDetailResponse(BaseModel):
    """Response model for user detail"""
    user: UserProfile = Field(..., description="User profile")
    credentials: Optional[UserCredentials] = Field(None, description="User credentials info")
    active_sessions: List[SessionDetail] = Field(..., description="Active sessions for this user")
    devices: List[DeviceInfo] = Field(..., description="Registered devices")
    statistics: dict = Field(..., description="User statistics")


class SessionStatistics(BaseModel):
    """Session statistics"""
    total_sessions: int = Field(..., description="Total sessions")
    active_sessions: int = Field(..., description="Active sessions")
    expired_sessions: int = Field(..., description="Expired sessions")
    sessions_by_type: dict = Field(..., description="Sessions grouped by type")
    sessions_by_device_type: dict = Field(..., description="Sessions grouped by device type")
    average_session_duration: Optional[float] = Field(None, description="Average session duration in seconds")


class SessionStatsResponse(BaseModel):
    """Response model for session statistics"""
    statistics: SessionStatistics = Field(..., description="Session statistics")
    recent_activity: List[dict] = Field(..., description="Recent session activity")
