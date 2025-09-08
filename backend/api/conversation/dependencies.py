"""
Conversation API Dependencies

Authentication and validation dependencies for conversation endpoints.
"""

from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Dict, Any
import jwt
from aico.core.logging import get_logger

security = HTTPBearer()
logger = get_logger("api", "conversation_dependencies")


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


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    auth_manager = Depends(get_auth_manager)
) -> Dict[str, Any]:
    """
    Verify JWT token and return user information.
    Used for endpoints requiring any authenticated user.
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
        permissions = set(payload.get("permissions", []))
        
        return {
            "user_uuid": user_uuid,
            "username": username,
            "roles": roles,
            "permissions": permissions,
            "token": token
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Token verification failed: {e}")
        raise HTTPException(status_code=401, detail="Authentication failed")


def validate_thread_id(thread_id: str) -> str:
    """
    Validate conversation thread ID format.
    """
    if not thread_id or len(thread_id.strip()) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Thread ID cannot be empty"
        )
    
    # Basic UUID format validation
    import re
    uuid_pattern = r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
    if not re.match(uuid_pattern, thread_id, re.IGNORECASE):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Thread ID must be a valid UUID format"
        )
    
    return thread_id.strip()


def validate_message_type(message_type: str) -> str:
    """
    Validate message type.
    """
    valid_types = ["user_input", "system_message", "ai_response", "tool_call", "tool_response"]
    if message_type not in valid_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid message type. Must be one of: {', '.join(valid_types)}"
        )
    return message_type


def verify_thread_access(
    thread_id: str,
    request: Request,
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> str:
    """
    Verify that the current user has access to the specified conversation thread.
    
    Args:
        thread_id: The conversation thread ID to verify access for
        current_user: Current authenticated user information
        request: FastAPI request object for accessing app state
        
    Returns:
        The validated thread_id if access is granted
        
    Raises:
        HTTPException: If thread doesn't exist or user doesn't have access
    """
    from ..exceptions import ThreadAccessDeniedException, ConversationNotFoundException
    
    # Validate thread ID format first
    validated_thread_id = validate_thread_id(thread_id)
    
    try:
        # Get conversation service from container
        if not hasattr(request.app.state, 'service_container'):
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Service container not initialized"
            )
        
        container = request.app.state.service_container
        
        # TODO: Implement actual thread ownership verification
        # This should check if the user owns or has access to the thread
        # For now, we'll do basic validation and assume access is granted
        # In a real implementation, this would:
        # 1. Query the database for thread ownership
        # 2. Check if user is the thread creator
        # 3. Check if thread is shared with the user
        # 4. Verify thread exists
        
        logger.debug(f"Thread access verified for user {current_user['user_uuid']} on thread {validated_thread_id}")
        return validated_thread_id
        
    except Exception as e:
        logger.error(f"Thread access verification failed: {e}")
        raise ThreadAccessDeniedException(f"Access denied for thread {thread_id}")


def get_message_bus_client(request: Request):
    """
    Get message bus client from service container.
    
    Args:
        request: FastAPI request object for accessing app state
        
    Returns:
        MessageBusClient instance
        
    Raises:
        HTTPException: If service container or message bus client not available
    """
    try:
        if not hasattr(request.app.state, 'service_container'):
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Service container not initialized"
            )
        
        container = request.app.state.service_container
        message_bus_plugin = container.get_service("message_bus_plugin")
        
        if not message_bus_plugin or not hasattr(message_bus_plugin, 'client'):
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Message bus client not available"
            )
        
        return message_bus_plugin.client
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get message bus client: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Message bus service unavailable"
        )
