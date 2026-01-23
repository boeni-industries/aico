"""Scheduler Health Maintenance Skill

Skill for checking task scheduler health and execution status.
"""

from __future__ import annotations

from typing import Dict, Any, List
from datetime import datetime, UTC

from aico.core.logging import get_logger
from ...tools import get_tool_registry
from ..registry import Skill, SkillParameter, SkillParameterType, SkillResult


logger = get_logger("aico.ai.agency.skills.maintenance.scheduler")


class MaintenanceSchedulerCheckHealthSkill(Skill):
    """Check task scheduler health and recent execution status."""
    
    @property
    def skill_id(self) -> str:
        return "maint.scheduler.check_health"
    
    @property
    def name(self) -> str:
        return "Check Scheduler Health"
    
    @property
    def description(self) -> str:
        return "Check task scheduler health and recent execution status."
    
    @property
    def category(self) -> str:
        return "maintenance"
    
    @property
    def capability_tags(self) -> List[str]:
        return ["check_health", "query_database"]
    
    @property
    def side_effect_tags(self) -> List[str]:
        return ["reads_database"]
    
    @property
    def safety_level(self) -> str:
        return "low"
    
    @property
    def implementation_tools(self) -> List[str]:
        return ["tool.scheduler.check_status", "tool.scheduler.check_stuck_tasks"]
    
    @property
    def parameters(self) -> List[SkillParameter]:
        return [
            SkillParameter(
                name="lookback_minutes",
                type=SkillParameterType.INTEGER,
                description="Minutes to look back for recent executions",
                required=False,
                default=60,
            ),
        ]
    
    async def execute(
        self,
        user_id: str,
        input_data: Dict[str, Any],
        context: Dict[str, Any],
    ) -> SkillResult:
        """Execute scheduler health check."""
        logger.info("[MAINT_SCHEDULER] Checking scheduler health")
        
        try:
            from aico.ai.agency.tools.registry import get_tool_registry
            
            tool_registry = get_tool_registry()
            checks = {}
            lookback_minutes = input_data.get("lookback_minutes", 60)
            
            status_tool = tool_registry.get("tool.scheduler.check_status")
            if status_tool:
                status_result = await status_tool.handler(lookback_minutes=lookback_minutes)
                checks["status"] = status_result.get("data", {})
            else:
                logger.warning("[MAINT_SCHEDULER] Status tool not found")
                checks["status"] = {
                    "status": "error",
                    "error_message": "Status tool not registered"
                }
            
            stuck_tool = tool_registry.get("tool.scheduler.check_stuck_tasks")
            if stuck_tool:
                stuck_result = await stuck_tool.handler(threshold_minutes=60)
                checks["stuck_tasks"] = stuck_result.get("data", {})
            
            status_check = checks.get("status", {})
            stuck_check = checks.get("stuck_tasks", {})
            
            status_val = status_check.get("status", "error")
            stuck_val = stuck_check.get("status", "ok")
            
            if status_val == "error" or stuck_val == "error":
                summary_status = "unhealthy"
            elif status_val == "warning" or stuck_val == "warning":
                summary_status = "degraded"
            elif status_val == "ok":
                summary_status = "healthy"
            else:
                summary_status = "unknown"
            
            logger.info("[MAINT_SCHEDULER] Health check complete: %s", summary_status)
            
            return SkillResult(
                success=True,
                output={
                    "summary_status": summary_status,
                    "checks": checks,
                    "timestamp": datetime.now(UTC).isoformat()
                },
                error=None,
            )
        
        except Exception as exc:
            logger.error("[MAINT_SCHEDULER] Health check failed: %s", exc)
            return SkillResult(
                success=False,
                output={
                    "summary_status": "unhealthy",
                    "checks": {
                        "error": {
                            "status": "error",
                            "error_message": f"Health check failed: {str(exc)}"
                        }
                    },
                    "timestamp": datetime.now(UTC).isoformat()
                },
                error=str(exc),
            )
