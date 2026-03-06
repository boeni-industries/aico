"""Connectivity Maintenance Skills

Implements maintenance skills related to connectivity and basic system
health checks. These are designed to be safe, read-only diagnostics that
can be expanded over time.
"""

from __future__ import annotations

from typing import Dict, Any, List, Optional
from datetime import datetime, UTC

from aico.core.logging import get_logger
from ...tools import get_tool_registry

from ..registry import (
    Skill,
    SkillParameter,
    SkillParameterType,
    SkillResult,
)
from ...tools.registry import ToolRegistry


logger = get_logger("shared.ai.agency.skills.maintenance.connectivity")


class MaintenanceConnectivityFullScanSkill(Skill):
    """Run a connectivity and basic health scan for core components.

    Initial implementation focuses on PostgreSQL connectivity and returns a
    structured result shape that can be extended with additional checks for
    InfluxDB, modelservice, and message bus.
    """

    def __init__(self, session_factory: Any):
        self._session_factory = session_factory

    @property
    def skill_id(self) -> str:
        return "maint.connectivity.full_scan"

    @property
    def name(self) -> str:
        return "Connectivity Full Scan"

    @property
    def description(self) -> str:
        return (
            "Run a connectivity and basic health scan for core backend "
            "components (initially PostgreSQL; extensible to others)."
        )

    @property
    def category(self) -> str:
        return "maintenance"

    @property
    def capability_tags(self) -> List[str]:
        return ["check_health", "check_connectivity", "maintenance_scan"]

    @property
    def side_effect_tags(self) -> List[str]:
        # Read-only connectivity probes across multiple backends
        return [
            "reads_database",
            "reads_metrics",
            "reads_service_state",
        ]

    @property
    def safety_level(self) -> str:
        return "low"

    @property
    def implementation_tools(self) -> List[str]:
        return [
            "tool.db.postgres.ping",
            "tool.modelservice.ping",
        ]

    @property
    def parameters(self) -> List[SkillParameter]:
        return [
            SkillParameter(
                name="targets",
                type=SkillParameterType.ARRAY,
                description=(
                    "Optional list of components to check. If omitted, a "
                    "default subset is used."
                ),
                required=False,
                default=["postgres"],
            ),
        ]

    async def execute(
        self,
        user_id: str,
        input_data: Dict[str, Any],
        context: Dict[str, Any],
    ) -> SkillResult:
        """Execute the connectivity scan.

        For now this performs a safe PostgreSQL connectivity check via the
        UnitOfWork layer. The result format is designed to align with the
        WIP-self-healing-skills-tools spec so additional components can be
        added later without breaking callers.
        """

        # Full scan always runs all connectivity tools for core components,
        # regardless of requested targets. The "targets" parameter is kept
        # for forward compatibility but is currently ignored for behaviour.
        checks: Dict[str, Dict[str, Any]] = {}

        registry = get_tool_registry()

        async def _run_tool(tool_id: str, *args: Any) -> Dict[str, Any]:
            tool_def = registry.get(tool_id)
            if not tool_def:
                logger.error(
                    "[MAINT_CONNECTIVITY] Tool '%s' not found in registry",
                    tool_id,
                )
                return {
                    "ok": False,
                    "data": {
                        "status": "error",
                        "latency_ms": None,
                        "error_message": f"Tool '{tool_id}' not registered",
                        "details": {},
                    },
                    "error": {
                        "code": "tool_not_registered",
                        "message": f"Tool '{tool_id}' not registered",
                    },
                }
            return await tool_def.handler(*args)

        # PostgreSQL
        pg_result = await _run_tool("tool.db.postgres.ping", self._session_factory)
        checks["postgres"] = pg_result["data"]

        # Modelservice (ZMQ)
        modelservice_result = await _run_tool("tool.modelservice.ping")
        checks["modelservice"] = modelservice_result["data"]

        # Derive summary status
        summary_status = "healthy"
        for result in checks.values():
            status = result.get("status")
            if status in ("error", "unhealthy"):
                summary_status = "unhealthy"
                break
            if status in ("warning", "unsupported") and summary_status != "unhealthy":
                summary_status = "degraded"

        output = {
            "summary_status": summary_status,
            "checks": checks,
            "observables": {
                "metrics": [],
                "events": [],
                "logs": [],
            },
            "executed_at": datetime.now(UTC).isoformat(),
        }

        return SkillResult(
            # The scan itself is a diagnostic read-only operation; even if the
            # system is unhealthy, the skill execution is considered
            # successful. Callers should inspect summary_status/checks to see
            # whether components are healthy.
            success=True,
            output=output,
            metadata={
                "skill_id": self.skill_id,
                "summary_status": summary_status,
            },
        )


class MaintenanceConnectivityVerifyComponentSkill(Skill):
    """Check connectivity for a single named component using ping tools."""

    def __init__(self, session_factory: Any):
        self._session_factory = session_factory

    @property
    def skill_id(self) -> str:
        return "maint.connectivity.verify_component"

    @property
    def name(self) -> str:
        return "Connectivity Verify Component"

    @property
    def description(self) -> str:
        return "Check connectivity for a single backend component (e.g. postgres, influx, lmdb)."

    @property
    def category(self) -> str:
        return "maintenance"

    @property
    def parameters(self) -> List[SkillParameter]:
        return [
            SkillParameter(
                name="component",
                type=SkillParameterType.STRING,
                description=(
                    "Name of the component to verify (postgres, "
                    "modelservice)."
                ),
                required=True,
            ),
        ]

    async def execute(
        self,
        user_id: str,
        input_data: Dict[str, Any],
        context: Dict[str, Any],
    ) -> SkillResult:
        component = (input_data.get("component") or "").lower()

        # Map component names to tool_ids
        component_tools: Dict[str, str] = {
            "postgres": "tool.db.postgres.ping",
            "modelservice": "tool.modelservice.ping",
        }

        tool_id = component_tools.get(component)
        if not tool_id:
            error_msg = f"Unsupported component: {component!r}"
            logger.error("[MAINT_CONNECTIVITY] %s", error_msg)
            return SkillResult(
                success=False,
                output={
                    "component": component,
                    "check": {
                        "status": "error",
                        "latency_ms": None,
                        "error_message": error_msg,
                        "details": {},
                    },
                    "observables": {"metrics": [], "events": [], "logs": []},
                    "executed_at": datetime.now(UTC).isoformat(),
                },
                metadata={
                    "skill_id": self.skill_id,
                    "component": component,
                    "summary_status": "unhealthy",
                },
            )

        registry = get_tool_registry()
        tool_def = registry.get(tool_id)
        if not tool_def:
            error_msg = f"Tool '{tool_id}' not registered for component '{component}'"
            logger.error("[MAINT_CONNECTIVITY] %s", error_msg)
            return SkillResult(
                success=False,
                output={
                    "component": component,
                    "check": {
                        "status": "error",
                        "latency_ms": None,
                        "error_message": error_msg,
                        "details": {},
                    },
                    "observables": {"metrics": [], "events": [], "logs": []},
                    "executed_at": datetime.now(UTC).isoformat(),
                },
                metadata={
                    "skill_id": self.skill_id,
                    "component": component,
                    "summary_status": "unhealthy",
                },
            )

        # Postgres handler requires session_factory; others do not
        if component == "postgres":
            result = await tool_def.handler(self._session_factory)
        else:
            result = await tool_def.handler()

        check = result["data"]
        summary_status = "healthy" if check.get("status") == "ok" else "unhealthy"

        output = {
            "component": component,
            "check": check,
            "observables": {"metrics": [], "events": [], "logs": []},
            "executed_at": datetime.now(UTC).isoformat(),
        }

        return SkillResult(
            success=summary_status == "healthy",
            output=output,
            metadata={
                "skill_id": self.skill_id,
                "component": component,
                "summary_status": summary_status,
            },
        )
