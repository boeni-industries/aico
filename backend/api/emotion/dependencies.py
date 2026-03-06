"""
Emotion API dependencies.

Provides dependency injection for emotion-related resources.
"""

from typing import Annotated, Dict, Any
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt

from aico.core.logging import get_logger

from backend.api import dependencies as api_dependencies
from backend.api.errors import raise_api_error

logger = get_logger("backend.api.emotion.dependencies")
security = HTTPBearer()


def get_auth_manager(request: Request):
    """Get auth manager from service container via FastAPI app state."""
    if not hasattr(request.app.state, 'service_container'):
        raise_api_error(
            status_code=500,
            error_code="SERVICE_CONTAINER_NOT_INITIALIZED",
            message="Service container not initialized",
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
    return api_dependencies.get_current_user(credentials=credentials, auth_manager=auth_manager)


def get_emotion_engine(request: Request):
    """
    Get emotion engine service from service container.
    
    Args:
        request: FastAPI request object
        
    Returns:
        EmotionEngine instance
    """
    try:
        if not hasattr(request.app.state, 'service_container'):
            raise_api_error(
                status_code=500,
                error_code="SERVICE_CONTAINER_NOT_INITIALIZED",
                message="Service container not initialized",
            )
        
        container = request.app.state.service_container
        emotion_engine = container.get_service("emotion_engine")
        
        if emotion_engine is None:
            raise_api_error(
                status_code=503,
                error_code="EMOTION_ENGINE_NOT_AVAILABLE",
                message="Emotion engine not available",
            )
        
        return emotion_engine
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get emotion engine: {e}")
        raise_api_error(
            status_code=500,
            error_code="EMOTION_ENGINE_UNAVAILABLE",
            message="Emotion engine unavailable",
        )
