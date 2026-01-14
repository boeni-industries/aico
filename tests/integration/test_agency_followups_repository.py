"""
Integration tests for AgencyFollowupsRepository.

Tests AgencyFollowupsRepository with real PostgreSQL database.
"""

import pytest
import uuid
from datetime import datetime, UTC, timedelta

from aico.data.agency.models import AgencyFollowup, Goal
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
    """Create a test user for followup tests."""
    user = UserProfile(
        uuid=str(uuid.uuid4()),
        full_name="Followup Test User",
        nickname="followup_tester",
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
    """Create a test goal for followup tests."""
    goal = Goal(
        goal_id=str(uuid.uuid4()),
        user_id=test_user.uuid,
        origin="user",
        title="Test Goal for Followups",
        status="active",
        priority="high",
        goal_type="learning",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    await uow.goals.create(goal)
    await uow.commit()
    return goal


class TestAgencyFollowupsRepository:
    """Test AgencyFollowupsRepository CRUD operations."""
    
    @pytest.mark.asyncio
    async def test_create_followup(self, uow, test_user, test_goal):
        """Test creating a new agency followup."""
        followup = AgencyFollowup(
            followup_id=str(uuid.uuid4()),
            user_id=test_user.uuid,
            goal_id=test_goal.goal_id,
            followup_type="check_in",
            content="How is your progress on the goal?",
            scheduled_at=(datetime.now(UTC) + timedelta(hours=1)).isoformat(),
            status="pending",
            created_at=datetime.now(UTC).isoformat(),
            updated_at=datetime.now(UTC).isoformat(),
        )
        
        created = await uow.agency_followups.create(followup)
        await uow.commit()
        
        assert created.followup_id == followup.followup_id
        assert created.followup_type == "check_in"
        assert created.status == "pending"
    
    @pytest.mark.asyncio
    async def test_get_followup_by_id(self, uow, test_user):
        """Test retrieving followup by ID."""
        followup = AgencyFollowup(
            followup_id=str(uuid.uuid4()),
            user_id=test_user.uuid,
            followup_type="progress_update",
            content="Time to update your progress",
            scheduled_at=datetime.now(UTC).isoformat(),
            status="pending",
            created_at=datetime.now(UTC).isoformat(),
            updated_at=datetime.now(UTC).isoformat(),
        )
        
        await uow.agency_followups.create(followup)
        await uow.commit()
        
        found = await uow.agency_followups.get_by_id(followup.followup_id)
        assert found is not None
        assert found.followup_id == followup.followup_id
        assert found.followup_type == "progress_update"
    
    @pytest.mark.asyncio
    async def test_update_followup(self, uow, test_user):
        """Test updating a followup."""
        followup = AgencyFollowup(
            followup_id=str(uuid.uuid4()),
            user_id=test_user.uuid,
            followup_type="check_in",
            content="Check in message",
            scheduled_at=datetime.now(UTC).isoformat(),
            status="pending",
            created_at=datetime.now(UTC).isoformat(),
            updated_at=datetime.now(UTC).isoformat(),
        )
        
        await uow.agency_followups.create(followup)
        await uow.commit()
        
        # Update the followup
        followup.status = "responded"
        followup.user_response = "Making good progress!"
        followup.response_sentiment = 0.8
        updated = await uow.agency_followups.update(followup)
        await uow.commit()
        
        assert updated.status == "responded"
        
        # Verify update persisted
        found = await uow.agency_followups.get_by_id(followup.followup_id)
        assert found.user_response == "Making good progress!"
        assert found.response_sentiment == 0.8
    
    @pytest.mark.asyncio
    async def test_delete_followup(self, uow, test_user):
        """Test deleting a followup."""
        followup = AgencyFollowup(
            followup_id=str(uuid.uuid4()),
            user_id=test_user.uuid,
            followup_type="clarification",
            content="Need clarification",
            scheduled_at=datetime.now(UTC).isoformat(),
            status="pending",
            created_at=datetime.now(UTC).isoformat(),
            updated_at=datetime.now(UTC).isoformat(),
        )
        
        await uow.agency_followups.create(followup)
        await uow.commit()
        
        # Delete the followup
        success = await uow.agency_followups.delete(followup.followup_id)
        await uow.commit()
        
        assert success is True
        
        # Verify it's gone
        found = await uow.agency_followups.get_by_id(followup.followup_id)
        assert found is None
    
    @pytest.mark.asyncio
    async def test_list_followups(self, uow, test_user, test_goal):
        """Test listing followups with filters."""
        for i in range(3):
            followup = AgencyFollowup(
                followup_id=str(uuid.uuid4()),
                user_id=test_user.uuid,
                goal_id=test_goal.goal_id if i < 2 else None,
                followup_type="check_in" if i < 2 else "progress_update",
                content=f"Followup {i}",
                scheduled_at=datetime.now(UTC).isoformat(),
                status="pending" if i < 2 else "delivered",
                created_at=datetime.now(UTC).isoformat(),
                updated_at=datetime.now(UTC).isoformat(),
            )
            await uow.agency_followups.create(followup)
        
        await uow.commit()
        
        # List all followups for user
        all_followups = await uow.agency_followups.list(filters={"user_id": test_user.uuid})
        assert len(all_followups) >= 3
        
        # List by goal
        goal_followups = await uow.agency_followups.list(filters={"goal_id": test_goal.goal_id})
        assert len(goal_followups) >= 2
        
        # List by status
        pending = await uow.agency_followups.list(filters={"status": "pending"})
        assert len(pending) >= 2
    
    @pytest.mark.asyncio
    async def test_count_followups(self, uow, test_user):
        """Test counting followups."""
        for i in range(3):
            followup = AgencyFollowup(
                followup_id=str(uuid.uuid4()),
                user_id=test_user.uuid,
                followup_type="check_in",
                content=f"Count test {i}",
                scheduled_at=datetime.now(UTC).isoformat(),
                status="pending",
                created_at=datetime.now(UTC).isoformat(),
                updated_at=datetime.now(UTC).isoformat(),
            )
            await uow.agency_followups.create(followup)
        
        await uow.commit()
        
        count = await uow.agency_followups.count(filters={"user_id": test_user.uuid})
        assert count >= 3
    
    @pytest.mark.asyncio
    async def test_get_pending_for_user(self, uow, test_user):
        """Test getting pending followups for user."""
        for i in range(3):
            followup = AgencyFollowup(
                followup_id=str(uuid.uuid4()),
                user_id=test_user.uuid,
                followup_type="check_in",
                content=f"Pending test {i}",
                scheduled_at=datetime.now(UTC).isoformat(),
                status="pending" if i < 2 else "delivered",
                created_at=datetime.now(UTC).isoformat(),
                updated_at=datetime.now(UTC).isoformat(),
            )
            await uow.agency_followups.create(followup)
        
        await uow.commit()
        
        pending = await uow.agency_followups.get_pending_for_user(test_user.uuid)
        assert len(pending) >= 2
        for followup in pending:
            assert followup.status == "pending"
    
    @pytest.mark.asyncio
    async def test_mark_as_delivered(self, uow, test_user):
        """Test marking a followup as delivered."""
        followup = AgencyFollowup(
            followup_id=str(uuid.uuid4()),
            user_id=test_user.uuid,
            followup_type="check_in",
            content="Delivery test",
            scheduled_at=datetime.now(UTC).isoformat(),
            status="pending",
            created_at=datetime.now(UTC).isoformat(),
            updated_at=datetime.now(UTC).isoformat(),
        )
        
        await uow.agency_followups.create(followup)
        await uow.commit()
        
        # Mark as delivered
        success = await uow.agency_followups.mark_as_delivered(followup.followup_id)
        await uow.commit()
        
        assert success is True
        
        # Verify it's delivered
        found = await uow.agency_followups.get_by_id(followup.followup_id)
        assert found.status == "delivered"
        assert found.delivered_at is not None
    
    @pytest.mark.asyncio
    async def test_get_followups_for_goal(self, uow, test_user, test_goal):
        """Test getting followups for a specific goal."""
        for i in range(3):
            followup = AgencyFollowup(
                followup_id=str(uuid.uuid4()),
                user_id=test_user.uuid,
                goal_id=test_goal.goal_id,
                followup_type="check_in",
                content=f"Goal followup {i}",
                scheduled_at=datetime.now(UTC).isoformat(),
                status="pending",
                created_at=datetime.now(UTC).isoformat(),
                updated_at=datetime.now(UTC).isoformat(),
            )
            await uow.agency_followups.create(followup)
        
        await uow.commit()
        
        goal_followups = await uow.agency_followups.get_followups_for_goal(test_goal.goal_id)
        assert len(goal_followups) >= 3
        for followup in goal_followups:
            assert followup.goal_id == test_goal.goal_id
