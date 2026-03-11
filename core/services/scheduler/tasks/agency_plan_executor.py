"""
Agency Plan Executor Task

Periodically executes pending plan steps for active intentions.
This is the core execution loop that converts plans into actions.
"""

from datetime import datetime, timezone
from typing import Dict, Any

from core.services.scheduler.tasks.base import BaseTask, TaskContext, TaskResult
from aico.core.logging import get_logger

logger = get_logger("backend.scheduler.tasks.agency_plan_executor")


class AgencyPlanExecutorTask(BaseTask):
    """
    Scheduled task to execute plan steps for active intentions.
    
    The Plan Executor:
    1. Finds plans for active intentions without running executions
    2. Starts new executions or continues existing ones
    3. Executes next pending step for each execution
    4. Handles errors and records results
    5. Updates plan and goal status based on completion
    
    Runs frequently (every 2 minutes) to ensure responsive execution.
    """
    
    task_id = "agency.plan_executor"
    description = "Execute plan steps for active intentions"
    
    default_config = {
        "enabled": True,
        "schedule": "*/2 * * * *",  # Every 2 minutes
        "max_executions_per_run": 10,  # Limit concurrent executions
        "steps_per_execution": 3,  # Steps to execute per run per execution
    }
    
    async def execute(self, context: TaskContext) -> TaskResult:
        """
        Execute plan steps for active intentions.
        
        Args:
            context: Task execution context
            
        Returns:
            TaskResult with execution statistics
        """
        start_time = datetime.now(timezone.utc)
        
        try:
            logger.debug("Starting plan execution cycle")
            
            # Get configuration
            max_executions = context.get_config("max_executions_per_run", 10)
            steps_per_execution = context.get_config("steps_per_execution", 3)
            
            # Get plan executor from AI registry
            from aico.ai import ai_registry
            agency_engine = ai_registry.get("agency")
            
            if not agency_engine:
                logger.error("Agency engine not found in AI registry")
                return TaskResult(
                    success=False,
                    message="Agency engine not available",
                    error="AgencyEngine not registered in ai_registry"
                )
            
            # Get executor
            executor = agency_engine.executor
            if not executor:
                logger.error("Plan executor not initialized")
                return TaskResult(
                    success=False,
                    message="Plan executor not initialized",
                    error="PlanExecutor not available in AgencyEngine"
                )
            
            # Get active executions (running or pending)
            active_executions = await self._get_active_executions(
                context, 
                max_executions
            )
            
            if not active_executions:
                # No active executions - check for plans that need execution
                pending_plans = await self._get_plans_needing_execution(
                    context,
                    max_executions
                )
                
                if not pending_plans:
                    logger.debug("No plans to execute")
                    return TaskResult(
                        success=True,
                        message="No plans to execute",
                        data={"executions_processed": 0}
                    )
                
                # Start executions for pending plans
                logger.debug(f"Starting {len(pending_plans)} new executions")
                for plan_info in pending_plans:
                    try:
                        logger.debug(
                            f"Starting execution for plan {plan_info['plan_id'][:8]}... "
                            f"goal={plan_info['goal_id'][:8]}..."
                        )
                        
                        execution = await executor.start_execution(
                            plan_id=plan_info["plan_id"],
                            goal_id=plan_info["goal_id"],
                            user_id=plan_info["user_id"],
                            context={
                                "trigger": "scheduled_executor",
                                "timestamp": datetime.now(timezone.utc).isoformat()
                            }
                        )
                        active_executions.append({
                            "execution_id": execution.execution_id,
                            "plan_id": execution.plan_id,
                            "goal_id": execution.goal_id,
                            "user_id": execution.user_id,
                        })
                        
                        logger.debug(
                            f"Started execution {execution.execution_id[:8]}... "
                            f"for plan {plan_info['plan_id'][:8]}... ({execution.steps_total} steps)"
                        )
                    except Exception as e:
                        logger.error(
                            f"Failed to start execution for plan {plan_info['plan_id'][:8]}...: {e}",
                            exc_info=True
                        )
            
            # Execute steps for active executions
            logger.debug(
                f"Processing {len(active_executions)} active executions "
                f"(up to {steps_per_execution} steps each)"
            )
            
            results = []
            for exec_info in active_executions:
                try:
                    steps_executed = 0
                    exec_id_short = exec_info["execution_id"][:8]
                    
                    logger.debug(
                        f"Processing execution {exec_id_short}... plan={exec_info['plan_id'][:8]}..."
                    )
                    
                    # Execute up to N steps per execution
                    for step_num in range(steps_per_execution):
                        has_more, step_exec = await executor.execute_next_step(
                            exec_info["execution_id"]
                        )
                        
                        if step_exec:
                            steps_executed += 1
                            status_emoji = "✅" if step_exec.status.value == "completed" else "❌"
                            
                            logger.debug(
                                f"Step {step_exec.step_order} for execution {exec_id_short}...: "
                                f"{step_exec.status.value} (duration: {step_exec.duration_ms}ms)"
                            )
                        
                        if not has_more:
                            logger.debug(
                                f"Execution {exec_id_short}... completed ({steps_executed} steps executed)"
                            )
                            break
                    
                    results.append({
                        "execution_id": exec_info["execution_id"],
                        "plan_id": exec_info["plan_id"],
                        "steps_executed": steps_executed,
                        "status": "success"
                    })
                    
                except Exception as e:
                    logger.exception(
                        f"Failed to execute steps for execution {exec_info['execution_id'][:8]}...: {e}"
                    )
                    results.append({
                        "execution_id": exec_info["execution_id"],
                        "error": str(e),
                        "status": "failed"
                    })
            
            # Calculate summary
            successful = sum(1 for r in results if r.get("status") == "success")
            failed = sum(1 for r in results if r.get("status") == "failed")
            total_steps = sum(r.get("steps_executed", 0) for r in results)
            
            duration = (datetime.now(timezone.utc) - start_time).total_seconds()
            
            logger.info(
                f"Plan executor completed: {successful} successful, {failed} failed, "
                f"{total_steps} steps executed ({duration:.1f}s)"
            )
            
            return TaskResult(
                success=True,
                message=f"Executed {total_steps} steps across {len(results)} executions",
                data={
                    "executions_processed": len(results),
                    "successful": successful,
                    "failed": failed,
                    "total_steps_executed": total_steps,
                    "results": results,
                },
                duration_seconds=duration,
            )
            
        except Exception as e:
            duration = (datetime.now(timezone.utc) - start_time).total_seconds()
            logger.exception(f"Plan executor task failed: {e}")
            
            return TaskResult(
                success=False,
                message="Plan executor task failed",
                error=str(e),
                duration_seconds=duration,
            )
    
    async def _get_active_executions(
        self,
        context: TaskContext,
        limit: int
    ) -> list[Dict[str, Any]]:
        """Get active plan executions (running or pending)."""
        try:
            from aico.data.postgres.connection import get_session_factory
            from aico.data.uow import UnitOfWork
            
            session_factory = await get_session_factory()
            async with UnitOfWork(session_factory) as uow:
                # Get active executions via repository
                all_executions = await uow.agency_plan_executions.list(
                    filters={'status__in': ['pending', 'running']},
                    limit=limit
                )
                
                executions = [
                    {
                        'execution_id': e.execution_id,
                        'plan_id': e.plan_id,
                        'goal_id': e.goal_id,
                        'user_id': e.user_id
                    }
                    for e in all_executions
                ]
            
            logger.debug(
                f"🎬 [PLAN_EXECUTOR_TASK] Found {len(executions)} active executions"
            )
            return executions
            
        except Exception as e:
            logger.error(f"🎬 [PLAN_EXECUTOR_TASK] Failed to get active executions: {e}")
            return []
    
    async def _get_plans_needing_execution(
        self,
        context: TaskContext,
        limit: int
    ) -> list[Dict[str, Any]]:
        """Get plans for active intentions that don't have executions."""
        try:
            from aico.data.postgres.connection import get_session_factory
            from aico.data.uow import UnitOfWork
            from aico.services.agency_service import AgencyService
            
            session_factory = await get_session_factory()
            async with UnitOfWork(session_factory) as uow:
                agency_service = AgencyService(uow)
                
                # Get active intentions
                active_intentions = await uow.agency_intention_set.list(
                    filters={'status': 'active'},
                    limit=1000
                )
                
                # Get plans for these goals
                plans_needing_exec = []
                for intention in active_intentions[:limit*2]:  # Check more than limit
                    # Use list_plans instead of get_goal_plans
                    plans = await agency_service.list_plans(intention.goal_id)
                    
                    for plan in plans:
                        if plan.status in ['draft', 'active']:
                            # Check if execution exists
                            executions = await uow.agency_plan_executions.list(
                                filters={
                                    'plan_id': plan.plan_id,
                                    'status__in': ['pending', 'running']
                                },
                                limit=1
                            )
                            
                            if not executions:
                                goal = await agency_service.get_goal(intention.goal_id)
                                plans_needing_exec.append({
                                    'plan_id': plan.plan_id,
                                    'goal_id': plan.goal_id,
                                    'user_id': goal.user_id if goal else None
                                })
                                
                                if len(plans_needing_exec) >= limit:
                                    break
                    
                    if len(plans_needing_exec) >= limit:
                        break
            
            logger.debug(
                f"🎬 [PLAN_EXECUTOR_TASK] Found {len(plans_needing_exec)} plans needing execution"
            )
            return plans_needing_exec
            
        except Exception as e:
            logger.error(
                f"🎬 [PLAN_EXECUTOR_TASK] Failed to get plans needing execution: {e}"
            )
            return []
