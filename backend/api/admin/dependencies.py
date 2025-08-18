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


# Global auth manager - will be set during initialization
_auth_manager = None

def set_auth_manager(auth_manager):
    """Set the global auth manager for dependencies"""
    global _auth_manager
    _auth_manager = auth_manager

def verify_admin_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """
    Verify admin JWT token and require admin role.
    """
    if not _auth_manager:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Authentication manager not initialized"
        )
    
    try:
        token = credentials.credentials
        
        # Decode and validate JWT token (skip audience validation for CLI compatibility)
        try:
            payload = jwt.decode(
                token,
                _auth_manager._get_jwt_secret(),
                algorithms=[_auth_manager.jwt_algorithm],
                options={"verify_aud": False}
            )
        except jwt.ExpiredSignatureError:
            raise HTTPException(status_code=401, detail="Token has expired")
        except jwt.InvalidTokenError:
            raise HTTPException(status_code=401, detail="Invalid token")
        
        # Check if token is revoked
        if token in _auth_manager.revoked_tokens:
            raise HTTPException(status_code=401, detail="Token has been revoked")
        
        # Extract user information
        user_id = payload.get("sub")
        username = payload.get("username", user_id)
        roles = payload.get("roles", [])
        
        # Verify admin role
        if "admin" not in roles:
            raise HTTPException(status_code=403, detail="Admin access required")
        
        return {
            "user_id": user_id,
            "username": username,
            "roles": roles,
            "token": token
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Admin token verification failed: {e}")
        raise HTTPException(status_code=401, detail="Authentication failed")

def create_admin_auth_dependency(auth_manager):
    """
    Factory function to create admin auth dependency with injected auth_manager.
    Requires admin role for administrative operations.
    """
    set_auth_manager(auth_manager)
    return verify_admin_token


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
