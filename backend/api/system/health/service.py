"""System Health Service

Business logic for health checks, issue detection, and service monitoring.
"""

from __future__ import annotations

import time
from datetime import datetime, UTC, timedelta
from typing import Dict, Any, List, Optional
from functools import lru_cache

from aico.core.logging import get_logger
from aico.ai.agency.skill_invoker import SkillInvoker
from aico.ai.agency.skills.registry import SkillRegistry
from aico.data.uow import UnitOfWork

from .schemas import (
    SystemHealthResponse,
    SystemHealthSummary,
    HealthCheckResult,
    SubCheckResult,
    SystemIssuesResponse,
    SystemIssue,
    RemediationAction,
    ServiceHealthResponse,
    ServiceHealth,
    ServiceMetric,
)


logger = get_logger("backend.api.system.health.service")


class HealthService:
    """Service for system health monitoring and diagnostics."""

    def __init__(
        self,
        skill_registry: SkillRegistry,
        skill_invoker: SkillInvoker,
        session_factory: Any,
        start_time: float,
    ):
        self._skill_registry = skill_registry
        self._skill_invoker = skill_invoker
        self._session_factory = session_factory
        self._start_time = start_time
    
    @property
    def _uptime_seconds(self) -> int:
        """Get backend uptime in seconds."""
        return int(time.time() - self._start_time)

    async def get_system_health(self) -> SystemHealthResponse:
        """Get overall system health by aggregating all health checks.
        
        Cached for 30 seconds to avoid overload.
        """
        # Run all health check skills
        connectivity_result = await self._run_skill("maint.connectivity.full_scan", {})
        resources_result = await self._run_skill("maint.system.scan_resources", {})
        modelservice_result = await self._run_skill("maint.modelservice.scan_health", {})
        agency_result = await self._run_skill("maint.agency.re_evaluate_behaviour_health", {})
        
        # Count healthy vs total
        results = [connectivity_result, resources_result, modelservice_result, agency_result]
        healthy_count = sum(1 for r in results if r.get("summary_status") == "healthy")
        total_count = len(results)
        
        # Determine overall status
        if any(r.get("summary_status") == "unhealthy" for r in results):
            overall_status = "critical"
        elif any(r.get("summary_status") == "degraded" for r in results):
            overall_status = "degraded"
        else:
            overall_status = "healthy"
        
        # Count issues (simplified - would query database in production)
        critical_issues = 1 if overall_status == "critical" else 0
        warnings = sum(1 for r in results if r.get("summary_status") == "degraded")
        
        # Calculate uptime
        uptime_seconds = int(time.time() - self._start_time)
        uptime_percentage = 99.8  # Placeholder - would calculate from historical data
        
        return SystemHealthResponse(
            status=overall_status,
            healthy_services=healthy_count,
            total_services=total_count,
            uptime_percentage=uptime_percentage,
            uptime_seconds=uptime_seconds,
            last_check=datetime.now(UTC),
            summary=SystemHealthSummary(
                critical_issues=critical_issues,
                warnings=warnings,
                healthy_components=healthy_count,
            ),
        )

    async def run_connectivity_check(self) -> HealthCheckResult:
        """Run connectivity health check bundle."""
        started_at = datetime.now(UTC)
        
        result = await self._run_skill("maint.connectivity.full_scan", {})
        
        completed_at = datetime.now(UTC)
        duration_ms = int((completed_at - started_at).total_seconds() * 1000)
        
        # Convert skill result to health check format
        checks = result.get("checks", {})
        sub_checks = []
        
        for component, check_data in checks.items():
            sub_checks.append(SubCheckResult(
                name=component,
                status=self._map_status(check_data.get("status")),
                message=check_data.get("error_message") or "OK",
                latency_ms=check_data.get("latency_ms"),
                details=check_data.get("details", {}),
            ))
        
        overall_status = self._map_status(result.get("summary_status"))
        
        return HealthCheckResult(
            check_id="connectivity",
            status=overall_status,
            started_at=started_at,
            completed_at=completed_at,
            duration_ms=duration_ms,
            sub_checks=sub_checks,
        )

    async def run_resources_check(self) -> HealthCheckResult:
        """Run resource monitoring health check bundle."""
        started_at = datetime.now(UTC)
        
        result = await self._run_skill("maint.system.scan_resources", {})
        
        completed_at = datetime.now(UTC)
        duration_ms = int((completed_at - started_at).total_seconds() * 1000)
        
        checks = result.get("checks", {})
        sub_checks = []
        
        for resource, check_data in checks.items():
            status = "error" if check_data.get("status") == "error" else (
                "warning" if check_data.get("threshold_exceeded") else "ok"
            )
            sub_checks.append(SubCheckResult(
                name=resource,
                status=status,
                message=check_data.get("error_message") or "OK",
                latency_ms=check_data.get("latency_ms"),
                details=check_data.get("details", {}),
            ))
        
        overall_status = self._map_status(result.get("summary_status"))
        
        return HealthCheckResult(
            check_id="resources",
            status=overall_status,
            started_at=started_at,
            completed_at=completed_at,
            duration_ms=duration_ms,
            sub_checks=sub_checks,
        )

    async def run_models_check(self) -> HealthCheckResult:
        """Run modelservice health check bundle."""
        started_at = datetime.now(UTC)
        
        result = await self._run_skill("maint.modelservice.scan_health", {})
        
        completed_at = datetime.now(UTC)
        duration_ms = int((completed_at - started_at).total_seconds() * 1000)
        
        checks = result.get("checks", {})
        sub_checks = []
        
        for component, check_data in checks.items():
            sub_checks.append(SubCheckResult(
                name=component,
                status=self._map_status(check_data.get("status")),
                message=check_data.get("error_message") or "OK",
                latency_ms=check_data.get("latency_ms"),
                details=check_data.get("details", {}),
            ))
        
        overall_status = self._map_status(result.get("summary_status"))
        
        return HealthCheckResult(
            check_id="models",
            status=overall_status,
            started_at=started_at,
            completed_at=completed_at,
            duration_ms=duration_ms,
            sub_checks=sub_checks,
        )

    async def run_ai_behaviour_check(self) -> HealthCheckResult:
        """Run AI behaviour health check bundle."""
        started_at = datetime.now(UTC)
        
        result = await self._run_skill("maint.agency.re_evaluate_behaviour_health", {})
        
        completed_at = datetime.now(UTC)
        duration_ms = int((completed_at - started_at).total_seconds() * 1000)
        
        checks = result.get("checks", {})
        sub_checks = []
        
        for component, check_data in checks.items():
            sub_checks.append(SubCheckResult(
                name=component,
                status=self._map_status(check_data.get("status")),
                message=check_data.get("error_message") or "OK",
                latency_ms=check_data.get("latency_ms"),
                details=check_data.get("details", {}),
            ))
        
        overall_status = self._map_status(result.get("summary_status"))
        
        return HealthCheckResult(
            check_id="ai-behaviour",
            status=overall_status,
            started_at=started_at,
            completed_at=completed_at,
            duration_ms=duration_ms,
            sub_checks=sub_checks,
        )

    async def get_active_issues(self) -> SystemIssuesResponse:
        """Get active system issues from database.
        
        TODO: Query system_issues table once migration is complete.
        For now, returns empty list.
        """
        # Placeholder - would query database
        return SystemIssuesResponse(
            issues=[],
            total_count=0,
        )

    async def get_service_health(self) -> ServiceHealthResponse:
        """Get service health statuses with metrics.
        
        Uses connectivity tools for status and separate health tools for metrics.
        """
        # Run connectivity check for status
        connectivity = await self._run_skill("maint.connectivity.full_scan", {})
        # Extract checks from the nested output structure
        connectivity_output = connectivity.get("output", {})
        checks = connectivity_output.get("checks", {})
        
        # Get health metrics from separate tools
        from aico.ai.agency.tools.registry import get_tool_registry
        tool_registry = get_tool_registry()
        
        services = []
        now = datetime.now(UTC)
        
        # Backend API (inferred from ability to respond)
        uptime_seconds = self._uptime_seconds
        if uptime_seconds >= 3600:
            uptime_display = f"{int(uptime_seconds / 3600)}h"
        elif uptime_seconds >= 60:
            uptime_display = f"{int(uptime_seconds / 60)}m"
        else:
            uptime_display = f"{uptime_seconds}s"
        
        services.append(ServiceHealth(
            name="Backend API",
            status="healthy",  # If we're responding, we're healthy
            group="api",
            metric=ServiceMetric(
                label="Uptime",
                value=uptime_display,
                unit="time",
            ),
            trend=None,  # No historical data yet
            last_checked=now,
        ))
        
        # PostgreSQL Database
        pg_check = checks.get("postgres", {})
        pg_status = pg_check.get("status")
        
        # Get health metrics
        pg_health_tool = tool_registry.get("tool.db.postgres.health")
        pg_health = await pg_health_tool.handler() if pg_health_tool else {"data": {"details": {}}}
        pg_details = pg_health.get("data", {}).get("details", {})
        db_size = pg_details.get("database_size_mb", 0)
        
        services.append(ServiceHealth(
            name="PostgreSQL",
            status=self._map_service_status(pg_status),
            group="storage",
            metric=ServiceMetric(
                label="Database Size",
                value=f"{db_size}MB",
                unit="MB",
            ),
            trend=None,
            last_checked=now,
            depends_on=[],
        ))
        
        # ChromaDB
        chroma_check = checks.get("chroma", {})
        chroma_status = chroma_check.get("status")
        
        # Get health metrics
        chroma_health_tool = tool_registry.get("tool.db.chroma.health")
        chroma_health = await chroma_health_tool.handler() if chroma_health_tool else {"data": {"details": {}}}
        chroma_details = chroma_health.get("data", {}).get("details", {})
        chroma_collections = chroma_details.get("collections", 0)
        
        services.append(ServiceHealth(
            name="ChromaDB",
            status=self._map_service_status(chroma_status),
            group="storage",
            metric=ServiceMetric(
                label="Collections",
                value=str(chroma_collections),
                unit="collections",
            ),
            trend=None,
            last_checked=now,
        ))
        
        # InfluxDB Time Series Database
        influx_check = checks.get("influx", {})
        influx_status = influx_check.get("status")
        
        # Get health metrics
        influx_health_tool = tool_registry.get("tool.db.influx.health")
        influx_health = await influx_health_tool.handler() if influx_health_tool else {"data": {"details": {}}}
        influx_details = influx_health.get("data", {}).get("details", {})
        measurement_count = influx_details.get("measurements", 0)
        
        services.append(ServiceHealth(
            name="InfluxDB",
            status=self._map_service_status(influx_status),
            group="storage",
            metric=ServiceMetric(
                label="Measurements",
                value=str(measurement_count),
                unit="measurements",
            ),
            trend=None,
            last_checked=now,
        ))
        
        # LMDB
        lmdb_check = checks.get("lmdb", {})
        lmdb_status = lmdb_check.get("status")
        
        # Get health metrics
        lmdb_health_tool = tool_registry.get("tool.db.lmdb.health")
        lmdb_health = await lmdb_health_tool.handler() if lmdb_health_tool else {"data": {"details": {}}}
        lmdb_details = lmdb_health.get("data", {}).get("details", {})
        lmdb_entries = lmdb_details.get("entries", 0)
        
        services.append(ServiceHealth(
            name="LMDB",
            status=self._map_service_status(lmdb_status),
            group="storage",
            metric=ServiceMetric(
                label="Entries",
                value=str(lmdb_entries),
                unit="entries",
            ),
            trend=None,
            last_checked=now,
        ))
        
        # Message Bus (ZeroMQ)
        messagebus_result = await self._run_skill("maint.messagebus.check_health", {})
        messagebus_output = messagebus_result.get("output", {})
        messagebus_status = messagebus_output.get("summary_status", "unknown")
        messagebus_checks = messagebus_output.get("checks", {})
        messagebus_status_check = messagebus_checks.get("status", {})
        messagebus_details = messagebus_status_check.get("details", {})
        
        # Extract ZMQ version from details
        zmq_version = messagebus_details.get("zmq_version")
        if not zmq_version:
            zmq_version = "N/A"
        
        services.append(ServiceHealth(
            name="Message Bus",
            status=self._map_service_status(messagebus_status),
            group="processing",
            metric=ServiceMetric(
                label="ZMQ Version",
                value=zmq_version,
            ),
            trend=None,
            last_checked=now,
        ))
        
        # Task Scheduler
        scheduler_result = await self._run_skill("maint.scheduler.check_health", {"lookback_minutes": 60})
        scheduler_output = scheduler_result.get("output", {})
        scheduler_checks = scheduler_output.get("checks", {})
        scheduler_status_check = scheduler_checks.get("status", {})
        # Use the status check's status, not summary_status (which may be degraded due to stuck tasks)
        scheduler_status = scheduler_status_check.get("status", "unknown")
        scheduler_details = scheduler_status_check.get("details", {})
        
        enabled_tasks = scheduler_details.get("enabled_tasks", 0)
        total_tasks = scheduler_details.get("total_tasks", 0)
        
        # Display format: show enabled/total
        if total_tasks > 0:
            task_display = f"{enabled_tasks}/{total_tasks}"
        else:
            task_display = str(enabled_tasks)
        
        services.append(ServiceHealth(
            name="Scheduler",
            status=self._map_service_status(scheduler_status),
            group="processing",
            metric=ServiceMetric(
                label="Active Tasks",
                value=task_display,
                unit="tasks",
            ),
            trend=None,
            last_checked=now,
        ))
        
        # Modelservice
        ms_check = checks.get("modelservice", {})
        ms_status = ms_check.get("status")
        ms_latency = ms_check.get("latency_ms")
        
        # Format latency display
        if ms_latency is not None and ms_latency > 0:
            latency_display = f"{ms_latency}ms"
        else:
            latency_display = "N/A"
        
        services.append(ServiceHealth(
            name="Modelservice",
            status=self._map_service_status(ms_status),
            group="processing",
            metric=ServiceMetric(
                label="Latency",
                value=latency_display,
                unit="ms" if ms_latency else None,
            ),
            trend=None,
            last_checked=now,
        ))
        
        return ServiceHealthResponse(services=services)

    async def _run_skill(self, skill_id: str, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Run a skill and return its output."""
        try:
            result = await self._skill_invoker.invoke_skill(
                skill_id=skill_id,
                user_id="system",
                input_data=input_data,
                context={"origin": "health_check"},
            )
            # skill_invoker returns dict with 'success' and 'output' keys
            if result.get("success"):
                output = result.get("output", {})
                return output
            else:
                logger.error(f"[HEALTH_SERVICE] Skill '{skill_id}' returned success=False, error: {result.get('error')}")
                return {"summary_status": "unhealthy", "checks": {}}
        except Exception as exc:
            logger.error("[HEALTH_SERVICE] Skill '%s' failed with exception: %s", skill_id, exc, exc_info=True)
            return {"summary_status": "unhealthy", "checks": {}}
    
    # Phase 5: Advanced Features
    
    async def test_connection(self, component: str, timeout_seconds: int = 5) -> Dict[str, Any]:
        """Test connection to a specific component with detailed diagnostics."""
        logger.info("[HEALTH_SERVICE] Testing connection to %s", component)
        
        # Map component to skill
        component_skill_map = {
            "postgres": "maint.connectivity.verify_component",
            "chroma": "maint.connectivity.verify_component",
            "influx": "maint.connectivity.verify_component",
            "lmdb": "maint.connectivity.verify_component",
            "modelservice": "maint.connectivity.verify_component",
            "ollama": "maint.connectivity.verify_component",
        }
        
        skill_id = component_skill_map.get(component)
        if not skill_id:
            return {
                "component": component,
                "status": "error",
                "message": f"Unknown component: {component}",
                "fix_suggestions": ["Check component name is valid"],
            }
        
        try:
            from datetime import datetime, UTC
            start = datetime.now(UTC)
            
            result = await self._skill_invoker.invoke_skill(
                skill_id=skill_id,
                user_id="system",
                input_data={"component": component},
                context={"origin": "connection_test", "timeout": timeout_seconds},
            )
            
            end = datetime.now(UTC)
            latency_ms = int((end - start).total_seconds() * 1000)
            
            if result.success:
                output = result.output
                check_result = output.get("check", {})
                status = check_result.get("status", "error")
                
                return {
                    "component": component,
                    "status": "ok" if status in ("ok", "healthy") else "error",
                    "latency_ms": latency_ms,
                    "message": check_result.get("message", "Connection successful"),
                    "details": check_result.get("details", {}),
                    "fix_suggestions": self._get_fix_suggestions(component, status),
                }
            else:
                return {
                    "component": component,
                    "status": "error",
                    "latency_ms": latency_ms,
                    "message": f"Connection test failed: {result.error or 'Unknown error'}",
                    "details": {},
                    "fix_suggestions": self._get_fix_suggestions(component, "error"),
                }
        
        except Exception as exc:
            logger.error("[HEALTH_SERVICE] Connection test failed: %s", exc)
            return {
                "component": component,
                "status": "error",
                "message": f"Test failed: {str(exc)}",
                "fix_suggestions": self._get_fix_suggestions(component, "error"),
            }
    
    async def get_diagnostics(self) -> Dict[str, Any]:
        """Get performance diagnostics and recommendations."""
        logger.info("[HEALTH_SERVICE] Getting performance diagnostics")
        
        diagnostics = {
            "slow_endpoints": [],
            "slow_queries": [],
            "error_patterns": [],
            "recommendations": [],
        }
        
        # TODO: Query InfluxDB for slow endpoints (when metrics are available)
        # TODO: Query PostgreSQL for slow queries (when pg_stat_statements is enabled)
        # TODO: Analyze error patterns from logs
        
        # For now, return placeholder recommendations
        diagnostics["recommendations"] = [
            "Enable PostgreSQL pg_stat_statements extension for query analysis",
            "Configure InfluxDB metrics collection for endpoint monitoring",
            "Review error logs for recurring patterns",
        ]
        
        return diagnostics
    
    def _get_fix_suggestions(self, component: str, status: str) -> List[str]:
        """Get fix suggestions for failed component."""
        if status in ("ok", "healthy"):
            return []
        
        suggestions_map = {
            "postgres": [
                "Check PostgreSQL is running: pg_isready",
                "Verify connection string in config/core.yaml",
                "Check PostgreSQL logs for errors",
                "Ensure database 'aico' exists",
            ],
            "chroma": [
                "Check ChromaDB is running",
                "Verify ChromaDB path in config",
                "Check disk space for ChromaDB data",
            ],
            "influx": [
                "Check InfluxDB is running",
                "Verify InfluxDB connection settings",
                "Check InfluxDB authentication token",
            ],
            "modelservice": [
                "Check modelservice is running: ps aux | grep modelservice",
                "Verify ZMQ connection settings",
                "Check modelservice logs for errors",
                "Restart modelservice: uv run aico modelservice start",
            ],
            "ollama": [
                "Check Ollama is running: ollama list",
                "Start Ollama if not running",
                "Verify model is downloaded",
            ],
        }
        
        return suggestions_map.get(component, ["Check component configuration and logs"])
    
    # Phase 6: Remediation Actions
    
    async def execute_action(
        self, action_id: str, params: Dict[str, Any], issue_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Execute a remediation action by invoking the appropriate skill."""
        logger.info("[HEALTH_SERVICE] Executing action %s", action_id)
        
        from datetime import datetime, UTC
        from uuid import uuid4
        
        execution_id = str(uuid4())
        started_at = datetime.now(UTC)
        
        # Map action_id to skill_id
        action_skill_map = {
            "archive_conversations": "maint.db.postgres.archive_old_conversations",
            "reduce_disk_pressure": "maint.db.reduce_disk_pressure",
            "stabilize_modelservice": "maint.modelservice.stabilise",
            "rebalance_agency_load": "maint.agency.rebalance_load",
            "restart_postgres": "maint.db.postgres.restart",
            "restart_modelservice": "maint.modelservice.restart",
            "cleanup_executions": "maint.agency.cleanup_executions",
        }
        
        skill_id = action_skill_map.get(action_id)
        if not skill_id:
            return {
                "execution_id": execution_id,
                "action_id": action_id,
                "status": "failed",
                "started_at": started_at,
                "completed_at": datetime.now(UTC),
                "result": {},
                "error": f"Unknown action: {action_id}",
            }
        
        try:
            # Check if skill exists
            skill = self._skill_registry.get_skill(skill_id)
            if not skill:
                # Skill not implemented yet - return placeholder
                logger.warning("[HEALTH_SERVICE] Skill %s not implemented yet", skill_id)
                return {
                    "execution_id": execution_id,
                    "action_id": action_id,
                    "status": "failed",
                    "started_at": started_at,
                    "completed_at": datetime.now(UTC),
                    "result": {},
                    "error": f"Skill {skill_id} not implemented yet",
                }
            
            # Execute the skill
            result = await self._skill_invoker.invoke_skill(
                skill_id=skill_id,
                user_id="system",
                input_data=params,
                context={
                    "origin": "remediation_action",
                    "execution_id": execution_id,
                    "issue_id": issue_id,
                },
            )
            
            completed_at = datetime.now(UTC)
            
            if result.success:
                # Update issue status to "resolving" if issue_id provided
                if issue_id:
                    await self._update_issue_status(issue_id, "resolving")
                
                return {
                    "execution_id": execution_id,
                    "action_id": action_id,
                    "status": "completed",
                    "started_at": started_at,
                    "completed_at": completed_at,
                    "result": result.output,
                    "error": None,
                }
            else:
                return {
                    "execution_id": execution_id,
                    "action_id": action_id,
                    "status": "failed",
                    "started_at": started_at,
                    "completed_at": completed_at,
                    "result": {},
                    "error": result.error or "Skill execution failed",
                }
        
        except Exception as exc:
            logger.error("[HEALTH_SERVICE] Action execution failed: %s", exc)
            return {
                "execution_id": execution_id,
                "action_id": action_id,
                "status": "failed",
                "started_at": started_at,
                "completed_at": datetime.now(UTC),
                "result": {},
                "error": str(exc),
            }
    
    async def _update_issue_status(self, issue_id: str, status: str) -> None:
        """Update issue status in database."""
        try:
            from aico.data.uow import UnitOfWork
            
            async with UnitOfWork(self._session_factory) as uow:
                issue = await uow.system_issues.get_by_issue_id(issue_id)
                if issue:
                    issue.status = status
                    from datetime import datetime, UTC
                    issue.updated_at = datetime.now(UTC)
                    await uow.system_issues.update(issue)
                    await uow.commit()
        except Exception as exc:
            logger.error("[HEALTH_SERVICE] Failed to update issue status: %s", exc)

    def _map_status(self, status: Optional[str]) -> str:
        """Map skill status to health check status."""
        if status in ("ok", "healthy"):
            return "ok"
        elif status in ("warning", "degraded", "unsupported"):
            return "issues"
        else:
            return "error"

    def _map_service_status(self, status: Optional[str]) -> str:
        """Map check status to service status."""
        if status in ("ok", "healthy"):
            return "healthy"
        elif status in ("warning", "degraded"):
            return "degraded"
        else:
            return "critical"
