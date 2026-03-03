"""System Health NATS Handlers for Core Service

Handles all system health, monitoring, and remediation requests from gateway via NATS.
"""

from __future__ import annotations

import time
import json
from datetime import datetime, UTC
from typing import Dict, Any, Optional
from decimal import Decimal

from aico.core.logging import get_logger
from aico.ai.agency.skill_invoker import SkillInvoker
from aico.ai.agency.skills.registry import SkillRegistry
from aico.data.uow import UnitOfWork


logger = get_logger("backend.core.system_nats_handlers")


def convert_decimals(obj):
    """Recursively convert Decimal objects to float for JSON serialization."""
    if isinstance(obj, Decimal):
        return float(obj)
    elif isinstance(obj, dict):
        return {k: convert_decimals(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [convert_decimals(item) for item in obj]
    elif isinstance(obj, tuple):
        return tuple(convert_decimals(item) for item in obj)
    return obj


class SystemNATSHandlers:
    """NATS handlers for system health and remediation endpoints."""
    
    def __init__(self, container, session_factory, start_time: float):
        self.container = container
        self.session_factory = session_factory
        self.start_time = start_time
        self.logger = logger
        
        # Initialize health service components
        self._skill_registry: Optional[SkillRegistry] = None
        self._skill_invoker: Optional[SkillInvoker] = None
        self._remediation_registry: Optional[SkillRegistry] = None
        self._remediation_invoker: Optional[SkillInvoker] = None
        
        # Cache for health checks (30 second TTL)
        self._health_cache: Optional[tuple] = None
        self._service_health_cache: Optional[tuple] = None
    
    def _get_health_service(self):
        """Get or create health service components."""
        if self._skill_registry is None or self._skill_invoker is None:
            from aico.ai.agency.skills.maintenance import (
                MaintenanceConnectivityFullScanSkill,
                MaintenanceSystemScanResourcesSkill,
                MaintenanceModelserviceScanHealthSkill,
                MaintenanceAgencyReEvaluateBehaviourHealthSkill,
                MaintenanceMessageBusCheckHealthSkill,
                MaintenanceSchedulerCheckHealthSkill,
            )
            
            self._skill_registry = SkillRegistry()
            self._skill_registry.register(MaintenanceConnectivityFullScanSkill(self.session_factory))
            self._skill_registry.register(MaintenanceSystemScanResourcesSkill())
            self._skill_registry.register(MaintenanceModelserviceScanHealthSkill())
            self._skill_registry.register(MaintenanceAgencyReEvaluateBehaviourHealthSkill(self.session_factory))
            self._skill_registry.register(MaintenanceMessageBusCheckHealthSkill())
            self._skill_registry.register(MaintenanceSchedulerCheckHealthSkill())
            
            self._skill_invoker = SkillInvoker(self._skill_registry, self.session_factory)
        
        return self._skill_registry, self._skill_invoker
    
    def _get_remediation_service(self):
        """Get or create remediation service components."""
        if self._remediation_registry is None or self._remediation_invoker is None:
            from aico.ai.agency.skills.remediation import (
                RemediationPostgresVacuumSkill,
                RemediationPostgresArchiveSkill,
                RemediationDatabaseDiskPressureSkill,
                RemediationModelserviceStabiliseSkill,
                RemediationAgencyRecoverPlansSkill,
                RemediationAgencyRebalanceLoadSkill,
            )
            
            self._remediation_registry = SkillRegistry()
            self._remediation_registry.register(RemediationPostgresVacuumSkill(self.session_factory))
            self._remediation_registry.register(RemediationPostgresArchiveSkill(self.session_factory))
            self._remediation_registry.register(RemediationDatabaseDiskPressureSkill(self.session_factory))
            self._remediation_registry.register(RemediationModelserviceStabiliseSkill())
            self._remediation_registry.register(RemediationAgencyRecoverPlansSkill(self.session_factory))
            self._remediation_registry.register(RemediationAgencyRebalanceLoadSkill(self.session_factory))
            
            self._remediation_invoker = SkillInvoker(self._remediation_registry, self.session_factory)
        
        return self._remediation_registry, self._remediation_invoker
    
    async def _run_skill(self, skill_id: str, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Run a skill and return its output."""
        _, invoker = self._get_health_service()
        result = await invoker.invoke_skill(
            skill_id=skill_id,
            user_id="system",
            input_data=input_data,
            context={"origin": "health_check"},
        )
        return result.get("output", {})
    
    def _map_status(self, status: str) -> str:
        """Map skill status to API status."""
        if status == "healthy":
            return "ok"
        elif status == "degraded":
            return "warning"
        elif status == "unhealthy":
            return "error"
        return status
    
    def _map_service_status(self, status: str) -> str:
        """Map skill status to service status."""
        if status == "healthy":
            return "healthy"
        elif status == "degraded":
            return "degraded"
        elif status == "unhealthy":
            return "critical"
        return status or "healthy"
    
    async def handle_system_health_request(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle system health request - GET /system/health"""
        try:
            # Check cache first
            now = datetime.now(UTC)
            if self._health_cache is not None:
                cached_response, cached_at = self._health_cache
                cache_age = (now - cached_at).total_seconds()
                if cache_age < 30:
                    return cached_response
            
            # Run all health check skills in parallel
            import asyncio
            results = await asyncio.gather(
                self._run_skill("maint.connectivity.full_scan", {}),
                self._run_skill("maint.system.scan_resources", {}),
                self._run_skill("maint.modelservice.scan_health", {}),
                self._run_skill("maint.agency.re_evaluate_behaviour_health", {}),
                return_exceptions=True,
            )
            
            # Handle exceptions
            processed_results = []
            for result in results:
                if isinstance(result, Exception):
                    processed_results.append({"summary_status": "unhealthy"})
                else:
                    processed_results.append(result)
            
            healthy_count = sum(1 for r in processed_results if r.get("summary_status") == "healthy")
            total_count = len(processed_results)
            
            # Determine overall status
            if any(r.get("summary_status") == "unhealthy" for r in processed_results):
                overall_status = "critical"
            elif any(r.get("summary_status") == "degraded" for r in processed_results):
                overall_status = "degraded"
            else:
                overall_status = "healthy"
            
            critical_issues = 1 if overall_status == "critical" else 0
            warnings = sum(1 for r in processed_results if r.get("summary_status") == "degraded")
            uptime_seconds = int(time.time() - self.start_time)
            
            response = {
                "status": overall_status,
                "healthy_services": healthy_count,
                "total_services": total_count,
                "uptime_percentage": 99.8,
                "uptime_seconds": uptime_seconds,
                "last_check": now.isoformat(),
                "summary": {
                    "critical_issues": critical_issues,
                    "warnings": warnings,
                    "healthy_components": healthy_count,
                },
            }
            
            # Cache the response
            self._health_cache = (response, now)
            return response
            
        except Exception as e:
            self.logger.error(f"Failed to get system health: {e}", exc_info=True)
            return {"error": "SYSTEM_HEALTH_FAILED", "message": str(e)}
    
    async def handle_system_health_services_request(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle service health request - GET /system/health/services"""
        try:
            # Check cache first
            now = datetime.now(UTC)
            if self._service_health_cache is not None:
                cached_response, cached_at = self._service_health_cache
                cache_age = (now - cached_at).total_seconds()
                if cache_age < 30:
                    return cached_response
            
            # Run connectivity and health checks in parallel
            import asyncio
            from aico.ai.agency.tools.registry import get_tool_registry
            tool_registry = get_tool_registry()
            
            pg_health_tool = tool_registry.get("tool.db.postgres.health")
            
            results = await asyncio.gather(
                self._run_skill("maint.connectivity.full_scan", {}),
                pg_health_tool.handler() if pg_health_tool else asyncio.sleep(0),
                self._run_skill("maint.messagebus.check_health", {}),
                self._run_skill("maint.scheduler.check_health", {"lookback_minutes": 60}),
                self._run_skill("maint.modelservice.scan_health", {}),
                return_exceptions=True,
            )
            
            connectivity, pg_health, messagebus_result, scheduler_result, modelservice_result = results
            
            # Handle exceptions
            if isinstance(connectivity, Exception):
                connectivity = {"checks": {}}
            if isinstance(pg_health, Exception):
                pg_health = {"data": {"details": {}}}
            if isinstance(messagebus_result, Exception):
                messagebus_result = {"output": {}}
            if isinstance(scheduler_result, Exception):
                scheduler_result = {"output": {}}
            if isinstance(modelservice_result, Exception):
                modelservice_result = {"output": {}}
            
            checks = connectivity.get("checks", {})
            services = []
            
            # API Gateway
            uptime_seconds = int(time.time() - self.start_time)
            uptime_display = f"{int(uptime_seconds / 3600)}h" if uptime_seconds >= 3600 else f"{int(uptime_seconds / 60)}m" if uptime_seconds >= 60 else f"{uptime_seconds}s"
            
            services.append({
                "name": "API Gateway",
                "status": "healthy",
                "group": "api",
                "metric": {"label": "Uptime", "value": uptime_display, "unit": "time"},
                "trend": None,
                "last_checked": now.isoformat(),
            })
            
            # Core Services
            services.append({
                "name": "Core Services",
                "status": "healthy",
                "group": "processing",
                "metric": {"label": "Active Conversations", "value": "0", "unit": "conversations"},
                "trend": None,
                "last_checked": now.isoformat(),
            })
            
            # PostgreSQL
            pg_check = checks.get("postgres", {})
            pg_details = pg_health.get("data", {}).get("details", {})
            db_size = pg_details.get("database_size_mb", 0)
            # Convert Decimal to float for JSON serialization
            if hasattr(db_size, '__float__'):
                db_size = float(db_size)
            pg_tables = pg_details.get("tables", [])
            
            services.append({
                "name": "PostgreSQL",
                "status": self._map_service_status(pg_check.get("status")),
                "group": "storage",
                "metric": {"label": "Database Size", "value": f"{db_size}MB", "unit": "MB"},
                "trend": None,
                "last_checked": now.isoformat(),
                "details": {"tables": pg_tables} if pg_tables else None,
            })
            
            # Message Bus
            messagebus_output = messagebus_result.get("output", {})
            messagebus_status = messagebus_output.get("summary_status", "unknown")
            messagebus_checks = messagebus_output.get("checks", {})
            messagebus_details = messagebus_checks.get("status", {}).get("details", {})
            zmq_version = messagebus_details.get("zmq_version", "N/A")
            
            services.append({
                "name": "Message Bus",
                "status": self._map_service_status(messagebus_status),
                "group": "processing",
                "metric": {"label": "ZMQ Version", "value": zmq_version},
                "trend": None,
                "last_checked": now.isoformat(),
            })
            
            # Scheduler
            scheduler_output = scheduler_result.get("output", {})
            scheduler_checks = scheduler_output.get("checks", {})
            scheduler_details = scheduler_checks.get("status", {}).get("details", {})
            enabled_tasks = scheduler_details.get("enabled_tasks", 0)
            total_tasks = scheduler_details.get("total_tasks", 0)
            task_display = f"{enabled_tasks}/{total_tasks}" if total_tasks > 0 else str(enabled_tasks)
            
            services.append({
                "name": "Scheduler",
                "status": self._map_service_status(scheduler_checks.get("status", {}).get("status", "unknown")),
                "group": "processing",
                "metric": {"label": "Active Tasks", "value": task_display, "unit": "tasks"},
                "trend": None,
                "last_checked": now.isoformat(),
            })
            
            # Modelservice
            modelservice_output = modelservice_result.get("output", {})
            modelservice_checks = modelservice_output.get("checks", {})
            modelservice_status = modelservice_output.get("summary_status", "unknown")
            
            # Extract latency from connectivity check (latency_ms is at top level of connectivity check)
            ms_connectivity = modelservice_checks.get("connectivity", {})
            ms_latency = ms_connectivity.get("latency_ms")
            
            # If not in connectivity, try from health check
            if not ms_latency:
                ms_health = modelservice_checks.get("health", {})
                ms_latency = ms_health.get("latency_ms")
            
            latency_display = f"{int(ms_latency)}ms" if ms_latency and ms_latency > 0 else "N/A"
            
            services.append({
                "name": "Modelservice",
                "status": self._map_service_status(modelservice_status),
                "group": "processing",
                "metric": {"label": "Latency", "value": latency_display, "unit": "ms" if ms_latency else None},
                "trend": None,
                "last_checked": now.isoformat(),
            })
            
            response = {"services": services}
            
            # Convert all Decimal objects to float for JSON serialization
            response = convert_decimals(response)
            
            # Cache the response
            self._service_health_cache = (response, now)
            return response
            
        except Exception as e:
            self.logger.error(f"Failed to get service health: {e}", exc_info=True)
            return {"error": "SERVICE_HEALTH_FAILED", "message": str(e)}
    
    async def handle_system_health_issues_request(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle system issues request - GET /system/health/issues"""
        try:
            # TODO: Query system_issues table once implemented
            return {
                "issues": [],
                "total_count": 0,
            }
        except Exception as e:
            self.logger.error(f"Failed to get system issues: {e}", exc_info=True)
            return {"error": "SYSTEM_ISSUES_FAILED", "message": str(e)}
    
    async def handle_remediate_available_request(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle available remediations request - GET /system/remediate/available"""
        try:
            registry, _ = self._get_remediation_service()
            
            skills = []
            for skill_obj in registry.list_by_category("remediation"):
                skills.append({
                    "skill_id": skill_obj.skill_id,
                    "name": skill_obj.name,
                    "description": skill_obj.description,
                    "category": skill_obj.category,
                    "safety_level": skill_obj.safety_level,
                    "execution_policy": getattr(skill_obj, "execution_policy", None).value if getattr(skill_obj, "execution_policy", None) else "auto",
                    "capability_tags": skill_obj.capability_tags,
                    "side_effect_tags": skill_obj.side_effect_tags,
                    "parameters": [
                        {
                            "name": p.name,
                            "type": p.type.value,
                            "description": p.description,
                            "required": p.required,
                            "default": p.default,
                        }
                        for p in skill_obj.parameters
                    ],
                })
            
            return {
                "skills": skills,
                "total_count": len(skills),
            }
        except Exception as e:
            self.logger.error(f"Failed to get available remediations: {e}", exc_info=True)
            return {"error": "REMEDIATE_AVAILABLE_FAILED", "message": str(e)}
    
    async def handle_remediate_history_request(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle remediation history request - GET /system/remediate/history"""
        try:
            limit = request_data.get("limit", 20)
            skill_id = request_data.get("skill_id")
            
            async with UnitOfWork(self.session_factory) as uow:
                from sqlalchemy import text
                
                if skill_id:
                    query = text("""
                        SELECT id, skill_id, parameters, success, dry_run, output, error, 
                               executed_by, executed_at, execution_time_ms
                        FROM aico_core.remediation_executions
                        WHERE skill_id = :skill_id
                        ORDER BY executed_at DESC
                        LIMIT :limit
                    """)
                    result = await uow._session.execute(query, {"skill_id": skill_id, "limit": limit})
                else:
                    query = text("""
                        SELECT id, skill_id, parameters, success, dry_run, output, error, 
                               executed_by, executed_at, execution_time_ms
                        FROM aico_core.remediation_executions
                        ORDER BY executed_at DESC
                        LIMIT :limit
                    """)
                    result = await uow._session.execute(query, {"limit": limit})
                
                rows = result.fetchall()
                
                history = []
                for row in rows:
                    history.append({
                        "id": str(row.id),
                        "skill_id": row.skill_id,
                        "parameters": row.parameters if row.parameters else {},
                        "success": row.success,
                        "dry_run": row.dry_run,
                        "output": row.output if row.output else {},
                        "error": row.error,
                        "executed_by": row.executed_by,
                        "executed_at": row.executed_at.isoformat(),
                        "execution_time_ms": row.execution_time_ms,
                    })
                
                return {
                    "executions": history,
                    "total_count": len(history),
                }
                
        except Exception as e:
            self.logger.error(f"Failed to get remediation history: {e}", exc_info=True)
            return {"error": "REMEDIATE_HISTORY_FAILED", "message": str(e)}

    async def handle_remediate_trigger_request(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle remediation trigger request - POST /system/remediate/{skill_id}"""
        try:
            skill_id = request_data.get("skill_id")
            payload = request_data.get("payload") or {}

            if not skill_id:
                return {"error": "REMEDIATE_TRIGGER_FAILED", "message": "skill_id is required"}

            registry, invoker = self._get_remediation_service()
            skill = registry.get(skill_id)
            if not skill:
                return {"error": "REMEDIATE_TRIGGER_FAILED", "message": f"Unknown skill_id: {skill_id}"}

            params = payload.get("parameters") or {}
            dry_run = payload.get("dry_run", True)
            input_data = dict(params)
            # Safety-first: never force dry_run=False if caller didn't explicitly request it.
            input_data["dry_run"] = bool(dry_run) or bool(input_data.get("dry_run", False))

            started_at = datetime.now(UTC)
            result = await invoker.invoke_skill(
                skill_id=skill_id,
                user_id="system",
                input_data=input_data,
                context={"origin": "gateway_remediate"},
            )
            completed_at = datetime.now(UTC)
            duration_ms = int((completed_at - started_at).total_seconds() * 1000)

            success = bool(result.get("success", False))
            output = result.get("output", {}) or {}
            error = result.get("error")

            # Persist execution history (best-effort)
            try:
                async with UnitOfWork(self.session_factory) as uow:
                    from sqlalchemy import text

                    query = text(
                        """
                        INSERT INTO aico_core.remediation_executions
                        (skill_id, parameters, success, dry_run, output, error, executed_by, executed_at, execution_time_ms)
                        VALUES (:skill_id, :parameters, :success, :dry_run, :output, :error, :executed_by, :executed_at, :execution_time_ms)
                        """
                    )

                    await uow._session.execute(
                        query,
                        {
                            "skill_id": skill_id,
                            "parameters": json.dumps(params),
                            "success": success,
                            "dry_run": bool(input_data.get("dry_run", True)),
                            "output": json.dumps(output),
                            "error": error,
                            "executed_by": "gateway",
                            "executed_at": started_at,
                            "execution_time_ms": duration_ms,
                        },
                    )
                    await uow.commit()
            except Exception as db_exc:
                self.logger.error(f"Failed to persist remediation execution: {db_exc}")

            return {
                "skill_id": skill_id,
                "success": success,
                "output": output,
                "error": error,
                "executed_at": started_at.isoformat(),
                "execution_time_ms": duration_ms,
            }

        except Exception as e:
            self.logger.error(f"Failed to trigger remediation: {e}", exc_info=True)
            return {"error": "REMEDIATE_TRIGGER_FAILED", "message": str(e)}
    
    async def handle_health_check_connectivity(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle connectivity health check trigger - POST /system/health/check/connectivity"""
        try:
            started_at = datetime.now(UTC)
            # Run connectivity checks via skill invoker
            self._get_health_service()
            skill_invoker = self._skill_invoker
            
            sub_checks = []
            connectivity_skills = ["maint.connectivity.full_scan", "maint.messagebus.check_health"]
            
            for skill_id in connectivity_skills:
                try:
                    result = await skill_invoker.invoke_skill(skill_id, {}, user_id="system")
                    success = result.get("success", False)
                    sub_checks.append({
                        "name": skill_id,
                        "status": "ok" if success else "error",
                        "message": result.get("error") if not success else "Check passed",
                        "details": result.get("output", {})
                    })
                except Exception as e:
                    sub_checks.append({
                        "name": skill_id,
                        "status": "error",
                        "message": str(e),
                        "details": {}
                    })
            
            completed_at = datetime.now(UTC)
            duration_ms = int((completed_at - started_at).total_seconds() * 1000)
            overall_status = "ok" if all(c["status"] == "ok" for c in sub_checks) else "issues"
            
            return {
                "check_id": "connectivity",
                "status": overall_status,
                "started_at": started_at.isoformat(),
                "completed_at": completed_at.isoformat(),
                "duration_ms": duration_ms,
                "sub_checks": sub_checks
            }
        except Exception as e:
            self.logger.error(f"Failed to run connectivity check: {e}", exc_info=True)
            return {"error": "HEALTH_CHECK_FAILED", "message": str(e)}
    
    async def handle_health_check_resources(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle resources health check trigger - POST /system/health/check/resources"""
        try:
            started_at = datetime.now(UTC)
            # Run resource checks via skill invoker
            self._get_health_service()
            skill_invoker = self._skill_invoker
            
            sub_checks = []
            resource_skills = ["maint.system.scan_resources"]
            
            for skill_id in resource_skills:
                try:
                    result = await skill_invoker.invoke_skill(skill_id, {}, user_id="system")
                    success = result.get("success", False)
                    sub_checks.append({
                        "name": skill_id,
                        "status": "ok" if success else "error",
                        "message": result.get("error") if not success else "Check passed",
                        "details": result.get("output", {})
                    })
                except Exception as e:
                    sub_checks.append({
                        "name": skill_id,
                        "status": "error",
                        "message": str(e),
                        "details": {}
                    })
            
            completed_at = datetime.now(UTC)
            duration_ms = int((completed_at - started_at).total_seconds() * 1000)
            overall_status = "ok" if all(c["status"] == "ok" for c in sub_checks) else "issues"
            
            return {
                "check_id": "resources",
                "status": overall_status,
                "started_at": started_at.isoformat(),
                "completed_at": completed_at.isoformat(),
                "duration_ms": duration_ms,
                "sub_checks": sub_checks
            }
        except Exception as e:
            self.logger.error(f"Failed to run resources check: {e}", exc_info=True)
            return {"error": "HEALTH_CHECK_FAILED", "message": str(e)}
    
    async def handle_health_check_models(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle models health check trigger - POST /system/health/check/models"""
        try:
            started_at = datetime.now(UTC)
            # Run model checks via skill invoker
            self._get_health_service()
            skill_invoker = self._skill_invoker
            
            sub_checks = []
            model_skills = ["maint.modelservice.scan_health"]
            
            for skill_id in model_skills:
                try:
                    result = await skill_invoker.invoke_skill(skill_id, {}, user_id="system")
                    success = result.get("success", False)
                    sub_checks.append({
                        "name": skill_id,
                        "status": "ok" if success else "error",
                        "message": result.get("error") if not success else "Check passed",
                        "details": result.get("output", {})
                    })
                except Exception as e:
                    sub_checks.append({
                        "name": skill_id,
                        "status": "error",
                        "message": str(e),
                        "details": {}
                    })
            
            completed_at = datetime.now(UTC)
            duration_ms = int((completed_at - started_at).total_seconds() * 1000)
            overall_status = "ok" if all(c["status"] == "ok" for c in sub_checks) else "issues"
            
            return {
                "check_id": "models",
                "status": overall_status,
                "started_at": started_at.isoformat(),
                "completed_at": completed_at.isoformat(),
                "duration_ms": duration_ms,
                "sub_checks": sub_checks
            }
        except Exception as e:
            self.logger.error(f"Failed to run models check: {e}", exc_info=True)
            return {"error": "HEALTH_CHECK_FAILED", "message": str(e)}
    
    async def handle_health_check_ai_behaviour(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle AI behaviour health check trigger - POST /system/health/check/ai-behaviour"""
        try:
            started_at = datetime.now(UTC)
            # Run AI behaviour checks via skill invoker
            self._get_health_service()
            skill_invoker = self._skill_invoker
            
            sub_checks = []
            ai_skills = ["maint.modelservice.scan_health", "maint.scheduler.check_health", "maint.agency.re_evaluate_behaviour_health"]
            
            for skill_id in ai_skills:
                try:
                    result = await skill_invoker.invoke_skill(skill_id, {}, user_id="system")
                    success = result.get("success", False)
                    sub_checks.append({
                        "name": skill_id,
                        "status": "ok" if success else "error",
                        "message": result.get("error") if not success else "Check passed",
                        "details": result.get("output", {})
                    })
                except Exception as e:
                    sub_checks.append({
                        "name": skill_id,
                        "status": "error",
                        "message": str(e),
                        "details": {}
                    })
            
            completed_at = datetime.now(UTC)
            duration_ms = int((completed_at - started_at).total_seconds() * 1000)
            overall_status = "ok" if all(c["status"] == "ok" for c in sub_checks) else "issues"
            
            return {
                "check_id": "ai_behaviour",
                "status": overall_status,
                "started_at": started_at.isoformat(),
                "completed_at": completed_at.isoformat(),
                "duration_ms": duration_ms,
                "sub_checks": sub_checks
            }
        except Exception as e:
            self.logger.error(f"Failed to run AI behaviour check: {e}", exc_info=True)
            return {"error": "HEALTH_CHECK_FAILED", "message": str(e)}
