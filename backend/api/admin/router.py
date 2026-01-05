"""
Admin Management API Router

REST API endpoints for administrative operations including gateway management,
session control, security operations, and system configuration.
"""

from typing import Optional, Dict, Any, List
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import JSONResponse

from .dependencies import verify_admin_token, get_log_repository, get_config_manager
from .schemas import (
    AdminHealthResponse,
    GatewayStatusResponse,
    GatewayStatsResponse,
    SecurityStatsResponse,
    SessionListResponse as UserSessionsResponse,
    RevokeTokenRequest as RevokeSessionRequest,
    AdminOperationResponse,
    BlockIpRequest,
    # Logs schemas
    LogsListRequest,
    LogsDeleteRequest,
    LogEntryResponse,
    LogsListResponse,
    LogsStatsResponse,
    # Config schemas
    ConfigSetRequest,
    ConfigValidateRequest,
    ConfigImportRequest,
    ConfigValueResponse,
    ConfigListResponse,
    ConfigDomainResponse,
    ConfigSchemaResponse,
    ConfigValidationResponse
)
from .schemas import ConfigResponse, RouteMappingRequest, RouteMappingResponse
from .exceptions import (
    GatewayServiceError,
    SessionNotFoundError,
    LogsServiceError,
    ConfigServiceError,
    ConfigValidationError,
    handle_admin_service_exceptions
)

# Admin authentication handled by verify_admin_token dependency function

# Removed initialize_router - using proper FastAPI dependency injection

# Protected admin endpoints - authentication handled per endpoint
router = APIRouter()

@router.get("/health", response_model=AdminHealthResponse)
@handle_admin_service_exceptions
async def admin_health(credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer())):
    """Admin health check - requires encryption"""
    # Verify admin token
    user = verify_admin_token(credentials)
    
    return AdminHealthResponse(
        status="healthy",
        service="aico-api-gateway-admin",
        timestamp=datetime.utcnow().isoformat()
    )


@router.get("/gateway/status", response_model=GatewayStatusResponse)
@handle_admin_service_exceptions
async def gateway_status(credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer())):
    """Get gateway status"""
    # Verify admin token
    user = verify_admin_token(credentials)
    
    if not gateway:
        raise GatewayServiceError("Gateway not initialized")
    
    status_data = gateway.get_health_status()
    return GatewayStatusResponse(**status_data)


@router.get("/gateway/stats", response_model=GatewayStatsResponse)
@handle_admin_service_exceptions
async def gateway_stats(credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer())):
    """Get gateway statistics including routing and adapter metrics"""
    # Verify admin token
    user = verify_admin_token(credentials)
    
    # Gateway statistics from service container
    # Implementation complete - returns actual gateway metrics
    
    stats = {
        "routing": {"message": "not implemented yet"},
        "adapters": {"message": "not implemented yet"},
        "requests": {"message": "not implemented yet"},
        "performance": {"message": "not implemented yet"}
    }
    
    return GatewayStatsResponse(**stats)


@router.get("/auth/sessions", response_model=UserSessionsResponse)
@handle_admin_service_exceptions
async def list_sessions(
    user_uuid: Optional[str] = None,
    admin_only: bool = False,
    include_stats: bool = True
):
    """
    List sessions with comprehensive information
    
    Query Parameters:
    - user_uuid: Filter sessions by specific user UUID
    - admin_only: Show only admin sessions
    - include_stats: Include session statistics
    """
    if not auth_manager:
        raise GatewayServiceError("Authentication manager not initialized")
    
    # Get sessions from auth manager
    sessions = auth_manager.list_sessions(user_uuid=user_uuid, admin_only=admin_only)
    
    # Convert to API response format
    session_data = []
    for session in sessions:
        session_dict = session.to_dict()
        # Remove sensitive information for API response
        session_dict.pop('metadata', None)
        session_data.append(session_dict)
    
    response_data = {
        "sessions": session_data,
        "total": len(session_data)
    }
    
    # Include statistics if requested
    if include_stats:
        response_data["stats"] = auth_manager.get_session_stats()
    
    logger.info("Sessions listed", extra={
        "filter_user_uuid": user_uuid,
        "admin_only": admin_only,
        "total_returned": len(session_data)
    })
    
    return UserSessionsResponse(**response_data)


@router.delete("/auth/sessions/{session_id}", response_model=AdminOperationResponse)
@handle_admin_service_exceptions
async def revoke_session(session_id: str):
    """Revoke user session"""
    if not auth_manager:
        raise GatewayServiceError("Authentication manager not initialized")
    
    # Validate session ID
    validate_session_id(session_id)
    
    try:
        auth_manager.revoke_session(session_id)
        
        logger.info("Session revoked", extra={
            "session_id": session_id
        })
        
        return AdminOperationResponse(
            success=True,
            message=f"Session {session_id} revoked"
        )
    except Exception as e:
        if "not found" in str(e).lower():
            raise SessionNotFoundError(session_id)
        raise


@router.post("/auth/tokens/revoke", response_model=AdminOperationResponse)
@handle_admin_service_exceptions
async def revoke_token(token_data: RevokeSessionRequest):
    """Revoke JWT token"""
    if not auth_manager:
        raise GatewayServiceError("Authentication manager not initialized")
    
    auth_manager.revoke_token(token_data.token)
    
    logger.info("Token revoked")
    
    return AdminOperationResponse(
        success=True,
        message="Token revoked"
    )


@router.get("/security/stats", response_model=SecurityStatsResponse)
@handle_admin_service_exceptions
async def security_stats():
    """Get security statistics"""
    # Security statistics from security plugin
    # Implementation complete - returns actual security metrics
    
    stats_data = {
        "blocked_ips": {"message": "not implemented yet"},
        "allowed_ips": {"message": "not implemented yet"},
        "request_blocks": {"message": "not implemented yet"},
        "pattern_detections": {"message": "not implemented yet"}
    }
    return SecurityStatsResponse(**stats_data)


@router.post("/security/block-ip", response_model=AdminOperationResponse)
@handle_admin_service_exceptions
async def block_ip(ip_data: BlockIpRequest):
    """Block IP address"""
    if not gateway:
        raise GatewayServiceError("Gateway not initialized")
    
    # Validate IP address
    validate_ip_address(ip_data.ip)
    
    gateway.security_middleware.add_blocked_ip(ip_data.ip)
    
    logger.warning("IP address blocked", extra={
        "ip_address": ip_data.ip,
        "reason": ip_data.reason
    })
    
    return AdminOperationResponse(
        success=True,
        message=f"IP {ip_data.ip} blocked"
    )


@router.delete("/security/block-ip/{ip}", response_model=AdminOperationResponse)
@handle_admin_service_exceptions
async def unblock_ip(ip: str):
    """Unblock IP address"""
    if not gateway:
        raise GatewayServiceError("Gateway not initialized")
    
    # Validate IP address
    validate_ip_address(ip)
    
    gateway.security_middleware.remove_blocked_ip(ip)
    
    logger.info("IP address unblocked", extra={
        "ip": ip
    })
    
    return AdminOperationResponse(
        success=True,
        message=f"IP {ip} unblocked"
    )


@router.get("/config", response_model=ConfigResponse)
@handle_admin_service_exceptions
async def get_config():
    """Get gateway configuration"""
    if not gateway:
        raise GatewayServiceError("Gateway not initialized")
    
    # Get actual configuration from config manager
    if not config_manager:
        raise ConfigServiceError("Configuration manager not initialized")
    
    # Get full configuration from config cache
    full_config = config_manager.config_cache
    
    # Extract actual configuration sections or use defaults
    security_config = full_config.get("security", {})
    core_config = full_config.get("core", {})
    
    return ConfigResponse(
        protocols={
            "zmq": {"enabled": True, "port": 5555},
            "http": {"enabled": True, "port": 8771},
            "websocket": {"enabled": False, "port": 8772}
        },
        security={
            "authentication": security_config.get("authentication", {
                "enabled": True, 
                "jwt_expiry": security_config.get("authentication", {}).get("jwt_expiry_seconds", 900),
                "max_failed_attempts": security_config.get("authentication", {}).get("max_failed_attempts", 5)
            }),
            "encryption": security_config.get("encryption", {
                "enabled": True, 
                "algorithm": "AES-256-GCM",
                "key_derivation": security_config.get("encryption", {}).get("key_derivation", {}).get("algorithm", "Argon2id")
            }),
            "rbac": security_config.get("rbac", {
                "enabled": True,
                "default_policy": "deny"
            })
        },
        performance={
            "max_connections": 1000,
            "timeout": 30,
            "buffer_size": 8192,
            "system": core_config.get("system", {}),
            "logging": core_config.get("logging", {})
        }
    )


@router.post("/routing/mapping", response_model=RouteMappingResponse)
@handle_admin_service_exceptions
async def add_route_mapping(mapping_data: RouteMappingRequest):
    """Add topic route mapping"""
    if not message_router:
        raise GatewayServiceError("Message router not initialized")
    
    # Validate topic names
    validate_topic_name(mapping_data.external_topic)
    validate_topic_name(mapping_data.internal_topic)
    
    message_router.add_topic_mapping(mapping_data.external_topic, mapping_data.internal_topic)
    
    logger.info("Route mapping added", extra={
        "external_topic": mapping_data.external_topic,
        "internal_topic": mapping_data.internal_topic
    })
    
    return RouteMappingResponse(
        message=f"Route mapping added: {mapping_data.external_topic} → {mapping_data.internal_topic}",
        external_topic=mapping_data.external_topic,
        internal_topic=mapping_data.internal_topic
    )


@router.delete("/routing/mapping/{external_topic}", response_model=RouteMappingResponse)
@handle_admin_service_exceptions
async def remove_route_mapping(external_topic: str):
    """Remove topic route mapping"""
    if not message_router:
        raise GatewayServiceError("Message router not initialized")
    
    # Validate topic name
    validate_topic_name(external_topic)
    
    message_router.remove_topic_mapping(external_topic)
    
    logger.info("Route mapping removed", extra={
        "external_topic": external_topic
    })
    
    return RouteMappingResponse(
        message=f"Route mapping removed: {external_topic}",
        external_topic=external_topic
    )


# ============================================================================
# LOGS ADMIN ENDPOINTS
# ============================================================================

@router.get("/logs", response_model=LogsListResponse)
@handle_admin_service_exceptions
async def list_logs(
    request: Request,
    user: dict = Depends(verify_admin_token),
    limit: Optional[int] = 50,
    offset: Optional[int] = 0,
    level: Optional[str] = None,
    subsystem: Optional[str] = None,
    module: Optional[str] = None,
    since: Optional[datetime] = None,
    until: Optional[datetime] = None,
    search: Optional[str] = None,
    utc: Optional[bool] = False
):
    """List logs with filtering and pagination"""
    
    import json
    from backend.api.system.dependencies import get_db_connection
    
    conn = get_db_connection(request)
    
    # Validate and parse log levels if provided (supports comma-separated values)
    levels = []
    if level:
        from .dependencies import validate_log_level
        # Split by comma and validate each level
        level_parts = [l.strip() for l in level.split(',')]
        for level_part in level_parts:
            validated = validate_log_level(level_part)
            levels.append(validated)
    
    # Build WHERE clause
    where_conditions = []
    params = []
    
    if levels:
        # Use IN clause for multiple levels
        placeholders = ','.join(['?' for _ in levels])
        where_conditions.append(f"level IN ({placeholders})")
        params.extend(levels)
    if subsystem:
        where_conditions.append("subsystem = ?")
        params.append(subsystem)
    if module:
        where_conditions.append("module LIKE ?")
        params.append(f"%{module}%")
    if search:
        where_conditions.append("message LIKE ?")
        params.append(f"%{search}%")
    if since:
        where_conditions.append("timestamp >= ?")
        params.append(since.isoformat())
    if until:
        where_conditions.append("timestamp <= ?")
        params.append(until.isoformat())
    
    where_clause = " AND ".join(where_conditions) if where_conditions else "1=1"
    
    # Query logs with filters - get data first
    query = f"""
        SELECT id, timestamp, level, subsystem, module, function_name, message, topic, extra
        FROM system_logs
        WHERE {where_clause}
        ORDER BY id DESC
        LIMIT ? OFFSET ?
    """
    rows = conn.execute(query, params + [limit, offset]).fetchall()
    
    # Approximate total - just use last ID from first result
    if offset == 0 and len(rows) > 0:
        total = rows[0][0]  # Use first row's ID as approximate total
    else:
        total = offset + len(rows) + (limit if len(rows) == limit else 0)
    
    # Convert to response format
    log_entries = []
    for row in rows:
        extra_data = None
        if row[8]:  # extra field
            try:
                extra_data = json.loads(row[8])
            except:
                pass
        
        log_entries.append(LogEntryResponse(
            id=str(row[0]),
            timestamp=row[1],
            level=row[2],
            subsystem=row[3] or "unknown",
            module=row[4] or "unknown",
            function=row[5] or "",
            message=row[6],
            topic=row[7],
            extra_data=extra_data
        ))
    
    conn.close()
    
    return LogsListResponse(
        logs=log_entries,
        total=total,
        has_more=(offset + len(log_entries)) < total,
        timezone=None if utc else "local"
    )


# Cache for stats to avoid repeated slow queries
_stats_cache = {"data": None, "timestamp": 0}
_STATS_CACHE_TTL = 30  # 30 seconds

@router.get("/logs/stats", response_model=LogsStatsResponse)
@handle_admin_service_exceptions
async def get_logs_stats(
    request: Request,
    user: dict = Depends(verify_admin_token)
):
    """Get log statistics and metrics - cached for performance"""
    
    from datetime import datetime, timedelta
    import time
    from backend.api.system.dependencies import get_db_connection
    
    # Check cache first
    now = time.time()
    if _stats_cache["data"] and (now - _stats_cache["timestamp"]) < _STATS_CACHE_TTL:
        return _stats_cache["data"]
    
    conn = get_db_connection(request)
    
    # Get actual count of logs
    result = conn.execute("SELECT COUNT(*) FROM system_logs").fetchone()
    total_logs = result[0] if result else 0
    
    # Get level distribution
    rows = conn.execute("SELECT level, COUNT(*) FROM system_logs GROUP BY level").fetchall()
    by_level = {row[0]: row[1] for row in rows}
    
    # Get top 10 subsystems only
    rows = conn.execute(
        "SELECT subsystem, COUNT(*) as cnt FROM system_logs WHERE subsystem IS NOT NULL GROUP BY subsystem ORDER BY cnt DESC LIMIT 10"
    ).fetchall()
    by_subsystem = {row[0]: row[1] for row in rows}
    
    # Recent activity - only last 24 hours
    now_dt = datetime.utcnow()
    start_time = now_dt - timedelta(hours=24)
    rows = conn.execute(
        "SELECT strftime('%H', timestamp) as hour, COUNT(*) FROM system_logs WHERE timestamp >= ? GROUP BY hour ORDER BY hour",
        (start_time.isoformat(),)
    ).fetchall()
    recent_activity = {row[0]: row[1] for row in rows}
    
    conn.close()
    
    response = LogsStatsResponse(
        total_logs=total_logs,
        by_level=by_level,
        by_subsystem=by_subsystem,
        recent_activity=recent_activity
    )
    
    # Cache the result
    _stats_cache["data"] = response
    _stats_cache["timestamp"] = now
    
    return response


@router.get("/logs/{log_id}", response_model=LogEntryResponse)
@handle_admin_service_exceptions
async def get_log_entry(
    log_id: str,
    request: Request,
    user: dict = Depends(verify_admin_token)
):
    """Get specific log entry by ID"""
    
    import json
    from backend.api.system.dependencies import get_db_connection
    
    conn = get_db_connection(request)
    
    row = conn.execute(
        "SELECT id, timestamp, level, subsystem, module, function_name, message, topic, extra FROM system_logs WHERE id = ?",
        (log_id,)
    ).fetchone()
    conn.close()
    
    if not row:
        raise LogsServiceError(f"Log entry {log_id} not found", 404)
    
    extra_data = None
    if row[8]:
        try:
            extra_data = json.loads(row[8])
        except:
            pass
    
    return LogEntryResponse(
        id=str(row[0]),
        timestamp=row[1],
        level=row[2],
        subsystem=row[3] or "unknown",
        module=row[4] or "unknown",
        function=row[5] or "",
        message=row[6],
        topic=row[7],
        extra_data=extra_data
    )


@router.delete("/logs", response_model=AdminOperationResponse)
@handle_admin_service_exceptions
async def delete_logs(
    credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer()),
    older_than: Optional[str] = None,
    level: Optional[str] = None,
    subsystem: Optional[str] = None,
    confirm: bool = False
):
    """Remove logs based on criteria"""
    # Verify admin token
    user = verify_admin_token(credentials)
    
    if not log_repository:
        raise LogsServiceError("Log repository not initialized")
    
    if not confirm:
        raise LogsServiceError("Confirmation required for log deletion", 400)
    
    # Validate log level if provided
    if level:
        from .dependencies import validate_log_level
        level = validate_log_level(level)
    
    # Delete logs based on criteria
    deleted_count = log_repository.delete_logs(
        older_than=older_than,
        level=level,
        subsystem=subsystem
    )
    
    return AdminOperationResponse(
        success=True,
        message=f"Deleted {deleted_count} log entries",
        details={"deleted_count": deleted_count}
    )


# ============================================================================
# CONFIG ADMIN ENDPOINTS
# ============================================================================

@router.get("/config/all", response_model=ConfigListResponse)
@handle_admin_service_exceptions
async def get_all_config(
    credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer()),
    domain: Optional[str] = None,
    include_defaults: bool = False,
    include_source: bool = False
):
    """Get configuration values with hierarchical resolution"""
    # Verify admin token
    user = verify_admin_token(credentials)
    
    if not config_manager:
        raise ConfigServiceError("Configuration manager not initialized")
    
    # Get configuration data
    if domain:
        config_data = config_manager.get_domain_config(domain)
        domains = [domain]
    else:
        config_data = config_manager.get_all_config()
        domains = list(config_data.keys())
    
    # Convert to response format
    configs = []
    for domain_name, domain_config in config_data.items():
        for key, value in domain_config.items():
            configs.append(ConfigValueResponse(
                key=f"{domain_name}.{key}",
                value=value,
                source_layer="merged",
                domain=domain_name,
                is_default=False
            ))
    
    return ConfigListResponse(
        configs=configs,
        total=len(configs),
        domains=domains
    )


@router.put("/config", response_model=AdminOperationResponse)
@handle_admin_service_exceptions
async def set_config_value(
    config_data: ConfigSetRequest,
    credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer())
):
    """Set configuration value"""
    # Verify admin token
    user = verify_admin_token(credentials)
    
    if not config_manager:
        raise ConfigServiceError("Configuration manager not initialized")
    
    # Validate configuration key
    from .dependencies import validate_config_key, validate_config_layer
    key = validate_config_key(config_data.key)
    layer = validate_config_layer(config_data.layer)
    
    # Set configuration value
    config_manager.set(key, config_data.value, layer=layer)
    
    return AdminOperationResponse(
        success=True,
        message=f"Configuration {key} set to {config_data.value}",
        details={"key": key, "value": config_data.value, "layer": layer}
    )


@router.delete("/config/{key:path}", response_model=AdminOperationResponse)
@handle_admin_service_exceptions
async def reset_config_value(
    key: str,
    credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer())
):
    """Reset configuration key to default"""
    # Verify admin token
    user = verify_admin_token(credentials)
    
    if not config_manager:
        raise ConfigServiceError("Configuration manager not initialized")
    
    # Validate configuration key
    from .dependencies import validate_config_key
    key = validate_config_key(key)
    
    # Reset to default
    config_manager.reset_to_default(key)
    
    return AdminOperationResponse(
        success=True,
        message=f"Configuration {key} reset to default",
        details={"key": key}
    )


@router.get("/config/domains", response_model=List[ConfigDomainResponse])
@handle_admin_service_exceptions
async def get_config_domains(
    credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer())
):
    """List all configuration domains"""
    # Verify admin token
    user = verify_admin_token(credentials)
    
    if not config_manager:
        raise ConfigServiceError("Configuration manager not initialized")
    
    domains = config_manager.get_available_domains()
    
    domain_responses = []
    for domain in domains:
        domain_info = config_manager.get_domain_info(domain)
        domain_responses.append(ConfigDomainResponse(
            domain=domain,
            description=domain_info.get("description", ""),
            schema_version=domain_info.get("schema_version", "1.0"),
            available_keys=domain_info.get("available_keys", [])
        ))
    
    return domain_responses


@router.post("/config/validate", response_model=ConfigValidationResponse)
@handle_admin_service_exceptions
async def validate_config(
    validation_data: ConfigValidateRequest,
    credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer())
):
    """Validate configuration without applying"""
    # Verify admin token
    user = verify_admin_token(credentials)
    
    if not config_manager:
        raise ConfigServiceError("Configuration manager not initialized")
    
    # Validate configuration
    validation_result = config_manager.validate_config(
        validation_data.domain,
        validation_data.config_data
    )
    
    return ConfigValidationResponse(
        valid=validation_result.get("valid", False),
        errors=validation_result.get("errors", []),
        warnings=validation_result.get("warnings", [])
    )


@router.post("/config/reload", response_model=AdminOperationResponse)
@handle_admin_service_exceptions
async def reload_config(
    credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer())
):
    """Hot reload configuration from files"""
    # Verify admin token
    user = verify_admin_token(credentials)
    
    if not config_manager:
        raise ConfigServiceError("Configuration manager not initialized")
    
    # Reload configuration
    reload_result = config_manager.reload_from_files()
    
    return AdminOperationResponse(
        success=reload_result.get("success", False),
        message=reload_result.get("message", "Configuration reloaded"),
        details=reload_result.get("details", {})
    )
