"""
Goal Expiration Scheduled Task

Automatically expires old pending hobby goals that haven't been activated.
Prevents accumulation of stale curiosity-generated goals.
"""

from datetime import datetime, timedelta, UTC
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
            
            # Find expired goals via UoW - filter by ORIGIN not goal_type to ensure we never expire user goals
            from aico.data.postgres.connection import get_session_factory
            from aico.data.uow import UnitOfWork
            from aico.services.agency_service import AgencyService
            
            session_factory = await get_session_factory()
            async with UnitOfWork(session_factory) as uow:
                # Get pending goals
                pending_goals = await uow.goals.list(
                    filters={'status': 'pending'},
                    limit=10000
                )
                # Filter by origin and age in memory
                expired_goals = [
                    g for g in pending_goals
                    if (g.origin.value if hasattr(g.origin, 'value') else g.origin) in agent_origins
                    and g.created_at < threshold
                ]
            
            if not expired_goals:
                logger.info("[GOAL_EXPIRATION] No expired goals found")
                return TaskResult(
                    success=True,
                    message="No expired goals",
                    data={"expired_count": 0},
                )
            
            logger.info(f"[GOAL_EXPIRATION] Found {len(expired_goals)} expired goals")
            
            # Retire expired goals via UoW
            retired_count = 0
            async with UnitOfWork(session_factory) as uow:
                from aico.ai.agency.models import GoalStatus
                import json
                
                for goal in expired_goals:
                    try:
                        # Update goal status to retired
                        goal.status = GoalStatus.RETIRED
                        goal.updated_at = datetime.now(UTC)
                        
                        # Update metadata with retirement reason
                        if goal.metadata:
                            metadata = json.loads(goal.metadata) if isinstance(goal.metadata, str) else goal.metadata
                        else:
                            metadata = {}
                        metadata['retirement_reason'] = 'expired'
                        goal.metadata = json.dumps(metadata)
                        
                        await uow.goals.update(goal)
                        
                        # Remove from intention set
                        intentions = await uow.agency_intention_set.list(
                            filters={'goal_id': goal.goal_id},
                            limit=100
                        )
                        for intention in intentions:
                            await uow.agency_intention_set.delete(intention.intention_id)
                        
                        retired_count += 1
                        logger.debug(
                            f"[GOAL_EXPIRATION] Retired goal: {goal.title} "
                            f"(created {goal.created_at})"
                        )
                        
                    except Exception as e:
                        logger.error(
                            f"[GOAL_EXPIRATION] Failed to retire goal {goal.goal_id}: {e}"
                        )
                
                await uow.commit()
            
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
