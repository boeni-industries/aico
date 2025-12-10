"""
Agency Self-Reflection Task

Runs periodic self-reflection jobs to analyze AICO's behavior and generate
behavioral learning lessons. Typically scheduled during low-activity periods
or "sleep" phases.
"""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any

from aico.ai.agency.engine import AgencyEngine
from aico.ai.agency.models import RunType
from aico.core.logging import get_logger

from .base import BaseTask, TaskContext, TaskResult


logger = get_logger("backend", "scheduler.agency_reflection")


class AgencyReflectionTask(BaseTask):
    """
    Periodic self-reflection task for behavioral learning.
    
    Analyzes recent behavior (skill usage, goal patterns, user feedback)
    and generates lessons for improvement. Runs during idle periods to
    minimize impact on active user interactions.
    """
    
    task_id = "agency_reflection"
    
    default_config = {
        "analysis_window_days": 7,  # How many days back to analyze
        "min_idle_minutes": 30,     # Minimum idle time before running
        "per_user": True,           # Run reflection per user
        "skip_on_battery": True,    # Skip when on battery power
    }
    
    async def execute(self, context: TaskContext) -> TaskResult:
        """
        Execute reflection job for all active users.
        
        Args:
            context: Task execution context
            
        Returns:
            TaskResult with reflection summary
        """
        start_time = datetime.utcnow()
        
        try:
            # Get configuration
            analysis_window_days = context.get_config("analysis_window_days", 7)
            min_idle_minutes = context.get_config("min_idle_minutes", 30)
            skip_on_battery = context.get_config("skip_on_battery", True)
            per_user = context.get_config("per_user", True)
            
            # Check if we should skip (battery, not idle, etc.)
            if skip_on_battery and context.should_skip_on_battery():
                logger.info("[REFLECTION] Skipping reflection - running on battery")
                return TaskResult(
                    success=True,
                    message="Skipped - running on battery",
                    skipped=True
                )
            
            if not context.system_idle():
                logger.info("[REFLECTION] Skipping reflection - system not idle")
                return TaskResult(
                    success=True,
                    message="Skipped - system not idle",
                    skipped=True
                )
            
            # Initialize agency engine
            agency_engine = AgencyEngine(
                config=context.config_manager,
                db_connection=context.db_connection,
            )
            
            # Get active users
            user_ids = await self._get_active_users(context)
            
            if not user_ids:
                logger.info("[REFLECTION] No active users found for reflection")
                return TaskResult(
                    success=True,
                    message="No active users to reflect on",
                    data={"users_processed": 0}
                )
            
            logger.info(f"[REFLECTION] Starting reflection for {len(user_ids)} users")
            
            # Run reflection for each user
            results = []
            for user_id in user_ids:
                try:
                    run = await agency_engine.run_self_reflection(
                        user_id=user_id,
                        run_type=RunType.SCHEDULED,
                        trigger_reason="scheduled_task",
                        analysis_window_days=analysis_window_days,
                    )
                    
                    results.append({
                        "user_id": user_id,
                        "run_id": run.run_id,
                        "lessons_generated": run.lessons_generated or 0,
                        "lessons_applied": run.lessons_applied or 0,
                        "status": run.status.value,
                    })
                    
                    logger.info(
                        f"[REFLECTION] User {user_id}: {run.lessons_generated} lessons generated, "
                        f"{run.lessons_applied} applied"
                    )
                    
                except Exception as e:
                    logger.error(f"[REFLECTION] Failed for user {user_id}: {e}", exc_info=True)
                    results.append({
                        "user_id": user_id,
                        "error": str(e),
                        "status": "failed",
                    })
            
            # Calculate summary
            total_lessons = sum(r.get("lessons_generated", 0) for r in results)
            total_applied = sum(r.get("lessons_applied", 0) for r in results)
            failed_count = sum(1 for r in results if r.get("status") == "failed")
            
            duration = (datetime.utcnow() - start_time).total_seconds()
            
            logger.info(
                f"[REFLECTION] Completed: {len(user_ids)} users, "
                f"{total_lessons} lessons generated, {total_applied} applied, "
                f"{failed_count} failures ({duration:.1f}s)"
            )
            
            return TaskResult(
                success=True,
                message=f"Reflection completed for {len(user_ids)} users",
                data={
                    "users_processed": len(user_ids),
                    "total_lessons_generated": total_lessons,
                    "total_lessons_applied": total_applied,
                    "failed_users": failed_count,
                    "results": results,
                },
                duration_seconds=duration,
            )
            
        except Exception as e:
            duration = (datetime.utcnow() - start_time).total_seconds()
            logger.error(f"[REFLECTION] Task failed: {e}", exc_info=True)
            
            return TaskResult(
                success=False,
                message="Reflection task failed",
                error=str(e),
                duration_seconds=duration,
            )
    
    async def _get_active_users(self, context: TaskContext) -> list[str]:
        """
        Get list of active users who should have reflection run.
        
        Active users are those who have had activity in the last 30 days.
        
        Args:
            context: Task execution context
            
        Returns:
            List of user UUIDs
        """
        try:
            # Query users with recent activity
            cutoff_date = datetime.utcnow() - timedelta(days=30)
            
            rows = context.db_connection.execute(
                """SELECT DISTINCT user_id 
                   FROM agency_goals 
                   WHERE created_at > ?
                   LIMIT 100""",  # Limit to prevent overwhelming the system
                (cutoff_date.isoformat(),)
            ).fetchall()
            
            user_ids = [row["user_id"] for row in rows]
            
            logger.debug(f"[REFLECTION] Found {len(user_ids)} active users")
            return user_ids
            
        except Exception as e:
            logger.error(f"[REFLECTION] Failed to get active users: {e}")
            return []
