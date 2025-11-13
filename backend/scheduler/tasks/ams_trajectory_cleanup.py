"""
AMS Trajectory Cleanup Task

Scheduled task for cleaning up old trajectories based on retention policy.
Runs weekly on Sunday at 3 AM.

Retention Policy:
- Keep all trajectories with feedback indefinitely
- Archive trajectories without feedback after 90 days
- Hard delete archived trajectories after 365 days
"""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any

from aico.core.logging import get_logger
from .base import BaseTask, TaskContext, TaskResult

logger = get_logger("backend", "scheduler.tasks.ams_trajectory_cleanup")


class TrajectoryCleanupTask(BaseTask):
    """
    Scheduled task for trajectory cleanup.
    
    Implements retention policy to prevent unbounded trajectory growth
    while preserving valuable feedback data.
    
    Configuration:
    - Schedule: Weekly on Sunday at 3 AM
    - Archive after: core.memory.behavioral.trajectory_logging.retention_days
    - Delete after: core.memory.behavioral.trajectory_logging.hard_delete_days
    """
    
    task_id = "ams.trajectory_cleanup"
    default_config = {
        "enabled": False,  # Disabled until Phase 3 fully integrated
        "schedule": "0 3 * * 0",  # Weekly on Sunday at 3 AM
        "archive_after_days": 90,
        "delete_after_days": 365
    }
    
    async def execute(self, context: TaskContext) -> TaskResult:
        """
        Execute trajectory cleanup task.
        
        Returns:
            TaskResult with cleanup statistics
        """
        start_time = datetime.utcnow()
        
        try:
            logger.info("🧠 [AMS_CLEANUP] Starting trajectory cleanup task")
            
            # Check if behavioral learning is enabled
            behavioral_config = context.config_manager.get("core.memory.behavioral", {})
            enabled = behavioral_config.get("enabled", False)
            
            if not enabled:
                logger.info("🧠 [AMS_CLEANUP] Behavioral learning disabled in configuration")
                return TaskResult(
                    success=False,
                    skipped=True,
                    message="Behavioral learning disabled",
                    data={"enabled": False}
                )
            
            # Get configuration
            archive_after_days = context.get_config("archive_after_days", 90)
            delete_after_days = context.get_config("delete_after_days", 365)
            
            archive_cutoff = (datetime.utcnow() - timedelta(days=archive_after_days)).isoformat()
            delete_cutoff = (datetime.utcnow() - timedelta(days=delete_after_days)).isoformat()
            
            # Step 1: Archive old trajectories without feedback
            logger.info(f"🧠 [AMS_CLEANUP] Archiving trajectories older than {archive_after_days} days without feedback")
            
            archive_result = context.db_connection.execute(
                """UPDATE trajectories 
                   SET archived = TRUE
                   WHERE feedback_reward IS NULL 
                   AND timestamp < ?
                   AND archived = FALSE""",
                (archive_cutoff,)
            )
            
            archived_count = archive_result.rowcount if hasattr(archive_result, 'rowcount') else 0
            
            # Step 2: Hard delete very old archived trajectories
            logger.info(f"🧠 [AMS_CLEANUP] Deleting archived trajectories older than {delete_after_days} days")
            
            delete_result = context.db_connection.execute(
                """DELETE FROM trajectories
                   WHERE archived = TRUE
                   AND timestamp < ?""",
                (delete_cutoff,)
            )
            
            deleted_count = delete_result.rowcount if hasattr(delete_result, 'rowcount') else 0
            
            context.db_connection.commit()
            
            # Get current trajectory counts
            stats = context.db_connection.execute(
                """SELECT 
                    COUNT(*) as total,
                    SUM(CASE WHEN archived = TRUE THEN 1 ELSE 0 END) as archived,
                    SUM(CASE WHEN feedback_reward IS NOT NULL THEN 1 ELSE 0 END) as with_feedback
                   FROM trajectories"""
            ).fetchone()
            
            total, archived, with_feedback = stats if stats else (0, 0, 0)
            
            execution_time = (datetime.utcnow() - start_time).total_seconds()
            
            logger.info(f"🧠 [AMS_CLEANUP] Cleanup complete: archived={archived_count}, deleted={deleted_count}")
            logger.info(f"🧠 [AMS_CLEANUP] Current state: total={total}, archived={archived}, with_feedback={with_feedback}")
            
            return TaskResult(
                success=True,
                message=f"Archived {archived_count}, deleted {deleted_count} trajectories",
                duration_seconds=execution_time,
                data={
                    "archived": archived_count,
                    "deleted": deleted_count,
                    "current_total": total,
                    "current_archived": archived,
                    "current_with_feedback": with_feedback
                }
            )
            
        except Exception as e:
            execution_time = (datetime.utcnow() - start_time).total_seconds()
            logger.error(f"🧠 [AMS_CLEANUP] Task execution failed: {e}")
            
            return TaskResult(
                success=False,
                message=f"Task execution failed: {str(e)}",
                error=str(e),
                duration_seconds=execution_time
            )
