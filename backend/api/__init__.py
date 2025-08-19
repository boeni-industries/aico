"""
AICO API Layer

Domain-based API organization following FastAPI best practices.
Each domain is self-contained with its own routers, schemas, dependencies, and exceptions.
"""

from fastapi import APIRouter
from .users import router as users_router
from .admin import router as admin_router, health_router as admin_health_router
from .health import router as health_router

# Main API router that includes all domain routers
api_router = APIRouter()

# Include domain routers with appropriate prefixes
api_router.include_router(users_router, prefix="/users", tags=["users"])
api_router.include_router(admin_health_router, prefix="/admin", tags=["admin"])  # Public health endpoint
api_router.include_router(admin_router, prefix="/admin", tags=["admin"])  # Protected admin endpoints
api_router.include_router(health_router, prefix="/health", tags=["health"])

__all__ = ["api_router"]
