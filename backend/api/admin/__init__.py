"""
Admin Management API Domain

Provides REST API endpoints for administrative operations.
"""

from .router import router, health_router

__all__ = ["router", "health_router"]
