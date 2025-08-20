"""
Admin Management API Router

REST API endpoints for administrative operations including gateway management,
session control, security operations, and system configuration.
"""

from typing import Optional, Dict, Any, List
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import JSONResponse

from .dependencies import verify_admin_token
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

# Global variables for dependency injection
auth_manager = None
authz_manager = None
message_router = None
gateway = None
log_repository = None
config_manager = None

# Admin authentication dependency function
async def get_admin_user():
    """Admin authentication dependency"""
    from .dependencies import _auth_manager
    if not _auth_manager:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Admin router not properly initialized"
        )
    # verify_admin_token is already configured with the auth manager
    # Just need to call it with the credentials dependency
    from fastapi.security import HTTPBearer
    from fastapi import Depends
    security = HTTPBearer()
    # This will be handled by FastAPI's dependency injection
    pass

def initialize_router(auth_mgr, authz_mgr, msg_router, gw, log_repo=None, config_mgr=None):
    """Initialize router with dependencies from main.py"""
    global auth_manager, authz_manager, message_router, gateway, log_repository, config_manager
    auth_manager = auth_mgr
    authz_manager = authz_mgr
    message_router = msg_router
    gateway = gw
    log_repository = log_repo
    config_manager = config_mgr
    
    # Initialize dependencies module with service managers
    from .dependencies import set_auth_manager, set_log_repository, set_config_manager
    set_auth_manager(auth_mgr)
    if log_repo:
        set_log_repository(log_repo)
    if config_mgr:
        set_config_manager(config_mgr)

# Health endpoint without authentication (public)
health_router = APIRouter()

@health_router.get("/health", response_model=AdminHealthResponse)
async def admin_health():
    """Admin health check"""
    return AdminHealthResponse(
        status="healthy",
        service="aico-api-gateway-admin",
        timestamp=datetime.utcnow().isoformat()
    )

# Protected admin endpoints - authentication handled per endpoint
router = APIRouter()


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
    
    # TODO: Implement comprehensive gateway statistics collection
    # Need to add get_stats() methods to REST and ZeroMQ adapters
    # Currently returning placeholder response - not implemented yet
    
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
    # TODO: Implement security statistics collection
    # Need to add get_security_stats() method to SecurityMiddleware
    # Currently returning placeholder response - not implemented yet
    
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
    credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer()),
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
    # Verify admin token
    user = verify_admin_token(credentials)
    
    if not log_repository:
        raise LogsServiceError("Log repository not initialized")
    
    # Validate log level if provided
    if level:
        from .dependencies import validate_log_level
        level = validate_log_level(level)
    
    # Query logs with filters
    logs = log_repository.query_logs(
        limit=limit,
        offset=offset,
        level=level,
        subsystem=subsystem,
        module=module,
        since=since,
        until=until,
        search=search
    )
    
    # Convert to response format
    log_entries = []
    for log in logs:
        log_entries.append(LogEntryResponse(
            id=log.get("id"),
            timestamp=log.get("timestamp"),
            level=log.get("level"),
            subsystem=log.get("subsystem"),
            module=log.get("module"),
            function=log.get("function"),
            message=log.get("message"),
            topic=log.get("topic"),
            extra_data=log.get("extra_data")
        ))
    
    # Get total count for pagination
    total = log_repository.count_logs(
        level=level,
        subsystem=subsystem,
        module=module,
        since=since,
        until=until,
        search=search
    )
    
    return LogsListResponse(
        logs=log_entries,
        total=total,
        has_more=(offset + len(log_entries)) < total,
        timezone=None if utc else "local"
    )


@router.get("/logs/{log_id}", response_model=LogEntryResponse)
@handle_admin_service_exceptions
async def get_log_entry(
    log_id: str,
    credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer())
):
    """Get specific log entry by ID"""
    # Verify admin token
    user = verify_admin_token(credentials)
    
    if not log_repository:
        raise LogsServiceError("Log repository not initialized")
    
    log = log_repository.get_log_by_id(log_id)
    if not log:
        raise LogsServiceError(f"Log entry {log_id} not found", 404)
    
    return LogEntryResponse(
        id=log.get("id"),
        timestamp=log.get("timestamp"),
        level=log.get("level"),
        subsystem=log.get("subsystem"),
        module=log.get("module"),
        function=log.get("function"),
        message=log.get("message"),
        topic=log.get("topic"),
        extra_data=log.get("extra_data")
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


@router.get("/logs/stats", response_model=LogsStatsResponse)
@handle_admin_service_exceptions
async def get_logs_stats(
    credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer())
):
    """Get log statistics and metrics"""
    # Verify admin token
    user = verify_admin_token(credentials)
    
    if not log_repository:
        raise LogsServiceError("Log repository not initialized")
    
    stats = log_repository.get_log_statistics()
    
    return LogsStatsResponse(
        total_logs=stats.get("total_logs", 0),
        by_level=stats.get("by_level", {}),
        by_subsystem=stats.get("by_subsystem", {}),
        recent_activity=stats.get("recent_activity", {})
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
                source_layer="merged",  # TODO: Add source tracking
                domain=domain_name,
                is_default=False  # TODO: Add default detection
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
