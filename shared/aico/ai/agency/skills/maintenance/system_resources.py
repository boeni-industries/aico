"""System Resource Maintenance Skills

Implements maintenance skills for monitoring system resources (CPU, memory, disk).
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


logger = get_logger("shared.ai.agency.skills.maintenance.system_resources")


class MaintenanceSystemScanResourcesSkill(Skill):
    """Scan system resources (CPU, memory, disk) and check against thresholds.
    
    This skill orchestrates resource monitoring tools and evaluates whether
    resources are within acceptable limits.
    """

    @property
    def skill_id(self) -> str:
        return "maint.system.scan_resources"

    @property
    def name(self) -> str:
        return "System Resource Scan"

    @property
    def description(self) -> str:
        return (
            "Scan system resources (CPU, memory, disk) and check against "
            "configured thresholds."
        )

    @property
    def category(self) -> str:
        return "maintenance"

    @property
    def capability_tags(self) -> List[str]:
        return ["check_health", "measure_resources", "maintenance_scan"]

    @property
    def side_effect_tags(self) -> List[str]:
        return ["reads_system_state"]

    @property
    def safety_level(self) -> str:
        return "low"

    @property
    def implementation_tools(self) -> List[str]:
        return [
            "tool.system.cpu.measure_load",
            "tool.system.memory.measure_usage",
            "tool.system.disk.measure_usage",
        ]

    @property
    def parameters(self) -> List[SkillParameter]:
        return [
            SkillParameter(
                name="thresholds",
                type=SkillParameterType.OBJECT,
                description=(
                    "Optional threshold overrides. Keys: cpu_percent, "
                    "memory_percent, disk_percent. Defaults: 80, 85, 90."
                ),
                required=False,
                default={},
            ),
        ]

    async def execute(
        self,
        user_id: str,
        input_data: Dict[str, Any],
        context: Dict[str, Any],
    ) -> SkillResult:
        """Execute the resource scan."""
        
        # Get thresholds with defaults
        thresholds = input_data.get("thresholds", {})
        cpu_threshold = thresholds.get("cpu_percent", 80)
        memory_threshold = thresholds.get("memory_percent", 85)
        disk_threshold = thresholds.get("disk_percent", 90)
        
        registry = get_tool_registry()
        checks: Dict[str, Dict[str, Any]] = {}
        
        async def _run_tool(tool_id: str) -> Dict[str, Any]:
            tool_def = registry.get(tool_id)
            if not tool_def:
                logger.error(
                    "[MAINT_SYSTEM_RESOURCES] Tool '%s' not found in registry",
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
        
        # CPU
        cpu_result = await _run_tool("tool.system.cpu.measure_load")
        cpu_data = cpu_result["data"]
        cpu_percent = cpu_data.get("details", {}).get("cpu_percent", 0)
        cpu_data["threshold"] = cpu_threshold
        cpu_data["threshold_exceeded"] = cpu_percent > cpu_threshold
        checks["cpu"] = cpu_data
        
        # Memory
        memory_result = await _run_tool("tool.system.memory.measure_usage")
        memory_data = memory_result["data"]
        memory_percent = memory_data.get("details", {}).get("percent", 0)
        memory_data["threshold"] = memory_threshold
        memory_data["threshold_exceeded"] = memory_percent > memory_threshold
        checks["memory"] = memory_data
        
        # Disk
        disk_result = await _run_tool("tool.system.disk.measure_usage")
        disk_data = disk_result["data"]
        disk_percent = disk_data.get("details", {}).get("percent", 0)
        disk_data["threshold"] = disk_threshold
        disk_data["threshold_exceeded"] = disk_percent > disk_threshold
        checks["disk"] = disk_data
        
        # Derive summary status
        summary_status = "healthy"
        threshold_violations = []
        
        for resource_name, check in checks.items():
            if check.get("status") == "error":
                summary_status = "unhealthy"
                break
            if check.get("threshold_exceeded"):
                threshold_violations.append(resource_name)
                if summary_status == "healthy":
                    summary_status = "degraded"
        
        output = {
            "summary_status": summary_status,
            "checks": checks,
            "threshold_violations": threshold_violations,
            "observables": {
                "metrics": [],
                "events": [],
                "logs": [],
            },
            "executed_at": datetime.now(UTC).isoformat(),
        }
        
        return SkillResult(
            success=True,
            output=output,
            metadata={
                "skill_id": self.skill_id,
                "summary_status": summary_status,
                "threshold_violations": threshold_violations,
            },
        )
