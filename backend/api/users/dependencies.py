"""
User Management API Dependencies

User-specific authentication and validation dependencies.
"""

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Dict, Any
import uuid as uuid_module
import jwt
from aico.core.logging import get_logger

security = HTTPBearer()
logger = get_logger("api", "users_dependencies")


def create_user_auth_dependency(auth_manager):
    """
    Factory function to create user auth dependency with injected auth_manager.
    Requires valid user authentication with user management permissions.
    """
    async def verify_user_access(credentials: HTTPAuthorizationCredentials = Depends(security)) -> Dict[str, Any]:
        try:
            token = credentials.credentials
            
            # Use auth_manager to validate JWT token
            payload = jwt.decode(
                token,
                auth_manager._get_jwt_secret(),
                algorithms=[auth_manager.jwt_algorithm],
                options={"verify_aud": False}
            )
            
            # Check if token is revoked
            if token in auth_manager.revoked_tokens:
                raise HTTPException(status_code=401, detail="Token has been revoked")
            
            # Check if user has admin permissions for user management
            roles = payload.get("roles", [])
            permissions = set(payload.get("permissions", []))
            
            if "admin" not in roles and "*" not in permissions and "user.*" not in permissions:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Admin access required for user management"
                )
            
            return {
                "user_id": payload.get("sub"),
                "username": payload.get("username"),
                "roles": roles,
                "permissions": permissions,
                "token": token
            }
            
        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token expired"
            )
        except jwt.InvalidTokenError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token"
            )
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"User auth verification failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication failed"
            )
    
    return verify_user_access


def validate_uuid(uuid_str: str) -> str:
    """
    Validate UUID format and return normalized UUID string.
    Raises HTTPException if invalid.
    """
    try:
        # Validate and normalize UUID
        uuid_obj = uuid_module.UUID(uuid_str)
        return str(uuid_obj)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid UUID format"
        )


def validate_user_type(user_type: str) -> str:
    """
    Validate user type is one of the allowed values.
    """
    allowed_types = {"parent", "child", "admin"}
    if user_type not in allowed_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid user type. Must be one of: {', '.join(allowed_types)}"
        )
    return user_type


def validate_pin(pin: str) -> str:
    """
    Validate PIN format and requirements.
    """
    if not pin or len(pin) < 4 or len(pin) > 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="PIN must be between 4 and 8 characters"
        )
    
    if not pin.isdigit():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="PIN must contain only digits"
        )
    
    return pin
