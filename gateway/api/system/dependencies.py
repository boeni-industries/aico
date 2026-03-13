"""
System API dependencies.
"""

from typing import Annotated, Dict, Any
from fastapi import Depends, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from aico.core.logging import get_logger

from gateway.api import dependencies as api_dependencies
from gateway.api.errors import raise_api_error

logger = get_logger("gateway.api.system.dependencies")
security = HTTPBearer()


def get_auth_manager(request: Request):
    """Get auth manager from service container via FastAPI app state."""
    return api_dependencies.get_auth_manager(request)


def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)],
    auth_manager = Depends(get_auth_manager)
) -> Dict[str, Any]:
    """Verify JWT token and return user information."""
    return api_dependencies.get_current_user(credentials=credentials, auth_manager=auth_manager)


def get_db_connection(request: Request):
    """Get database connection from service container."""
    if not hasattr(request.app.state, 'service_container'):
        raise_api_error(
            status_code=500,
            error_code="SERVICE_CONTAINER_NOT_INITIALIZED",
            message="Service container not initialized",
        )
    
    container = request.app.state.service_container
    db_connection = container.get_service("database")
    
    if db_connection is None:
        raise_api_error(
            status_code=503,
            error_code="DATABASE_UNAVAILABLE",
            message="Database not available",
        )
    
    return db_connection
