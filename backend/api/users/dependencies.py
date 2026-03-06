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


def validate_password(password: str) -> str:
    """Validate interactive password/passcode requirements.

    Policy is configurable to be stricter (min_length only), but never weaker.
    """

    base_min_length = 12
    try:
        config_manager = ConfigurationManager()
        configured = config_manager.get('security.authentication.admin_passcode_policy', {})
        configured_min_length = configured.get('min_length') if isinstance(configured, dict) else None
        if isinstance(configured_min_length, int) and configured_min_length > base_min_length:
            base_min_length = configured_min_length
    except Exception:
        pass

    value = (password or "").strip()
    if not value:
        raise_api_error(status_code=400, error_code="PASSWORD_EMPTY", message="Password cannot be empty")

    if any(ch.isspace() for ch in value):
        raise_api_error(status_code=400, error_code="PASSWORD_WHITESPACE", message="Password must not contain whitespace")

    if len(value) < base_min_length:
        raise_api_error(
            status_code=400,
            error_code="PASSWORD_TOO_SHORT",
            message=f"Password must be at least {base_min_length} characters",
        )

    if value.isdigit():
        raise_api_error(
            status_code=400,
            error_code="PASSWORD_DIGITS_ONLY",
            message="Password must not be digits-only",
        )

    if not any(ch.islower() for ch in value):
        raise_api_error(status_code=400, error_code="PASSWORD_MISSING_LOWER", message="Password must contain a lowercase letter")
    if not any(ch.isupper() for ch in value):
        raise_api_error(status_code=400, error_code="PASSWORD_MISSING_UPPER", message="Password must contain an uppercase letter")
    if not any(ch.isdigit() for ch in value):
        raise_api_error(status_code=400, error_code="PASSWORD_MISSING_DIGIT", message="Password must contain a digit")
    if not any((not ch.isalnum()) for ch in value):
        raise_api_error(status_code=400, error_code="PASSWORD_MISSING_SYMBOL", message="Password must contain a symbol")

    return value


def validate_pin(pin: str) -> str:
    """Backwards-compatible alias for legacy clients."""
    return validate_password(pin)
