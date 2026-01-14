"""
Integration tests for SchedulerTasksRepository.
"""

import pytest
import uuid
from datetime import datetime, UTC

from aico.data.scheduler.models import SchedulerTask
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


class TestSchedulerTasksRepository:
    
    @pytest.mark.asyncio
    async def test_create_task(self, uow):
        task = SchedulerTask(
            task_id=str(uuid.uuid4()),
            task_class="TestTask",
            schedule="0 * * * *",
            enabled=True,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        
        created = await uow.scheduler_tasks.create(task)
        await uow.commit()
        
        assert created.task_id == task.task_id
        assert created.task_class == "TestTask"
    
    @pytest.mark.asyncio
    async def test_get_task_by_id(self, uow):
        task = SchedulerTask(
            task_id=str(uuid.uuid4()),
            task_class="GetTask",
            schedule="0 0 * * *",
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        
        await uow.scheduler_tasks.create(task)
        await uow.commit()
        
        found = await uow.scheduler_tasks.get_by_id(task.task_id)
        assert found is not None
        assert found.schedule == "0 0 * * *"
    
    @pytest.mark.asyncio
    async def test_update_task(self, uow):
        task = SchedulerTask(
            task_id=str(uuid.uuid4()),
            task_class="UpdateTask",
            schedule="0 0 * * *",
            enabled=True,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        
        await uow.scheduler_tasks.create(task)
        await uow.commit()
        
        task.schedule = "0 12 * * *"
        task.enabled = False
        updated = await uow.scheduler_tasks.update(task)
        await uow.commit()
        
        assert updated.schedule == "0 12 * * *"
        
        found = await uow.scheduler_tasks.get_by_id(task.task_id)
        assert found.enabled is False
    
    @pytest.mark.asyncio
    async def test_delete_task(self, uow):
        task = SchedulerTask(
            task_id=str(uuid.uuid4()),
            task_class="DeleteTask",
            schedule="0 0 * * *",
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        
        await uow.scheduler_tasks.create(task)
        await uow.commit()
        
        success = await uow.scheduler_tasks.delete(task.task_id)
        await uow.commit()
        
        assert success is True
        
        found = await uow.scheduler_tasks.get_by_id(task.task_id)
        assert found is None
    
    @pytest.mark.asyncio
    async def test_list_tasks(self, uow):
        for i in range(3):
            task = SchedulerTask(
                task_id=str(uuid.uuid4()),
                task_class=f"ListTask{i}",
                schedule="0 0 * * *",
                enabled=True if i < 2 else False,
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC),
            )
            await uow.scheduler_tasks.create(task)
        
        await uow.commit()
        
        all_tasks = await uow.scheduler_tasks.list()
        assert len(all_tasks) >= 3
        
        enabled = await uow.scheduler_tasks.list(filters={"enabled": True})
        assert len(enabled) >= 2
    
    @pytest.mark.asyncio
    async def test_count_tasks(self, uow):
        for i in range(3):
            task = SchedulerTask(
                task_id=str(uuid.uuid4()),
                task_class=f"CountTask{i}",
                schedule="0 0 * * *",
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC),
            )
            await uow.scheduler_tasks.create(task)
        
        await uow.commit()
        
        count = await uow.scheduler_tasks.count()
        assert count >= 3
    
    @pytest.mark.asyncio
    async def test_get_enabled_tasks(self, uow):
        for i in range(3):
            task = SchedulerTask(
                task_id=str(uuid.uuid4()),
                task_class=f"EnabledTask{i}",
                schedule="0 0 * * *",
                enabled=True if i < 2 else False,
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC),
            )
            await uow.scheduler_tasks.create(task)
        
        await uow.commit()
        
        enabled = await uow.scheduler_tasks.get_enabled_tasks()
        assert len(enabled) >= 2
        for t in enabled:
            assert t.enabled is True
