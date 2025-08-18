"""
Admin Management API Router

REST API endpoints for administrative operations including gateway management,
session control, security operations, and system configuration.
"""

from typing import Optional, Dict, Any
from fastapi import APIRouter, HTTPException, Depends, status
from datetime import datetime
from aico.core.logging import get_logger
from .schemas import (
    GatewayStatusResponse, GatewayStatsResponse, SessionListResponse,
    RevokeTokenRequest, BlockIpRequest, SecurityStatsResponse,
    ConfigResponse, RouteMappingRequest, RouteMappingResponse,
    AdminHealthResponse, AdminOperationResponse
)
from .dependencies import validate_ip_address, validate_topic_name, validate_session_id
from .exceptions import (
    SessionNotFoundError, GatewayServiceError, SecurityOperationError,
    RoutingConfigurationError, handle_admin_service_exceptions
)

router = APIRouter()
logger = get_logger("api", "admin_router")

# These will be injected during app initialization
auth_manager = None
authz_manager = None
message_router = None
gateway = None
verify_admin_access = None


def initialize_router(auth_mgr, authz_mgr, msg_router, gw, admin_dependency):
    """Initialize router with dependencies from main.py"""
    global auth_manager, authz_manager, message_router, gateway, verify_admin_access
    auth_manager = auth_mgr
    authz_manager = authz_mgr
    message_router = msg_router
    gateway = gw
    verify_admin_access = admin_dependency


@router.get("/health", response_model=AdminHealthResponse)
async def admin_health():
    """Admin health check"""
    return AdminHealthResponse(
        status="healthy",
        service="aico-api-gateway-admin",
        timestamp=datetime.utcnow().isoformat()
    )


@router.get("/gateway/status", response_model=GatewayStatusResponse)
@handle_admin_service_exceptions
async def gateway_status(user: dict = Depends(lambda: verify_admin_access)):
    """Get gateway status"""
    if not gateway:
        raise GatewayServiceError("Gateway not initialized")
    
    status_data = gateway.get_health_status()
    return GatewayStatusResponse(**status_data)


@router.get("/gateway/stats", response_model=GatewayStatsResponse)
@handle_admin_service_exceptions
async def gateway_stats(user: dict = Depends(lambda: verify_admin_access)):
    """Get gateway statistics including routing and adapter metrics"""
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


@router.get("/auth/sessions", response_model=SessionListResponse)
@handle_admin_service_exceptions
async def list_sessions(
    user_id: Optional[str] = None,
    admin_only: bool = False,
    include_stats: bool = True,
    user: dict = Depends(lambda: verify_admin_access)
):
    """
    List sessions with comprehensive information
    
    Query Parameters:
    - user_id: Filter sessions by specific user ID
    - admin_only: Show only admin sessions
    - include_stats: Include session statistics
    """
    if not auth_manager:
        raise GatewayServiceError("Authentication manager not initialized")
    
    # Get sessions from auth manager
    sessions = auth_manager.list_sessions(user_id=user_id, admin_only=admin_only)
    
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
        "admin_user": user["username"],
        "filter_user_id": user_id,
        "admin_only": admin_only,
        "total_returned": len(session_data)
    })
    
    return SessionListResponse(**response_data)


@router.delete("/auth/sessions/{session_id}", response_model=AdminOperationResponse)
@handle_admin_service_exceptions
async def revoke_session(
    session_id: str,
    user: dict = Depends(lambda: verify_admin_access)
):
    """Revoke user session"""
    if not auth_manager:
        raise GatewayServiceError("Authentication manager not initialized")
    
    # Validate session ID
    validate_session_id(session_id)
    
    try:
        auth_manager.revoke_session(session_id)
        
        logger.info("Session revoked", extra={
            "session_id": session_id,
            "revoked_by": user["username"]
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
async def revoke_token(
    token_data: RevokeTokenRequest,
    user: dict = Depends(lambda: verify_admin_access)
):
    """Revoke JWT token"""
    if not auth_manager:
        raise GatewayServiceError("Authentication manager not initialized")
    
    auth_manager.revoke_token(token_data.token)
    
    logger.info("Token revoked", extra={
        "revoked_by": user["username"]
    })
    
    return AdminOperationResponse(
        success=True,
        message="Token revoked"
    )


@router.get("/security/stats", response_model=SecurityStatsResponse)
@handle_admin_service_exceptions
async def security_stats(user: dict = Depends(lambda: verify_admin_access)):
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
async def block_ip(
    ip_data: BlockIpRequest,
    user: dict = Depends(lambda: verify_admin_access)
):
    """Block IP address"""
    if not gateway:
        raise GatewayServiceError("Gateway not initialized")
    
    # Validate IP address
    validate_ip_address(ip_data.ip)
    
    gateway.security_middleware.add_blocked_ip(ip_data.ip)
    
    logger.warning("IP address blocked", extra={
        "ip_address": ip_data.ip,
        "reason": ip_data.reason,
        "blocked_by": user["username"]
    })
    
    return AdminOperationResponse(
        success=True,
        message=f"IP {ip_data.ip} blocked"
    )


@router.delete("/security/block-ip/{ip}", response_model=AdminOperationResponse)
@handle_admin_service_exceptions
async def unblock_ip(
    ip: str,
    user: dict = Depends(lambda: verify_admin_access)
):
    """Unblock IP address"""
    if not gateway:
        raise GatewayServiceError("Gateway not initialized")
    
    # Validate IP address
    validate_ip_address(ip)
    
    gateway.security_middleware.remove_blocked_ip(ip)
    
    logger.info("IP address unblocked", extra={
        "ip_address": ip,
        "unblocked_by": user["username"]
    })
    
    return AdminOperationResponse(
        success=True,
        message=f"IP {ip} unblocked"
    )


@router.get("/config", response_model=ConfigResponse)
@handle_admin_service_exceptions
async def get_config(user: dict = Depends(lambda: verify_admin_access)):
    """Get gateway configuration"""
    if not gateway:
        raise GatewayServiceError("Gateway not initialized")
    
    return ConfigResponse(
        protocols=gateway.config.protocols,
        security=gateway.config.security,
        performance=gateway.config.performance
    )


@router.post("/routing/mapping", response_model=RouteMappingResponse)
@handle_admin_service_exceptions
async def add_route_mapping(
    mapping_data: RouteMappingRequest,
    user: dict = Depends(lambda: verify_admin_access)
):
    """Add topic route mapping"""
    if not message_router:
        raise GatewayServiceError("Message router not initialized")
    
    # Validate topic names
    validate_topic_name(mapping_data.external_topic)
    validate_topic_name(mapping_data.internal_topic)
    
    message_router.add_topic_mapping(mapping_data.external_topic, mapping_data.internal_topic)
    
    logger.info("Route mapping added", extra={
        "external_topic": mapping_data.external_topic,
        "internal_topic": mapping_data.internal_topic,
        "added_by": user["username"]
    })
    
    return RouteMappingResponse(
        message=f"Route mapping added: {mapping_data.external_topic} → {mapping_data.internal_topic}",
        external_topic=mapping_data.external_topic,
        internal_topic=mapping_data.internal_topic
    )


@router.delete("/routing/mapping/{external_topic}", response_model=RouteMappingResponse)
@handle_admin_service_exceptions
async def remove_route_mapping(
    external_topic: str,
    user: dict = Depends(lambda: verify_admin_access)
):
    """Remove topic route mapping"""
    if not message_router:
        raise GatewayServiceError("Message router not initialized")
    
    # Validate topic name
    validate_topic_name(external_topic)
    
    message_router.remove_topic_mapping(external_topic)
    
    logger.info("Route mapping removed", extra={
        "external_topic": external_topic,
        "removed_by": user["username"]
    })
    
    return RouteMappingResponse(
        message=f"Route mapping removed: {external_topic}",
        external_topic=external_topic
    )
