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
            
            logger.info("[SCHEDULER_SERVICE] Created task", extra={"task_id": created.task_id})
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
            return await self.uow.scheduler_tasks.list(filters={"is_active": True})
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
            
            logger.info("[SCHEDULER_SERVICE] Updated task", extra={"task_id": task.task_id})
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

    # ==================== Lock Operations ====================

    async def acquire_lock(self, task_id: str, worker_id: str, ttl_seconds: int = 300) -> bool:
        """Acquire a lock for task execution."""
        try:
            from aico.ai.scheduler.models import SchedulerTaskLock
            
            lock = SchedulerTaskLock(
                task_id=task_id,
                worker_id=worker_id,
                acquired_at=datetime.now(UTC),
                expires_at=datetime.now(UTC).timestamp() + ttl_seconds
            )
            
            await self.uow.scheduler_task_locks.create(lock)
            await self.uow.commit()
            
            logger.info("[SCHEDULER_SERVICE] Acquired lock", extra={"task_id": task_id, "worker_id": worker_id})
            return True
        except Exception as e:
            # Lock already exists or other error
            logger.warning(f"[SCHEDULER_SERVICE] Failed to acquire lock: {e}", extra={"task_id": task_id})
            await self.uow.rollback()
            return False

    async def release_lock(self, task_id: str, worker_id: str) -> bool:
        """Release a task lock."""
        try:
            # Delete lock for this task/worker combination
            success = await self.uow.scheduler_task_locks.delete(f"{task_id}:{worker_id}")
            await self.uow.commit()
            
            logger.info("[SCHEDULER_SERVICE] Released lock", extra={"task_id": task_id, "worker_id": worker_id})
            return success
        except Exception as e:
            logger.error(f"[SCHEDULER_SERVICE] Failed to release lock: {e}", extra={"task_id": task_id})
            await self.uow.rollback()
            raise

    async def check_lock(self, task_id: str) -> Optional[Any]:
        """Check if a task is locked."""
        try:
            locks = await self.uow.scheduler_task_locks.list(filters={"task_id": task_id})
            return locks[0] if locks else None
        except Exception as e:
            logger.error(f"[SCHEDULER_SERVICE] Failed to check lock: {e}", extra={"task_id": task_id})
            raise

    async def cleanup_expired_locks(self) -> int:
        """Remove expired locks."""
        try:
            current_time = datetime.now(UTC).timestamp()
            # This would need a custom query in the repository
            # For now, get all locks and filter
            all_locks = await self.uow.scheduler_task_locks.list()
            expired_count = 0
            
            for lock in all_locks:
                if lock.expires_at and lock.expires_at < current_time:
                    await self.uow.scheduler_task_locks.delete(f"{lock.task_id}:{lock.worker_id}")
                    expired_count += 1
            
            await self.uow.commit()
            logger.info(f"[SCHEDULER_SERVICE] Cleaned up {expired_count} expired locks")
            return expired_count
        except Exception as e:
            logger.error(f"[SCHEDULER_SERVICE] Failed to cleanup expired locks: {e}")
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
