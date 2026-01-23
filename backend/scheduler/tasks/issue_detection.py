"""Issue Detection Scheduled Task

Runs the IssueDetectionService periodically to monitor system health
and automatically detect, create, and resolve issues.
"""

from datetime import datetime, UTC
from typing import Dict, Any

from aico.core.logging import get_logger
from backend.scheduler.tasks.base import BaseTask, TaskContext, TaskResult
from backend.services.issue_detection_service import IssueDetectionService


logger = get_logger("backend.scheduler.tasks.issue_detection")


class IssueDetectionTask(BaseTask):
    """Scheduled task for running issue detection cycles."""
    
    task_id = "system.health.issue_detection"
    
    def get_default_config(self) -> Dict[str, Any]:
        """Get default configuration for this task."""
        return {
            "enabled": True,
            "schedule": "*/5 * * * *",  # Every 5 minutes
            "timeout": 300,  # 5 minutes
            "description": "Monitor system health and detect/resolve issues",
        }
    
    async def execute(self, context: TaskContext) -> TaskResult:
        """Execute issue detection cycle.
        
        Args:
            context: Task execution context
            
        Returns:
            TaskResult with detection summary
        """
        logger.info("[ISSUE_DETECTION_TASK] Starting issue detection cycle")
        
        try:
            # Get dependencies from service container
            config_manager = context.config_manager
            
            # Get session factory
            from aico.data.postgres.connection import get_session_factory
            session_factory = await get_session_factory()
            
            # Create skill registry and register maintenance skills
            from aico.ai.agency.skills.registry import SkillRegistry
            from aico.ai.agency.skills.maintenance import (
                MaintenanceConnectivityFullScanSkill,
                MaintenanceSystemScanResourcesSkill,
                MaintenanceModelserviceScanHealthSkill,
                MaintenanceAgencyReEvaluateBehaviourHealthSkill,
            )
            
            skill_registry = SkillRegistry()
            skill_registry.register(MaintenanceConnectivityFullScanSkill(session_factory))
            skill_registry.register(MaintenanceSystemScanResourcesSkill())
            skill_registry.register(MaintenanceModelserviceScanHealthSkill())
            skill_registry.register(MaintenanceAgencyReEvaluateBehaviourHealthSkill(session_factory))
            
            # Create issue detection service
            service = IssueDetectionService(
                config=config_manager,
                session_factory=session_factory,
                skill_registry=skill_registry,
            )
            
            # Run detection cycle
            result = await service.run_detection_cycle()
            
            # Log results
            detected = result.get("detected_count", 0)
            resolved = result.get("resolved_count", 0)
            
            logger.info(
                "[ISSUE_DETECTION_TASK] Cycle complete: %d detected, %d resolved",
                detected,
                resolved
            )
            
            # Return success
            return TaskResult(
                success=True,
                message=f"Detected {detected} issues, resolved {resolved} issues",
                data={
                    "detected_count": detected,
                    "resolved_count": resolved,
                    "detected_issues": result.get("detected_issues", []),
                    "resolved_issues": result.get("resolved_issues", []),
                    "timestamp": datetime.now(UTC).isoformat(),
                }
            )
            
        except Exception as exc:
            logger.error("[ISSUE_DETECTION_TASK] Detection cycle failed: %s", exc)
            return TaskResult(
                success=False,
                error=str(exc),
                message="Issue detection cycle failed"
            )
    
    async def cleanup(self):
        """Cleanup task resources."""
        logger.debug("[ISSUE_DETECTION_TASK] Cleanup complete")
