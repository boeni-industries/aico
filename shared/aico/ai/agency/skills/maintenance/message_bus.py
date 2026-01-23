"""Message Bus Health Maintenance Skill

Skill for checking message bus (ZeroMQ) health and connectivity.
"""

from __future__ import annotations

from typing import Dict, Any, List
from datetime import datetime, UTC

from aico.core.logging import get_logger
from ...tools import get_tool_registry
from ..registry import Skill, SkillParameter, SkillResult


logger = get_logger("aico.ai.agency.skills.maintenance.message_bus")


class MaintenanceMessageBusCheckHealthSkill(Skill):
    """Check message bus (ZeroMQ) health and connectivity status."""
    
    @property
    def skill_id(self) -> str:
        return "maint.messagebus.check_health"
    
    @property
    def name(self) -> str:
        return "Check Message Bus Health"
    
    @property
    def description(self) -> str:
        return "Check ZeroMQ message bus health and connectivity status."
    
    @property
    def category(self) -> str:
        return "maintenance"
    
    @property
    def capability_tags(self) -> List[str]:
        return ["check_health", "check_connectivity"]
    
    @property
    def side_effect_tags(self) -> List[str]:
        return ["reads_service_state"]
    
    @property
    def safety_level(self) -> str:
        return "low"
    
    @property
    def implementation_tools(self) -> List[str]:
        return ["tool.messagebus.check_status"]
    
    @property
    def parameters(self) -> List[SkillParameter]:
        return []
    
    async def execute(
        self,
        user_id: str,
        input_data: Dict[str, Any],
        context: Dict[str, Any],
    ) -> SkillResult:
        """Execute message bus health check."""
        logger.info("[MAINT_MESSAGEBUS] Checking message bus health")
        
        try:
            from aico.ai.agency.tools.registry import get_tool_registry
            
            tool_registry = get_tool_registry()
            checks = {}
            
            status_tool = tool_registry.get("tool.messagebus.check_status")
            if status_tool:
                status_result = await status_tool.handler()
                checks["status"] = status_result.get("data", {})
            else:
                logger.warning("[MAINT_MESSAGEBUS] Status tool not found")
                checks["status"] = {
                    "status": "error",
                    "error_message": "Status tool not registered"
                }
            
            status_check = checks.get("status", {})
            status = status_check.get("status", "error")
            
            if status == "ok":
                summary_status = "healthy"
            elif status == "warning":
                summary_status = "degraded"
            else:
                summary_status = "unhealthy"
            
            logger.info("[MAINT_MESSAGEBUS] Health check complete: %s", summary_status)
            
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
            logger.error("[MAINT_MESSAGEBUS] Health check failed: %s", exc)
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
