import uuid
from datetime import datetime, UTC

import pytest

from aico.data.uow import UnitOfWork
from aico.services.scheduler_service import SchedulerService

from backend.scheduler.core import TaskExecutor
from backend.scheduler.tasks.base import BaseTask, TaskResult


class _RunKeyIdempotencyTask(BaseTask):
    task_id = "test.run_key_idempotency"

    async def execute(self, context):
        return TaskResult(success=True, message="ok")


@pytest.mark.asyncio
async def test_task_executor_run_key_idempotency_prevents_duplicate_execution_rows(test_db, session_factory):
    # Use a minimal config manager stub
    class _Cfg:
        def get(self, key, default=None):
            if key == "scheduler":
                # Avoid flakiness from local machine load during tests.
                return {
                    "max_cpu_percent": 100,
                    "max_memory_percent": 100,
                    "max_concurrent_tasks": 1000,
                }
            return default

    cfg = _Cfg()

    # TaskExecutor requires a db_connection object but tasks don't use it here
    executor = TaskExecutor(cfg, db_connection=None, container=None)

    task_id = _RunKeyIdempotencyTask.task_id
    run_key = f"{task_id}:{datetime.now(UTC).isoformat()}"

    task_config = {
        "task_id": task_id,
        "queue": "default",
        "config": {},
    }

    # First run: should create one execution row
    result1 = await executor.execute_task(_RunKeyIdempotencyTask, task_config, run_key=run_key)
    assert result1.success is True
    assert result1.skipped is False

    # Second run with the same run_key: should be skipped due to unique constraint
    result2 = await executor.execute_task(_RunKeyIdempotencyTask, task_config, run_key=run_key)
    assert result2.skipped is True

    async with UnitOfWork(session_factory) as uow:
        svc = SchedulerService(uow)
        executions = await svc.get_task_executions(task_id, limit=500)

        # Count executions with this exact run_key
        matching = [e for e in executions if getattr(e, "run_key", None) == run_key]
        assert len(matching) == 1
