"""Service Remediation Skills

Skills for service maintenance and remediation actions.
"""

from __future__ import annotations

from typing import Dict, Any, List
from datetime import datetime, UTC

from aico.core.logging import get_logger
from ...tools import get_tool_registry
from ..registry import Skill, SkillParameter, SkillParameterType, SkillResult


logger = get_logger("shared.ai.agency.skills.remediation.service")


class RemediationModelserviceStabiliseSkill(Skill):
    """Stabilize modelservice by restarting workers and clearing caches."""
    
    @property
    def skill_id(self) -> str:
        return "maint.modelservice.stabilise"
    
    @property
    def name(self) -> str:
        return "Modelservice Stabilise"
    
    @property
    def description(self) -> str:
        return "Stabilize modelservice by restarting workers and clearing caches."
    
    @property
    def category(self) -> str:
        return "remediation"
    
    @property
    def capability_tags(self) -> List[str]:
        return ["service_recovery", "restart", "clear_cache"]
    
    @property
    def side_effect_tags(self) -> List[str]:
        return ["restarts_service", "clears_cache"]
    
    @property
    def safety_level(self) -> str:
        return "high"
    
    @property
    def implementation_tools(self) -> List[str]:
        return ["tool.modelservice.restart_workers", "tool.modelservice.clear_cache"]
    
    @property
    def parameters(self) -> List[SkillParameter]:
        return [
            SkillParameter(
                name="restart_workers",
                type=SkillParameterType.BOOLEAN,
                description="Whether to restart worker processes",
                required=False,
                default=False,
            ),
            SkillParameter(
                name="clear_cache",
                type=SkillParameterType.BOOLEAN,
                description="Whether to clear internal caches",
                required=False,
                default=True,
            ),
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
        """Execute modelservice stabilization."""
        logger.info("[REMEDIATION_MODELSERVICE] Running stabilization")
        
        try:
            from aico.ai.agency.tools.service_remediation import (
                tool_modelservice_restart_workers,
                tool_modelservice_clear_cache,
            )
            
            dry_run = input_data.get("dry_run", True)
            results = {}
            
            # Clear cache if requested
            if input_data.get("clear_cache", True):
                cache_result = await tool_modelservice_clear_cache(dry_run=dry_run)
                results["clear_cache"] = cache_result.get("data", {})
            
            # Restart workers if requested
            if input_data.get("restart_workers", False):
                restart_result = await tool_modelservice_restart_workers(dry_run=dry_run)
                results["restart_workers"] = restart_result.get("data", {})
            
            return SkillResult(
                success=True,
                output={
                    "summary_status": "healthy",
                    "results": results,
                    "timestamp": datetime.now(UTC).isoformat(),
                },
                error=None,
            )
        
        except Exception as exc:
            logger.error("[REMEDIATION_MODELSERVICE] Stabilization failed: %s", exc)
            return SkillResult(
                success=False,
                output={
                    "summary_status": "unhealthy",
                    "error": str(exc),
                    "timestamp": datetime.now(UTC).isoformat(),
                },
                error=str(exc),
            )


class RemediationAgencyRecoverPlansSkill(Skill):
    """Recover stalled agency plans."""
    
    def __init__(self, session_factory: Any):
        self._session_factory = session_factory
    
    @property
    def skill_id(self) -> str:
        return "maint.agency.recover_stalled_plans"
    
    @property
    def name(self) -> str:
        return "Agency Recover Stalled Plans"
    
    @property
    def description(self) -> str:
        return "Recover stalled agency plans by retiring them."
    
    @property
    def category(self) -> str:
        return "remediation"
    
    @property
    def capability_tags(self) -> List[str]:
        return ["agency_maintenance", "recover", "cleanup"]
    
    @property
    def side_effect_tags(self) -> List[str]:
        return ["modifies_database", "updates_plans"]
    
    @property
    def safety_level(self) -> str:
        return "medium"
    
    @property
    def implementation_tools(self) -> List[str]:
        return ["tool.agency.retire_stalled_plans"]
    
    @property
    def parameters(self) -> List[SkillParameter]:
        return [
            SkillParameter(
                name="max_age_hours",
                type=SkillParameterType.INTEGER,
                description="Maximum age in hours for a plan to be considered stalled",
                required=False,
                default=24,
            ),
            SkillParameter(
                name="max_plans",
                type=SkillParameterType.INTEGER,
                description="Maximum number of plans to retire",
                required=False,
                default=10,
            ),
            SkillParameter(
                name="dry_run",
                type=SkillParameterType.BOOLEAN,
                description="If true, only count plans that would be retired",
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
        """Execute plan recovery."""
        logger.info("[REMEDIATION_AGENCY] Running plan recovery")
        
        try:
            from aico.ai.agency.tools.service_remediation import tool_agency_retire_stalled_plans
            
            result = await tool_agency_retire_stalled_plans(
                self._session_factory,
                max_age_hours=input_data.get("max_age_hours", 24),
                max_plans=input_data.get("max_plans", 10),
                dry_run=input_data.get("dry_run", True),
            )
            
            success = result.get("ok", False)
            data = result.get("data", {})
            
            return SkillResult(
                success=success,
                output={
                    "summary_status": "healthy" if success else "unhealthy",
                    "result": data,
                    "timestamp": datetime.now(UTC).isoformat(),
                },
                error=result.get("error", {}).get("message") if not success else None,
            )
        
        except Exception as exc:
            logger.error("[REMEDIATION_AGENCY] Plan recovery failed: %s", exc)
            return SkillResult(
                success=False,
                output={
                    "summary_status": "unhealthy",
                    "error": str(exc),
                    "timestamp": datetime.now(UTC).isoformat(),
                },
                error=str(exc),
            )


class RemediationAgencyRebalanceLoadSkill(Skill):
    """Rebalance agency scheduler load."""
    
    def __init__(self, session_factory: Any):
        self._session_factory = session_factory
    
    @property
    def skill_id(self) -> str:
        return "maint.agency.rebalance_load"
    
    @property
    def name(self) -> str:
        return "Agency Rebalance Load"
    
    @property
    def description(self) -> str:
        return "Rebalance agency scheduler load by adjusting task configuration."
    
    @property
    def category(self) -> str:
        return "remediation"
    
    @property
    def capability_tags(self) -> List[str]:
        return ["agency_maintenance", "rebalance", "optimize"]
    
    @property
    def side_effect_tags(self) -> List[str]:
        return ["modifies_config"]
    
    @property
    def safety_level(self) -> str:
        return "medium"
    
    @property
    def implementation_tools(self) -> List[str]:
        return ["tool.agency.update_scheduler_config"]
    
    @property
    def parameters(self) -> List[SkillParameter]:
        return [
            SkillParameter(
                name="task_id",
                type=SkillParameterType.STRING,
                description="ID of the scheduler task to update",
                required=True,
            ),
            SkillParameter(
                name="config_updates",
                type=SkillParameterType.OBJECT,
                description="Dictionary of config keys and new values",
                required=True,
            ),
            SkillParameter(
                name="dry_run",
                type=SkillParameterType.BOOLEAN,
                description="If true, only report what would be changed",
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
        """Execute load rebalancing."""
        logger.info("[REMEDIATION_AGENCY] Running load rebalancing")
        
        try:
            from aico.ai.agency.tools.service_remediation import tool_agency_update_scheduler_config
            
            result = await tool_agency_update_scheduler_config(
                self._session_factory,
                task_id=input_data["task_id"],
                config_updates=input_data["config_updates"],
                dry_run=input_data.get("dry_run", True),
            )
            
            success = result.get("ok", False)
            data = result.get("data", {})
            
            return SkillResult(
                success=success,
                output={
                    "summary_status": "healthy" if success else "unhealthy",
                    "result": data,
                    "timestamp": datetime.now(UTC).isoformat(),
                },
                error=result.get("error", {}).get("message") if not success else None,
            )
        
        except Exception as exc:
            logger.error("[REMEDIATION_AGENCY] Load rebalancing failed: %s", exc)
            return SkillResult(
                success=False,
                output={
                    "summary_status": "unhealthy",
                    "error": str(exc),
                    "timestamp": datetime.now(UTC).isoformat(),
                },
                error=str(exc),
            )
