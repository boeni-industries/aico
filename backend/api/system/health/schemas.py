"""Pydantic schemas for System Health API responses."""

from datetime import datetime
from typing import List, Dict, Any, Optional, Literal
from pydantic import BaseModel, Field


class SystemHealthSummary(BaseModel):
    """Summary counts for system health."""
    critical_issues: int = Field(..., description="Number of critical issues")
    warnings: int = Field(..., description="Number of warnings")
    healthy_components: int = Field(..., description="Number of healthy components")


class SystemHealthResponse(BaseModel):
    """Overall system health status."""
    status: Literal["healthy", "degraded", "critical"] = Field(..., description="Overall health status")
    healthy_services: int = Field(..., description="Number of healthy services")
    total_services: int = Field(..., description="Total number of services")
    uptime_percentage: float = Field(..., description="System uptime percentage")
    uptime_seconds: int = Field(..., description="System uptime in seconds")
    last_check: datetime = Field(..., description="Timestamp of last health check")
    summary: SystemHealthSummary = Field(..., description="Summary statistics")


class SubCheckResult(BaseModel):
    """Result of a single sub-check."""
    name: str = Field(..., description="Sub-check name")
    status: Literal["ok", "warning", "error"] = Field(..., description="Check status")
    message: str = Field(..., description="Status message")
    latency_ms: Optional[int] = Field(None, description="Check latency in milliseconds")
    details: Dict[str, Any] = Field(default_factory=dict, description="Additional details")


class HealthCheckResult(BaseModel):
    """Result of a health check bundle."""
    check_id: str = Field(..., description="Health check identifier")
    status: Literal["ok", "issues", "error"] = Field(..., description="Overall check status")
    started_at: datetime = Field(..., description="Check start time")
    completed_at: Optional[datetime] = Field(None, description="Check completion time")
    duration_ms: Optional[int] = Field(None, description="Check duration in milliseconds")
    sub_checks: List[SubCheckResult] = Field(default_factory=list, description="Sub-check results")


class RemediationAction(BaseModel):
    """Remediation action for an issue."""
    action_id: str = Field(..., description="Action identifier")
    label: str = Field(..., description="Action label")
    impact: str = Field(..., description="Expected impact")
    skill_id: Optional[str] = Field(None, description="Skill to invoke for remediation")


class SystemIssue(BaseModel):
    """Active system issue."""
    id: str = Field(..., description="Issue identifier")
    issue_id: str = Field(..., description="Unique issue ID")
    severity: Literal["warning", "error", "critical"] = Field(..., description="Issue severity")
    service: str = Field(..., description="Affected service")
    title: str = Field(..., description="Issue title")
    detected_at: datetime = Field(..., description="Detection timestamp")
    resolved_at: Optional[datetime] = Field(None, description="Resolution timestamp")
    status: Literal["active", "resolving", "resolved"] = Field(..., description="Issue status")
    metrics: Dict[str, Any] = Field(default_factory=dict, description="Related metrics")
    impact: Dict[str, Any] = Field(default_factory=dict, description="Impact assessment")
    remediation: List[RemediationAction] = Field(default_factory=list, description="Remediation actions")


class SystemIssuesResponse(BaseModel):
    """Response containing active system issues."""
    issues: List[SystemIssue] = Field(default_factory=list, description="List of active issues")
    total_count: int = Field(..., description="Total number of issues")


class ServiceMetric(BaseModel):
    """Service metric with current value and history."""
    label: str = Field(..., description="Metric label")
    value: str = Field(..., description="Current metric value")
    unit: Optional[str] = Field(None, description="Metric unit")
    history: Optional[List[float]] = Field(None, description="Historical values for sparkline")
    percentage: Optional[float] = Field(None, description="Percentage value (0-100)")


class ServiceHealth(BaseModel):
    """Health status of a single service."""
    name: str = Field(..., description="Service name")
    status: Literal["healthy", "degraded", "critical"] = Field(..., description="Service status")
    group: Literal["api", "storage", "processing"] = Field(..., description="Service group")
    metric: ServiceMetric = Field(..., description="Primary metric")
    trend: Optional[Literal["up", "down", "stable"]] = Field(None, description="Metric trend")
    last_checked: Optional[datetime] = Field(None, description="Last check timestamp")
    dependencies: Optional[List[str]] = Field(None, description="Service dependencies")
    depends_on: Optional[List[str]] = Field(None, description="Services this depends on")


class ServiceHealthResponse(BaseModel):
    """Response containing service health statuses."""
    services: List[ServiceHealth] = Field(default_factory=list, description="List of service health statuses")


# Phase 5: Advanced Features Schemas

class ConnectionTestRequest(BaseModel):
    """Request to test connection to a specific component."""
    component: str = Field(..., description="Component to test (postgres, chroma, influx, modelservice, etc.)")
    timeout_seconds: Optional[int] = Field(5, description="Test timeout in seconds")


class ConnectionTestResult(BaseModel):
    """Result of a connection test."""
    component: str = Field(..., description="Component tested")
    status: Literal["ok", "error"] = Field(..., description="Test result status")
    latency_ms: Optional[int] = Field(None, description="Connection latency in milliseconds")
    message: str = Field(..., description="Test result message")
    details: Dict[str, Any] = Field(default_factory=dict, description="Additional details")
    fix_suggestions: List[str] = Field(default_factory=list, description="Suggested fixes if failed")


class LogEntry(BaseModel):
    """Log entry for streaming."""
    timestamp: datetime = Field(..., description="Log timestamp")
    level: str = Field(..., description="Log level")
    service: str = Field(..., description="Service name")
    message: str = Field(..., description="Log message")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class DiagnosticsResponse(BaseModel):
    """Performance diagnostics response."""
    slow_endpoints: List[Dict[str, Any]] = Field(default_factory=list, description="Slow API endpoints")
    slow_queries: List[Dict[str, Any]] = Field(default_factory=list, description="Slow database queries")
    error_patterns: List[Dict[str, Any]] = Field(default_factory=list, description="Common error patterns")
    recommendations: List[str] = Field(default_factory=list, description="Performance recommendations")


# Phase 6: Remediation Actions Schemas

class ActionExecutionRequest(BaseModel):
    """Request to execute a remediation action."""
    action_id: str = Field(..., description="Action identifier")
    params: Dict[str, Any] = Field(default_factory=dict, description="Action parameters")
    issue_id: Optional[str] = Field(None, description="Related issue ID")


class ActionExecutionResponse(BaseModel):
    """Response from action execution."""
    execution_id: str = Field(..., description="Execution identifier")
    action_id: str = Field(..., description="Action identifier")
    status: Literal["running", "completed", "failed"] = Field(..., description="Execution status")
    started_at: datetime = Field(..., description="Execution start time")
    completed_at: Optional[datetime] = Field(None, description="Execution completion time")
    result: Dict[str, Any] = Field(default_factory=dict, description="Execution result")
    error: Optional[str] = Field(None, description="Error message if failed")
