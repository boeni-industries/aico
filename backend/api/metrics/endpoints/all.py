"""
All Metrics Endpoint

Provides a single endpoint that returns all system metrics in one request.
This is used by AICO Studio's System Metrics dashboard for efficient data loading.
"""

from typing import Annotated
from fastapi import APIRouter, Depends
from datetime import datetime, UTC

from backend.api.metrics.models import (
    GatewayMetrics,
    ModelserviceMetrics,
    MemoryMetrics,
    SchedulerMetrics,
    MessageBusMetrics,
    SystemHealthMetrics,
)
from backend.api.metrics.endpoints.gateway import get_gateway_metrics
from backend.api.metrics.endpoints.modelservice import get_modelservice_metrics
from backend.api.metrics.endpoints.memory import get_memory_metrics
from backend.api.metrics.endpoints.scheduler import get_scheduler_metrics
from backend.api.metrics.endpoints.messagebus import get_messagebus_metrics
from backend.api.metrics.endpoints.system import get_system_health_metrics
from backend.api.system.dependencies import get_current_user
from backend.core.postgres_dependencies import get_uow
from aico.data.uow import UnitOfWork

from pydantic import BaseModel, Field
from aico.core.logging import get_logger

logger = get_logger("backend.api.metrics.all")

router = APIRouter()


class AllMetrics(BaseModel):
    """Complete metrics response with all subsystems."""
    timestamp: str = Field(..., description="ISO timestamp of metrics collection")
    gateway: GatewayMetrics
    modelservice: ModelserviceMetrics
    memory: MemoryMetrics
    scheduler: SchedulerMetrics
    message_bus: MessageBusMetrics
    system_health: SystemHealthMetrics


@router.get("/all", response_model=AllMetrics)
async def get_all_metrics(
    user: Annotated[dict, Depends(get_current_user)],
    uow: Annotated[UnitOfWork, Depends(get_uow)],
) -> AllMetrics:
    """
    Get all system metrics in a single request.
    
    This endpoint efficiently collects metrics from all subsystems:
    - API Gateway performance
    - Modelservice inference statistics
    - Memory system health
    - Task scheduler metrics
    - Message bus throughput
    - Overall system health
    
    Returns:
        Complete metrics snapshot with timestamp
    """
    import asyncio
    
    # Collect all metrics in parallel instead of sequential FastAPI dependencies
    # This reduces total time from ~15s (sequential) to ~3s (parallel)
    # Note: get_memory_metrics requires user and uow, others don't
    gateway, modelservice, memory, scheduler, message_bus, system_health = await asyncio.gather(
        get_gateway_metrics(),
        get_modelservice_metrics(),
        get_memory_metrics(user, uow),
        get_scheduler_metrics(),
        get_messagebus_metrics(),
        get_system_health_metrics(),
    )
    
    return AllMetrics(
        timestamp=datetime.now(UTC).isoformat() + "Z",
        gateway=gateway,
        modelservice=modelservice,
        memory=memory,
        scheduler=scheduler,
        message_bus=message_bus,
        system_health=system_health,
    )
