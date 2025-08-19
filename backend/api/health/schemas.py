"""
Health Management API Schemas

Pydantic models for health and monitoring API requests and responses.
"""

from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    """Response schema for health check"""
    status: str = Field(..., description="Overall health status")
    version: str = Field(..., description="Service version")
    service: str = Field(..., description="Service name")
    timestamp: str = Field(..., description="Health check timestamp")
    components: Optional[Dict[str, Any]] = Field(None, description="Component health details")


class ComponentHealth(BaseModel):
    """Schema for individual component health"""
    status: str = Field(..., description="Component status")
    uptime: Optional[float] = Field(None, description="Component uptime in seconds")
    last_check: str = Field(..., description="Last health check timestamp")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional component details")


class SystemMetrics(BaseModel):
    """Schema for system performance metrics"""
    cpu_usage: float = Field(..., description="CPU usage percentage")
    memory_usage: float = Field(..., description="Memory usage percentage")
    disk_usage: float = Field(..., description="Disk usage percentage")
    uptime: float = Field(..., description="System uptime in seconds")
    load_average: Optional[List[float]] = Field(None, description="System load averages")


class DatabaseHealth(BaseModel):
    """Schema for database health status"""
    status: str = Field(..., description="Database status")
    connection_count: int = Field(..., description="Active database connections")
    query_performance: Optional[Dict[str, float]] = Field(None, description="Query performance metrics")
    storage_size: Optional[int] = Field(None, description="Database storage size in bytes")


class MessageBusHealth(BaseModel):
    """Schema for message bus health status"""
    status: str = Field(..., description="Message bus status")
    active_connections: int = Field(..., description="Active connections")
    message_throughput: Optional[Dict[str, int]] = Field(None, description="Message throughput metrics")
    topics: Optional[List[str]] = Field(None, description="Active topics")


class DetailedHealthResponse(BaseModel):
    """Response schema for detailed health information"""
    overall_status: str = Field(..., description="Overall system health")
    timestamp: str = Field(..., description="Health check timestamp")
    system_metrics: SystemMetrics = Field(..., description="System performance metrics")
    components: Dict[str, ComponentHealth] = Field(..., description="Individual component health")
    database: Optional[DatabaseHealth] = Field(None, description="Database health")
    message_bus: Optional[MessageBusHealth] = Field(None, description="Message bus health")


class ReadinessResponse(BaseModel):
    """Response schema for readiness check"""
    ready: bool = Field(..., description="Whether system is ready to serve requests")
    components: Dict[str, bool] = Field(..., description="Component readiness status")
    missing_dependencies: Optional[List[str]] = Field(None, description="Missing dependencies if not ready")


class LivenessResponse(BaseModel):
    """Response schema for liveness check"""
    alive: bool = Field(..., description="Whether system is alive and responding")
    uptime: float = Field(..., description="System uptime in seconds")
    last_heartbeat: str = Field(..., description="Last heartbeat timestamp")
