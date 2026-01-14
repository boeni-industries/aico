"""
Integration tests for SchedulerService.

Tests scheduler service layer using actual repositories and database.
"""

import pytest
import uuid
from datetime import datetime, UTC, timedelta

from aico.services.scheduler_service import SchedulerService
# SchedulerService test - checking basic functionality


@pytest.fixture
async def scheduler_service(uow):
    """Create SchedulerService with UnitOfWork."""
    return SchedulerService(uow)


class TestSchedulerService:
    """Test suite for SchedulerService."""

    @pytest.mark.asyncio
    async def test_create_task(self, scheduler_service, test_user):
        """Test creating a scheduled task."""
        from aico.ai.scheduler.models import SchedulerTask
        from datetime import datetime, UTC
        
        task_data = {
            "task_id": str(uuid.uuid4()),
            "task_class": "aico.tasks.TestTask",
            "schedule": "0 0 * * *",
            "config": None,
            "enabled": True,
            "created_at": datetime.now(UTC),
            "updated_at": datetime.now(UTC),
        }
        
        created = await scheduler_service.create_task(task_data)
        
        assert created.task_id == task_data["task_id"]
        assert created.task_class == "aico.tasks.TestTask"

    @pytest.mark.asyncio
    async def test_get_task(self, scheduler_service, test_user):
        """Test retrieving a task."""
        from aico.ai.scheduler.models import SchedulerTask
        from datetime import datetime, UTC
        
        task_data = {
            "task_id": str(uuid.uuid4()),
            "task_class": "aico.tasks.TestTask",
            "schedule": "0 0 * * *",
            "config": None,
            "enabled": True,
            "created_at": datetime.now(UTC),
            "updated_at": datetime.now(UTC),
        }
        
        created = await scheduler_service.create_task(task_data)
        retrieved = await scheduler_service.get_task(created.task_id)
        
        assert retrieved is not None
        assert retrieved.task_id == created.task_id

    @pytest.mark.asyncio
    async def test_get_active_tasks(self, scheduler_service, test_user):
        """Test getting active tasks."""
        from datetime import datetime, UTC
        
        task_data = {
            "task_id": str(uuid.uuid4()),
            "task_class": "aico.tasks.TestTask",
            "schedule": "0 0 * * *",
            "config": None,
            "enabled": True,
            "created_at": datetime.now(UTC),
            "updated_at": datetime.now(UTC),
        }
        
        created = await scheduler_service.create_task(task_data)
        tasks = await scheduler_service.get_active_tasks()
        
        assert len(tasks) >= 1
        assert any(t.task_id == created.task_id for t in tasks)

    @pytest.mark.asyncio
    async def test_update_task(self, scheduler_service, test_user):
        """Test updating a task."""
        from datetime import datetime, UTC
        
        task_data = {
            "task_id": str(uuid.uuid4()),
            "task_class": "aico.tasks.TestTask",
            "schedule": "0 0 * * *",
            "config": None,
            "enabled": True,
            "created_at": datetime.now(UTC),
            "updated_at": datetime.now(UTC),
        }
        created = await scheduler_service.create_task(task_data)
        
        task_data["schedule"] = "0 12 * * *"
        task_data["enabled"] = False
        updated = await scheduler_service.update_task(task_data)
        
        assert updated.schedule == "0 12 * * *"
        assert updated.enabled is False

    @pytest.mark.asyncio
    async def test_delete_task(self, scheduler_service, test_user):
        """Test deleting a task."""
        from datetime import datetime, UTC
        
        task_data = {
            "task_id": str(uuid.uuid4()),
            "task_class": "aico.tasks.TempTask",
            "schedule": "0 0 * * *",
            "config": None,
            "enabled": True,
            "created_at": datetime.now(UTC),
            "updated_at": datetime.now(UTC),
        }
        created = await scheduler_service.create_task(task_data)
        
        success = await scheduler_service.delete_task(created.task_id)
        assert success is True
        
        deleted = await scheduler_service.get_task(created.task_id)
        assert deleted is None

    @pytest.mark.asyncio
    async def test_disable_task(self, scheduler_service, test_user):
        """Test disabling a task."""
        from datetime import datetime, UTC
        
        task_data = {
            "task_id": str(uuid.uuid4()),
            "task_class": "aico.tasks.TestTask",
            "schedule": "0 0 * * *",
            "config": None,
            "enabled": True,
            "created_at": datetime.now(UTC),
            "updated_at": datetime.now(UTC),
        }
        created = await scheduler_service.create_task(task_data)
        
        success = await scheduler_service.disable_task(created.task_id)
        assert success is True
        
        disabled = await scheduler_service.get_task(created.task_id)
        assert disabled.enabled is False

    @pytest.mark.asyncio
    async def test_enable_task(self, scheduler_service, test_user):
        """Test enabling a task."""
        from datetime import datetime, UTC
        
        task_data = {
            "task_id": str(uuid.uuid4()),
            "task_class": "aico.tasks.TestTask",
            "schedule": "0 0 * * *",
            "config": None,
            "enabled": False,
            "created_at": datetime.now(UTC),
            "updated_at": datetime.now(UTC),
        }
        created = await scheduler_service.create_task(task_data)
        
        success = await scheduler_service.enable_task(created.task_id)
        assert success is True
        
        enabled = await scheduler_service.get_task(created.task_id)
        assert enabled.enabled is True
