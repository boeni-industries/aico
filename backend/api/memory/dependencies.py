"""
Memory API dependencies.

Provides dependency injection for memory-related resources.
"""

from typing import Annotated, Dict, Any
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt

from aico.core.logging import get_logger

logger = get_logger("backend", "api.memory.dependencies")
security = HTTPBearer()


def get_auth_manager(request: Request):
    """Get auth manager from service container via FastAPI app state."""
    if not hasattr(request.app.state, 'service_container'):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Service container not initialized"
        )
    container = request.app.state.service_container
    security_plugin = container.get_service("security_plugin")
    return security_plugin.auth_manager


def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)],
    auth_manager = Depends(get_auth_manager)
) -> Dict[str, Any]:
    """
    Verify JWT token and return user information.
    
    Args:
        credentials: HTTP Bearer token
        auth_manager: Auth manager from service container
        
    Returns:
        User dict with user_id and other claims
        
    Raises:
        HTTPException: If authentication fails
    """
    try:
        token = credentials.credentials
        
        # Decode and validate JWT token (same as emotion router)
        try:
            payload = jwt.decode(
                token,
                auth_manager._get_jwt_secret(),
                algorithms=["HS256"],
                options={"verify_aud": False}  # Skip audience validation for CLI compatibility
            )
            
            user_id = payload.get("sub")
            if not user_id:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid token: missing user ID"
                )
            
            return {
                "user_id": user_id,
                "username": payload.get("username"),
                "role": payload.get("role", "user")
            }
            
        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has expired"
            )
        except jwt.InvalidTokenError as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Invalid token: {str(e)}"
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Authentication failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
