"""
Agency Arbiter Task

Periodically evaluates pending goals and updates the active intention set.
This is the core decision-making loop that converts goals into active intentions.
"""

from datetime import datetime, timezone
from typing import Dict, Any

from backend.scheduler.tasks.base import BaseTask, TaskContext, TaskResult
from aico.core.logging import get_logger

logger = get_logger("backend.scheduler.tasks.agency_arbiter")


class AgencyArbiterTask(BaseTask):
    """
    Scheduled task to run the Goal Arbiter and update intention sets.
    
    The Arbiter:
    1. Collects pending goals from all sources (user, curiosity, maintenance)
    2. Scores and ranks them using personality, emotion, values, and context
    3. Updates the active intention set (top-ranked goals become active)
    4. Publishes changes to message bus for other components
    
    Runs frequently (every 5 minutes) to ensure responsive goal activation.
    """
    
    task_id = "agency.arbiter"
    description = "Run Goal Arbiter to update active intention sets"
    
    default_config = {
        "enabled": True,
        "schedule": "*/5 * * * *",  # Every 5 minutes
        "max_users_per_run": 10,  # Limit to prevent overwhelming system
    }
    
    async def execute(self, context: TaskContext) -> TaskResult:
        """
        Execute arbiter evaluation for active users.
        
        Args:
            context: Task execution context
            
        Returns:
            TaskResult with arbiter statistics
        """
        start_time = datetime.now(timezone.utc)
        
        try:
            print("🎯 [ARBITER_TASK] Starting arbiter evaluation")
            logger.info("🎯 [ARBITER_TASK] Starting arbiter evaluation")
            
            # Get configuration
            max_users = context.get_config("max_users_per_run", 10)
            
            # Get active users (users with pending goals)
            user_ids = await self._get_active_users(context, max_users)
            
            if not user_ids:
                print("🎯 [ARBITER_TASK] No active users with pending goals")
                logger.info("🎯 [ARBITER_TASK] No active users with pending goals")
                return TaskResult(
                    success=True,
                    message="No active users to evaluate",
                    data={"users_processed": 0}
                )
            
            print(f"🎯 [ARBITER_TASK] Evaluating {len(user_ids)} users")
            logger.info(f"🎯 [ARBITER_TASK] Evaluating {len(user_ids)} users")
            
            # Get agency engine from AI registry
            from aico.ai import ai_registry
            agency_engine = ai_registry.get("agency")
            
            if not agency_engine:
                print("🎯 [ARBITER_TASK] ❌ Agency engine not found in AI registry")
                logger.error("🎯 [ARBITER_TASK] Agency engine not found in AI registry")
                return TaskResult(
                    success=False,
                    message="Agency engine not available",
                    error="AgencyEngine not registered in ai_registry"
                )
            
            # Process each user
            results = []
            for user_id in user_ids:
                try:
                    # Get pending goals for this user
                    pending_goals = await self._get_pending_goals(context, user_id)
                    
                    if not pending_goals:
                        print(f"🎯 [ARBITER_TASK] No pending goals for user {user_id}")
                        logger.debug(f"🎯 [ARBITER_TASK] No pending goals for user {user_id}")
                        continue
                    
                    print(f"🎯 [ARBITER_TASK] User {user_id}: {len(pending_goals)} pending goals")
                    logger.info(f"🎯 [ARBITER_TASK] User {user_id}: {len(pending_goals)} pending goals")
                    
                    # Update intention set via agency engine
                    intention_set = await agency_engine.update_intention_set_for_user(
                        user_id=user_id,
                        context={
                            "trigger": "scheduled_arbiter",
                            "timestamp": datetime.now(timezone.utc).isoformat()
                        }
                    )
                    
                    active_count = len(intention_set.active_intentions)
                    total_count = len(intention_set.intentions)
                    
                    results.append({
                        "user_id": user_id,
                        "pending_goals": len(pending_goals),
                        "active_intentions": active_count,
                        "total_intentions": total_count,
                        "status": "success"
                    })
                    
                    print(f"🎯 [ARBITER_TASK] User {user_id}: {active_count} active intentions from {len(pending_goals)} goals")
                    logger.info(
                        f"🎯 [ARBITER_TASK] User {user_id}: "
                        f"{active_count} active intentions from {len(pending_goals)} goals"
                    )
                    
                except Exception as e:
                    print(f"🎯 [ARBITER_TASK] ❌ Failed for user {user_id}: {e}")
                    import traceback
                    print(f"🎯 [ARBITER_TASK] Traceback: {traceback.format_exc()}")
                    logger.exception(f"🎯 [ARBITER_TASK] Failed for user {user_id}: {e}")
                    results.append({
                        "user_id": user_id,
                        "error": str(e),
                        "status": "failed"
                    })
            
            # Calculate summary
            successful = sum(1 for r in results if r.get("status") == "success")
            failed = sum(1 for r in results if r.get("status") == "failed")
            total_active = sum(r.get("active_intentions", 0) for r in results)
            
            duration = (datetime.now(timezone.utc) - start_time).total_seconds()
            
            print(f"🎯 [ARBITER_TASK] Completed: {successful} successful, {failed} failed, {total_active} total active intentions ({duration:.1f}s)")
            logger.info(
                f"🎯 [ARBITER_TASK] Completed: {successful} successful, {failed} failed, "
                f"{total_active} total active intentions ({duration:.1f}s)"
            )
            
            return TaskResult(
                success=True,
                message=f"Arbiter evaluated {len(user_ids)} users",
                data={
                    "users_processed": len(user_ids),
                    "successful": successful,
                    "failed": failed,
                    "total_active_intentions": total_active,
                    "results": results,
                },
                duration_seconds=duration,
            )
            
        except Exception as e:
            duration = (datetime.now(timezone.utc) - start_time).total_seconds()
            print(f"🎯 [ARBITER_TASK] ❌ Task failed: {e}")
            import traceback
            print(f"🎯 [ARBITER_TASK] Traceback: {traceback.format_exc()}")
            logger.exception(f"🎯 [ARBITER_TASK] Task failed: {e}")
            
            return TaskResult(
                success=False,
                message="Arbiter task failed",
                error=str(e),
                duration_seconds=duration,
            )
    
    async def _get_active_users(self, context: TaskContext, limit: int) -> list[str]:
        """
        Get list of users with pending goals.
        
        Args:
            context: Task execution context
            limit: Maximum number of users to return
            
        Returns:
            List of user UUIDs
        """
        try:
            from aico.data.postgres.connection import get_session_factory
            from aico.data.uow import UnitOfWork
            from aico.services.agency_service import AgencyService, GoalStatus
            
            session_factory = await get_session_factory()
            async with UnitOfWork(session_factory) as uow:
                agency_service = AgencyService(uow)
                # Use service-layer helper to retrieve pending goals across users
                pending_goals = await agency_service.get_goals_by_status(GoalStatus.PENDING, limit=limit * 10)
                
                # Get unique user IDs from pending goals
                user_ids = list({g.user_id for g in pending_goals})[:limit]
            
            logger.debug(f"🎯 [ARBITER_TASK] Found {len(user_ids)} users with pending goals")
            return user_ids
            
        except Exception as e:
            logger.error(f"🎯 [ARBITER_TASK] Failed to get active users: {e}")
            return []
    
    async def _get_pending_goals(self, context: TaskContext, user_id: str) -> list[Dict[str, Any]]:
        """
        Get pending goals for a user.
        
        Args:
            context: Task execution context
            user_id: User UUID
            
        Returns:
            List of goal dictionaries
        """
        try:
            from aico.data.postgres.connection import get_session_factory
            from aico.data.uow import UnitOfWork
            from aico.services.agency_service import AgencyService
            
            session_factory = await get_session_factory()
            async with UnitOfWork(session_factory) as uow:
                agency_service = AgencyService(uow)
                from aico.ai.agency.models import GoalStatus
                goal_models = await agency_service.list_goals(user_id, status=GoalStatus.PENDING)
                
                # Convert to dicts
                goals = [
                    {
                        'goal_id': g.goal_id,
                        'title': g.title,
                        'origin': g.origin.value if hasattr(g.origin, 'value') else g.origin,
                        'priority': g.priority.value if hasattr(g.priority, 'value') else g.priority,
                        'created_at': g.created_at
                    }
                    for g in goal_models
                ]
            
            return goals
            
        except Exception as e:
            logger.error(f"🎯 [ARBITER_TASK] Failed to get pending goals for {user_id}: {e}")
            return []
