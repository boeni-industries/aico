"""Test Maintenance Skills

Deterministic, safe skills for end-to-end testing of the agency self-healing loop.
"""

from __future__ import annotations

from datetime import datetime, UTC
from typing import Any, Dict, List

from aico.core.logging import get_logger

from ..registry import Skill, SkillParameter, SkillParameterType, SkillResult


logger = get_logger("shared.ai.agency.skills.maintenance.test_noop")


class MaintenanceTestNoopRemediationSkill(Skill):
    @property
    def skill_id(self) -> str:
        return "maint.test.noop_remediation"

    @property
    def name(self) -> str:
        return "Test No-Op Remediation"

    @property
    def description(self) -> str:
        return "No-op remediation used for deterministic end-to-end self-healing tests."

    @property
    def category(self) -> str:
        return "maintenance"

    @property
    def capability_tags(self) -> List[str]:
        return ["test", "self_healing", "no_op"]

    @property
    def side_effect_tags(self) -> List[str]:
        return []

    @property
    def safety_level(self) -> str:
        return "low"

    @property
    def implementation_tools(self) -> List[str]:
        return []

    @property
    def parameters(self) -> List[SkillParameter]:
        return [
            SkillParameter(
                name="dry_run",
                type=SkillParameterType.BOOLEAN,
                description="If true, only report what would be done",
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
        dry_run = input_data.get("dry_run", True)
        logger.info("[MAINT_TEST_NOOP] Executing noop remediation dry_run=%s user_id=%s", dry_run, user_id)
        return SkillResult(
            success=True,
            output={
                "summary_status": "healthy",
                "simulated": True,
                "dry_run": dry_run,
                "timestamp": datetime.now(UTC).isoformat(),
            },
            error=None,
        )
