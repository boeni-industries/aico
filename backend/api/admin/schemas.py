"""
Admin Management API Schemas

Pydantic models for admin-related API requests and responses.
"""

from typing import Optional, Dict, List, Any
from pydantic import BaseModel, Field
from datetime import datetime


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


# ============================================================================
# LOGS ADMIN SCHEMAS
# ============================================================================

class LogsListRequest(BaseModel):
    """Request schema for listing logs"""
    limit: Optional[int] = Field(50, description="Number of entries to return")
    offset: Optional[int] = Field(0, description="Pagination offset")
    level: Optional[str] = Field(None, description="Filter by log level")
    subsystem: Optional[str] = Field(None, description="Filter by subsystem")
    module: Optional[str] = Field(None, description="Filter by module")
    since: Optional[datetime] = Field(None, description="Show logs after timestamp")
    until: Optional[datetime] = Field(None, description="Show logs before timestamp")
    search: Optional[str] = Field(None, description="Text search in log messages")
    utc: Optional[bool] = Field(False, description="Return timestamps in UTC")


class LogsDeleteRequest(BaseModel):
    """Request schema for deleting logs"""
    older_than: Optional[str] = Field(None, description="Remove logs older than duration (e.g., '7d', '30d')")
    level: Optional[str] = Field(None, description="Remove logs of specific level")
    subsystem: Optional[str] = Field(None, description="Remove logs from specific subsystem")
    confirm: bool = Field(False, description="Required confirmation flag")


class LogEntryResponse(BaseModel):
    """Response schema for individual log entry"""
    id: str = Field(..., description="Unique log identifier")
    timestamp: datetime = Field(..., description="Log timestamp")
    level: str = Field(..., description="Log level")
    subsystem: str = Field(..., description="Subsystem name")
    module: str = Field(..., description="Module name")
    function: str = Field(..., description="Function name")
    message: str = Field(..., description="Log message")
    topic: Optional[str] = Field(None, description="ZMQ topic")
    extra_data: Optional[Dict[str, Any]] = Field(None, description="Additional log data")


class LogsListResponse(BaseModel):
    """Response schema for logs list"""
    logs: List[LogEntryResponse] = Field(..., description="List of log entries")
    total: int = Field(..., description="Total number of logs matching criteria")
    has_more: bool = Field(..., description="Whether more logs are available")
    timezone: Optional[str] = Field(None, description="Timezone for timestamps")


class LogsStatsResponse(BaseModel):
    """Response schema for log statistics"""
    total_logs: int = Field(..., description="Total number of logs")
    by_level: Dict[str, int] = Field(..., description="Log counts by level")
    by_subsystem: Dict[str, int] = Field(..., description="Log counts by subsystem")
    recent_activity: Dict[str, int] = Field(..., description="Recent activity (last 24h by hour)")


# ============================================================================
# CONFIG ADMIN SCHEMAS
# ============================================================================

class ConfigSetRequest(BaseModel):
    """Request schema for setting configuration"""
    key: str = Field(..., description="Configuration key in dot notation")
    value: Any = Field(..., description="Configuration value")
    layer: str = Field("user", description="Configuration layer (user, environment, runtime)")


class ConfigValidateRequest(BaseModel):
    """Request schema for configuration validation"""
    domain: str = Field(..., description="Configuration domain")
    config_data: Dict[str, Any] = Field(..., description="Configuration data to validate")


class ConfigImportRequest(BaseModel):
    """Request schema for configuration import"""
    format: str = Field(..., description="Import format (yaml, json)")
    data: str = Field(..., description="Configuration data as string")
    layer: str = Field("user", description="Target configuration layer")
    merge: bool = Field(True, description="Whether to merge with existing config")


class ConfigValueResponse(BaseModel):
    """Response schema for individual configuration value"""
    key: str = Field(..., description="Configuration key")
    value: Any = Field(..., description="Configuration value")
    source_layer: str = Field(..., description="Layer that provided this value")
    domain: str = Field(..., description="Configuration domain")
    is_default: bool = Field(..., description="Whether this is a default value")


class ConfigListResponse(BaseModel):
    """Response schema for configuration list"""
    configs: List[ConfigValueResponse] = Field(..., description="List of configuration values")
    total: int = Field(..., description="Total number of configuration values")
    domains: List[str] = Field(..., description="Available configuration domains")


class ConfigDomainResponse(BaseModel):
    """Response schema for configuration domain info"""
    domain: str = Field(..., description="Domain name")
    description: str = Field(..., description="Domain description")
    schema_version: str = Field(..., description="Schema version")
    available_keys: List[str] = Field(..., description="Available configuration keys")


class ConfigSchemaResponse(BaseModel):
    """Response schema for configuration schema"""
    domain: str = Field(..., description="Domain name")
    schema_definition: Dict[str, Any] = Field(..., description="JSON Schema definition", alias="schema")
    version: str = Field(..., description="Schema version")


class ConfigValidationResponse(BaseModel):
    """Response schema for configuration validation"""
    valid: bool = Field(..., description="Whether configuration is valid")
    errors: List[str] = Field(..., description="Validation errors")
    warnings: List[str] = Field(..., description="Validation warnings")
