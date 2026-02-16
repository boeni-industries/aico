"""
Integration tests for AgencyRemindersRepository.

Tests AgencyRemindersRepository with real PostgreSQL database.
"""

import pytest
import uuid
from datetime import datetime, UTC, timedelta

from aico.data.agency.models import AgencyReminder, Goal
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
    """Create a test user for reminder tests."""
    user = UserProfile(
        uuid=str(uuid.uuid4()),
        full_name="Reminder Test User",
        nickname="reminder_tester",
        user_type="parent",
        is_active=True,
        primary_language="en",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    await uow.users.create(user)
    await uow.commit()
    return user


@pytest.fixture
async def test_goal(uow, test_user):
    """Create a test goal for reminder tests."""
    goal = Goal(
        goal_id=str(uuid.uuid4()),
        user_id=test_user.uuid,
        origin="user",
        title="Test Goal for Reminders",
        status="active",
        priority="high",
        goal_type="learning",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    await uow.goals.create(goal)
    await uow.commit()
    return goal


class TestAgencyRemindersRepository:
    """Test AgencyRemindersRepository CRUD operations."""
    
    @pytest.mark.asyncio
    async def test_create_reminder(self, uow, test_user, test_goal):
        """Test creating a new agency reminder."""
        reminder = AgencyReminder(
            reminder_id=str(uuid.uuid4()),
            user_id=test_user.uuid,
            goal_id=test_goal.goal_id,
            title="Complete your goal",
            description="Don't forget to work on your goal today",
            scheduled_at=(datetime.now(UTC) + timedelta(hours=2)).isoformat(),
            status="pending",
            priority="normal",
            created_at=datetime.now(UTC).isoformat(),
            updated_at=datetime.now(UTC).isoformat(),
        )
        
        created = await uow.agency_reminders.create(reminder)
        await uow.commit()
        
        assert created.reminder_id == reminder.reminder_id
        assert created.title == "Complete your goal"
        assert created.status == "pending"
    
    @pytest.mark.asyncio
    async def test_get_reminder_by_id(self, uow, test_user):
        """Test retrieving reminder by ID."""
        reminder = AgencyReminder(
            reminder_id=str(uuid.uuid4()),
            user_id=test_user.uuid,
            title="Test Reminder",
            scheduled_at=datetime.now(UTC).isoformat(),
            status="pending",
            priority="high",
            created_at=datetime.now(UTC).isoformat(),
            updated_at=datetime.now(UTC).isoformat(),
        )
        
        await uow.agency_reminders.create(reminder)
        await uow.commit()
        
        found = await uow.agency_reminders.get_by_id(reminder.reminder_id)
        assert found is not None
        assert found.reminder_id == reminder.reminder_id
        assert found.priority == "high"
    
    @pytest.mark.asyncio
    async def test_update_reminder(self, uow, test_user):
        """Test updating a reminder."""
        reminder = AgencyReminder(
            reminder_id=str(uuid.uuid4()),
            user_id=test_user.uuid,
            title="Update Test",
            scheduled_at=datetime.now(UTC).isoformat(),
            status="pending",
            priority="normal",
            snooze_count=0,
            created_at=datetime.now(UTC).isoformat(),
            updated_at=datetime.now(UTC).isoformat(),
        )
        
        await uow.agency_reminders.create(reminder)
        await uow.commit()
        
        # Update the reminder
        reminder.status = "delivered"
        reminder.delivered_at = datetime.now(UTC).isoformat()
        updated = await uow.agency_reminders.update(reminder)
        await uow.commit()
        
        assert updated.status == "delivered"
        
        # Verify update persisted
        found = await uow.agency_reminders.get_by_id(reminder.reminder_id)
        assert found.delivered_at is not None
    
    @pytest.mark.asyncio
    async def test_delete_reminder(self, uow, test_user):
        """Test deleting a reminder."""
        reminder = AgencyReminder(
            reminder_id=str(uuid.uuid4()),
            user_id=test_user.uuid,
            title="Delete Me",
            scheduled_at=datetime.now(UTC).isoformat(),
            status="pending",
            priority="normal",
            created_at=datetime.now(UTC).isoformat(),
            updated_at=datetime.now(UTC).isoformat(),
        )
        
        await uow.agency_reminders.create(reminder)
        await uow.commit()
        
        # Delete the reminder
        success = await uow.agency_reminders.delete(reminder.reminder_id)
        await uow.commit()
        
        assert success is True
        
        # Verify it's gone
        found = await uow.agency_reminders.get_by_id(reminder.reminder_id)
        assert found is None
    
    @pytest.mark.asyncio
    async def test_list_reminders(self, uow, test_user, test_goal):
        """Test listing reminders with filters."""
        for i in range(3):
            reminder = AgencyReminder(
                reminder_id=str(uuid.uuid4()),
                user_id=test_user.uuid,
                goal_id=test_goal.goal_id if i < 2 else None,
                title=f"Reminder {i}",
                scheduled_at=datetime.now(UTC).isoformat(),
                status="pending" if i < 2 else "delivered",
                priority="high" if i == 0 else "normal",
                created_at=datetime.now(UTC).isoformat(),
                updated_at=datetime.now(UTC).isoformat(),
            )
            await uow.agency_reminders.create(reminder)
        
        await uow.commit()
        
        # List all reminders for user
        all_reminders = await uow.agency_reminders.list(filters={"user_id": test_user.uuid})
        assert len(all_reminders) >= 3
        
        # List by status
        pending = await uow.agency_reminders.list(filters={"status": "pending"})
        assert len(pending) >= 2
        
        # List by priority
        high_priority = await uow.agency_reminders.list(filters={"priority": "high"})
        assert len(high_priority) >= 1
    
    @pytest.mark.asyncio
    async def test_count_reminders(self, uow, test_user):
        """Test counting reminders."""
        for i in range(3):
            reminder = AgencyReminder(
                reminder_id=str(uuid.uuid4()),
                user_id=test_user.uuid,
                title=f"Count Reminder {i}",
                scheduled_at=datetime.now(UTC).isoformat(),
                status="pending",
                priority="normal",
                created_at=datetime.now(UTC).isoformat(),
                updated_at=datetime.now(UTC).isoformat(),
            )
            await uow.agency_reminders.create(reminder)
        
        await uow.commit()
        
        count = await uow.agency_reminders.count(filters={"user_id": test_user.uuid})
        assert count >= 3
    
    @pytest.mark.asyncio
    async def test_get_pending_for_user(self, uow, test_user):
        """Test getting pending reminders for user."""
        for i in range(3):
            reminder = AgencyReminder(
                reminder_id=str(uuid.uuid4()),
                user_id=test_user.uuid,
                title=f"Pending Reminder {i}",
                scheduled_at=datetime.now(UTC).isoformat(),
                status="pending" if i < 2 else "delivered",
                priority="normal",
                created_at=datetime.now(UTC).isoformat(),
                updated_at=datetime.now(UTC).isoformat(),
            )
            await uow.agency_reminders.create(reminder)
        
        await uow.commit()
        
        pending = await uow.agency_reminders.get_pending_for_user(test_user.uuid)
        assert len(pending) >= 2
        for reminder in pending:
            assert reminder.status == "pending"
    
    @pytest.mark.asyncio
    async def test_snooze_reminder(self, uow, test_user):
        """Test snoozing a reminder."""
        reminder = AgencyReminder(
            reminder_id=str(uuid.uuid4()),
            user_id=test_user.uuid,
            title="Snooze Test",
            scheduled_at=datetime.now(UTC).isoformat(),
            status="pending",
            priority="normal",
            snooze_count=0,
            created_at=datetime.now(UTC).isoformat(),
            updated_at=datetime.now(UTC).isoformat(),
        )
        
        await uow.agency_reminders.create(reminder)
        await uow.commit()
        
        # Snooze the reminder
        snoozed_until = (datetime.now(UTC) + timedelta(hours=1)).isoformat()
        success = await uow.agency_reminders.snooze_reminder(reminder.reminder_id, snoozed_until)
        await uow.commit()
        
        assert success is True
        
        # Verify it's snoozed
        found = await uow.agency_reminders.get_by_id(reminder.reminder_id)
        assert found.status == "snoozed"
        assert found.snoozed_until == snoozed_until
        assert found.snooze_count == 1
    
    @pytest.mark.asyncio
    async def test_mark_as_delivered(self, uow, test_user):
        """Test marking a reminder as delivered."""
        reminder = AgencyReminder(
            reminder_id=str(uuid.uuid4()),
            user_id=test_user.uuid,
            title="Delivery Test",
            scheduled_at=datetime.now(UTC).isoformat(),
            status="pending",
            priority="normal",
            created_at=datetime.now(UTC).isoformat(),
            updated_at=datetime.now(UTC).isoformat(),
        )
        
        await uow.agency_reminders.create(reminder)
        await uow.commit()
        
        # Mark as delivered
        success = await uow.agency_reminders.mark_as_delivered(reminder.reminder_id)
        await uow.commit()
        
        assert success is True
        
        # Verify it's delivered
        found = await uow.agency_reminders.get_by_id(reminder.reminder_id)
        assert found.status == "delivered"
        assert found.delivered_at is not None
    
    @pytest.mark.asyncio
    async def test_get_reminders_by_cluster(self, uow, test_user):
        """Test getting reminders by cluster ID."""
        cluster_id = str(uuid.uuid4())
        
        for i in range(3):
            reminder = AgencyReminder(
                reminder_id=str(uuid.uuid4()),
                user_id=test_user.uuid,
                title=f"Cluster Reminder {i}",
                scheduled_at=datetime.now(UTC).isoformat(),
                status="pending",
                priority="normal",
                cluster_id=cluster_id,
                created_at=datetime.now(UTC).isoformat(),
                updated_at=datetime.now(UTC).isoformat(),
            )
            await uow.agency_reminders.create(reminder)
        
        await uow.commit()
        
        cluster_reminders = await uow.agency_reminders.get_reminders_by_cluster(cluster_id)
        assert len(cluster_reminders) >= 3
        for reminder in cluster_reminders:
            assert reminder.cluster_id == cluster_id
