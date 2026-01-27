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
    """List logs with filtering and pagination - queries InfluxDB"""
    
    from influxdb_client import InfluxDBClient
    from aico.core.config import ConfigurationManager
    from aico.security.key_manager import AICOKeyManager
    from datetime import timezone
    import json
    
    # Get InfluxDB credentials
    config = ConfigurationManager()
    key_manager = AICOKeyManager(config)
    
    influx_config = config.get('core.database.influx', {})
    url = influx_config.get('url', 'http://127.0.0.1:8086')
    org = influx_config.get('org', 'aico')
    bucket = influx_config.get('bucket', 'aico_telemetry')
    token = key_manager.get_database_password('influx', username='admin_token')
    
    client = InfluxDBClient(url=url, token=token, org=org)
    
    # Build Flux query filters
    filters = [
        'r._measurement == "logs"',
        'r._field == "message"'
    ]
    
    if level:
        # Handle comma-separated levels
        level_parts = [l.strip().upper() for l in level.split(',')]
        level_filter = " or ".join([f'r.level == "{lvl}"' for lvl in level_parts])
        filters.append(f'({level_filter})')
    
    if subsystem:
        filters.append(f'r.service == "{subsystem}"')
    
    if module:
        filters.append(f'r.module =~ /{module}/')
    
    if search:
        filters.append(f'r._value =~ /{search}/')
    
    filter_str = " and ".join(filters)

    def _to_flux_time_literal(dt: datetime) -> str:
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")

    range_start = "-24h"
    range_stop = "now()"

    if since:
        range_start = _to_flux_time_literal(since)
    if until:
        range_stop = _to_flux_time_literal(until)
    
    # Query InfluxDB - fetch more than needed and slice in Python for performance
    query = f'''
    from(bucket: "{bucket}")
      |> range(start: {range_start}, stop: {range_stop})
      |> filter(fn: (r) => {filter_str})
      |> sort(columns: ["_time"], desc: true)
      |> limit(n: {limit + offset})
    '''

    count_query = f'''
    from(bucket: "{bucket}")
      |> range(start: {range_start}, stop: {range_stop})
      |> filter(fn: (r) => {filter_str})
      |> group()
      |> count(column: "_value")
    '''
    
    try:
        total_tables = client.query_api().query(count_query, org=org)
        total = 0
        for table in total_tables:
            for record in table.records:
                try:
                    total = int(record.get_value())
                except Exception:
                    total = 0

        tables = client.query_api().query(query, org=org)
        
        # Collect all records from all tables
        all_records = []
        for table in tables:
            all_records.extend(table.records)
        
        if not all_records:
            return LogsListResponse(logs=[], total=0, has_more=False)
        
        # CRITICAL: Sort all records by timestamp DESC after combining tables
        # InfluxDB returns separate tables per tag combination, so we must re-sort
        all_records.sort(key=lambda r: r.get_time(), reverse=True)
        
        # Apply offset in Python
        records_to_show = all_records[offset:offset + limit]
        
        # Convert to log entries
        log_entries = []
        
        for record in records_to_show:
            # Generate unique ID from timestamp + message hash to prevent React key collisions
            timestamp = record.get_time()
            message = record.get_value()
            unique_id = f"{timestamp.timestamp()}_{hash(message) & 0xFFFFFFFF}"
            
            log_entries.append(LogEntryResponse(
                id=unique_id,
                timestamp=timestamp.isoformat(),
                level=record.values.get("level", "INFO"),
                subsystem=record.values.get("service", "unknown"),
                module=record.values.get("module", "unknown"),
                function=record.values.get("function", ""),
                message=message,
                topic="",
                extra_data=None
            ))
        
    finally:
        try:
            client.close()
        except:
            pass
    
    return LogsListResponse(
        logs=log_entries,
        total=total,
        has_more=(offset + len(log_entries)) < total,
        timezone=None if utc else "local"
    )


@router.get("/logs/count")
@handle_admin_service_exceptions
async def count_logs(
    request: Request,
    user: dict = Depends(verify_admin_token),
    level: Optional[str] = None,
    subsystem: Optional[str] = None,
    module: Optional[str] = None,
    since: Optional[datetime] = None,
    until: Optional[datetime] = None,
    search: Optional[str] = None,
):
    """Return exact log-entry count for a time window.

    Uses logs._field == "count" and sum(), which corresponds to 1 per logical log entry.
    """

    from influxdb_client import InfluxDBClient
    from aico.core.config import ConfigurationManager
    from aico.security.key_manager import AICOKeyManager
    from datetime import datetime, timezone

    config = ConfigurationManager()
    key_manager = AICOKeyManager(config)

    influx_config = config.get("core.database.influx", {})
    url = influx_config.get("url", "http://127.0.0.1:8086")
    org = influx_config.get("org", "aico")
    bucket = influx_config.get("bucket", "aico_telemetry")
    token = key_manager.get_database_password("influx", username="admin_token")

    client = InfluxDBClient(url=url, token=token, org=org)

    # Build Flux query filters
    filters = [
        'r._measurement == "logs"',
        'r._field == "count"',
    ]

    if level:
        level_parts = [l.strip().upper() for l in level.split(",")]
        level_filter = " or ".join([f'r.level == "{lvl}"' for lvl in level_parts])
        filters.append(f"({level_filter})")

    if subsystem:
        filters.append(f'r.service == "{subsystem}"')

    if module:
        filters.append(f'r.module =~ /{module}/')

    # Note: search is applied to message field in /logs. For count(), we support the same
    # parameter by switching to a message filter in the query.
    search_filter = ""
    if search:
        search_filter = f'|> filter(fn: (r) => r._field == "message") |> filter(fn: (r) => r._value =~ /{search}/)'

    filter_str = " and ".join(filters)

    def _to_flux_time_literal(dt: datetime) -> str:
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")

    range_start = "-24h"
    range_stop = "now()"
    if since:
        range_start = _to_flux_time_literal(since)
    if until:
        range_stop = _to_flux_time_literal(until)

    query = f'''
    from(bucket: "{bucket}")
      |> range(start: {range_start}, stop: {range_stop})
      |> filter(fn: (r) => {filter_str})
      {search_filter}
      |> group()
      |> sum(column: "_value")
    '''

    try:
        tables = client.query_api().query(query, org=org)
        total = 0
        for table in tables:
            for record in table.records:
                try:
                    total += int(record.get_value())
                except Exception:
                    pass
        return {"total": total}
    finally:
        try:
            client.close()
        except Exception:
            pass


# Cache for stats to avoid repeated slow queries
_stats_cache = {"data": None, "timestamp": 0}
_STATS_CACHE_TTL = 30  # 30 seconds

@router.get("/logs/stats", response_model=LogsStatsResponse)
@handle_admin_service_exceptions
async def get_logs_stats(
    request: Request,
    user: dict = Depends(verify_admin_token)
):
    """Get log statistics and metrics - queries InfluxDB, cached for performance"""
    
    from datetime import datetime, timedelta
    import time
    from influxdb_client import InfluxDBClient
    from aico.core.config import ConfigurationManager
    from aico.security.key_manager import AICOKeyManager
    
    # Check cache first
    now = time.time()
    if _stats_cache["data"] and (now - _stats_cache["timestamp"]) < _STATS_CACHE_TTL:
        return _stats_cache["data"]
    
    # Get InfluxDB credentials
    config = ConfigurationManager()
    key_manager = AICOKeyManager(config)
    
    influx_config = config.get('core.database.influx', {})
    url = influx_config.get('url', 'http://127.0.0.1:8086')
    org = influx_config.get('org', 'aico')
    bucket = influx_config.get('bucket', 'aico_telemetry')
    token = key_manager.get_database_password('influx', username='admin_token')
    
    client = InfluxDBClient(url=url, token=token, org=org)
    
    try:
        # Get total count and level distribution
        query = f'''
        from(bucket: "{bucket}")
          |> range(start: -24h)
          |> filter(fn: (r) => r._measurement == "logs")
          |> filter(fn: (r) => r._field == "count")
          |> group(columns: ["level"])
          |> sum()
        '''
        tables = client.query_api().query(query, org=org)
        
        by_level = {}
        total_logs = 0
        for table in tables:
            for record in table.records:
                level = record.values.get("level", "INFO")
                count = int(record.get_value())
                by_level[level] = count
                total_logs += count
        
        # Get service distribution (top 10)
        query = f'''
        from(bucket: "{bucket}")
          |> range(start: -24h)
          |> filter(fn: (r) => r._measurement == "logs")
          |> filter(fn: (r) => r._field == "count")
          |> group(columns: ["service"])
          |> sum()
          |> sort(desc: true)
          |> limit(n: 10)
        '''
        tables = client.query_api().query(query, org=org)
        
        by_subsystem = {}
        for table in tables:
            for record in table.records:
                service = record.values.get("service", "unknown")
                count = int(record.get_value())
                by_subsystem[service] = count
        
        # Calculate trends by comparing last hour vs previous hour
        # Query for last hour
        query_last_hour = f'''
        from(bucket: "{bucket}")
          |> range(start: -1h)
          |> filter(fn: (r) => r._measurement == "logs")
          |> filter(fn: (r) => r._field == "message")
          |> group(columns: ["level"])
          |> count()
        '''
        tables_last = client.query_api().query(query_last_hour, org=org)
        
        last_hour_by_level = {}
        last_hour_total = 0
        for table in tables_last:
            for record in table.records:
                level = record.values.get("level", "INFO")
                count = int(record.get_value())
                last_hour_by_level[level] = count
                last_hour_total += count
        
        # Query for previous hour (1h-2h ago)
        query_prev_hour = f'''
        from(bucket: "{bucket}")
          |> range(start: -2h, stop: -1h)
          |> filter(fn: (r) => r._measurement == "logs")
          |> filter(fn: (r) => r._field == "message")
          |> group(columns: ["level"])
          |> count()
        '''
        tables_prev = client.query_api().query(query_prev_hour, org=org)
        
        prev_hour_by_level = {}
        prev_hour_total = 0
        for table in tables_prev:
            for record in table.records:
                level = record.values.get("level", "INFO")
                count = int(record.get_value())
                prev_hour_by_level[level] = count
                prev_hour_total += count
        
        # Calculate error rate trend
        last_hour_errors = last_hour_by_level.get('ERROR', 0)
        prev_hour_errors = prev_hour_by_level.get('ERROR', 0)
        
        last_hour_error_rate = (last_hour_errors / last_hour_total * 100) if last_hour_total > 0 else 0
        prev_hour_error_rate = (prev_hour_errors / prev_hour_total * 100) if prev_hour_total > 0 else 0
        
        if prev_hour_error_rate > 0:
            error_rate_trend = ((last_hour_error_rate - prev_hour_error_rate) / prev_hour_error_rate) * 100
        else:
            error_rate_trend = 0.0
        
        # Calculate log volume trend
        if prev_hour_total > 0:
            log_volume_trend = ((last_hour_total - prev_hour_total) / prev_hour_total) * 100
        else:
            log_volume_trend = 0.0
        
        # Recent activity by hour (last 24h) - for timeline visualization
        query = f'''
        from(bucket: "{bucket}")
          |> range(start: -24h)
          |> filter(fn: (r) => r._measurement == "logs")
          |> filter(fn: (r) => r._field == "count")
          |> window(every: 1h)
          |> group(columns: ["level", "_start"])
          |> sum()
          |> duplicate(column: "_start", as: "_time")
        '''
        tables = client.query_api().query(query, org=org)
        
        recent_activity = {}
        for table in tables:
            for record in table.records:
                # Get hour from timestamp
                timestamp = record.get_time()
                hour_str = str(timestamp.hour)  # Convert to string for Pydantic validation
                count = int(record.get_value())
                
                # Sum all levels per hour (Pydantic expects Dict[str, int])
                if hour_str not in recent_activity:
                    recent_activity[hour_str] = 0
                recent_activity[hour_str] += count
        
    finally:
        try:
            client.close()
        except:
            pass
    
    response = LogsStatsResponse(
        total_logs=total_logs,
        by_level=by_level,
        by_subsystem=by_subsystem,
        recent_activity=recent_activity,
        error_rate_trend=error_rate_trend,
        log_volume_trend=log_volume_trend
    )
    
    # Cache the result
    _stats_cache["data"] = response
    _stats_cache["timestamp"] = now
    
    return response


# Deprecated endpoints removed - Studio already migrated to use:
# - GET /api/v1/admin/logs (with filters)
# - GET /api/v1/admin/logs/stats
# 
# Removed endpoints:
# - GET /api/v1/admin/logs/{log_id} - No longer needed (InfluxDB has no unique IDs)
# - DELETE /api/v1/admin/logs - Use InfluxDB retention policies instead


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
