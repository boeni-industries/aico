"""
Integration tests for SchedulerTaskExecutionsRepository.
"""

import pytest
import uuid
from datetime import datetime, UTC

from aico.data.scheduler.models import TaskExecution, SchedulerTask
from aico.data.postgres.connection import get_session_factory
from aico.data.uow import UnitOfWork


@pytest.fixture
async def session_factory():
    factory = await get_session_factory()
    return factory


@pytest.fixture
async def uow(session_factory):
    uow = UnitOfWork(session_factory)
    async with uow:
        yield uow


@pytest.fixture
async def test_task(uow):
    task_id = "exec_test_task"
    existing = await uow.scheduler_tasks.get_by_id(task_id)
    if not existing:
        task = SchedulerTask(
            task_id=task_id,
            task_class="test.Task",
            schedule="0 * * * *",
            enabled=True,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        await uow.scheduler_tasks.create(task)
        await uow.commit()
    return await uow.scheduler_tasks.get_by_id(task_id)


class TestSchedulerTaskExecutionsRepository:
    
    @pytest.mark.asyncio
    async def test_create_execution(self, uow, test_task):
        execution = TaskExecution(
            id=0,
            task_id=test_task.task_id,
            execution_id=str(uuid.uuid4()),
            status="running",
            started_at=datetime.now(UTC),
        )
        
        created = await uow.scheduler_task_executions.create(execution)
        await uow.commit()
        
        assert created.id > 0
        assert created.status == "running"
    
    @pytest.mark.asyncio
    async def test_get_execution_by_id(self, uow, test_task):
        execution = TaskExecution(
            id=0,
            task_id=test_task.task_id,
            execution_id=str(uuid.uuid4()),
            status="completed",
            started_at=datetime.now(UTC),
            completed_at=datetime.now(UTC),
        )
        
        created = await uow.scheduler_task_executions.create(execution)
        await uow.commit()
        
        found = await uow.scheduler_task_executions.get_by_id(str(created.id))
        assert found is not None
        assert found.status == "completed"
    
    @pytest.mark.asyncio
    async def test_update_execution(self, uow, test_task):
        execution = TaskExecution(
            id=0,
            task_id=test_task.task_id,
            execution_id=str(uuid.uuid4()),
            status="running",
            started_at=datetime.now(UTC),
        )
        
        created = await uow.scheduler_task_executions.create(execution)
        await uow.commit()
        
        created.status = "completed"
        created.completed_at = datetime.now(UTC)
        created.duration_seconds = 1.5
        updated = await uow.scheduler_task_executions.update(created)
        await uow.commit()
        
        assert updated.status == "completed"
        
        found = await uow.scheduler_task_executions.get_by_id(str(created.id))
        assert found.duration_seconds == 1.5
    
    @pytest.mark.asyncio
    async def test_delete_execution(self, uow, test_task):
        execution = TaskExecution(
            id=0,
            task_id=test_task.task_id,
            execution_id=str(uuid.uuid4()),
            status="failed",
            started_at=datetime.now(UTC),
        )
        
        created = await uow.scheduler_task_executions.create(execution)
        await uow.commit()
        
        success = await uow.scheduler_task_executions.delete(str(created.id))
        await uow.commit()
        
        assert success is True
        
        found = await uow.scheduler_task_executions.get_by_id(str(created.id))
        assert found is None
    
    @pytest.mark.asyncio
    async def test_list_executions(self, uow, test_task):
        for i in range(3):
            execution = TaskExecution(
                id=0,
                task_id=test_task.task_id,
                execution_id=str(uuid.uuid4()),
                status="completed" if i < 2 else "failed",
                started_at=datetime.now(UTC),
            )
            await uow.scheduler_task_executions.create(execution)
        
        await uow.commit()
        
        all_executions = await uow.scheduler_task_executions.list(filters={"task_id": test_task.task_id})
        assert len(all_executions) >= 3
        
        completed = await uow.scheduler_task_executions.list(filters={"status": "completed"})
        assert len(completed) >= 2
    
    @pytest.mark.asyncio
    async def test_count_executions(self, uow, test_task):
        for i in range(3):
            execution = TaskExecution(
                id=0,
                task_id=test_task.task_id,
                execution_id=str(uuid.uuid4()),
                status="completed",
                started_at=datetime.now(UTC),
            )
            await uow.scheduler_task_executions.create(execution)
        
        await uow.commit()
        
        count = await uow.scheduler_task_executions.count(filters={"task_id": test_task.task_id})
        assert count >= 3
    
    @pytest.mark.asyncio
    async def test_get_task_executions(self, uow, test_task):
        for i in range(3):
            execution = TaskExecution(
                id=0,
                task_id=test_task.task_id,
                execution_id=str(uuid.uuid4()),
                status="completed",
                started_at=datetime.now(UTC),
            )
            await uow.scheduler_task_executions.create(execution)
        
        await uow.commit()
        
        executions = await uow.scheduler_task_executions.get_task_executions(test_task.task_id)
        assert len(executions) >= 3
        for e in executions:
            assert e.task_id == test_task.task_id
