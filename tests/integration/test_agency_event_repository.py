"""
Integration tests for AgencyEventRepository.

Tests AgencyEventRepository with real PostgreSQL database.
"""

import pytest
import uuid
from datetime import datetime, UTC

from aico.data.agency.models import AgencyEvent, Goal
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
    """Create a test user for agency event tests."""
    user = UserProfile(
        uuid=str(uuid.uuid4()),
        full_name="Agency Event Test User",
        nickname="event_tester",
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
    """Create a test goal for event tests."""
    goal = Goal(
        goal_id=str(uuid.uuid4()),
        user_id=test_user.uuid,
        origin="user",
        title="Test Goal",
        status="active",
        priority="high",
        goal_type="learning",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    await uow.goals.create(goal)
    await uow.commit()
    return goal


class TestAgencyEventRepository:
    """Test AgencyEventRepository CRUD operations."""
    
    @pytest.mark.asyncio
    async def test_create_event(self, uow, test_user, test_goal):
        """Test creating a new agency event."""
        event = AgencyEvent(
            id=0,  # Will be set by database
            user_id=test_user.uuid,
            goal_id=test_goal.goal_id,
            event_type="decision",
            source="engine",
            payload_json={"action": "goal_created", "details": "Test goal created"},
        )
        
        created = await uow.agency_events.create(event)
        await uow.commit()
        
        assert created.id > 0
        assert created.user_id == test_user.uuid
        assert created.event_type == "decision"
    
    @pytest.mark.asyncio
    async def test_get_event_by_id(self, uow, test_user):
        """Test retrieving event by ID."""
        event = AgencyEvent(
            id=0,
            user_id=test_user.uuid,
            event_type="metric",
            source="arbiter",
            payload_json={"metric": "success_rate", "value": 0.85},
        )
        
        await uow.agency_events.create(event)
        await uow.commit()
        
        found = await uow.agency_events.get_by_id(event.id)
        assert found is not None
        assert found.id == event.id
        assert found.event_type == "metric"
    
    @pytest.mark.asyncio
    async def test_update_event(self, uow, test_user):
        """Test updating an event."""
        event = AgencyEvent(
            id=0,
            user_id=test_user.uuid,
            event_type="plan_update",
            source="planner",
            payload_json={"status": "draft"},
        )
        
        await uow.agency_events.create(event)
        await uow.commit()
        
        # Update the event
        event.payload_json = {"status": "active", "updated": True}
        updated = await uow.agency_events.update(event)
        await uow.commit()
        
        assert updated.payload_json["status"] == "active"
        
        # Verify update persisted
        found = await uow.agency_events.get_by_id(event.id)
        assert found.payload_json["updated"] is True
    
    @pytest.mark.asyncio
    async def test_delete_event(self, uow, test_user):
        """Test deleting an event."""
        event = AgencyEvent(
            id=0,
            user_id=test_user.uuid,
            event_type="error",
            source="engine",
            payload_json={"error": "test_error"},
        )
        
        await uow.agency_events.create(event)
        await uow.commit()
        
        # Delete the event
        success = await uow.agency_events.delete(event.id)
        await uow.commit()
        
        assert success is True
        
        # Verify it's gone
        found = await uow.agency_events.get_by_id(event.id)
        assert found is None
    
    @pytest.mark.asyncio
    async def test_list_events(self, uow, test_user, test_goal):
        """Test listing events with filters."""
        for i in range(3):
            event = AgencyEvent(
                id=0,
                user_id=test_user.uuid,
                goal_id=test_goal.goal_id if i < 2 else None,
                event_type="decision" if i < 2 else "metric",
                source="engine",
                payload_json={"index": i},
            )
            await uow.agency_events.create(event)
        
        await uow.commit()
        
        # List all events for user
        all_events = await uow.agency_events.list(filters={"user_id": test_user.uuid})
        assert len(all_events) >= 3
        
        # List by goal
        goal_events = await uow.agency_events.list(filters={"goal_id": test_goal.goal_id})
        assert len(goal_events) >= 2
        
        # List by event type
        decision_events = await uow.agency_events.list(filters={"event_type": "decision"})
        assert len(decision_events) >= 2
    
    @pytest.mark.asyncio
    async def test_count_events(self, uow, test_user):
        """Test counting events."""
        for i in range(3):
            event = AgencyEvent(
                id=0,
                user_id=test_user.uuid,
                event_type="trigger",
                source="engine",
                payload_json={"count": i},
            )
            await uow.agency_events.create(event)
        
        await uow.commit()
        
        count = await uow.agency_events.count(filters={"user_id": test_user.uuid})
        assert count >= 3
    
    @pytest.mark.asyncio
    async def test_get_events_for_goal(self, uow, test_user, test_goal):
        """Test getting all events for a specific goal."""
        for i in range(3):
            event = AgencyEvent(
                id=0,
                user_id=test_user.uuid,
                goal_id=test_goal.goal_id,
                event_type="decision",
                source="engine",
                payload_json={"step": i},
            )
            await uow.agency_events.create(event)
        
        await uow.commit()
        
        goal_events = await uow.agency_events.get_events_for_goal(test_goal.goal_id)
        assert len(goal_events) >= 3
        for event in goal_events:
            assert event.goal_id == test_goal.goal_id
    
    @pytest.mark.asyncio
    async def test_get_events_by_type(self, uow, test_user):
        """Test getting events by type for a user."""
        for i in range(3):
            event = AgencyEvent(
                id=0,
                user_id=test_user.uuid,
                event_type="metric" if i < 2 else "error",
                source="arbiter",
                payload_json={"value": i},
            )
            await uow.agency_events.create(event)
        
        await uow.commit()
        
        metric_events = await uow.agency_events.get_events_by_type(test_user.uuid, "metric")
        assert len(metric_events) >= 2
        for event in metric_events:
            assert event.event_type == "metric"
