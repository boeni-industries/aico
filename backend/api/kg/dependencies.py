"""
Knowledge Graph API dependencies.

Provides dependency injection for KG-related resources.
"""

from typing import Annotated, Dict, Any
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt

from aico.core.logging import get_logger

from backend.api import dependencies as api_dependencies
from backend.api.errors import raise_api_error

logger = get_logger("backend.api.kg.dependencies")
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


def get_kg_storage(request: Request):
    """
    Get KG storage instance from service container.
    
    Args:
        request: FastAPI request object
        
    Returns:
        PropertyGraphStorage instance
    """
    try:
        if not hasattr(request.app.state, 'service_container'):
            raise_api_error(
                status_code=500,
                error_code="SERVICE_CONTAINER_NOT_INITIALIZED",
                message="Service container not initialized",
            )
        
        container = request.app.state.service_container
        
        # Get database connection
        db_connection = container.get_service("database")
        
        # Create storage instance with PostgreSQL + pgvector only
        from aico.ai.knowledge_graph import PropertyGraphStorage
        storage = PropertyGraphStorage(db_connection, None, None)
        
        return storage
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get KG storage: {e}")
        raise_api_error(
            status_code=500,
            error_code="KG_STORAGE_UNAVAILABLE",
            message="Knowledge graph storage unavailable",
        )


def get_db_connection(request: Request):
    """
    Get database connection from service container.
    
    Args:
        request: FastAPI request object
        
    Returns:
        EncryptedPostgreSQLConnection instance
    """
    try:
        if not hasattr(request.app.state, 'service_container'):
            raise_api_error(
                status_code=500,
                error_code="SERVICE_CONTAINER_NOT_INITIALIZED",
                message="Service container not initialized",
            )
        
        container = request.app.state.service_container
        return container.get_service("database")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get database connection: {e}")
        raise_api_error(
            status_code=500,
            error_code="DATABASE_UNAVAILABLE",
            message="Database connection unavailable",
        )
