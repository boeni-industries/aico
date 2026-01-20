"""
AMS Thompson Sampling Update Task

Scheduled task for updating Thompson Sampling parameters based on processed feedback.
Runs daily at 4 AM (after feedback classification at 3 AM).

Schedule: Daily at 4 AM (configurable via cron)
"""

import asyncio
from datetime import datetime, timedelta, timezone
from typing import Dict, Any

from aico.core.logging import get_logger
from .base import BaseTask, TaskContext, TaskResult

logger = get_logger("backend.scheduler.tasks.ams_thompson_sampling")


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
        "enabled": True,  # ENABLED - Phase 3 implementation complete
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
        start_time = datetime.now(timezone.utc)
        
        try:
            print("\n" + "="*60)
            print("🧠 [AMS_TS] Starting Thompson Sampling update task")
            print("="*60)
            logger.info("🧠 [AMS_TS] Starting Thompson Sampling update task")
            
            # Check if behavioral learning is enabled
            behavioral_config = context.config_manager.get("core.memory.behavioral", {})
            enabled = behavioral_config.get("enabled", False)
            
            print(f"🧠 [AMS_TS] Behavioral learning enabled: {enabled}")
            
            if not enabled:
                print("⚠️  [AMS_TS] Behavioral learning disabled - skipping task")
                logger.info("🧠 [AMS_TS] Behavioral learning disabled in configuration")
                return TaskResult(
                    success=False,
                    skipped=True,
                    message="Behavioral learning disabled",
                    data={"enabled": False}
                )
            
            # Get configuration from behavioral config
            min_trajectories = behavioral_config.get("contextual_bandit", {}).get("min_trajectories", 1)
            lookback_days = context.get_config("lookback_days", 7)
            # Use a datetime object for lookback_date so we can compare against
            # the timestamp field (which is stored as a TIMESTAMP in PostgreSQL).
            lookback_date = datetime.now(timezone.utc) - timedelta(days=lookback_days)
            
            # Get feedback events from last N days via UoW
            from aico.data.postgres.connection import get_session_factory
            from aico.data.uow import UnitOfWork
            
            session_factory = await get_session_factory()
            async with UnitOfWork(session_factory) as uow:
                all_feedback = await uow.ams_behavioral_feedback.list(
                    filters={'reward__ne': 0},
                    limit=100000
                )
                # Filter in memory for timestamp and valid skill_id.
                # Be tolerant to legacy rows where timestamp may have been
                # stored as an ISO8601 string instead of a datetime.
                feedback_events = []
                for f in all_feedback:
                    ts = f.timestamp
                    if isinstance(ts, str):
                        try:
                            # fromisoformat handles the strings written by our tests
                            ts = datetime.fromisoformat(ts)
                        except Exception:
                            continue
                    if not ts or not f.skill_id or not f.skill_id.strip():
                        continue
                    if ts >= lookback_date:
                        feedback_events.append((f.user_id, f.skill_id, f.reward, ts))
            
            if not feedback_events:
                print("  [AMS_TS] No feedback events to process")
                logger.info(" [AMS_TS] No feedback events to process")
                return TaskResult(
                    success=True,
                    message="No feedback events",
                    data={"updated": 0}
                )
            
            print(f" [AMS_TS] Found {len(feedback_events)} feedback events to process")
            logger.info(f" [AMS_TS] Processing {len(feedback_events)} feedback events")
            
            # Group feedback by (user_id, skill_id)
            from collections import defaultdict
            user_skill_feedback = defaultdict(lambda: {"successes": 0, "failures": 0})
            
            for user_id, skill_id, reward, timestamp in feedback_events:
                # skill_id is guaranteed to be non-NULL/non-empty by the query filter
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
            
            print(f"\n [AMS_TS] Updating {len(user_skill_feedback)} user-skill pairs...")
            print(f"   Prior: α={prior_alpha}, β={prior_beta}")
            
            for idx, ((user_id, skill_id), stats) in enumerate(user_skill_feedback.items(), 1):
                successes = stats["successes"]
                failures = stats["failures"]
                
                print(f"  [{idx}/{len(user_skill_feedback)}] User: {user_id[:8]}..., Skill: {skill_id or 'None'}")
                print(f"      Feedback: +{successes} / -{failures}")
                
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
                
                print(f"      New: α={new_alpha:.2f}, β={new_beta:.2f}")
                
                # Upsert into ams_context_skill_stats via UoW
                async with UnitOfWork(session_factory) as uow:
                    from aico.data.ams.models import AMSContextSkillStats
                    
                    # Check if exists
                    existing = await uow.ams_context_skill_stats.get(
                        filters={
                            'user_id': user_id,
                            'context_bucket': context_bucket,
                            'skill_id': skill_id
                        }
                    )
                    
                    stats_data = AMSContextSkillStats(
                        user_id=user_id,
                        context_bucket=context_bucket,
                        skill_id=skill_id,
                        alpha=new_alpha,
                        beta=new_beta,
                        last_updated_at=datetime.now(timezone.utc)
                    )
                    
                    if existing:
                        await uow.ams_context_skill_stats.update(stats_data)
                    else:
                        await uow.ams_context_skill_stats.create(stats_data)
                    
                    await uow.commit()
                
                updated_count += 1
                
                logger.debug(f" [AMS_TS] Updated {user_id}/{skill_id}: α={new_alpha:.1f}, β={new_beta:.1f}")
            
            duration = (datetime.now(timezone.utc) - start_time).total_seconds()
            print(f"\n [AMS_TS] Updated {updated_count} skill confidences in {duration:.2f}s")
            print(f"   Processed {len(feedback_events)} feedback events")
            print("="*60 + "\n")
            logger.info(f" [AMS_TS] Updated {updated_count} skill confidences in {duration:.2f}s")
            
            return TaskResult(
                success=True,
                message=f"Updated {updated_count} Thompson Sampling parameters",
                duration_seconds=duration,
                data={
                    "feedback_events": len(feedback_events),
                    "user_skill_pairs": len(user_skill_feedback),
                    "updated": updated_count,
                    "min_trajectories": min_trajectories
                }
            )
            
        except Exception as e:
            execution_time = (datetime.now(timezone.utc) - start_time).total_seconds()
            logger.error(f"🧠 [AMS_TS] Task execution failed: {e}")
            
            return TaskResult(
                success=False,
                message=f"Task execution failed: {str(e)}",
                error=str(e),
                duration_seconds=execution_time
            )
