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


logger = get_logger("core.core.system_nats_handlers")


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
        return status or "unknown"

    def _explain_check(self, check: Dict[str, Any], default: str) -> str:
        if not isinstance(check, dict):
            return default
        details = check.get("details")
        error_message = check.get("error_message")
        latency_ms = check.get("latency_ms")
        if error_message:
            return str(error_message)
        if isinstance(details, dict):
            for key in ("message", "summary", "reason", "status_message"):
                value = details.get(key)
                if value:
                    return str(value)
            available_models = details.get("available_models")
            model_count = details.get("model_count")
            if isinstance(available_models, list) and available_models:
                return f"Available models: {', '.join(str(model) for model in available_models[:3])}"
            if isinstance(model_count, int) and model_count >= 0:
                return f"Modelservice responded with {model_count} available model{'s' if model_count != 1 else ''}."
        if latency_ms:
            return f"Last check latency {int(latency_ms)}ms"
        return default

    def _summarize_health_result(self, result: Dict[str, Any], fallback_name: str) -> Dict[str, str]:
        if not isinstance(result, dict):
            return {"component": fallback_name, "status": "unknown", "reason": "No diagnostic output returned."}
        component = str(result.get("component") or fallback_name)
        status = str(result.get("summary_status") or "unknown")
        checks = result.get("checks") if isinstance(result.get("checks"), dict) else {}
        for check_name, check_value in checks.items():
            mapped_status = str(check_value.get("status") or "unknown") if isinstance(check_value, dict) else "unknown"
            if mapped_status in {"error", "unhealthy", "warning", "unsupported"}:
                return {
                    "component": component,
                    "status": status,
                    "reason": self._explain_check(
                        check_value,
                        f"{component} check '{check_name}' reported status {mapped_status}.",
                    ),
                }
        return {
            "component": component,
            "status": status,
            "reason": f"{component} reported status {status}.",
        }

    def _summarize_service_health(self, service: Dict[str, Any]) -> Dict[str, str] | None:
        if not isinstance(service, dict):
            return None
        status = str(service.get("status") or "unknown")
        if status not in {"warning", "degraded", "critical", "error"}:
            return None
        details = service.get("details") if isinstance(service.get("details"), dict) else {}
        checks = details.get("checks") if isinstance(details.get("checks"), list) else []
        reason = None
        for check in checks:
            if not isinstance(check, dict):
                continue
            check_status = str(check.get("status") or "unknown")
            if check_status in {"warning", "degraded", "critical", "error", "unknown"}:
                reason = str(check.get("message") or "").strip() or None
                if reason:
                    break
        if not reason:
            reason = str(details.get("summary") or "").strip() or f"{service.get('name', 'Component')} reported status {status}."
        return {
            "name": str(service.get("name") or "Unknown"),
            "status": "critical" if status in {"critical", "error"} else "degraded",
            "reason": reason,
        }
    
    async def handle_system_health_request(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle system health request - GET /system/health"""
        try:
            # Check cache first
            now = datetime.now(UTC)
            if self._health_cache is not None:
                cached_response, cached_at = self._health_cache
                cache_age = (now - cached_at).total_seconds()
                if cache_age < 30:
                    self.logger.info(
                        "System health response served: source=cache, "
                        f"status={cached_response.get('status')}, healthy_services={cached_response.get('healthy_services')}, "
                        f"total_services={cached_response.get('total_services')}, cache_age_seconds={cache_age:.1f}"
                    )
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
            services_response = await self.handle_system_health_services_request({})
            services = services_response.get("services") if isinstance(services_response, dict) else []
            
            check_names = [
                "Connectivity Scan",
                "Resource Scan",
                "Models & Pipeline",
                "AI Behaviour Scan",
            ]

            # Handle exceptions
            processed_results = []
            degraded_components = []
            for index, result in enumerate(results):
                if isinstance(result, Exception):
                    processed = {
                        "component": check_names[index],
                        "summary_status": "unhealthy",
                        "checks": {},
                        "error_message": str(result),
                    }
                    processed_results.append(processed)
                    degraded_components.append({
                        "name": check_names[index],
                        "status": "critical",
                        "reason": str(result),
                    })
                else:
                    processed_results.append(result)
                    if result.get("summary_status") in {"degraded", "unhealthy"}:
                        summary = self._summarize_health_result(result, check_names[index])
                        degraded_components.append({
                            "name": summary["component"],
                            "status": self._map_service_status(summary["status"]),
                            "reason": summary["reason"],
                        })
            
            service_summaries = [
                summary
                for service in (services if isinstance(services, list) else [])
                for summary in [self._summarize_service_health(service)]
                if summary is not None
            ]
            if service_summaries:
                degraded_components = service_summaries

            if isinstance(services, list) and services:
                healthy_count = sum(1 for service in services if str(service.get("status")) in {"healthy", "ok"})
                total_count = len(services)
                critical_issues = sum(
                    1 for service in services if str(service.get("status")) in {"critical", "error"}
                )
                warnings = sum(
                    1 for service in services if str(service.get("status")) in {"warning", "degraded"}
                )
                if critical_issues > 0:
                    overall_status = "critical"
                elif warnings > 0:
                    overall_status = "degraded"
                else:
                    overall_status = "healthy"
            else:
                healthy_count = sum(1 for r in processed_results if r.get("summary_status") == "healthy")
                total_count = len(processed_results)

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
                "uptime_percentage": (healthy_count / total_count * 100.0) if total_count else 0.0,
                "uptime_seconds": uptime_seconds,
                "last_check": now.isoformat(),
                "summary": {
                    "critical_issues": critical_issues,
                    "warnings": warnings,
                    "healthy_components": healthy_count,
                    "affected_components": degraded_components,
                    "headline": (
                        "All monitored health checks are passing."
                        if not degraded_components
                        else f"{len(degraded_components)} health check(s) need attention."
                    ),
                },
            }
            
            # Cache the response
            self._health_cache = (response, now)
            self.logger.info(
                "System health response served: source=fresh, "
                f"status={response.get('status')}, healthy_services={response.get('healthy_services')}, "
                f"total_services={response.get('total_services')}"
            )
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
                    self.logger.info(
                        "System services health response served: source=cache, "
                        f"service_count={len(cached_response.get('services') or [])}, cache_age_seconds={cache_age:.1f}"
                    )
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
            connectivity_status = connectivity.get("summary_status")
            services = []
            
            modelservice_connectivity_check = checks.get("modelservice", {})
            api_gateway_status = "healthy"
            if isinstance(modelservice_connectivity_check, dict):
                modelservice_connectivity_status = modelservice_connectivity_check.get("status")
                if modelservice_connectivity_status in {"error", "unhealthy"}:
                    api_gateway_status = "degraded"
                elif modelservice_connectivity_status in {"warning", "unsupported"}:
                    api_gateway_status = "degraded"

            # API Gateway
            uptime_seconds = int(time.time() - self.start_time)
            uptime_display = f"{int(uptime_seconds / 3600)}h" if uptime_seconds >= 3600 else f"{int(uptime_seconds / 60)}m" if uptime_seconds >= 60 else f"{uptime_seconds}s"
            
            services.append({
                "name": "API Gateway",
                "status": self._map_service_status(api_gateway_status),
                "group": "api",
                "metric": {"label": "Uptime", "value": uptime_display, "unit": "time"},
                "trend": None,
                "last_checked": now.isoformat(),
                "dependencies": ["Core Services", "PostgreSQL", "Modelservice"],
                "details": {
                    "summary": (
                        "Gateway process reachable; downstream dependency issues may degrade request handling."
                        if api_gateway_status != "healthy"
                        else "Gateway process is healthy and serving API traffic."
                    ),
                    "checks": [
                        {
                            "name": "Modelservice connectivity",
                            "status": self._map_service_status(
                                "healthy" if modelservice_connectivity_check.get("status") == "ok" else "unhealthy" if modelservice_connectivity_check.get("status") == "error" else "degraded"
                            ) if isinstance(modelservice_connectivity_check, dict) and modelservice_connectivity_check.get("status") else "unknown",
                            "message": self._explain_check(
                                modelservice_connectivity_check,
                                "No downstream connectivity details were returned.",
                            ),
                        }
                    ],
                },
            })
            
            # Core Services
            core_check_statuses = []
            for result in (messagebus_result, scheduler_result, modelservice_result):
                if isinstance(result, dict):
                    summary_status = result.get("output", {}).get("summary_status")
                    if summary_status:
                        core_check_statuses.append(summary_status)

            healthy_core_checks = sum(1 for status in core_check_statuses if status == "healthy")
            if core_check_statuses:
                core_status = "healthy" if healthy_core_checks == len(core_check_statuses) else "degraded" if healthy_core_checks > 0 else "critical"
                core_metric_value = f"{healthy_core_checks}/{len(core_check_statuses)}"
            else:
                core_status = "unknown"
                core_metric_value = "unknown"

            services.append({
                "name": "Core Services",
                "status": core_status,
                "group": "processing",
                "metric": {"label": "Healthy Checks", "value": core_metric_value, "unit": "checks" if core_check_statuses else None},
                "trend": None,
                "last_checked": now.isoformat(),
                "dependencies": ["Message Bus", "Scheduler", "Modelservice"],
                "details": {
                    "summary": (
                        f"{healthy_core_checks} of {len(core_check_statuses)} core service checks are healthy."
                        if core_check_statuses
                        else "No core service health checks returned data."
                    ),
                    "checks": [
                        {
                            "name": "Message Bus",
                            "status": self._map_service_status(messagebus_result.get("output", {}).get("summary_status", "unknown")),
                            "message": self._explain_check(
                                messagebus_result.get("output", {}).get("checks", {}).get("status", {}),
                                "No message bus status details were returned.",
                            ),
                        },
                        {
                            "name": "Scheduler",
                            "status": self._map_service_status(scheduler_result.get("output", {}).get("summary_status", "unknown")),
                            "message": self._explain_check(
                                scheduler_result.get("output", {}).get("checks", {}).get("status", {}),
                                "No scheduler status details were returned.",
                            ),
                        },
                        {
                            "name": "Modelservice",
                            "status": self._map_service_status(modelservice_result.get("output", {}).get("summary_status", "unknown")),
                            "message": self._explain_check(
                                modelservice_result.get("output", {}).get("checks", {}).get("health", {})
                                or modelservice_result.get("output", {}).get("checks", {}).get("connectivity", {}),
                                "No modelservice health details were returned.",
                            ),
                        },
                    ],
                },
            })
            
            # PostgreSQL
            pg_check = checks.get("postgres", {})
            pg_details = pg_health.get("data", {}).get("details", {})
            db_size = pg_details.get("database_size_mb", 0)
            # Convert Decimal to float for JSON serialization
            if hasattr(db_size, '__float__'):
                db_size = float(db_size)
            pg_tables = pg_details.get("tables", [])
            
            pg_status = self._map_service_status(pg_check.get("status"))
            if pg_status == "unknown" and db_size:
                pg_status = "healthy"

            services.append({
                "name": "PostgreSQL",
                "status": pg_status,
                "group": "storage",
                "metric": {"label": "Database Size", "value": f"{db_size}MB", "unit": "MB"},
                "trend": None,
                "last_checked": now.isoformat(),
                "details": {
                    "summary": self._explain_check(pg_check, "Database size and table statistics loaded successfully."),
                    "tables": pg_tables,
                },
            })
            
            # Message Bus
            messagebus_output = messagebus_result.get("output", {})
            messagebus_status = messagebus_output.get("summary_status", "unknown")
            messagebus_checks = messagebus_output.get("checks", {})
            messagebus_details = messagebus_checks.get("status", {}).get("details", {})
            zmq_version = messagebus_details.get("zmq_version", "unknown")
            
            services.append({
                "name": "Message Bus",
                "status": self._map_service_status(messagebus_status),
                "group": "processing",
                "metric": {"label": "ZMQ Version", "value": zmq_version},
                "trend": None,
                "last_checked": now.isoformat(),
                "details": {
                    "summary": self._explain_check(
                        messagebus_checks.get("status", {}),
                        "Message bus status check completed.",
                    ),
                },
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
                "details": {
                    "summary": self._explain_check(
                        scheduler_checks.get("status", {}),
                        "Scheduler status check completed.",
                    ),
                    "jobs": scheduler_details.get("jobs") if isinstance(scheduler_details.get("jobs"), list) else [],
                },
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
            
            latency_display = f"{int(ms_latency)}ms" if ms_latency and ms_latency > 0 else "unknown"
            modelservice_summary_source = modelservice_checks.get("connectivity", {}) or modelservice_checks.get("health", {})
            modelservice_service_status = self._map_service_status(modelservice_status)
            if modelservice_service_status == "unknown" and ms_latency and ms_latency > 0:
                modelservice_service_status = "healthy"
            
            services.append({
                "name": "Modelservice",
                "status": modelservice_service_status,
                "group": "processing",
                "metric": {"label": "Latency", "value": latency_display, "unit": "ms" if ms_latency and ms_latency > 0 else None},
                "trend": None,
                "last_checked": now.isoformat(),
                "details": {
                    "summary": self._explain_check(
                        modelservice_summary_source,
                        "Modelservice scan completed.",
                    ),
                    "checks": [
                        {
                            "name": "Connectivity",
                            "status": self._map_service_status(
                                "healthy" if ms_connectivity.get("status") == "ok" else "unhealthy" if ms_connectivity.get("status") == "error" else "degraded"
                            ) if ms_connectivity.get("status") else "unknown",
                            "message": self._explain_check(ms_connectivity, "No connectivity details were returned."),
                        },
                        {
                            "name": "Health",
                            "status": self._map_service_status(
                                "healthy" if modelservice_checks.get("health", {}).get("status") == "ok" else "unhealthy" if modelservice_checks.get("health", {}).get("status") == "error" else "degraded"
                            ) if modelservice_checks.get("health", {}).get("status") else "unknown",
                            "message": self._explain_check(
                                modelservice_checks.get("health", {}),
                                "No model health details were returned.",
                            ),
                        },
                    ],
                },
            })
            
            response = {"services": services}
            
            # Convert all Decimal objects to float for JSON serialization
            response = convert_decimals(response)
            
            # Cache the response
            self._service_health_cache = (response, now)
            service_count = len(response.get("services") or [])
            healthy_count = len([service for service in (response.get("services") or []) if service.get("status") == "healthy"])
            degraded_count = len([service for service in (response.get("services") or []) if service.get("status") in {"degraded", "warning"}])
            unhealthy_count = len([service for service in (response.get("services") or []) if service.get("status") in {"critical", "unhealthy"}])
            self.logger.info(
                "System services health response served: source=fresh, "
                f"service_count={service_count}, healthy={healthy_count}, "
                f"degraded={degraded_count}, unhealthy={unhealthy_count}"
            )
            return response
            
        except Exception as e:
            self.logger.error(f"Failed to get service health: {e}", exc_info=True)
            return {"error": "SERVICE_HEALTH_FAILED", "message": str(e)}
    
    async def handle_system_health_issues_request(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle system issues request - GET /system/health/issues"""
        try:
            service = request_data.get("service")
            severity = request_data.get("severity")

            async with UnitOfWork(self.session_factory) as uow:
                issues = await uow.system_issues.list_active(service=service, severity=severity)

            response = {
                "issues": [issue.to_dict() for issue in issues],
                "total_count": len(issues),
            }

            self.logger.info(
                "System issues response served: "
                f"service_filter={service or 'all'}, severity_filter={severity or 'all'}, total_count={len(issues)}"
            )
            return convert_decimals(response)
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
