"""
AMS Thompson Sampling Update Task

Scheduled task for updating Thompson Sampling parameters based on processed feedback.
Runs daily at 4 AM (after feedback classification at 3 AM).

Schedule: Daily at 4 AM (configurable via cron)
"""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any

from aico.core.logging import get_logger
from .base import BaseTask, TaskContext, TaskResult

logger = get_logger("backend", "scheduler.tasks.ams_thompson_sampling")


class ThompsonSamplingUpdateTask(BaseTask):
    """
    Scheduled task for Thompson Sampling parameter updates.
    
    Updates Beta distribution parameters (α, β) for each (user, context, skill)
    triple based on processed feedback events.
    
    Configuration:
    - Schedule: core.memory.behavioral.contextual_bandit.update_interval_hours
    - Min trajectories: core.memory.behavioral.contextual_bandit.min_trajectories
    """
    
    task_id = "ams.thompson_sampling_update"
    default_config = {
        "enabled": False,  # Disabled until Phase 3 fully integrated
        "schedule": "0 4 * * *",  # Daily at 4 AM (after feedback classification)
        "min_trajectories": 10,
        "lookback_days": 7
    }
    
    async def execute(self, context: TaskContext) -> TaskResult:
        """
        Execute Thompson Sampling parameter update.
        
        Returns:
            TaskResult with update statistics
        """
        start_time = datetime.utcnow()
        
        try:
            logger.info("🧠 [AMS_TS] Starting Thompson Sampling update task")
            
            # Check if behavioral learning is enabled
            behavioral_config = context.config_manager.get("core.memory.behavioral", {})
            enabled = behavioral_config.get("enabled", False)
            
            if not enabled:
                logger.info("🧠 [AMS_TS] Behavioral learning disabled in configuration")
                return TaskResult(
                    success=False,
                    skipped=True,
                    message="Behavioral learning disabled",
                    data={"enabled": False}
                )
            
            # Get configuration
            min_trajectories = context.get_config("min_trajectories", 10)
            lookback_days = context.get_config("lookback_days", 7)
            lookback_date = (datetime.utcnow() - timedelta(days=lookback_days)).isoformat()
            
            # Get feedback events with skill assignments from last N days
            feedback_events = context.db_connection.execute(
                """SELECT user_id, skill_id, reward, timestamp
                   FROM feedback_events
                   WHERE skill_id IS NOT NULL 
                   AND reward != 0
                   AND timestamp >= ?
                   ORDER BY user_id, skill_id""",
                (lookback_date,)
            ).fetchall()
            
            if not feedback_events:
                logger.info("🧠 [AMS_TS] No feedback events to process")
                return TaskResult(
                    success=True,
                    message="No feedback events",
                    data={"updated": 0}
                )
            
            logger.info(f"🧠 [AMS_TS] Processing {len(feedback_events)} feedback events")
            
            # Group feedback by (user_id, skill_id)
            from collections import defaultdict
            user_skill_feedback = defaultdict(lambda: {"successes": 0, "failures": 0})
            
            for user_id, skill_id, reward, timestamp in feedback_events:
                key = (user_id, skill_id)
                if reward > 0:
                    user_skill_feedback[key]["successes"] += 1
                elif reward < 0:
                    user_skill_feedback[key]["failures"] += 1
            
            # Update Thompson Sampling parameters
            # Note: We use a simplified approach - update global skill stats
            # rather than context-specific buckets for this batch update
            
            updated_count = 0
            prior_alpha = behavioral_config.get("contextual_bandit", {}).get("prior_alpha", 1.0)
            prior_beta = behavioral_config.get("contextual_bandit", {}).get("prior_beta", 1.0)
            
            for (user_id, skill_id), stats in user_skill_feedback.items():
                successes = stats["successes"]
                failures = stats["failures"]
                
                # Skip if not enough data
                if successes + failures < min_trajectories:
                    continue
                
                # Update all context buckets for this user-skill pair
                # In practice, we'd want to track which context each feedback came from
                # For now, we update a default context bucket (0)
                context_bucket = 0
                
                # Calculate new α and β
                new_alpha = prior_alpha + successes
                new_beta = prior_beta + failures
                
                # Upsert into context_skill_stats
                context.db_connection.execute(
                    """INSERT INTO context_skill_stats (
                        user_id, context_bucket, skill_id, alpha, beta, last_updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?)
                    ON CONFLICT(user_id, context_bucket, skill_id)
                    DO UPDATE SET
                        alpha = excluded.alpha,
                        beta = excluded.beta,
                        last_updated_at = excluded.last_updated_at""",
                    (
                        user_id,
                        context_bucket,
                        skill_id,
                        new_alpha,
                        new_beta,
                        datetime.utcnow().isoformat()
                    )
                )
                
                updated_count += 1
                
                logger.debug(f"🧠 [AMS_TS] Updated {user_id}/{skill_id}: α={new_alpha:.1f}, β={new_beta:.1f}")
            
            context.db_connection.commit()
            
            execution_time = (datetime.utcnow() - start_time).total_seconds()
            
            logger.info(f"🧠 [AMS_TS] Update complete: {updated_count} user-skill pairs updated")
            
            return TaskResult(
                success=True,
                message=f"Updated {updated_count} Thompson Sampling parameters",
                duration_seconds=execution_time,
                data={
                    "feedback_events": len(feedback_events),
                    "user_skill_pairs": len(user_skill_feedback),
                    "updated": updated_count,
                    "min_trajectories": min_trajectories
                }
            )
            
        except Exception as e:
            execution_time = (datetime.utcnow() - start_time).total_seconds()
            logger.error(f"🧠 [AMS_TS] Task execution failed: {e}")
            
            return TaskResult(
                success=False,
                message=f"Task execution failed: {str(e)}",
                error=str(e),
                duration_seconds=execution_time
            )
