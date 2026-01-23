"""Agency Behaviour Maintenance Skills

Implements maintenance skills for monitoring agency behaviour health.
"""

from __future__ import annotations

from typing import Dict, Any, List
from datetime import datetime, UTC

from aico.core.logging import get_logger
from ...tools import get_tool_registry

from ..registry import (
    Skill,
    SkillParameter,
    SkillParameterType,
    SkillResult,
)


logger = get_logger("shared.ai.agency.skills.maintenance.agency_behaviour")


class MaintenanceAgencyReEvaluateBehaviourHealthSkill(Skill):
    """Re-evaluate agency behaviour health by checking goals, plans, and reflections.
    
    This skill orchestrates agency health checks to ensure the system is
    functioning properly and not experiencing issues like stalled plans.
    """

    def __init__(self, session_factory: Any):
        self._session_factory = session_factory

    @property
    def skill_id(self) -> str:
        return "maint.agency.re_evaluate_behaviour_health"

    @property
    def name(self) -> str:
        return "Agency Behaviour Health Re-evaluation"

    @property
    def description(self) -> str:
        return (
            "Re-evaluate agency behaviour health by checking goals, plans, "
            "reflections, and detecting stalled or problematic execution."
        )

    @property
    def category(self) -> str:
        return "maintenance"

    @property
    def capability_tags(self) -> List[str]:
        return ["check_health", "detect_issues", "maintenance_scan"]

    @property
    def side_effect_tags(self) -> List[str]:
        return ["reads_database"]

    @property
    def safety_level(self) -> str:
        return "low"

    @property
    def implementation_tools(self) -> List[str]:
        return [
            "tool.agency.metrics.snapshot",
            "tool.agency.detect_stalled_plans",
        ]

    @property
    def parameters(self) -> List[SkillParameter]:
        return [
            SkillParameter(
                name="check_goals",
                type=SkillParameterType.BOOLEAN,
                description="Whether to check goal health.",
                required=False,
                default=True,
            ),
            SkillParameter(
                name="check_plans",
                type=SkillParameterType.BOOLEAN,
                description="Whether to check plan execution health.",
                required=False,
                default=True,
            ),
            SkillParameter(
                name="check_reflection",
                type=SkillParameterType.BOOLEAN,
                description="Whether to check reflection activity.",
                required=False,
                default=True,
            ),
        ]

    async def execute(
        self,
        user_id: str,
        input_data: Dict[str, Any],
        context: Dict[str, Any],
    ) -> SkillResult:
        """Execute the agency behaviour health check."""
        
        check_goals = input_data.get("check_goals", True)
        check_plans = input_data.get("check_plans", True)
        check_reflection = input_data.get("check_reflection", True)
        
        registry = get_tool_registry()
        checks: Dict[str, Dict[str, Any]] = {}
        
        async def _run_tool(tool_id: str, *args: Any) -> Dict[str, Any]:
            tool_def = registry.get(tool_id)
            if not tool_def:
                logger.error(
                    "[MAINT_AGENCY_BEHAVIOUR] Tool '%s' not found in registry",
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
        
        # Metrics snapshot (goals, intentions, reflections)
        if check_goals or check_reflection:
            metrics_result = await _run_tool(
                "tool.agency.metrics.snapshot",
                self._session_factory
            )
            checks["metrics"] = metrics_result["data"]
        
        # Stalled plan detection
        if check_plans:
            stalled_result = await _run_tool(
                "tool.agency.detect_stalled_plans",
                self._session_factory
            )
            checks["stalled_plans"] = stalled_result["data"]
        
        # Derive summary status
        summary_status = "healthy"
        issues = []
        
        for check_name, check in checks.items():
            status = check.get("status")
            if status == "error":
                summary_status = "unhealthy"
                issues.append(f"{check_name}_error")
            elif status == "warning":
                if summary_status == "healthy":
                    summary_status = "degraded"
                issues.append(f"{check_name}_warning")
        
        # Check for specific issues
        if "stalled_plans" in checks:
            stalled_count = checks["stalled_plans"].get("details", {}).get("stalled_count", 0)
            if stalled_count > 0:
                if summary_status == "healthy":
                    summary_status = "degraded"
                issues.append(f"stalled_plans_{stalled_count}")
        
        output = {
            "summary_status": summary_status,
            "checks": checks,
            "issues": issues,
            "observables": {
                "metrics": [],
                "events": [],
                "logs": [],
            },
            "executed_at": datetime.now(UTC).isoformat(),
        }
        
        logger.info(
            "[MAINT_AGENCY_BEHAVIOUR] Behaviour health check completed: %s (issues: %s)",
            summary_status,
            issues,
        )
        
        return SkillResult(
            success=True,
            output=output,
            metadata={
                "skill_id": self.skill_id,
                "summary_status": summary_status,
                "issues": issues,
            },
        )
