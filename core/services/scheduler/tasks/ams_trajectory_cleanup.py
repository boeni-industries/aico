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
from datetime import datetime, timedelta, timezone
from typing import Dict, Any

from aico.core.logging import get_logger
from .base import BaseTask, TaskContext, TaskResult

logger = get_logger("core.scheduler.tasks.ams_trajectory_cleanup")


class TrajectoryCleanupTask(BaseTask):
    """
    Scheduled task for trajectory cleanup.
    
    Implements retention policy to prevent unbounded trajectory growth
    while preserving valuable feedback data.
    
    Configuration:
    - Schedule: Weekly on Sunday at 3 AM
    - Archive after: memory.behavioral.trajectory_logging.retention_days
    - Delete after: memory.behavioral.trajectory_logging.hard_delete_days
    """
    
    task_id = "ams.trajectory_cleanup"
    default_config = {
        "enabled": False,  # Disabled until Phase 3 fully integrated
        "schedule": "0 5 * * 0",  # Weekly on Sunday at 5:00 AM (with database vacuum)
        "archive_after_days": 90,
        "delete_after_days": 365
    }
    
    async def execute(self, context: TaskContext) -> TaskResult:
        """
        Execute trajectory cleanup task.
        
        Returns:
            TaskResult with cleanup statistics
        """
        start_time = datetime.now(timezone.utc)
        
        try:
            print("\n" + "="*60)
            print("🧠 [AMS_CLEANUP] Starting trajectory cleanup task")
            print("="*60)
            logger.info("🧠 [AMS_CLEANUP] Starting trajectory cleanup task")
            
            # Check if behavioral learning is enabled
            behavioral_config = context.config_manager.get("memory.behavioral", {})
            enabled = behavioral_config.get("enabled", False)
            
            print(f"🧠 [AMS_CLEANUP] Behavioral learning enabled: {enabled}")
            
            if not enabled:
                print("⚠️  [AMS_CLEANUP] Behavioral learning disabled - skipping task")
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
            
            archive_cutoff = datetime.now(timezone.utc) - timedelta(days=archive_after_days)
            print(f"\n [AMS_CLEANUP] Archiving trajectories older than {archive_cutoff.date()} ({archive_after_days} days)")
            logger.info(f" [AMS_CLEANUP] Archiving trajectories older than {archive_cutoff.date()} ({archive_after_days} days without feedback)")
            
            from aico.data.postgres.connection import get_session_factory
            from aico.data.uow import UnitOfWork
            
            session_factory = await get_session_factory()
            
            print("   Querying trajectories to archive...")
            # Archive old trajectories without feedback via UoW
            async with UnitOfWork(session_factory) as uow:
                # Get trajectories to archive
                old_trajectories = await uow.ams_trajectories.list(
                    filters={
                        'timestamp__lt': archive_cutoff,
                        'archived': False
                    },
                    limit=100000
                )
                
                # Filter out those with feedback
                feedback_trajectory_ids = set()
                all_feedback = await uow.ams_behavioral_feedback.list(
                    filters={'trajectory_id__ne': None},
                    limit=100000
                )
                feedback_trajectory_ids = {f.trajectory_id for f in all_feedback if f.trajectory_id}
                
                archived_count = 0
                for traj in old_trajectories:
                    if traj.trajectory_id not in feedback_trajectory_ids:
                        traj.archived = True
                        await uow.ams_trajectories.update(traj)
                        archived_count += 1
                
                await uow.commit()
            print(f"   Archived {archived_count} trajectories")
            
            delete_cutoff = datetime.now(timezone.utc) - timedelta(days=delete_after_days)
            print(f"\n [AMS_CLEANUP] Deleting archived trajectories older than {delete_cutoff.date()} ({delete_after_days} days)")
            logger.info(f" [AMS_CLEANUP] Deleting archived trajectories older than {delete_cutoff.date()} ({delete_after_days} days)")
            
            print("   Querying archived trajectories to delete...")
            async with UnitOfWork(session_factory) as uow:
                old_archived = await uow.ams_trajectories.list(
                    filters={
                        'timestamp__lt': delete_cutoff,
                        'archived': True
                    },
                    limit=100000
                )
                
                deleted_count = 0
                for traj in old_archived:
                    await uow.ams_trajectories.delete(traj.trajectory_id)
                    deleted_count += 1
                
                await uow.commit()
            print(f"   Deleted {deleted_count} archived trajectories")
            
            # Get current trajectory counts
            async with UnitOfWork(session_factory) as uow:
                all_trajs = await uow.ams_trajectories.list(limit=100000)
                total = len(all_trajs)
                archived = sum(1 for t in all_trajs if t.archived)
                with_feedback = sum(1 for t in all_trajs if t.feedback_reward is not None)
            
            duration = (datetime.now(timezone.utc) - start_time).total_seconds()
            print(f"\n [AMS_CLEANUP] Cleanup complete in {duration:.2f}s")
            print(f"   Archived: {archived_count} trajectories")
            print(f"   Deleted: {deleted_count} archived trajectories")
            print("="*60 + "\n")
            logger.info(f" [AMS_CLEANUP] Cleanup complete: archived={archived_count}, deleted={deleted_count} in {duration:.2f}s")
            logger.info(f" [AMS_CLEANUP] Current state: total={total}, archived={archived}, with_feedback={with_feedback}")
            
            return TaskResult(
                success=True,
                message=f"Archived {archived_count}, deleted {deleted_count} trajectories",
                duration_seconds=duration,
                data={
                    "archived": archived_count,
                    "deleted": deleted_count,
                    "current_total": total,
                    "current_archived": archived,
                    "current_with_feedback": with_feedback
                }
            )
            
        except Exception as e:
            execution_time = (datetime.now(timezone.utc) - start_time).total_seconds()
            logger.error(f"🧠 [AMS_CLEANUP] Task execution failed: {e}")
            
            return TaskResult(
                success=False,
                message=f"Task execution failed: {str(e)}",
                error=str(e),
                duration_seconds=execution_time
            )
