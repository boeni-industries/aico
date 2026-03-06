"""
Conversation API Dependencies

Authentication and validation dependencies for conversation endpoints.
"""

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from aico.core.logging import get_logger
from typing import Dict, Any
import jwt
import uuid
import re

from backend.api import dependencies as api_dependencies
from backend.api.errors import raise_api_error
from aico.core.bus import MessageBusClient

logger = get_logger("backend.api.conversation.dependencies")
security = HTTPBearer()

# Module-level cache for message bus client to avoid repeated connections
_message_bus_client_cache: MessageBusClient | None = None
logger = get_logger("api.conversation_dependencies")


def get_auth_manager(request: Request):
    """Get auth manager from service container via FastAPI app state"""
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
    credentials: HTTPAuthorizationCredentials = Depends(security),
    auth_manager = Depends(get_auth_manager)
) -> Dict[str, Any]:
    """
    Verify JWT token and return user information.
    Used for endpoints requiring any authenticated user.
    """
    return api_dependencies.get_current_user(credentials=credentials, auth_manager=auth_manager)


def validate_conversation_id(conversation_id: str) -> str:
    """
    Validate conversation ID format.
    Simple validation for conversation identifiers used with semantic memory.
    """
    if not conversation_id or len(conversation_id.strip()) == 0:
        raise_api_error(
            status_code=400,
            error_code="CONVERSATION_ID_EMPTY",
            message="Conversation ID cannot be empty",
        )
    
    # Basic format validation - allow flexible conversation IDs
    conversation_id = conversation_id.strip()
    if len(conversation_id) > 255:
        raise_api_error(
            status_code=400,
            error_code="CONVERSATION_ID_TOO_LONG",
            message="Conversation ID too long (max 255 characters)",
        )
    
    return conversation_id


def validate_message_type(message_type: str) -> str:
    """
    Validate message type.
    """
    valid_types = ["user_input", "system_message", "ai_response", "tool_call", "tool_response"]
    if message_type not in valid_types:
        raise_api_error(
            status_code=400,
            error_code="MESSAGE_TYPE_INVALID",
            message=f"Invalid message type. Must be one of: {', '.join(valid_types)}",
        )
    return message_type


# Thread access verification removed - conversations are now user-scoped through authentication
# Semantic memory handles context continuity without explicit thread management


async def get_message_bus_client(request: Request):
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
            raise_api_error(
                status_code=500,
                error_code="SERVICE_CONTAINER_NOT_INITIALIZED",
                message="Service container not initialized",
            )
        
        # Use cached client to avoid repeated connections
        global _message_bus_client_cache
        if _message_bus_client_cache:
            return _message_bus_client_cache

        client = MessageBusClient("backend_conversation_api")
        await client.connect()
        _message_bus_client_cache = client
        return client
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get message bus client: {e}")
        raise_api_error(
            status_code=500,
            error_code="MESSAGE_BUS_UNAVAILABLE",
            message="Message bus service unavailable",
        )
