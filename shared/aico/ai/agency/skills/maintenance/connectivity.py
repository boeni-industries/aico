"""Connectivity Maintenance Skills

Implements maintenance skills related to connectivity and basic system
health checks. These are designed to be safe, read-only diagnostics that
can be expanded over time.
"""

from __future__ import annotations

from typing import Dict, Any, List, Optional
from datetime import datetime, UTC

from aico.core.logging import get_logger
from aico.data.uow import UnitOfWork

from ..registry import (
    Skill,
    SkillParameter,
    SkillParameterType,
    SkillResult,
)


logger = get_logger("shared.ai.agency.skills.maintenance.connectivity")


class MaintenanceConnectivityFullScanSkill(Skill):
    """Run a connectivity and basic health scan for core components.

    Initial implementation focuses on PostgreSQL connectivity and returns a
    structured result shape that can be extended with additional checks for
    ChromaDB, InfluxDB, modelservice, and message bus.
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

        requested_targets = input_data.get("targets") or ["postgres"]
        checks: Dict[str, Dict[str, Any]] = {}

        # PostgreSQL connectivity
        if "postgres" in requested_targets:
            checks["postgres"] = await self._check_postgres_connectivity()

        # Placeholder entries for future components, marked as unsupported
        for component in ["chroma", "influx", "modelservice", "message_bus"]:
            if component in requested_targets and component not in checks:
                checks[component] = {
                    "status": "unsupported",
                    "error_message": "Check not implemented yet",
                    "latency_ms": None,
                    "details": {},
                }

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

        logger.info(
            "[MAINT_CONNECTIVITY] Full scan completed: %s",
            summary_status,
        )

        return SkillResult(
            success=summary_status == "healthy",
            output=output,
            metadata={
                "skill_id": self.skill_id,
                "summary_status": summary_status,
            },
        )

    async def _check_postgres_connectivity(self) -> Dict[str, Any]:
        """Check PostgreSQL connectivity via a lightweight repository call.

        Uses UnitOfWork with a minimal read operation to validate that the
        database is reachable and responsive. Mirrors existing health check
        patterns that query a small amount of data through repositories.
        """

        start = datetime.now(UTC)
        try:
            async with UnitOfWork(self._session_factory) as uow:
                # Simple query to test database connectivity via repositories.
                # User profiles are small and safe to list with a tiny limit.
                if hasattr(uow, "user_profiles"):
                    await uow.user_profiles.list(limit=1)

            latency_ms = int((datetime.now(UTC) - start).total_seconds() * 1000)
            return {
                "status": "ok",
                "latency_ms": latency_ms,
                "error_message": None,
                "details": {},
            }
        except Exception as exc:  # pragma: no cover - defensive safety net
            logger.error("[MAINT_CONNECTIVITY] PostgreSQL check failed: %s", exc)
            latency_ms = int((datetime.now(UTC) - start).total_seconds() * 1000)
            return {
                "status": "error",
                "latency_ms": latency_ms,
                "error_message": str(exc),
                "details": {},
            }
