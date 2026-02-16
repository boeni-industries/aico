"""
Integration tests for Policy and Scheduler repositories.

Tests PolicyRepository and SchedulerTaskRepository with real PostgreSQL database.
"""

import pytest
import uuid
from datetime import datetime, UTC

from aico.data.agency.models import Policy
from aico.data.scheduler.models import SchedulerTask
from aico.data.user.models import UserProfile
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
async def test_user(uow):
    """Create a test user for policy tests."""
    user = UserProfile(
        uuid=str(uuid.uuid4()),
        full_name="Policy Test User",
        nickname="policy_tester",
        user_type="parent",
        is_active=True,
        primary_language="en",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    await uow.users.create(user)
    await uow.commit()
    return user


class TestPolicyRepository:
    """Test PolicyRepository CRUD operations."""
    
    @pytest.mark.asyncio
    async def test_create_policy(self, uow, test_user):
        """Test creating a new policy."""
        policy = Policy(
            rule_id=str(uuid.uuid4()),
            rule_name="Test Policy",
            target_type="goal",
            conditions='{"type": "learning"}',
            effect="allow",
            scope="user",
            user_id=test_user.uuid,
            priority=100,
        )
        
        created = await uow.policies.create(policy)
        await uow.commit()
        
        assert created.rule_id == policy.rule_id
        assert created.rule_name == "Test Policy"
    
    @pytest.mark.asyncio
    async def test_get_policy_by_id(self, uow, test_user):
        """Test retrieving policy by ID."""
        policy = Policy(
            rule_id=str(uuid.uuid4()),
            rule_name="Get Test Policy",
            target_type="plan",
            conditions='{"priority": "high"}',
            effect="needs_consent",
            scope="user",
            user_id=test_user.uuid,
        )
        
        await uow.policies.create(policy)
        await uow.commit()
        
        found = await uow.policies.get_by_id(policy.rule_id)
        assert found is not None
        assert found.rule_name == "Get Test Policy"
    
    @pytest.mark.asyncio
    async def test_update_policy(self, uow, test_user):
        """Test updating a policy."""
        policy = Policy(
            rule_id=str(uuid.uuid4()),
            rule_name="Original Policy",
            target_type="goal",
            conditions='{}',
            effect="allow",
            scope="user",
            user_id=test_user.uuid,
        )
        
        await uow.policies.create(policy)
        await uow.commit()
        
        # Update the policy
        policy.rule_name = "Updated Policy"
        policy.priority = 200
        updated = await uow.policies.update(policy)
        await uow.commit()
        
        assert updated.rule_name == "Updated Policy"
        
        # Verify update persisted
        found = await uow.policies.get_by_id(policy.rule_id)
        assert found.priority == 200
    
    @pytest.mark.asyncio
    async def test_delete_policy(self, uow, test_user):
        """Test deleting a policy."""
        policy = Policy(
            rule_id=str(uuid.uuid4()),
            rule_name="Delete Test",
            target_type="goal",
            conditions='{}',
            effect="block",
            scope="user",
            user_id=test_user.uuid,
        )
        
        await uow.policies.create(policy)
        await uow.commit()
        
        # Delete the policy
        success = await uow.policies.delete(policy.rule_id)
        await uow.commit()
        
        assert success is True
        
        # Verify it's gone
        found = await uow.policies.get_by_id(policy.rule_id)
        assert found is None
    
    @pytest.mark.asyncio
    async def test_list_policies(self, uow, test_user):
        """Test listing policies with filters."""
        for i in range(3):
            policy = Policy(
                rule_id=str(uuid.uuid4()),
                rule_name=f"List Policy {i}",
                target_type="goal" if i < 2 else "plan",
                conditions='{}',
                effect="allow",
                scope="user",
                user_id=test_user.uuid,
                active=i < 2,
            )
            await uow.policies.create(policy)
        
        await uow.commit()
        
        # List all policies for user
        all_policies = await uow.policies.list(filters={"user_id": test_user.uuid})
        assert len(all_policies) >= 3
        
        # List only active policies
        active_policies = await uow.policies.list(filters={"user_id": test_user.uuid, "active": True})
        assert len(active_policies) >= 2
    
    @pytest.mark.asyncio
    async def test_count_policies(self, uow, test_user):
        """Test counting policies."""
        for i in range(3):
            policy = Policy(
                rule_id=str(uuid.uuid4()),
                rule_name=f"Count Policy {i}",
                target_type="goal",
                conditions='{}',
                effect="allow",
                scope="user",
                user_id=test_user.uuid,
            )
            await uow.policies.create(policy)
        
        await uow.commit()
        
        count = await uow.policies.count(filters={"user_id": test_user.uuid})
        assert count >= 3
    
    @pytest.mark.asyncio
    async def test_get_active_policies_for_user(self, uow, test_user):
        """Test getting active policies for user and target type."""
        # Create user-specific policy
        user_policy = Policy(
            rule_id=str(uuid.uuid4()),
            rule_name="User Policy",
            target_type="goal",
            conditions='{}',
            effect="allow",
            scope="user",
            user_id=test_user.uuid,
            active=True,
        )
        await uow.policies.create(user_policy)
        
        # Create global policy
        global_policy = Policy(
            rule_id=str(uuid.uuid4()),
            rule_name="Global Policy",
            target_type="goal",
            conditions='{}',
            effect="needs_consent",
            scope="global",
            user_id=None,
            active=True,
        )
        await uow.policies.create(global_policy)
        
        await uow.commit()
        
        # Get active policies (should include both user and global)
        policies = await uow.policies.get_active_policies_for_user(test_user.uuid, "goal")
        assert len(policies) >= 2


class TestSchedulerTaskRepository:
    """Test SchedulerTaskRepository CRUD operations."""
    
    @pytest.mark.asyncio
    async def test_create_task(self, uow):
        """Test creating a new scheduler task."""
        task = SchedulerTask(
            task_id=str(uuid.uuid4()),
            task_class="TestTask",
            schedule="0 * * * *",
            config='{"param": "value"}',
            enabled=True,
        )
        
        created = await uow.scheduler_tasks.create(task)
        await uow.commit()
        
        assert created.task_id == task.task_id
        assert created.task_class == "TestTask"
    
    @pytest.mark.asyncio
    async def test_get_task_by_id(self, uow):
        """Test retrieving task by ID."""
        task = SchedulerTask(
            task_id=str(uuid.uuid4()),
            task_class="GetTestTask",
            schedule="0 0 * * *",
        )
        
        await uow.scheduler_tasks.create(task)
        await uow.commit()
        
        found = await uow.scheduler_tasks.get_by_id(task.task_id)
        assert found is not None
        assert found.task_class == "GetTestTask"
    
    @pytest.mark.asyncio
    async def test_update_task(self, uow):
        """Test updating a task."""
        task = SchedulerTask(
            task_id=str(uuid.uuid4()),
            task_class="UpdateTask",
            schedule="0 * * * *",
            enabled=True,
        )
        
        await uow.scheduler_tasks.create(task)
        await uow.commit()
        
        # Update the task
        task.schedule = "0 0 * * *"
        task.enabled = False
        updated = await uow.scheduler_tasks.update(task)
        await uow.commit()
        
        assert updated.schedule == "0 0 * * *"
        
        # Verify update persisted
        found = await uow.scheduler_tasks.get_by_id(task.task_id)
        assert found.enabled is False
    
    @pytest.mark.asyncio
    async def test_delete_task(self, uow):
        """Test deleting a task."""
        task = SchedulerTask(
            task_id=str(uuid.uuid4()),
            task_class="DeleteTask",
            schedule="0 * * * *",
        )
        
        await uow.scheduler_tasks.create(task)
        await uow.commit()
        
        # Delete the task
        success = await uow.scheduler_tasks.delete(task.task_id)
        await uow.commit()
        
        assert success is True
        
        # Verify it's gone
        found = await uow.scheduler_tasks.get_by_id(task.task_id)
        assert found is None
    
    @pytest.mark.asyncio
    async def test_list_tasks(self, uow):
        """Test listing tasks with filters."""
        for i in range(3):
            task = SchedulerTask(
                task_id=str(uuid.uuid4()),
                task_class=f"ListTask{i}",
                schedule="0 * * * *",
                enabled=i < 2,
            )
            await uow.scheduler_tasks.create(task)
        
        await uow.commit()
        
        # List all tasks
        all_tasks = await uow.scheduler_tasks.list()
        assert len(all_tasks) >= 3
        
        # List only enabled tasks
        enabled_tasks = await uow.scheduler_tasks.list(filters={"enabled": True})
        assert len(enabled_tasks) >= 2
    
    @pytest.mark.asyncio
    async def test_count_tasks(self, uow):
        """Test counting tasks."""
        for i in range(3):
            task = SchedulerTask(
                task_id=str(uuid.uuid4()),
                task_class=f"CountTask{i}",
                schedule="0 * * * *",
            )
            await uow.scheduler_tasks.create(task)
        
        await uow.commit()
        
        count = await uow.scheduler_tasks.count()
        assert count >= 3
    
    @pytest.mark.asyncio
    async def test_get_enabled_tasks(self, uow):
        """Test getting all enabled tasks."""
        for i in range(3):
            task = SchedulerTask(
                task_id=str(uuid.uuid4()),
                task_class=f"EnabledTask{i}",
                schedule="0 * * * *",
                enabled=i < 2,
            )
            await uow.scheduler_tasks.create(task)
        
        await uow.commit()
        
        enabled_tasks = await uow.scheduler_tasks.get_enabled_tasks()
        assert len(enabled_tasks) >= 2
        # All returned tasks should be enabled
        for task in enabled_tasks:
            assert task.enabled is True
