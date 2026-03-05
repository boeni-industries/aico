"""
Scheduler Service

Replaces backend/scheduler/storage.py with repository-based implementation.
Provides high-level scheduler operations using the 4 scheduler repositories.
"""

from __future__ import annotations

from datetime import datetime, UTC
from typing import Any, Dict, List, Optional

from aico.core.logging import get_logger
from aico.data.uow import UnitOfWork

logger = get_logger("shared.services.scheduler")


class SchedulerService:
    """
    Service layer for scheduler operations.
    
    Handles task management, executions, and locks.
    Uses scheduler repositories through Unit of Work pattern.
    """

    def __init__(self, uow: UnitOfWork):
        self.uow = uow

    # ==================== Task Operations ====================

    async def create_task(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new scheduled task."""
        try:
            from aico.ai.scheduler.models import SchedulerTask
            
            task = SchedulerTask(**task_data)
            created = await self.uow.scheduler_tasks.create(task)
            await self.uow.commit()
            
            logger.debug("[SCHEDULER_SERVICE] Created task", extra={"task_id": created.task_id})
            return created
        except Exception as e:
            logger.error(f"[SCHEDULER_SERVICE] Failed to create task: {e}")
            await self.uow.rollback()
            raise

    async def get_task(self, task_id: str) -> Optional[Any]:
        """Retrieve a task by ID."""
        try:
            return await self.uow.scheduler_tasks.get_by_id(task_id)
        except Exception as e:
            logger.error(f"[SCHEDULER_SERVICE] Failed to retrieve task: {e}", extra={"task_id": task_id})
            raise

    async def list_tasks(self, filters: Optional[Dict[str, Any]] = None) -> List[Any]:
        """List tasks with optional filters."""
        try:
            return await self.uow.scheduler_tasks.list(filters=filters or {})
        except Exception as e:
            logger.error(f"[SCHEDULER_SERVICE] Failed to list tasks: {e}")
            raise

    async def get_active_tasks(self) -> List[Any]:
        """Get all active tasks."""
        try:
            return await self.uow.scheduler_tasks.list(filters={"enabled": True})
        except Exception as e:
            logger.error(f"[SCHEDULER_SERVICE] Failed to get active tasks: {e}")
            raise

    async def get_due_tasks(self, current_time: datetime) -> List[Any]:
        """Get tasks that are due to run."""
        try:
            # This would need a custom query in the repository
            # For now, get all active tasks and filter in memory
            active_tasks = await self.get_active_tasks()
            return [t for t in active_tasks if t.next_run_at and t.next_run_at <= current_time]
        except Exception as e:
            logger.error(f"[SCHEDULER_SERVICE] Failed to get due tasks: {e}")
            raise

    async def update_task(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """Update a task."""
        try:
            from aico.ai.scheduler.models import SchedulerTask
            
            task = SchedulerTask(**task_data)
            updated = await self.uow.scheduler_tasks.update(task)
            await self.uow.commit()
            
            logger.debug("[SCHEDULER_SERVICE] Updated task", extra={"task_id": task.task_id})
            return updated
        except Exception as e:
            logger.error(f"[SCHEDULER_SERVICE] Failed to update task: {e}")
            await self.uow.rollback()
            raise

    async def delete_task(self, task_id: str) -> bool:
        """Delete a task."""
        try:
            success = await self.uow.scheduler_tasks.delete(task_id)
            await self.uow.commit()
            
            logger.info("[SCHEDULER_SERVICE] Deleted task", extra={"task_id": task_id})
            return success
        except Exception as e:
            logger.error(f"[SCHEDULER_SERVICE] Failed to delete task: {e}", extra={"task_id": task_id})
            await self.uow.rollback()
            raise

    async def disable_task(self, task_id: str) -> bool:
        """Disable a task (set enabled=False)."""
        try:
            task = await self.get_task(task_id)
            if not task:
                return False
            
            task_data = {
                "task_id": task.task_id,
                "task_class": task.task_class,
                "schedule": task.schedule,
                "config": task.config,
                "enabled": False,
                "created_at": task.created_at,
                "updated_at": datetime.now(UTC),
            }
            await self.update_task(task_data)
            return True
        except Exception as e:
            logger.error(f"[SCHEDULER_SERVICE] Failed to disable task: {e}", extra={"task_id": task_id})
            raise

    async def enable_task(self, task_id: str) -> bool:
        """Enable a task."""
        try:
            task = await self.get_task(task_id)
            if not task:
                return False
            
            task_data = {
                "task_id": task.task_id,
                "task_class": task.task_class,
                "schedule": task.schedule,
                "config": task.config,
                "enabled": True,
                "created_at": task.created_at,
                "updated_at": datetime.now(UTC),
            }
            
            await self.update_task(task_data)
            logger.info("[SCHEDULER_SERVICE] Enabled task", extra={"task_id": task_id})
            return True
        except Exception as e:
            logger.error(f"[SCHEDULER_SERVICE] Failed to enable task: {e}", extra={"task_id": task_id})
            raise

    # ==================== Run Ledger Operations ====================

    async def create_run(self, run_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a planned run ledger record."""
        try:
            from aico.data.scheduler.models import SchedulerTaskRun

            run = SchedulerTaskRun(**run_data)
            created = await self.uow.scheduler_run_ledger.create(run)
            await self.uow.commit()

            logger.debug("[SCHEDULER_SERVICE] Created run", extra={"task_id": created.task_id, "run_key": created.run_key})
            return created
        except Exception as e:
            logger.error(f"[SCHEDULER_SERVICE] Failed to create run: {e}")
            await self.uow.rollback()
            raise

    async def get_run(self, run_id: str) -> Optional[Any]:
        """Retrieve a planned run ledger record by numeric ID."""
        try:
            return await self.uow.scheduler_run_ledger.get_by_id(run_id)
        except Exception as e:
            logger.error(f"[SCHEDULER_SERVICE] Failed to retrieve run: {e}", extra={"run_id": run_id})
            raise

    async def list_runs(
        self,
        *,
        filters: Optional[Dict[str, Any]] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Any]:
        """List planned runs with optional filters."""
        try:
            return await self.uow.scheduler_run_ledger.list(filters=filters or {}, limit=limit, offset=offset)
        except Exception as e:
            logger.error(f"[SCHEDULER_SERVICE] Failed to list runs: {e}")
            raise

    async def update_run(self, run_data: Dict[str, Any]) -> Dict[str, Any]:
        """Update a planned run ledger record."""
        try:
            from aico.data.scheduler.models import SchedulerTaskRun

            run = SchedulerTaskRun(**run_data)
            updated = await self.uow.scheduler_run_ledger.update(run)
            await self.uow.commit()

            logger.debug(
                "[SCHEDULER_SERVICE] Updated run",
                extra={"task_id": updated.task_id, "run_key": updated.run_key, "state": updated.state},
            )
            return updated
        except Exception as e:
            logger.error(f"[SCHEDULER_SERVICE] Failed to update run: {e}")
            await self.uow.rollback()
            raise

    async def get_run_stats_in_range(
        self,
        *,
        start_dt: datetime,
        end_dt: datetime,
        bucket: str = "hour",
        task_id: str | None = None,
        tenant_id: str | None = None,
    ) -> List[Dict[str, Any]]:
        """Get run-ledger stats buckets in time range."""
        try:
            repo = self.uow.scheduler_run_ledger
            stats_in_range = getattr(repo, "stats_in_range", None)
            if stats_in_range is None:
                raise RuntimeError("scheduler_run_ledger repository missing stats_in_range")
            return await stats_in_range(
                start_dt=start_dt,
                end_dt=end_dt,
                bucket=bucket,
                task_id=task_id,
                tenant_id=tenant_id,
            )
        except Exception as e:
            logger.error(f"[SCHEDULER_SERVICE] Failed to get run stats: {e}")
            raise

    # ==================== Execution Operations ====================

    async def create_execution(self, execution_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a task execution record."""
        try:
            from aico.ai.scheduler.models import SchedulerTaskExecution
            
            execution = SchedulerTaskExecution(**execution_data)
            created = await self.uow.scheduler_task_executions.create(execution)
            await self.uow.commit()
            
            logger.info("[SCHEDULER_SERVICE] Created execution", extra={"execution_id": created.execution_id})
            return created
        except Exception as e:
            logger.error(f"[SCHEDULER_SERVICE] Failed to create execution: {e}")
            await self.uow.rollback()
            raise

    async def get_task_executions(self, task_id: str, limit: int = 100) -> List[Any]:
        """Get execution history for a task."""
        try:
            return await self.uow.scheduler_task_executions.list(filters={"task_id": task_id}, limit=limit)
        except Exception as e:
            logger.error(f"[SCHEDULER_SERVICE] Failed to get executions: {e}", extra={"task_id": task_id})
            raise

    async def get_recent_executions(self, limit: int = 50) -> List[Any]:
        """Get recent task executions across all tasks."""
        try:
            return await self.uow.scheduler_task_executions.list(limit=limit)
        except Exception as e:
            logger.error(f"[SCHEDULER_SERVICE] Failed to get recent executions: {e}")
            raise

    async def get_execution_by_execution_id(self, execution_id: str) -> Optional[Any]:
        """Get a single execution by its stable execution_id."""
        try:
            repo = self.uow.scheduler_task_executions
            get_by_execution_id = getattr(repo, "get_by_execution_id", None)
            if get_by_execution_id is None:
                raise RuntimeError("scheduler_task_executions repository missing get_by_execution_id")
            return await get_by_execution_id(execution_id)
        except Exception as e:
            logger.error(f"[SCHEDULER_SERVICE] Failed to get execution: {e}", extra={"execution_id": execution_id})
            raise

    async def list_executions_in_range_cursor(
        self,
        *,
        start_dt: datetime,
        end_dt: datetime,
        limit: int,
        cursor_started_at: datetime | None = None,
        cursor_execution_id: str | None = None,
        task_id: str | None = None,
        status: str | None = None,
        include_acknowledged: bool = True,
    ) -> List[Any]:
        """List executions in a time range with cursor pagination."""
        try:
            repo = self.uow.scheduler_task_executions
            list_in_range_cursor = getattr(repo, "list_in_range_cursor", None)
            if list_in_range_cursor is None:
                raise RuntimeError("scheduler_task_executions repository missing list_in_range_cursor")
            return await list_in_range_cursor(
                start_dt=start_dt,
                end_dt=end_dt,
                limit=limit,
                cursor_started_at=cursor_started_at,
                cursor_execution_id=cursor_execution_id,
                task_id=task_id,
                status=status,
                include_acknowledged=include_acknowledged,
            )
        except Exception as e:
            logger.error(f"[SCHEDULER_SERVICE] Failed to list executions: {e}")
            raise

    async def get_execution_stats_in_range(
        self,
        *,
        start_dt: datetime,
        end_dt: datetime,
        bucket: str = "hour",
        task_id: str | None = None,
    ) -> List[Dict[str, Any]]:
        """Get execution stats buckets in time range."""
        try:
            repo = self.uow.scheduler_task_executions
            stats_in_range = getattr(repo, "stats_in_range", None)
            if stats_in_range is None:
                raise RuntimeError("scheduler_task_executions repository missing stats_in_range")
            return await stats_in_range(
                start_dt=start_dt,
                end_dt=end_dt,
                bucket=bucket,
                task_id=task_id,
            )
        except Exception as e:
            logger.error(f"[SCHEDULER_SERVICE] Failed to get execution stats: {e}")
            raise

    async def update_execution(self, execution_data: Dict[str, Any]) -> Dict[str, Any]:
        """Update an execution record."""
        try:
            from aico.ai.scheduler.models import SchedulerTaskExecution
            
            execution = SchedulerTaskExecution(**execution_data)
            updated = await self.uow.scheduler_task_executions.update(execution)
            await self.uow.commit()
            
            logger.info("[SCHEDULER_SERVICE] Updated execution", extra={"execution_id": execution.execution_id})
            return updated
        except Exception as e:
            logger.error(f"[SCHEDULER_SERVICE] Failed to update execution: {e}")
            await self.uow.rollback()
            raise

    # ==================== Analytics Operations ====================

    async def get_task_count(self) -> int:
        """Get total task count."""
        try:
            return await self.uow.scheduler_tasks.count()
        except Exception as e:
            logger.error(f"[SCHEDULER_SERVICE] Failed to count tasks: {e}")
            raise

    async def get_active_task_count(self) -> int:
        """Get active task count."""
        try:
            return await self.uow.scheduler_tasks.count(filters={"is_active": True})
        except Exception as e:
            logger.error(f"[SCHEDULER_SERVICE] Failed to count active tasks: {e}")
            raise

    async def get_execution_count(self, task_id: Optional[str] = None) -> int:
        """Get execution count, optionally for a specific task."""
        try:
            filters = {"task_id": task_id} if task_id else {}
            return await self.uow.scheduler_task_executions.count(filters=filters)
        except Exception as e:
            logger.error(f"[SCHEDULER_SERVICE] Failed to count executions: {e}")
            raise

    async def cleanup_old_executions(self, cutoff_date: datetime) -> int:
        """Clean up old execution records before cutoff_date."""
        try:
            # Get all executions and filter by date
            all_executions = await self.uow.scheduler_task_executions.list(limit=100000)
            deleted_count = 0
            
            for execution in all_executions:
                if execution.started_at and execution.started_at < cutoff_date:
                    # Repository delete() targets the numeric DB primary key (id), not the UUID execution_id.
                    # Passing execution_id would raise int() conversion errors.
                    if execution.id is not None:
                        await self.uow.scheduler_task_executions.delete(str(execution.id))
                    deleted_count += 1
            
            logger.info(f"[SCHEDULER_SERVICE] Cleaned up {deleted_count} old executions before {cutoff_date}")
            return deleted_count
        except Exception as e:
            logger.error(f"[SCHEDULER_SERVICE] Failed to cleanup old executions: {e}")
            raise

    # ==================== Acknowledgement Operations ====================

    async def acknowledge_execution(self, execution_id: str) -> bool:
        """Mark a single execution as acknowledged."""
        try:
            # Get the execution
            executions = await self.uow.scheduler_task_executions.list(limit=1000)
            execution = None
            for exec in executions:
                if exec.execution_id == execution_id:
                    execution = exec
                    break
            
            if not execution:
                logger.warning(f"[SCHEDULER_SERVICE] Execution not found: {execution_id}")
                return False
            
            # Update acknowledged flag
            execution.acknowledged = True
            await self.uow.scheduler_task_executions.update(execution)
            await self.uow.commit()
            
            logger.info("[SCHEDULER_SERVICE] Acknowledged execution", extra={"execution_id": execution_id})
            return True
        except Exception as e:
            logger.error(f"[SCHEDULER_SERVICE] Failed to acknowledge execution: {e}", extra={"execution_id": execution_id})
            await self.uow.rollback()
            raise

    async def acknowledge_all_failed(self, task_id: Optional[str] = None) -> int:
        """Mark all failed executions as acknowledged.
        
        Args:
            task_id: Optional task ID to limit acknowledgement to specific task
            
        Returns:
            Number of executions acknowledged
        """
        try:
            # Build filters for failed, unacknowledged executions
            filters = {"status": "failed", "acknowledged": False}
            if task_id:
                filters["task_id"] = task_id
            
            # Get all matching executions
            executions = await self.uow.scheduler_task_executions.list(filters=filters, limit=10000)
            
            # Acknowledge each one
            acknowledged_count = 0
            for execution in executions:
                execution.acknowledged = True
                await self.uow.scheduler_task_executions.update(execution)
                acknowledged_count += 1
            
            await self.uow.commit()
            
            logger.info(
                f"[SCHEDULER_SERVICE] Acknowledged {acknowledged_count} failed executions",
                extra={"task_id": task_id, "count": acknowledged_count}
            )
            return acknowledged_count
        except Exception as e:
            logger.error(f"[SCHEDULER_SERVICE] Failed to acknowledge all failed executions: {e}")
            await self.uow.rollback()
            raise

    async def get_unacknowledged_failures(self, task_id: Optional[str] = None, limit: int = 100) -> List[Any]:
        """Get unacknowledged failed executions.
        
        Args:
            task_id: Optional task ID to filter by
            limit: Maximum number of results
            
        Returns:
            List of unacknowledged failed executions
        """
        try:
            filters = {"status": "failed", "acknowledged": False}
            if task_id:
                filters["task_id"] = task_id
            
            return await self.uow.scheduler_task_executions.list(filters=filters, limit=limit)
        except Exception as e:
            logger.error(f"[SCHEDULER_SERVICE] Failed to get unacknowledged failures: {e}")
            raise
