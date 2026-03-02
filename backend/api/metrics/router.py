"""
Metrics API Router

Main router that aggregates all metrics endpoints.
Provides a clean, modular API for system metrics.

Endpoints:
- GET /metrics/gateway       - API Gateway performance metrics
- GET /metrics/modelservice  - Model inference metrics
- GET /metrics/memory        - Memory system metrics
- GET /metrics/scheduler     - Task scheduler metrics
- GET /metrics/messagebus    - Message bus metrics
- GET /metrics/system        - Overall system health
- GET /metrics/all           - All metrics in one request
"""

from fastapi import APIRouter

from .endpoints import (
    gateway_router,
    modelservice_router,
    memory_router,
    scheduler_router,
    messagebus_router,
    system_router,
    all_router,
)

# Create main metrics router
router = APIRouter(prefix="/metrics", tags=["metrics"])

# Include all endpoint routers
router.include_router(gateway_router)
router.include_router(modelservice_router)
router.include_router(memory_router)
router.include_router(scheduler_router)
router.include_router(messagebus_router)
router.include_router(system_router)
router.include_router(all_router)


@router.get("/health")
async def metrics_health():
    """
    Health check endpoint for metrics API.
    
    Returns:
        Simple health status
    """
    return {
        "status": "healthy",
        "service": "metrics-api",
        "version": "2.0.0",
        "backend": "prometheus"
    }
