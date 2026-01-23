"""Modelservice Maintenance Skills

Implements maintenance skills for monitoring modelservice health.
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


logger = get_logger("shared.ai.agency.skills.maintenance.modelservice")


class MaintenanceModelserviceScanHealthSkill(Skill):
    """Scan modelservice health by testing inference and checking connectivity.
    
    This skill orchestrates modelservice health checks including ZMQ connectivity
    and inference pipeline testing.
    """

    @property
    def skill_id(self) -> str:
        return "maint.modelservice.scan_health"

    @property
    def name(self) -> str:
        return "Modelservice Health Scan"

    @property
    def description(self) -> str:
        return (
            "Scan modelservice health by testing ZMQ connectivity and "
            "inference pipeline functionality."
        )

    @property
    def category(self) -> str:
        return "maintenance"

    @property
    def capability_tags(self) -> List[str]:
        return ["check_health", "test_inference", "maintenance_scan"]

    @property
    def side_effect_tags(self) -> List[str]:
        return ["reads_service_state", "uses_llm"]

    @property
    def safety_level(self) -> str:
        return "low"

    @property
    def implementation_tools(self) -> List[str]:
        return [
            "tool.modelservice.ping",
            "tool.modelservice.scan_health",
        ]

    @property
    def parameters(self) -> List[SkillParameter]:
        return [
            SkillParameter(
                name="test_inference",
                type=SkillParameterType.BOOLEAN,
                description="Whether to test inference pipeline (slower but thorough).",
                required=False,
                default=True,
            ),
            SkillParameter(
                name="test_embedding",
                type=SkillParameterType.BOOLEAN,
                description="Whether to test embedding generation.",
                required=False,
                default=False,
            ),
        ]

    async def execute(
        self,
        user_id: str,
        input_data: Dict[str, Any],
        context: Dict[str, Any],
    ) -> SkillResult:
        """Execute the modelservice health scan."""
        
        test_inference = input_data.get("test_inference", True)
        test_embedding = input_data.get("test_embedding", False)
        
        registry = get_tool_registry()
        checks: Dict[str, Dict[str, Any]] = {}
        
        async def _run_tool(tool_id: str) -> Dict[str, Any]:
            tool_def = registry.get(tool_id)
            if not tool_def:
                logger.error(
                    "[MAINT_MODELSERVICE] Tool '%s' not found in registry",
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
            return await tool_def.handler()
        
        # ZMQ connectivity
        ping_result = await _run_tool("tool.modelservice.ping")
        checks["connectivity"] = ping_result["data"]
        
        # Health check (includes inference test)
        if test_inference:
            health_result = await _run_tool("tool.modelservice.scan_health")
            checks["health"] = health_result["data"]
        
        # Embedding test (optional, not implemented yet)
        if test_embedding:
            checks["embedding"] = {
                "status": "unsupported",
                "latency_ms": None,
                "error_message": "Embedding test not yet implemented",
                "details": {},
            }
        
        # Derive summary status
        summary_status = "healthy"
        for check in checks.values():
            status = check.get("status")
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
            "[MAINT_MODELSERVICE] Health scan completed: %s",
            summary_status,
        )
        
        return SkillResult(
            success=True,
            output=output,
            metadata={
                "skill_id": self.skill_id,
                "summary_status": summary_status,
            },
        )
