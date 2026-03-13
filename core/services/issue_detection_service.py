"""Issue Detection Service

Monitors system health and automatically detects, creates, and resolves issues.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, UTC, timedelta
from typing import Dict, Any, List, Optional
from uuid import uuid4

from aico.core.logging import get_logger
from aico.core.config import ConfigurationManager
from aico.data.uow import UnitOfWork
from aico.data.models.system_health import SystemIssue
from aico.ai.agency.skill_invoker import SkillInvoker
from aico.ai.agency.skills.registry import SkillRegistry


logger = get_logger("core.services.issue_detection")


class IssueDetectionService:
    """Service for detecting and managing system issues based on health checks."""

    def __init__(
        self,
        config: ConfigurationManager,
        session_factory: Any,
        skill_registry: SkillRegistry,
    ):
        self._config = config
        self._session_factory = session_factory
        self._skill_registry = skill_registry
        self._skill_invoker = SkillInvoker(skill_registry, session_factory)
        
        # Thresholds from config or defaults
        self._thresholds = {
            "cpu_percent": config.get("system.health.thresholds.cpu_percent", 80),
            "memory_percent": config.get("system.health.thresholds.memory_percent", 85),
            "disk_percent": config.get("system.health.thresholds.disk_percent", 90),
            "stalled_plan_hours": config.get("system.health.thresholds.stalled_plan_hours", 1),
        }
        
        logger.debug(
            "[ISSUE_DETECTION] Initialized with thresholds: %s",
            self._thresholds
        )

    async def run_detection_cycle(self) -> Dict[str, Any]:
        """Run a complete issue detection cycle.
        
        Returns summary of detected and resolved issues.
        """
        logger.debug("[ISSUE_DETECTION] Starting detection cycle")
        
        detected_issues = []
        resolved_issues = []
        healing = {
            "enabled": bool(self._config.get("system.self_healing.enabled", False)),
            "triggered": False,
            "goals_created": 0,
            "executions_started": 0,
            "error": None,
        }
        
        try:
            # Optional deterministic simulated issue injection for end-to-end tests.
            # This is explicitly config-guarded and must never be enabled unintentionally.
            simulation_enabled = bool(
                self._config.get("system.self_healing.simulation.enabled", False)
            )
            simulation_issue_id = self._config.get(
                "system.self_healing.simulation.issue_id",
                "simulated_self_heal_noop",
            )
            simulation_persist_issue = bool(
                self._config.get("system.self_healing.simulation.persist_issue", False)
            )

            # Run all health checks
            connectivity_issues = await self._check_connectivity()
            resource_issues = await self._check_resources()
            modelservice_issues = await self._check_modelservice()
            agency_issues = await self._check_agency_behaviour()
            
            detected_issues.extend(connectivity_issues)
            detected_issues.extend(resource_issues)
            detected_issues.extend(modelservice_issues)
            detected_issues.extend(agency_issues)

            if simulation_enabled:
                detected_issues.append(
                    {
                        "issue_id": simulation_issue_id,
                        "severity": "info",
                        "service": "SelfHealingSimulation",
                        "title": "SIMULATED: End-to-end self-healing test issue",
                        "detected_at": datetime.now(UTC),
                        "metrics": {"simulated": True},
                        "impact": {
                            "description": "Simulated issue for deterministic testing",
                            "affected_features": [],
                        },
                        "remediation": [
                            {
                                "action_id": "test_noop_remediation",
                                "label": "SIMULATED: No-op remediation",
                                "impact": "No-op (deterministic test)",
                            }
                        ],
                        "simulated": True,
                    }
                )
                logger.warning(
                    "[ISSUE_DETECTION] Injected SIMULATED issue issue_id=%s (persist=%s)",
                    simulation_issue_id,
                    simulation_persist_issue,
                )
            
            # Create issues in database
            async with UnitOfWork(self._session_factory) as uow:
                for issue_data in detected_issues:
                    if issue_data.get("simulated") and not simulation_persist_issue:
                        continue
                    await self._create_or_update_issue(uow, issue_data)
                
                # Check for resolved issues
                resolved = await self._check_resolved_issues(uow)
                resolved_issues.extend(resolved)
                
                await uow.commit()

            # Optionally trigger autonomous self-healing via agency goal/intention/plan flow.
            # This is intentionally disabled by default and must be enabled in config.
            if healing["enabled"] and detected_issues:
                try:
                    healing_result = await self._trigger_self_healing(detected_issues)
                    healing.update(healing_result)
                except Exception as exc:  # pragma: no cover - defensive
                    healing["error"] = str(exc)
                    logger.error("[ISSUE_DETECTION] Self-healing trigger failed: %s", exc, exc_info=True)
            
            logger.debug(
                "[ISSUE_DETECTION] Cycle complete: %d detected, %d resolved",
                len(detected_issues),
                len(resolved_issues)
            )
            
            return {
                "detected_count": len(detected_issues),
                "resolved_count": len(resolved_issues),
                "detected_issues": [i["issue_id"] for i in detected_issues],
                "resolved_issues": resolved_issues,
                "self_healing": healing,
            }
            
        except Exception as exc:
            logger.error("[ISSUE_DETECTION] Detection cycle failed: %s", exc)
            return {
                "detected_count": 0,
                "resolved_count": 0,
                "error": str(exc),
                "self_healing": healing,
            }

    async def _trigger_self_healing(self, detected_issues: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Convert detected issues into system_maintenance goals and run agency flow.

        This is the missing glue between System Health detection and the Agency
        loop described in docs (maintenance goal → intention → plan → skill execution).

        Behavior:
        - Creates/updates maintenance goals for user_id='system_user'
        - Stores remediation/verification intent in goal metadata
        - Triggers arbiter intention-set update immediately
        - Optionally executes the resulting plan immediately (for end-to-end proof)
        """

        from aico.ai import ai_registry

        agency_engine = ai_registry.get("agency")
        if not agency_engine:
            raise RuntimeError("AgencyEngine not available in ai_registry")

        user_id = "system_user"
        run_immediately = bool(self._config.get("system.self_healing.run_immediately", True))
        allow_side_effects = bool(self._config.get("system.self_healing.allow_side_effects", False))

        goals_created = 0
        executions_started = 0

        for issue in detected_issues:
            remediation_actions = issue.get("remediation") or []
            if not remediation_actions:
                continue

            # For now we take the first remediation action from IssueDetectionService.
            # Future: choose via policy/risk scoring and past success rates.
            action_id = remediation_actions[0].get("action_id")
            if not action_id:
                continue

            remediation_skill_id = self._map_action_id_to_skill_id(action_id)
            if not remediation_skill_id:
                continue

            remediation_skill = self._skill_registry.get(remediation_skill_id)
            remediation_policy_value = None
            if remediation_skill is not None:
                remediation_policy = getattr(remediation_skill, "execution_policy", None)
                remediation_policy_value = (
                    getattr(remediation_policy, "value", None) if remediation_policy is not None else None
                )

            goal_title = f"Self-heal: {issue.get('title') or issue.get('issue_id')}"
            goal_description = (
                f"Autonomously remediate detected system issue '{issue.get('issue_id')}'. "
                f"Action: {action_id} → Skill: {remediation_skill_id}."
            )

            # Safety-first: autonomous self-healing defaults to dry-run.
            remediation_params: Dict[str, Any] = {"dry_run": (not allow_side_effects)}

            # Verification defaults: re-run connectivity scan.
            verify_skill_id = "maint.connectivity.full_scan"
            verify_params: Dict[str, Any] = {}

            _, _ = await agency_engine.create_maintenance_goal_with_optional_plan(
                user_id=user_id,
                title=goal_title,
                description=goal_description,
                goal_type="maintenance",
                metadata={
                    "issue_id": issue.get("issue_id"),
                    "severity": issue.get("severity"),
                    "service": issue.get("service"),
                    "remediation_action_id": action_id,
                    "remediation_skill_id": remediation_skill_id,
                    "remediation_execution_policy": remediation_policy_value,
                    "remediation_params": remediation_params,
                    "verify_skill_id": verify_skill_id,
                    "verify_params": verify_params,
                    "origin": "issue_detection",
                },
                auto_plan=False,
            )
            goals_created += 1

        if goals_created == 0:
            return {
                "triggered": False,
                "goals_created": 0,
                "executions_started": 0,
            }

        # Trigger arbiter now (instead of waiting up to 5 minutes).
        intention_set = await agency_engine.update_intention_set_for_user(
            user_id=user_id,
            context={
                "trigger": "issue_detection_self_healing",
                "timestamp": datetime.now(UTC).isoformat(),
            },
        )

        # Optionally execute immediately to prove end-to-end behavior.
        # IMPORTANT: only AUTO policy skills may be executed without explicit user consent.
        if run_immediately:
            # For any active intention, start plan execution if not already running.
            for intention in intention_set.active_intentions:
                plans = await agency_engine.agency_service.list_plans(goal_id=intention.goal_id)
                if not plans:
                    continue
                plan = plans[0]

                goal = await agency_engine.agency_service.get_goal(intention.goal_id)
                remediation_skill_id = None
                remediation_policy_value = None
                if goal is not None:
                    remediation_skill_id = (goal.metadata or {}).get("remediation_skill_id")
                    remediation_policy_value = (goal.metadata or {}).get("remediation_execution_policy")

                # Default to "needs_user_consent" if unknown.
                if remediation_policy_value != "auto":
                    logger.info(
                        "[ISSUE_DETECTION] Deferring self-healing execution for goal %s: remediation_skill_id=%s policy=%s",
                        intention.goal_id,
                        remediation_skill_id,
                        remediation_policy_value,
                    )
                    continue

                # Skip if an execution is already pending/running.
                existing = await agency_engine.agency_service.get_plan_executions(plan.plan_id)
                has_active_exec = any(
                    getattr(e, "status", None) in ("pending", "running")
                    for e in existing
                )
                if has_active_exec:
                    continue

                execution = await agency_engine.executor.start_execution(
                    plan_id=plan.plan_id,
                    goal_id=plan.goal_id,
                    user_id=user_id,
                    context={
                        "trigger": "issue_detection_self_healing",
                        "timestamp": datetime.now(UTC).isoformat(),
                    },
                )
                executions_started += 1

                # Execute steps synchronously (bounded) so detection cycle can report outcome.
                max_steps = int(self._config.get("system.self_healing.max_steps_per_goal", 10))
                steps_run = 0
                while steps_run < max_steps:
                    has_more, _ = await agency_engine.executor.execute_next_step(execution.execution_id)
                    steps_run += 1
                    if not has_more:
                        break

        return {
            "triggered": True,
            "goals_created": goals_created,
            "executions_started": executions_started,
        }

    def _map_action_id_to_skill_id(self, action_id: str) -> Optional[str]:
        """Map an issue remediation action_id to a concrete maintenance skill.

        This keeps IssueDetectionService agnostic of how skills are implemented,
        while still producing deterministic plans.
        """

        mapping = {
            "stabilize_modelservice": "maint.modelservice.stabilise",
            "restart_modelservice": "maint.modelservice.stabilise",
            "archive_conversations": "maint.db.reduce_disk_pressure",
            "reduce_disk_pressure": "maint.db.reduce_disk_pressure",
            "rebalance_agency_load": "maint.agency.rebalance_load",
            "test_noop_remediation": "maint.test.noop_remediation",
        }
        return mapping.get(action_id)

    async def _check_connectivity(self) -> List[Dict[str, Any]]:
        """Check connectivity and detect issues."""
        issues = []
        
        try:
            result = await self._skill_invoker.invoke_skill(
                skill_id="maint.connectivity.full_scan",
                user_id="system",
                input_data={},
                context={"origin": "issue_detection"},
            )
            
            if not result.get("success"):
                return issues
            
            checks = result.get("output", {}).get("checks", {})
            
            for component, check_data in checks.items():
                status = check_data.get("status")
                if status in ("error", "unhealthy"):
                    issues.append({
                        "issue_id": f"connectivity_{component}_{datetime.now(UTC).strftime('%Y%m%d')}",
                        "severity": "error",
                        "service": component.capitalize(),
                        "title": f"{component.capitalize()} Connectivity Failure",
                        "detected_at": datetime.now(UTC),
                        "metrics": {
                            "status": status,
                            "latency_ms": check_data.get("latency_ms"),
                            "error_message": check_data.get("error_message"),
                        },
                        "impact": {
                            "description": f"{component} is not accessible",
                            "affected_features": self._get_affected_features(component),
                        },
                        "remediation": self._get_connectivity_remediation(component),
                    })
        
        except Exception as exc:
            logger.error("[ISSUE_DETECTION] Connectivity check failed: %s", exc)
        
        return issues

    async def _check_resources(self) -> List[Dict[str, Any]]:
        """Check system resources and detect threshold violations."""
        issues = []
        
        try:
            result = await self._skill_invoker.invoke_skill(
                skill_id="maint.system.scan_resources",
                user_id="system",
                input_data={"thresholds": self._thresholds},
                context={"origin": "issue_detection"},
            )
            
            if not result.get("success"):
                return issues
            
            output = result.get("output", {})
            checks = output.get("checks", {})
            violations = output.get("threshold_violations", [])
            
            for resource in violations:
                check_data = checks.get(resource, {})
                details = check_data.get("details", {})
                
                if resource == "cpu":
                    cpu_percent = details.get("cpu_percent", 0)
                    issues.append({
                        "issue_id": f"resource_cpu_{datetime.now(UTC).strftime('%Y%m%d')}",
                        "severity": "warning" if cpu_percent < 90 else "error",
                        "service": "System",
                        "title": f"High CPU Usage ({cpu_percent:.1f}%)",
                        "detected_at": datetime.now(UTC),
                        "metrics": {
                            "cpu_percent": cpu_percent,
                            "threshold": self._thresholds["cpu_percent"],
                            "load_avg_1min": details.get("load_avg_1min"),
                        },
                        "impact": {
                            "description": "System performance degradation",
                            "time_to_critical": self._estimate_time_to_critical(cpu_percent, 100),
                        },
                        "remediation": [
                            {
                                "action_id": "inspect_cpu_workloads",
                                "label": "Inspect CPU Workloads",
                                "impact": "Identify high-CPU processes",
                            }
                        ],
                    })
                
                elif resource == "memory":
                    memory_percent = details.get("percent", 0)
                    issues.append({
                        "issue_id": f"resource_memory_{datetime.now(UTC).strftime('%Y%m%d')}",
                        "severity": "warning" if memory_percent < 95 else "critical",
                        "service": "System",
                        "title": f"High Memory Usage ({memory_percent:.1f}%)",
                        "detected_at": datetime.now(UTC),
                        "metrics": {
                            "memory_percent": memory_percent,
                            "threshold": self._thresholds["memory_percent"],
                            "used_bytes": details.get("used_bytes"),
                            "total_bytes": details.get("total_bytes"),
                        },
                        "impact": {
                            "description": "Risk of OOM errors",
                            "time_to_critical": self._estimate_time_to_critical(memory_percent, 100),
                        },
                        "remediation": [
                            {
                                "action_id": "reduce_memory_pressure",
                                "label": "Reduce Memory Pressure",
                                "impact": "Free up memory",
                            }
                        ],
                    })
                
                elif resource == "disk":
                    disk_percent = details.get("percent", 0)
                    issues.append({
                        "issue_id": f"resource_disk_{datetime.now(UTC).strftime('%Y%m%d')}",
                        "severity": "warning" if disk_percent < 95 else "critical",
                        "service": "Database",
                        "title": f"Low Disk Space ({disk_percent:.1f}% used)",
                        "detected_at": datetime.now(UTC),
                        "metrics": {
                            "disk_percent": disk_percent,
                            "threshold": self._thresholds["disk_percent"],
                            "used_bytes": details.get("used_bytes"),
                            "free_bytes": details.get("free_bytes"),
                        },
                        "impact": {
                            "description": "Database writes may fail",
                            "time_to_critical": self._estimate_time_to_critical(disk_percent, 100),
                        },
                        "remediation": [
                            {
                                "action_id": "archive_conversations",
                                "label": "Archive Old Conversations",
                                "impact": "Free ~500MB disk space",
                            }
                        ],
                    })
        
        except Exception as exc:
            logger.error("[ISSUE_DETECTION] Resource check failed: %s", exc)
        
        return issues

    async def _check_modelservice(self) -> List[Dict[str, Any]]:
        """Check modelservice health."""
        issues = []
        
        try:
            result = await self._skill_invoker.invoke_skill(
                skill_id="maint.modelservice.scan_health",
                user_id="system",
                input_data={"test_inference": True},
                context={"origin": "issue_detection"},
            )
            
            if not result.get("success"):
                return issues
            
            checks = result.get("output", {}).get("checks", {})
            
            # Check connectivity
            connectivity = checks.get("connectivity", {})
            if connectivity.get("status") in ("error", "unhealthy"):
                issues.append({
                    "issue_id": f"modelservice_connectivity_{datetime.now(UTC).strftime('%Y%m%d')}",
                    "severity": "error",
                    "service": "Modelservice",
                    "title": "Modelservice Connectivity Failure",
                    "detected_at": datetime.now(UTC),
                    "metrics": connectivity,
                    "impact": {
                        "description": "AI features unavailable",
                        "affected_features": ["conversation", "embeddings", "agency"],
                    },
                    "remediation": [
                        {
                            "action_id": "restart_modelservice",
                            "label": "Restart Modelservice",
                            "impact": "Restore AI functionality",
                        }
                    ],
                })
            
            # Check inference
            inference = checks.get("inference", {})
            if inference.get("status") in ("error", "unhealthy"):
                issues.append({
                    "issue_id": f"modelservice_inference_{datetime.now(UTC).strftime('%Y%m%d')}",
                    "severity": "error",
                    "service": "Modelservice",
                    "title": "Modelservice Inference Failure",
                    "detected_at": datetime.now(UTC),
                    "metrics": inference,
                    "impact": {
                        "description": "AI responses unavailable",
                        "affected_features": ["conversation", "planning"],
                    },
                    "remediation": [
                        {
                            "action_id": "stabilize_modelservice",
                            "label": "Stabilize Modelservice",
                            "impact": "Restore inference pipeline",
                        }
                    ],
                })
        
        except Exception as exc:
            logger.error("[ISSUE_DETECTION] Modelservice check failed: %s", exc)
        
        return issues

    async def _check_agency_behaviour(self) -> List[Dict[str, Any]]:
        """Check agency behaviour for anomalies."""
        issues = []
        
        try:
            result = await self._skill_invoker.invoke_skill(
                skill_id="maint.agency.re_evaluate_behaviour_health",
                user_id="system",
                input_data={"check_plans": True},
                context={"origin": "issue_detection"},
            )
            
            if not result.get("success"):
                return issues
            
            checks = result.get("output", {}).get("checks", {})
            
            # Check for stalled plans
            stalled_plans = checks.get("stalled_plans", {})
            stalled_count = stalled_plans.get("details", {}).get("stalled_count", 0)
            
            if stalled_count > 0:
                issues.append({
                    "issue_id": f"agency_stalled_plans_{datetime.now(UTC).strftime('%Y%m%d')}",
                    "severity": "warning",
                    "service": "Agency",
                    "title": f"{stalled_count} Stalled Plan(s) Detected",
                    "detected_at": datetime.now(UTC),
                    "metrics": {
                        "stalled_count": stalled_count,
                        "threshold_hours": self._thresholds["stalled_plan_hours"],
                        "stalled_plans": stalled_plans.get("details", {}).get("stalled_plans", []),
                    },
                    "impact": {
                        "description": "Goals not progressing",
                        "affected_features": ["goal_execution", "planning"],
                    },
                    "remediation": [
                        {
                            "action_id": "rebalance_agency_load",
                            "label": "Rebalance Agency Load",
                            "impact": "Unstall plans",
                        }
                    ],
                })
        
        except Exception as exc:
            logger.error("[ISSUE_DETECTION] Agency check failed: %s", exc)
        
        return issues

    async def _create_or_update_issue(
        self, uow: UnitOfWork, issue_data: Dict[str, Any]
    ) -> None:
        """Create a new issue or update existing one."""
        issue_id = issue_data["issue_id"]
        
        # Check if issue already exists
        existing = await uow.system_issues.get_by_issue_id(issue_id)
        
        if existing and existing.status == "active":
            # Update metrics
            existing.metrics = issue_data.get("metrics")
            existing.updated_at = datetime.now(UTC)
            await uow.system_issues.update(existing)
            logger.debug("[ISSUE_DETECTION] Updated existing issue: %s", issue_id)
        elif not existing:
            # Create new issue
            issue = SystemIssue(
                issue_id=issue_id,
                severity=issue_data["severity"],
                service=issue_data["service"],
                title=issue_data["title"],
                detected_at=issue_data["detected_at"],
                status="active",
                metrics=issue_data.get("metrics"),
                impact=issue_data.get("impact"),
                remediation=issue_data.get("remediation"),
            )
            await uow.system_issues.create(issue)
            logger.info("[ISSUE_DETECTION] Created new issue: %s", issue_id)

    async def _check_resolved_issues(self, uow: UnitOfWork) -> List[str]:
        """Check if any active issues have been resolved."""
        resolved = []
        
        active_issues = await uow.system_issues.list_active()
        
        for issue in active_issues:
            # Check if the condition that caused the issue is now resolved
            is_resolved = await self._is_issue_resolved(issue)
            
            if is_resolved:
                await uow.system_issues.resolve(issue.issue_id)
                resolved.append(issue.issue_id)
                logger.info("[ISSUE_DETECTION] Resolved issue: %s", issue.issue_id)
        
        return resolved

    async def _is_issue_resolved(self, issue: SystemIssue) -> bool:
        """Check if an issue's conditions have been resolved."""
        # For resource issues, re-run the check and see if threshold is no longer exceeded
        if issue.issue_id.startswith("resource_"):
            try:
                result = await self._skill_invoker.invoke_skill(
                    skill_id="maint.system.scan_resources",
                    user_id="system",
                    input_data={"thresholds": self._thresholds},
                    context={"origin": "issue_resolution_check"},
                )
                
                if result.get("success"):
                    violations = result.get("output", {}).get("threshold_violations", [])
                    
                    # Check if the specific resource is still in violation
                    if "cpu" in issue.issue_id and "cpu" not in violations:
                        return True
                    if "memory" in issue.issue_id and "memory" not in violations:
                        return True
                    if "disk" in issue.issue_id and "disk" not in violations:
                        return True
            except Exception as exc:
                logger.error("[ISSUE_DETECTION] Resolution check failed: %s", exc)
        
        # For connectivity issues, check if component is now reachable
        elif issue.issue_id.startswith("connectivity_"):
            try:
                result = await self._skill_invoker.invoke_skill(
                    skill_id="maint.connectivity.full_scan",
                    user_id="system",
                    input_data={},
                    context={"origin": "issue_resolution_check"},
                )
                
                if result.get("success"):
                    checks = result.get("output", {}).get("checks", {})
                    for component, check_data in checks.items():
                        if component in issue.issue_id:
                            if check_data.get("status") in ("ok", "healthy"):
                                return True
            except Exception as exc:
                logger.error("[ISSUE_DETECTION] Resolution check failed: %s", exc)
        
        return False

    def _get_affected_features(self, component: str) -> List[str]:
        """Get list of features affected by component failure."""
        feature_map = {
            "postgres": ["conversation", "memory", "agency", "user_data"],
            "chroma": ["semantic_search", "memory"],
            "influx": ["metrics", "monitoring"],
            "lmdb": ["working_memory"],
            "modelservice": ["conversation", "embeddings", "agency"],
            "ollama": ["conversation", "llm_features"],
        }
        return feature_map.get(component, ["unknown"])

    def _get_connectivity_remediation(self, component: str) -> List[Dict[str, str]]:
        """Get remediation actions for connectivity issues."""
        remediation_map = {
            "postgres": [
                {
                    "action_id": "restart_postgres",
                    "label": "Restart PostgreSQL",
                    "impact": "Restore database connectivity",
                }
            ],
            "modelservice": [
                {
                    "action_id": "restart_modelservice",
                    "label": "Restart Modelservice",
                    "impact": "Restore AI functionality",
                }
            ],
        }
        return remediation_map.get(component, [
            {
                "action_id": f"restart_{component}",
                "label": f"Restart {component.capitalize()}",
                "impact": "Restore connectivity",
            }
        ])

    def _estimate_time_to_critical(self, current: float, critical: float) -> str:
        """Estimate time until critical threshold based on current value."""
        if current >= critical:
            return "Critical now"
        
        # Simple linear estimation (would be better with historical data)
        remaining = critical - current
        if remaining > 10:
            return "> 24 hours"
        elif remaining > 5:
            return "12-24 hours"
        elif remaining > 2:
            return "6-12 hours"
        else:
            return "< 6 hours"
