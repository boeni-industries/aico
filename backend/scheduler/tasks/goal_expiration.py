"""
Goal Expiration Scheduled Task

Automatically expires old pending hobby goals that haven't been activated.
Prevents accumulation of stale curiosity-generated goals.
"""

from datetime import datetime, timedelta, timezone
from typing import Any, Dict

from .base import BaseTask, TaskContext, TaskResult
from aico.core.logging import get_logger

logger = get_logger("backend.scheduler.tasks.goal_expiration")


class GoalExpirationTask(BaseTask):
    """Scheduled task to expire old pending hobby goals.
    
    Runs periodically to:
    1. Find pending hobby/curiosity goals older than threshold
    2. Mark them as retired with reason "expired"
    3. Clean up associated intentions
    
    Prevents accumulation of stale goals from curiosity engine.
    """
    
    task_id = "agency.goal_expiration"
    default_config = {
        "enabled": True,
        "schedule": "0 4 * * *",  # Daily at 4 AM
        "description": "Expire old pending hobby goals",
        "expiration_days": 7,  # Goals older than 7 days
        "goal_types": ["hobby", "curiosity"],  # Only expire these types
    }
    
    async def execute(self, context: TaskContext) -> TaskResult:
        """Execute goal expiration.
        
        Args:
            context: Task execution context with services
            
        Returns:
            TaskResult with expiration statistics
        """
        start_time = datetime.now(UTC)
        
        try:
            logger.info("[GOAL_EXPIRATION] Starting goal expiration task")
            
            # Use hardcoded defaults (no config needed - these are safety constraints)
            expiration_days = 7  # Goals older than 7 days (matches arbiter freshness window)
            agent_origins = ["hobby", "curiosity"]  # Only auto-expire agent-generated goals, never user goals
            
            # Calculate expiration threshold
            threshold = datetime.now(UTC) - timedelta(days=expiration_days)
            threshold_str = threshold.isoformat()
            
            # Get database connection
            db = context.db_connection
            
            # Find expired goals - filter by ORIGIN not goal_type to ensure we never expire user goals
            expired_goals = db.execute(
                """SELECT goal_id, user_id, title, origin, goal_type, created_at 
                   FROM agency_goals 
                   WHERE status = 'pending' 
                   AND origin IN ({})
                   AND created_at < ?
                   ORDER BY created_at""".format(','.join('?' * len(agent_origins))),
                tuple(agent_origins + [threshold_str])
            ).fetchall()
            
            if not expired_goals:
                logger.info("[GOAL_EXPIRATION] No expired goals found")
                return TaskResult(
                    success=True,
                    message="No expired goals",
                    data={"expired_count": 0},
                )
            
            logger.info(f"[GOAL_EXPIRATION] Found {len(expired_goals)} expired goals")
            
            # Retire expired goals
            retired_count = 0
            for goal in expired_goals:
                try:
                    # Update goal status to retired
                    db.execute(
                        """UPDATE agency_goals 
                           SET status = 'retired', 
                               updated_at = ?,
                               metadata = json_set(COALESCE(metadata, '{}'), '$.retirement_reason', 'expired')
                           WHERE goal_id = ?""",
                        (datetime.now(UTC).isoformat(), goal['goal_id'])
                    )
                    
                    # Remove from intention set
                    db.execute(
                        "DELETE FROM agency_intention_set WHERE goal_id = ?",
                        (goal['goal_id'],)
                    )
                    
                    retired_count += 1
                    logger.debug(
                        f"[GOAL_EXPIRATION] Retired goal: {goal['title']} "
                        f"(created {goal['created_at']})"
                    )
                    
                except Exception as e:
                    logger.error(
                        f"[GOAL_EXPIRATION] Failed to retire goal {goal['goal_id']}: {e}"
                    )
            
            # Commit changes
            db.commit()
            
            # Calculate execution time
            duration = (datetime.now(UTC) - start_time).total_seconds()
            
            logger.info(
                f"[GOAL_EXPIRATION] Complete: retired {retired_count}/{len(expired_goals)} goals, "
                f"{duration:.1f}s"
            )
            
            return TaskResult(
                success=True,
                message=f"Retired {retired_count} expired goals",
                data={
                    "expired_count": len(expired_goals),
                    "retired_count": retired_count,
                    "expiration_days": expiration_days,
                    "threshold": threshold_str,
                },
                duration_seconds=duration,
            )
            
        except Exception as e:
            duration = (datetime.now(UTC) - start_time).total_seconds()
            logger.error(f"[GOAL_EXPIRATION] Task failed: {e}")
            
            return TaskResult(
                success=False,
                message=f"Goal expiration failed: {str(e)}",
                error=str(e),
                duration_seconds=duration,
            )
