"""
Admin Management API Schemas

Pydantic models for admin-related API requests and responses.
"""

from typing import Optional, Dict, List, Any, Literal
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
    user_uuid: str = Field(..., description="User UUID")
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
    error_rate_trend: float = Field(0.0, description="Error rate trend vs 1 hour ago (percentage points)")
    log_volume_trend: float = Field(0.0, description="Log volume trend vs 1 hour ago (percentage change)")


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


# ============================================================================
# USERS & SECURITY (ADMIN) SCHEMAS
# ============================================================================


class Pagination(BaseModel):
    limit: int = Field(..., description="Page size")
    offset: int = Field(..., description="Offset")
    total_count: int = Field(..., description="Total matching entries")


class AdminUserResponse(BaseModel):
    uuid: str = Field(..., description="User UUID")
    full_name: str = Field(..., description="User full name")
    nickname: Optional[str] = Field(None, description="User nickname")
    user_type: str = Field(..., description="User type")
    is_active: bool = Field(..., description="Whether user is active")
    primary_language: Optional[str] = Field(None, description="Primary language preference")
    created_at: Optional[str] = Field(None, description="Creation timestamp (ISO 8601)")
    updated_at: Optional[str] = Field(None, description="Update timestamp (ISO 8601)")


class AdminUserCreateRequest(BaseModel):
    full_name: str = Field(..., description="Full name")
    nickname: Optional[str] = Field(None, description="Nickname")
    user_type: str = Field(..., description="User type")
    password: Optional[str] = Field(None, description="Initial password")
    pin: Optional[str] = Field(None, description="Deprecated alias for password")
    primary_language: Optional[str] = Field(None, description="Primary language")


class AdminUserUpdateRequest(BaseModel):
    full_name: Optional[str] = Field(None, description="Full name")
    nickname: Optional[str] = Field(None, description="Nickname")
    user_type: Optional[str] = Field(None, description="User type")
    primary_language: Optional[str] = Field(None, description="Primary language")
    is_active: Optional[bool] = Field(None, description="Active flag")


class AdminUserDeleteRequest(BaseModel):
    hard_delete: bool = Field(False, description="Hard delete (default: soft delete)")
    confirm: bool = Field(False, description="Required confirmation flag")
    reason: Optional[str] = Field(None, description="Reason")


class AdminBulkDeleteRequest(BaseModel):
    """Request schema for bulk user deletion"""
    user_uuids: List[str] = Field(..., min_length=1, max_length=100, description="List of user UUIDs to delete (max 100)")
    hard_delete: bool = Field(False, description="Hard delete (default: soft delete)")
    confirm: bool = Field(False, description="Required confirmation flag")
    reason: Optional[str] = Field(None, description="Reason for deletion")


class BulkDeleteResult(BaseModel):
    """Result for individual user deletion in bulk operation"""
    user_uuid: str = Field(..., description="User UUID")
    success: bool = Field(..., description="Whether deletion succeeded")
    error: Optional[str] = Field(None, description="Error message if failed")


class AdminBulkDeleteResponse(BaseModel):
    """Response schema for bulk user deletion"""
    success: bool = Field(..., description="Whether overall operation succeeded")
    total_requested: int = Field(..., description="Total number of users requested for deletion")
    successful: int = Field(..., description="Number of successfully deleted users")
    failed: int = Field(..., description="Number of failed deletions")
    results: List[BulkDeleteResult] = Field(..., description="Detailed results for each user")


class AdminUserSetPinRequest(BaseModel):
    new_password: Optional[str] = Field(None, description="New password")
    new_pin: Optional[str] = Field(None, description="Deprecated alias for new_password")
    require_change_on_login: Optional[bool] = Field(None, description="If true, forces change on next login")
    confirm: bool = Field(False, description="Required confirmation flag")


class AdminUserRestoreRequest(BaseModel):
    reason: Optional[str] = Field(None, description="Reason")
    confirm: bool = Field(False, description="Required confirmation flag")


class AuditEntry(BaseModel):
    entry_id: str = Field(..., description="Audit entry ID")
    timestamp: str = Field(..., description="Timestamp (ISO 8601)")
    actor_uuid: Optional[str] = Field(None, description="Actor UUID")
    actor_name: Optional[str] = Field(None, description="Actor display name")
    action: str = Field(..., description="Action")
    resource_type: Optional[str] = Field(None, description="Resource type")
    resource_id: Optional[str] = Field(None, description="Resource ID")
    severity: str = Field("info", description="Severity")
    result: str = Field(..., description="Result")
    details: Optional[Dict[str, Any]] = Field(None, description="Details")
    ip_address: Optional[str] = Field(None, description="Client IP")


class AuditListResponse(BaseModel):
    entries: List[AuditEntry] = Field(..., description="Audit entries")
    pagination: Pagination = Field(..., description="Pagination metadata")


class AuditDetailResponse(BaseModel):
    entry: AuditEntry = Field(..., description="Audit entry")
    related_events: List[Dict[str, Any]] = Field(default_factory=list, description="Related events")


class SecurityPostureResponse(BaseModel):
    encryption: Dict[str, Any] = Field(..., description="Encryption posture")
    transport: Dict[str, Any] = Field(..., description="Transport posture")
    authentication: Dict[str, Any] = Field(..., description="Authentication posture")
    audit: Dict[str, Any] = Field(..., description="Audit posture")


class SecurityKeyInfoResponse(BaseModel):
    current_key_id: Optional[str] = Field(None, description="Current key identifier")
    created_at: Optional[str] = Field(None, description="Creation timestamp (ISO 8601)")
    age_days: Optional[int] = Field(None, description="Age in days")
    rotation_due: bool = Field(False, description="Rotation recommended")
    algorithm: str = Field(..., description="KDF / algorithm")
    key_strength: Optional[Dict[str, Any]] = Field(None, description="Key strength information")


class SecurityKeyHistoryEntry(BaseModel):
    key_id: str = Field(..., description="Key identifier")
    created_at: str = Field(..., description="Created timestamp")
    rotated_at: Optional[str] = Field(None, description="Rotated timestamp")
    reason: Optional[str] = Field(None, description="Reason")
    performed_by: Optional[str] = Field(None, description="Actor UUID")


class SecurityKeyHistoryResponse(BaseModel):
    history: List[SecurityKeyHistoryEntry] = Field(..., description="Key history")


class RotateKeysRequest(BaseModel):
    reason: str = Field(..., description="Rotation reason")
    confirm: bool = Field(False, description="Required confirmation flag")


class RotateKeysResponse(BaseModel):
    success: bool = Field(..., description="Success")
    new_key_id: Optional[str] = Field(None, description="New key identifier")
    old_key_id: Optional[str] = Field(None, description="Old key identifier")
    rotation_timestamp: str = Field(..., description="Rotation timestamp")


class AuthStatsResponse(BaseModel):
    total_attempts: int = Field(..., description="Total attempts")
    successful: int = Field(..., description="Successful attempts")
    failed: int = Field(..., description="Failed attempts")
    success_rate_percent: float = Field(..., description="Success rate")
    attempts_by_hour: Dict[str, int] = Field(..., description="Attempts by hour")
    top_failing_users: List[Dict[str, Any]] = Field(..., description="Top failing users")


class FailedAuthAttempt(BaseModel):
    timestamp: str = Field(..., description="Timestamp")
    user_uuid: Optional[str] = Field(None, description="User UUID")
    user_name: Optional[str] = Field(None, description="User display name")
    ip_address: Optional[str] = Field(None, description="IP address")
    device_type: Optional[str] = Field(None, description="Device type")
    reason: Optional[str] = Field(None, description="Failure reason")


class FailedAuthAttemptsResponse(BaseModel):
    attempts: List[FailedAuthAttempt] = Field(..., description="Failed auth attempts")
    pagination: Pagination = Field(..., description="Pagination metadata")


class AuditExportRequest(BaseModel):
    format: Literal["csv", "json"] = Field(..., description="Export format")
    filters: Dict[str, Any] = Field(default_factory=dict, description="Filters")
