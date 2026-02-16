"""Agency maintenance skills for cleaning up execution history.

Implements maint.agency.cleanup_executions which delegates to the
`tool.agency.postgres.cleanup_executions` tool to enforce retention on
Agency plan and step executions.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from aico.core.logging import get_logger

from ..registry import (
    Skill,
    SkillParameter,
    SkillParameterType,
    SkillResult,
)
from ...tools import get_tool_registry


logger = get_logger("shared.ai.agency.skills.maintenance.agency_cleanup")


class MaintenanceAgencyCleanupExecutionsSkill(Skill):
    """Clean up Agency execution history according to retention policy.

    This skill is a semantic wrapper around the
    `tool.agency.postgres.cleanup_executions` tool. It exposes a stable
    skill_id for Agency plans, the CLI, and System Health, while delegating
    actual deletion logic to the Tool layer.
    """

    def __init__(self, session_factory: Any):
        self._session_factory = session_factory

    # ------------------------------------------------------------------
    # Metadata
    # ------------------------------------------------------------------

    @property
    def skill_id(self) -> str:
        return "maint.agency.cleanup_executions"

    @property
    def name(self) -> str:
        return "Agency Execution Cleanup"

    @property
    def description(self) -> str:
        return (
            "Clean up Agency plan and step executions according to the "
            "configured retention policy (age and per-plan limits)."
        )

    @property
    def category(self) -> str:
        return "maintenance"

    @property
    def capability_tags(self) -> List[str]:
        return ["cleanup_history", "maintenance", "self_healing"]

    @property
    def side_effect_tags(self) -> List[str]:
        return ["writes_database", "deletes_history", "agency_internal"]

    @property
    def safety_level(self) -> str:
        return "privileged"

    @property
    def implementation_tools(self) -> List[str]:
        return ["tool.agency.postgres.cleanup_executions"]

    @property
    def parameters(self) -> List[SkillParameter]:
        # Parameters mirror the underlying tool, but callers may omit them to
        # rely on config defaults for retention.
        return [
            SkillParameter(
                name="max_age_days",
                type=SkillParameterType.INTEGER,
                description=(
                    "Delete executions older than this many days. If omitted, "
                    "the value from agency.execution_retention.max_age_days "
                    "is used."
                ),
                required=False,
            ),
            SkillParameter(
                name="max_executions_per_plan",
                type=SkillParameterType.INTEGER,
                description=(
                    "Maximum executions to keep per plan. If omitted, the "
                    "value from agency.execution_retention." \
                    "max_executions_per_plan is used."
                ),
                required=False,
            ),
            SkillParameter(
                name="min_keep_per_plan",
                type=SkillParameterType.INTEGER,
                description=(
                    "Minimum executions to always keep per plan regardless "
                    "of age."
                ),
                required=False,
            ),
            SkillParameter(
                name="plan_id",
                type=SkillParameterType.STRING,
                description=(
                    "If set, restrict cleanup to this specific plan_id. "
                    "If omitted, all plans are considered."
                ),
                required=False,
            ),
            SkillParameter(
                name="dry_run",
                type=SkillParameterType.BOOLEAN,
                description=(
                    "If true, only report what would be deleted without "
                    "actually deleting any rows."
                ),
                required=False,
                default=True,
            ),
        ]

    # ------------------------------------------------------------------
    # Execution
    # ------------------------------------------------------------------

    async def execute(
        self,
        user_id: str,
        input_data: Dict[str, Any],
        context: Dict[str, Any],
    ) -> SkillResult:
        """Execute the cleanup by delegating to the agency cleanup tool."""

        registry = get_tool_registry()
        tool_def = registry.get("tool.agency.postgres.cleanup_executions")
        if not tool_def:
            error_msg = "Tool 'tool.agency.postgres.cleanup_executions' not registered"
            logger.error("[MAINT_AGENCY_CLEANUP] %s", error_msg)
            return SkillResult(
                success=False,
                output={},
                error=error_msg,
                metadata={"skill_id": self.skill_id},
            )

        # Extract parameters with sensible defaults (tool will also apply
        # config-based defaults where parameters are None).
        max_age_days: Optional[int] = input_data.get("max_age_days")
        max_execs: Optional[int] = input_data.get("max_executions_per_plan")
        min_keep: Optional[int] = input_data.get("min_keep_per_plan")
        plan_id: Optional[str] = input_data.get("plan_id")
        dry_run: bool = input_data.get("dry_run", True)

        logger.info(
            "[MAINT_AGENCY_CLEANUP] Running execution cleanup (plan_id=%s, dry_run=%s)",
            plan_id,
            dry_run,
        )

        result = await tool_def.handler(
            self._session_factory,
            max_age_days=max_age_days,
            max_executions_per_plan=max_execs,
            min_keep_per_plan=min_keep or 3,
            plan_id=plan_id,
            dry_run=dry_run,
        )

        ok = result.get("ok", False)
        data = result.get("data", {})
        error = result.get("error")

        return SkillResult(
            success=ok,
            output=data,
            error=(error or {}).get("message") if error else None,
            metadata={
                "skill_id": self.skill_id,
                "tool_id": "tool.agency.postgres.cleanup_executions",
                "ok": ok,
            },
        )
