"""
Admin Management API Schemas

Pydantic models for admin-related API requests and responses.
"""

from typing import Optional, Dict, List, Any
from pydantic import BaseModel, Field


class GatewayStatusResponse(BaseModel):
    """Response schema for gateway status"""
    status: str = Field(..., description="Gateway status")
    version: str = Field(..., description="Gateway version")
    uptime: float = Field(..., description="Uptime in seconds")
    components: Dict[str, Any] = Field(..., description="Component status details")


class GatewayStatsResponse(BaseModel):
    """Response schema for gateway statistics"""
    routing: Dict[str, Any] = Field(..., description="Routing statistics")
    adapters: Dict[str, Any] = Field(..., description="Adapter statistics")
    requests: Dict[str, Any] = Field(..., description="Request statistics")
    performance: Dict[str, Any] = Field(..., description="Performance metrics")


class SessionInfo(BaseModel):
    """Session information schema"""
    session_id: str = Field(..., description="Session ID")
    user_id: str = Field(..., description="User ID")
    username: str = Field(..., description="Username")
    roles: List[str] = Field(..., description="User roles")
    created_at: str = Field(..., description="Session creation time")
    last_activity: str = Field(..., description="Last activity time")
    ip_address: Optional[str] = Field(None, description="Client IP address")
    user_agent: Optional[str] = Field(None, description="Client user agent")


class SessionListResponse(BaseModel):
    """Response schema for session list"""
    sessions: List[SessionInfo] = Field(..., description="List of sessions")
    total: int = Field(..., description="Total number of sessions")
    stats: Optional[Dict[str, Any]] = Field(None, description="Session statistics")


class RevokeTokenRequest(BaseModel):
    """Request schema for token revocation"""
    token: str = Field(..., description="JWT token to revoke")


class BlockIpRequest(BaseModel):
    """Request schema for IP blocking"""
    ip: str = Field(..., pattern=r'^(?:[0-9]{1,3}\.){3}[0-9]{1,3}$', description="IP address to block")
    reason: Optional[str] = Field(None, description="Reason for blocking")


class SecurityStatsResponse(BaseModel):
    """Response schema for security statistics"""
    blocked_ips: List[str] = Field(..., description="List of blocked IP addresses")
    failed_attempts: int = Field(..., description="Number of failed authentication attempts")
    active_sessions: int = Field(..., description="Number of active sessions")
    rate_limit_hits: int = Field(..., description="Number of rate limit violations")


class ConfigResponse(BaseModel):
    """Response schema for gateway configuration"""
    protocols: Dict[str, Any] = Field(..., description="Protocol configuration")
    security: Dict[str, Any] = Field(..., description="Security configuration")
    performance: Dict[str, Any] = Field(..., description="Performance configuration")


class RouteMappingRequest(BaseModel):
    """Request schema for adding route mapping"""
    external_topic: str = Field(..., description="External topic name")
    internal_topic: str = Field(..., description="Internal topic name")


class RouteMappingResponse(BaseModel):
    """Response schema for route mapping operations"""
    message: str = Field(..., description="Operation result message")
    external_topic: str = Field(..., description="External topic")
    internal_topic: Optional[str] = Field(None, description="Internal topic")


class AdminHealthResponse(BaseModel):
    """Response schema for admin health check"""
    status: str = Field(..., description="Service status")
    service: str = Field(..., description="Service name")
    timestamp: str = Field(..., description="Health check timestamp")


class AdminOperationResponse(BaseModel):
    """Generic response schema for admin operations"""
    success: bool = Field(..., description="Whether operation succeeded")
    message: str = Field(..., description="Operation result message")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional operation details")
