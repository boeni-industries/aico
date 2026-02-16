"""
Integration tests for SchedulerTaskLocksRepository.

Tests SchedulerTaskLocksRepository with real PostgreSQL database.
"""

import pytest
import uuid
from datetime import datetime, UTC, timedelta

from aico.data.scheduler.lock_models import SchedulerTaskLock
from aico.data.scheduler.models import SchedulerTask
from aico.data.postgres.connection import get_session_factory
from aico.data.uow import UnitOfWork


@pytest.fixture
async def session_factory():
    """Create async session factory for tests."""
    factory = await get_session_factory()
    return factory


@pytest.fixture
async def uow(session_factory):
    """Create Unit of Work for tests."""
    uow = UnitOfWork(session_factory)
    async with uow:
        yield uow


@pytest.fixture
async def test_task(uow):
    """Create a test scheduler task for lock tests."""
    task = SchedulerTask(
        task_id=str(uuid.uuid4()),
        task_class="TestTask",
        schedule="0 * * * *",
        enabled=True,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    await uow.scheduler_tasks.create(task)
    await uow.commit()
    return task


class TestSchedulerTaskLocksRepository:
    """Test SchedulerTaskLocksRepository CRUD operations."""
    
    @pytest.mark.asyncio
    async def test_create_task_lock(self, uow, test_task):
        """Test creating a new task lock."""
        lock = SchedulerTaskLock(
            task_id=test_task.task_id,
            execution_id=str(uuid.uuid4()),
            expires_at=datetime.now(UTC) + timedelta(minutes=5),
        )
        
        created = await uow.scheduler_task_locks.create(lock)
        await uow.commit()
        
        assert created.task_id == lock.task_id
        assert created.execution_id == lock.execution_id
    
    @pytest.mark.asyncio
    async def test_get_task_lock_by_id(self, uow, test_task):
        """Test retrieving task lock by ID."""
        lock = SchedulerTaskLock(
            task_id=test_task.task_id,
            execution_id=str(uuid.uuid4()),
            expires_at=datetime.now(UTC) + timedelta(minutes=10),
        )
        
        await uow.scheduler_task_locks.create(lock)
        await uow.commit()
        
        found = await uow.scheduler_task_locks.get_by_id(lock.task_id)
        assert found is not None
        assert found.task_id == lock.task_id
        assert found.execution_id == lock.execution_id
    
    @pytest.mark.asyncio
    async def test_update_task_lock(self, uow, test_task):
        """Test updating a task lock."""
        lock = SchedulerTaskLock(
            task_id=test_task.task_id,
            execution_id=str(uuid.uuid4()),
            expires_at=datetime.now(UTC) + timedelta(minutes=5),
        )
        
        await uow.scheduler_task_locks.create(lock)
        await uow.commit()
        
        # Update the lock
        lock.expires_at = datetime.now(UTC) + timedelta(minutes=15)
        updated = await uow.scheduler_task_locks.update(lock)
        await uow.commit()
        
        assert updated.task_id == lock.task_id
        
        # Verify update persisted
        found = await uow.scheduler_task_locks.get_by_id(lock.task_id)
        assert found.expires_at > datetime.now(UTC) + timedelta(minutes=10)
    
    @pytest.mark.asyncio
    async def test_delete_task_lock(self, uow, test_task):
        """Test deleting a task lock."""
        lock = SchedulerTaskLock(
            task_id=test_task.task_id,
            execution_id=str(uuid.uuid4()),
            expires_at=datetime.now(UTC) + timedelta(minutes=5),
        )
        
        await uow.scheduler_task_locks.create(lock)
        await uow.commit()
        
        # Delete the lock
        success = await uow.scheduler_task_locks.delete(lock.task_id)
        await uow.commit()
        
        assert success is True
        
        # Verify it's gone
        found = await uow.scheduler_task_locks.get_by_id(lock.task_id)
        assert found is None
    
    @pytest.mark.asyncio
    async def test_list_task_locks(self, uow, test_task):
        """Test listing task locks."""
        execution_id = str(uuid.uuid4())
        
        lock = SchedulerTaskLock(
            task_id=test_task.task_id,
            execution_id=execution_id,
            expires_at=datetime.now(UTC) + timedelta(minutes=5),
        )
        await uow.scheduler_task_locks.create(lock)
        await uow.commit()
        
        # List all locks
        all_locks = await uow.scheduler_task_locks.list()
        assert len(all_locks) >= 1
        
        # List by execution_id
        execution_locks = await uow.scheduler_task_locks.list(filters={"execution_id": execution_id})
        assert len(execution_locks) >= 1
    
    @pytest.mark.asyncio
    async def test_count_task_locks(self, uow, test_task):
        """Test counting task locks."""
        lock = SchedulerTaskLock(
            task_id=test_task.task_id,
            execution_id=str(uuid.uuid4()),
            expires_at=datetime.now(UTC) + timedelta(minutes=5),
        )
        await uow.scheduler_task_locks.create(lock)
        await uow.commit()
        
        count = await uow.scheduler_task_locks.count()
        assert count >= 1
    
    @pytest.mark.asyncio
    async def test_get_expired_locks(self, uow, test_task):
        """Test getting expired task locks."""
        # Create expired lock
        expired_lock = SchedulerTaskLock(
            task_id=test_task.task_id,
            execution_id=str(uuid.uuid4()),
            expires_at=datetime.now(UTC) - timedelta(minutes=5),
        )
        await uow.scheduler_task_locks.create(expired_lock)
        await uow.commit()
        
        expired = await uow.scheduler_task_locks.get_expired_locks()
        assert len(expired) >= 1
        for lock in expired:
            assert lock.expires_at < datetime.now(UTC)
    
    @pytest.mark.asyncio
    async def test_cleanup_expired_locks(self, uow, test_task):
        """Test cleaning up expired task locks."""
        # Create expired lock
        lock = SchedulerTaskLock(
            task_id=test_task.task_id,
            execution_id=str(uuid.uuid4()),
            expires_at=datetime.now(UTC) - timedelta(minutes=5),
        )
        await uow.scheduler_task_locks.create(lock)
        await uow.commit()
        
        # Cleanup expired locks
        deleted_count = await uow.scheduler_task_locks.cleanup_expired_locks()
        await uow.commit()
        
        assert deleted_count >= 1
    
    @pytest.mark.asyncio
    async def test_is_locked(self, uow, test_task):
        """Test checking if a task is locked."""
        task_id = test_task.task_id
        
        # Task should not be locked initially
        is_locked = await uow.scheduler_task_locks.is_locked(task_id)
        assert is_locked is False
        
        # Create active lock
        lock = SchedulerTaskLock(
            task_id=task_id,
            execution_id=str(uuid.uuid4()),
            expires_at=datetime.now(UTC) + timedelta(minutes=5),
        )
        await uow.scheduler_task_locks.create(lock)
        await uow.commit()
        
        # Task should now be locked
        is_locked = await uow.scheduler_task_locks.is_locked(task_id)
        assert is_locked is True
