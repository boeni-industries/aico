"""
AICO API Layer

Domain-based API organization following FastAPI best practices.
Each domain is self-contained with its own routers, schemas, dependencies, and exceptions.
"""

from fastapi import APIRouter
from .users import router as users_router
from .admin import router as admin_router
from .health import router as health_router
from .logs import router as logs_router
from .echo import router as echo_router
from .conversation import router as conversation_router

# Main API router that includes all domain routers
api_router = APIRouter()

# Include domain routers with appropriate prefixes
api_router.include_router(users_router, prefix="/users", tags=["users"])
api_router.include_router(logs_router, prefix="/logs", tags=["logs"])  # Public logging endpoints
api_router.include_router(admin_router, prefix="/admin", tags=["admin"])  # Protected admin endpoints
api_router.include_router(health_router, prefix="/health", tags=["health"])
api_router.include_router(echo_router, prefix="/echo", tags=["echo"])
api_router.include_router(conversation_router, prefix="/conversation", tags=["conversation"])  # Conversation endpoints

__all__ = ["api_router"]
