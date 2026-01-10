"""
AICO Metrics API

Modern, modular metrics system built on InfluxDB with clean architecture.

This package provides comprehensive system metrics for monitoring:
- API Gateway performance
- Model inference statistics
- Memory system health
- Task scheduler metrics
- Message bus throughput
- Overall system health

Architecture:
- Separation of concerns (models, queries, endpoints)
- Type-safe with Pydantic models
- InfluxDB-native with Flux queries
- Highly testable and maintainable
"""

from .router import router
from .models import (
    MetricValue,
    GatewayMetrics,
    ModelserviceMetrics,
    MemoryMetrics,
    SchedulerMetrics,
    MessageBusMetrics,
    SystemHealthMetrics,
)

__all__ = [
    "router",
    "MetricValue",
    "GatewayMetrics",
    "ModelserviceMetrics",
    "MemoryMetrics",
    "SchedulerMetrics",
    "MessageBusMetrics",
    "SystemHealthMetrics",
]
