"""
User Management API Dependencies

User-specific authentication and validation dependencies.
"""

from typing import Dict, Any, Optional
from fastapi import HTTPException, Depends, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt
import re
import uuid
from aico.core.config import ConfigurationManager
from aico.core.logging import get_logger
from backend.core.lifecycle_manager import get_auth_manager

from backend.api.errors import raise_api_error

security = HTTPBearer()
logger = get_logger("api.users_dependencies")


# Use the proper dependency injection functions from lifecycle_manager
# These are already imported above


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
            
            # Check if token is revoked (both in-memory and database)
            if token in auth_manager.revoked_tokens:
                raise_api_error(status_code=401, error_code="AUTH_TOKEN_REVOKED", message="Token has been revoked")
            
            # Check database session status if session service is available
            if auth_manager.session_service:
                session_info = auth_manager.session_service.get_session_by_token(token)
                if not session_info or not session_info.is_active:
                    raise_api_error(status_code=401, error_code="AUTH_SESSION_REVOKED", message="Session has been revoked")
            
            # Check if user has admin permissions for user management
            roles = payload.get("roles", [])
            permissions = set(payload.get("permissions", []))
            
            if "admin" not in roles and "*" not in permissions and "user.*" not in permissions:
                raise_api_error(
                    status_code=403,
                    error_code="ADMIN_REQUIRED",
                    message="Admin access required for user management",
                )
            
            return {
                "user_uuid": payload.get("user_uuid", payload.get("sub")),
                "username": payload.get("username"),
                "roles": roles,
                "permissions": permissions,
                "token": token
            }
            
        except jwt.ExpiredSignatureError:
            raise_api_error(status_code=401, error_code="AUTH_TOKEN_EXPIRED", message="Token expired")
        except jwt.InvalidTokenError:
            raise_api_error(status_code=401, error_code="AUTH_TOKEN_INVALID", message="Invalid token")
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"User auth verification failed: {e}")
            raise_api_error(status_code=401, error_code="AUTH_FAILED", message="Authentication failed")
    
    return verify_user_access


def validate_uuid(uuid_str: str) -> str:
    """
    Validate UUID format and return normalized UUID string.
    Raises HTTPException if invalid.
    """
    try:
        # Validate and normalize UUID
        uuid_obj = uuid.UUID(uuid_str)
        return str(uuid_obj)
    except ValueError:
        raise_api_error(status_code=400, error_code="UUID_INVALID", message="Invalid UUID format")


def validate_user_type(user_type: str) -> str:
    """
    Validate user type is one of the allowed values.
    """
    config_manager = ConfigurationManager()
    default_user_type = config_manager.get('core.user_profiles.default_user_type', 'person')
    allowed_types = {default_user_type}
    if user_type not in allowed_types:
        raise_api_error(
            status_code=400,
            error_code="USER_TYPE_INVALID",
            message=f"Invalid user type. Must be one of: {', '.join(allowed_types)}",
        )
    return user_type


def validate_full_name(full_name: str) -> str:
    """
    Validate full name with reasonable defaults.
    """
    min_length = 1
    max_length = 100
    
    if not full_name or len(full_name.strip()) < min_length:
        raise_api_error(
            status_code=400,
            error_code="FULL_NAME_TOO_SHORT",
            message=f"Full name must be at least {min_length} character(s)",
        )
    
    if len(full_name) > max_length:
        raise_api_error(
            status_code=400,
            error_code="FULL_NAME_TOO_LONG",
            message=f"Full name must not exceed {max_length} characters",
        )
    
    return full_name.strip()


def validate_nickname(nickname: Optional[str]) -> Optional[str]:
    """
    Validate nickname with reasonable defaults.
    """
    if nickname is None:
        return None
        
    max_length = 50
    
    if len(nickname) > max_length:
        raise_api_error(
            status_code=400,
            error_code="NICKNAME_TOO_LONG",
            message=f"Nickname must not exceed {max_length} characters",
        )
    
    return nickname.strip() if nickname.strip() else None


def validate_pin(pin: str) -> str:
    """
    Validate PIN format and requirements using configuration.
    """
    config_manager = ConfigurationManager()
    pin_policy = config_manager.get('security.pin_policy', {})
    min_length = pin_policy.get('min_length', 4)
    max_length = pin_policy.get('max_length', 8)
    require_numeric = pin_policy.get('require_numeric', True)
    
    if not pin or len(pin) < min_length or len(pin) > max_length:
        raise_api_error(
            status_code=400,
            error_code="PIN_INVALID_LENGTH",
            message=f"PIN must be between {min_length} and {max_length} characters",
        )
    
    if require_numeric and not pin.isdigit():
        raise_api_error(
            status_code=400,
            error_code="PIN_INVALID_FORMAT",
            message="PIN must contain only digits",
        )
    
    return pin
