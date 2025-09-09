"""
Admin Management API Dependencies

Admin-specific authentication and validation dependencies.
"""

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Dict, Any
import jwt
from aico.core.logging import get_logger

security = HTTPBearer()
logger = get_logger("api", "admin_dependencies")


# FastAPI dependency injection functions - no global state
from fastapi import Request

def get_auth_manager(request: Request):
    """Get auth manager from service container via FastAPI app state"""
    if not hasattr(request.app.state, 'service_container'):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Service container not initialized"
        )
    container = request.app.state.service_container
    security_plugin = container.get_service("security_plugin")
    return security_plugin.auth_manager

def get_log_repository(request: Request):
    """Get log repository from service container"""
    if not hasattr(request.app.state, 'service_container'):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Service container not initialized"
        )
    container = request.app.state.service_container
    return container.get_service("log_consumer")

def get_config_manager(request: Request):
    """Get config manager from service container"""
    if not hasattr(request.app.state, 'service_container'):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Service container not initialized"
        )
    container = request.app.state.service_container
    return container.get_service("config_manager")

def verify_admin_token(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    auth_manager = Depends(get_auth_manager)
):
    """
    Verify admin JWT token and require admin role.
    """
    try:
        token = credentials.credentials
        
        # Decode and validate JWT token (skip audience validation for CLI compatibility)
        try:
            payload = jwt.decode(
                token,
                auth_manager._get_jwt_secret(),
                algorithms=[auth_manager.jwt_algorithm],
                options={"verify_aud": False}
            )
        except jwt.ExpiredSignatureError:
            raise HTTPException(status_code=401, detail="Token has expired")
        except jwt.InvalidTokenError:
            raise HTTPException(status_code=401, detail="Invalid token")
        
        # Check if token is revoked
        if token in auth_manager.revoked_tokens:
            raise HTTPException(status_code=401, detail="Token has been revoked")
        
        # Extract user information
        user_uuid = payload.get("user_uuid", payload.get("sub"))
        username = payload.get("username", user_uuid)
        roles = payload.get("roles", [])
        
        # Verify admin role
        if "admin" not in roles:
            raise HTTPException(status_code=403, detail="Admin access required")
        
        return {
            "user_uuid": user_uuid,
            "username": username,
            "roles": roles,
            "token": token
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Admin token verification failed: {e}")
        raise HTTPException(status_code=401, detail="Authentication failed")

# Removed create_admin_auth_dependency - using proper FastAPI DI


def validate_ip_address(ip: str) -> str:
    """
    Validate IP address format.
    """
    import re
    ip_pattern = r'^(?:[0-9]{1,3}\.){3}[0-9]{1,3}$'
    if not re.match(ip_pattern, ip):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid IP address format"
        )
    
    # Additional validation for valid IP ranges
    parts = ip.split('.')
    for part in parts:
        if int(part) > 255:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid IP address: octets must be 0-255"
            )
    
    return ip


def validate_topic_name(topic: str) -> str:
    """
    Validate topic name format for message routing.
    """
    if not topic or len(topic.strip()) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Topic name cannot be empty"
        )
    
    # Basic validation - topics should be alphanumeric with dots, underscores, hyphens
    import re
    if not re.match(r'^[a-zA-Z0-9._-]+$', topic):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Topic name can only contain letters, numbers, dots, underscores, and hyphens"
        )
    
    return topic.strip()


def validate_session_id(session_id: str) -> str:
    """
    Validate session ID format.
    """
    if not session_id or len(session_id.strip()) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Session ID cannot be empty"
        )
    
    return session_id.strip()


def validate_log_level(level: str) -> str:
    """
    Validate log level format.
    """
    valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
    if level.upper() not in valid_levels:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid log level. Must be one of: {', '.join(valid_levels)}"
        )
    return level.upper()


def validate_config_key(key: str) -> str:
    """
    Validate configuration key format (dot notation).
    """
    if not key or len(key.strip()) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Configuration key cannot be empty"
        )
    
    # Basic validation - keys should be alphanumeric with dots and underscores
    import re
    if not re.match(r'^[a-zA-Z0-9._]+$', key):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Configuration key can only contain letters, numbers, dots, and underscores"
        )
    
    return key.strip()


def validate_config_layer(layer: str) -> str:
    """
    Validate configuration layer.
    """
    valid_layers = ["user", "environment", "runtime"]
    if layer not in valid_layers:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid configuration layer. Must be one of: {', '.join(valid_layers)}"
        )
    return layer
