"""
Integration tests for AgencyEventsLogRepository.

Tests AgencyEventsLogRepository with real PostgreSQL database.
"""

import pytest
import uuid
from datetime import datetime, UTC

from aico.data.agency.models import AgencyEventLog, Goal
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
    """Create a test user for event log tests."""
    user = UserProfile(
        uuid=str(uuid.uuid4()),
        full_name="Event Log Test User",
        nickname="eventlog_tester",
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
    """Create a test goal for event log tests."""
    goal = Goal(
        goal_id=str(uuid.uuid4()),
        user_id=test_user.uuid,
        origin="user",
        title="Test Goal for Events",
        status="active",
        priority="high",
        goal_type="learning",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    await uow.goals.create(goal)
    await uow.commit()
    return goal


class TestAgencyEventsLogRepository:
    """Test AgencyEventsLogRepository CRUD operations."""
    
    @pytest.mark.asyncio
    async def test_create_event_log(self, uow, test_user, test_goal):
        """Test creating a new agency event log entry."""
        event_log = AgencyEventLog(
            event_id=str(uuid.uuid4()),
            user_id=test_user.uuid,
            event_type="goal_created",
            event_category="goal",
            source_component="planner",
            entity_type="goal",
            entity_id=test_goal.goal_id,
            event_data='{"action": "created", "details": "New goal"}',
            created_at=datetime.now(UTC).isoformat(),
        )
        
        created = await uow.agency_events_log.create(event_log)
        await uow.commit()
        
        assert created.event_id == event_log.event_id
        assert created.event_type == "goal_created"
        assert created.entity_id == test_goal.goal_id
    
    @pytest.mark.asyncio
    async def test_get_event_log_by_id(self, uow, test_user):
        """Test retrieving event log by ID."""
        event_log = AgencyEventLog(
            event_id=str(uuid.uuid4()),
            user_id=test_user.uuid,
            event_type="plan_generated",
            event_category="plan",
            source_component="arbiter",
            event_data='{"status": "draft"}',
            created_at=datetime.now(UTC).isoformat(),
        )
        
        await uow.agency_events_log.create(event_log)
        await uow.commit()
        
        found = await uow.agency_events_log.get_by_id(event_log.event_id)
        assert found is not None
        assert found.event_id == event_log.event_id
        assert found.event_type == "plan_generated"
    
    @pytest.mark.asyncio
    async def test_update_event_log(self, uow, test_user):
        """Test updating an event log entry."""
        event_log = AgencyEventLog(
            event_id=str(uuid.uuid4()),
            user_id=test_user.uuid,
            event_type="skill_executed",
            event_category="execution",
            source_component="engine",
            event_data='{"status": "running"}',
            severity="info",
            created_at=datetime.now(UTC).isoformat(),
        )
        
        await uow.agency_events_log.create(event_log)
        await uow.commit()
        
        # Update the event log
        event_log.event_data = '{"status": "completed"}'
        event_log.severity = "debug"
        updated = await uow.agency_events_log.update(event_log)
        await uow.commit()
        
        assert updated.event_data == '{"status": "completed"}'
        
        # Verify update persisted
        found = await uow.agency_events_log.get_by_id(event_log.event_id)
        assert found.severity == "debug"
    
    @pytest.mark.asyncio
    async def test_delete_event_log(self, uow, test_user):
        """Test deleting an event log entry."""
        event_log = AgencyEventLog(
            event_id=str(uuid.uuid4()),
            user_id=test_user.uuid,
            event_type="feedback_received",
            event_category="feedback",
            source_component="ams",
            event_data='{"rating": 5}',
            created_at=datetime.now(UTC).isoformat(),
        )
        
        await uow.agency_events_log.create(event_log)
        await uow.commit()
        
        # Delete the event log
        success = await uow.agency_events_log.delete(event_log.event_id)
        await uow.commit()
        
        assert success is True
        
        # Verify it's gone
        found = await uow.agency_events_log.get_by_id(event_log.event_id)
        assert found is None
    
    @pytest.mark.asyncio
    async def test_list_event_logs(self, uow, test_user):
        """Test listing event logs with filters."""
        for i in range(3):
            event_log = AgencyEventLog(
                event_id=str(uuid.uuid4()),
                user_id=test_user.uuid,
                event_type="test_event" if i < 2 else "other_event",
                event_category="goal" if i < 2 else "plan",
                source_component="planner",
                event_data=f'{{"index": {i}}}',
                created_at=datetime.now(UTC).isoformat(),
            )
            await uow.agency_events_log.create(event_log)
        
        await uow.commit()
        
        # List all events for user
        all_events = await uow.agency_events_log.list(filters={"user_id": test_user.uuid})
        assert len(all_events) >= 3
        
        # List by category
        goal_events = await uow.agency_events_log.list(filters={"event_category": "goal"})
        assert len(goal_events) >= 2
        
        # List by event type
        test_events = await uow.agency_events_log.list(filters={"event_type": "test_event"})
        assert len(test_events) >= 2
    
    @pytest.mark.asyncio
    async def test_count_event_logs(self, uow, test_user):
        """Test counting event logs."""
        for i in range(3):
            event_log = AgencyEventLog(
                event_id=str(uuid.uuid4()),
                user_id=test_user.uuid,
                event_type="count_test",
                event_category="execution",
                source_component="engine",
                event_data=f'{{"count": {i}}}',
                created_at=datetime.now(UTC).isoformat(),
            )
            await uow.agency_events_log.create(event_log)
        
        await uow.commit()
        
        count = await uow.agency_events_log.count(filters={"user_id": test_user.uuid})
        assert count >= 3
    
    @pytest.mark.asyncio
    async def test_get_by_workflow_trace(self, uow, test_user):
        """Test getting events by workflow trace ID."""
        workflow_id = str(uuid.uuid4())
        
        for i in range(3):
            event_log = AgencyEventLog(
                event_id=str(uuid.uuid4()),
                user_id=test_user.uuid,
                event_type="workflow_event",
                event_category="execution",
                source_component="engine",
                event_data=f'{{"step": {i}}}',
                workflow_trace_id=workflow_id,
                created_at=datetime.now(UTC).isoformat(),
            )
            await uow.agency_events_log.create(event_log)
        
        await uow.commit()
        
        workflow_events = await uow.agency_events_log.get_by_workflow_trace(workflow_id)
        assert len(workflow_events) >= 3
        for event in workflow_events:
            assert event.workflow_trace_id == workflow_id
    
    @pytest.mark.asyncio
    async def test_get_by_entity(self, uow, test_user, test_goal):
        """Test getting events by entity type and ID."""
        for i in range(3):
            event_log = AgencyEventLog(
                event_id=str(uuid.uuid4()),
                user_id=test_user.uuid,
                event_type="entity_event",
                event_category="goal",
                source_component="planner",
                entity_type="goal",
                entity_id=test_goal.goal_id,
                event_data=f'{{"action": "update_{i}"}}',
                created_at=datetime.now(UTC).isoformat(),
            )
            await uow.agency_events_log.create(event_log)
        
        await uow.commit()
        
        entity_events = await uow.agency_events_log.get_by_entity("goal", test_goal.goal_id)
        assert len(entity_events) >= 3
        for event in entity_events:
            assert event.entity_type == "goal"
            assert event.entity_id == test_goal.goal_id
    
    @pytest.mark.asyncio
    async def test_get_by_category(self, uow, test_user):
        """Test getting events by category for a user."""
        for i in range(3):
            event_log = AgencyEventLog(
                event_id=str(uuid.uuid4()),
                user_id=test_user.uuid,
                event_type="category_test",
                event_category="reflection" if i < 2 else "policy",
                source_component="reflection_engine",
                event_data=f'{{"value": {i}}}',
                created_at=datetime.now(UTC).isoformat(),
            )
            await uow.agency_events_log.create(event_log)
        
        await uow.commit()
        
        reflection_events = await uow.agency_events_log.get_by_category(test_user.uuid, "reflection")
        assert len(reflection_events) >= 2
        for event in reflection_events:
            assert event.event_category == "reflection"
