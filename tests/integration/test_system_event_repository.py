"""
Integration tests for SystemEventRepository.

Tests SystemEventRepository with real PostgreSQL database.
"""

import pytest
import uuid
from datetime import datetime, UTC

from aico.data.system.models import SystemEvent
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


class TestSystemEventRepository:
    """Test SystemEventRepository CRUD operations."""
    
    @pytest.mark.asyncio
    async def test_create_event(self, uow):
        """Test creating a new system event."""
        event = SystemEvent(
            id=0,
            timestamp=datetime.now(UTC).isoformat(),
            topic="test.topic",
            source="test_service",
            message_type="TestMessage",
            message_id=str(uuid.uuid4()),
            priority=1,
            metadata={"test": "data"},
        )
        
        created = await uow.system_events.create(event)
        await uow.commit()
        
        assert created.id > 0
        assert created.topic == "test.topic"
        assert created.source == "test_service"
    
    @pytest.mark.asyncio
    async def test_get_event_by_id(self, uow):
        """Test retrieving event by ID."""
        event = SystemEvent(
            id=0,
            timestamp=datetime.now(UTC).isoformat(),
            topic="test.retrieve",
            source="test_service",
            message_type="RetrieveTest",
            message_id=str(uuid.uuid4()),
        )
        
        await uow.system_events.create(event)
        await uow.commit()
        
        found = await uow.system_events.get_by_id(event.id)
        assert found is not None
        assert found.id == event.id
        assert found.topic == "test.retrieve"
    
    @pytest.mark.asyncio
    async def test_update_event(self, uow):
        """Test updating an event."""
        event = SystemEvent(
            id=0,
            timestamp=datetime.now(UTC).isoformat(),
            topic="test.update",
            source="test_service",
            message_type="UpdateTest",
            message_id=str(uuid.uuid4()),
            priority=1,
            metadata={"version": 1},
        )
        
        await uow.system_events.create(event)
        await uow.commit()
        
        # Update the event
        event.priority = 5
        event.metadata = {"version": 2, "updated": True}
        updated = await uow.system_events.update(event)
        await uow.commit()
        
        assert updated.priority == 5
        
        # Verify update persisted
        found = await uow.system_events.get_by_id(event.id)
        assert found.metadata["version"] == 2
    
    @pytest.mark.asyncio
    async def test_delete_event(self, uow):
        """Test deleting an event."""
        event = SystemEvent(
            id=0,
            timestamp=datetime.now(UTC).isoformat(),
            topic="test.delete",
            source="test_service",
            message_type="DeleteTest",
            message_id=str(uuid.uuid4()),
        )
        
        await uow.system_events.create(event)
        await uow.commit()
        
        # Delete the event
        success = await uow.system_events.delete(event.id)
        await uow.commit()
        
        assert success is True
        
        # Verify it's gone
        found = await uow.system_events.get_by_id(event.id)
        assert found is None
    
    @pytest.mark.asyncio
    async def test_list_events(self, uow):
        """Test listing events with filters."""
        for i in range(3):
            event = SystemEvent(
                id=0,
                timestamp=datetime.now(UTC).isoformat(),
                topic="test.list" if i < 2 else "test.other",
                source="service_a" if i < 2 else "service_b",
                message_type="ListTest",
                message_id=str(uuid.uuid4()),
            )
            await uow.system_events.create(event)
        
        await uow.commit()
        
        # List by topic
        topic_events = await uow.system_events.list(filters={"topic": "test.list"})
        assert len(topic_events) >= 2
        
        # List by source
        source_events = await uow.system_events.list(filters={"source": "service_a"})
        assert len(source_events) >= 2
    
    @pytest.mark.asyncio
    async def test_count_events(self, uow):
        """Test counting events."""
        for i in range(3):
            event = SystemEvent(
                id=0,
                timestamp=datetime.now(UTC).isoformat(),
                topic="test.count",
                source="count_service",
                message_type="CountTest",
                message_id=str(uuid.uuid4()),
            )
            await uow.system_events.create(event)
        
        await uow.commit()
        
        count = await uow.system_events.count(filters={"topic": "test.count"})
        assert count >= 3
    
    @pytest.mark.asyncio
    async def test_get_by_message_id(self, uow):
        """Test getting event by message ID."""
        message_id = str(uuid.uuid4())
        event = SystemEvent(
            id=0,
            timestamp=datetime.now(UTC).isoformat(),
            topic="test.message_id",
            source="test_service",
            message_type="MessageIdTest",
            message_id=message_id,
        )
        
        await uow.system_events.create(event)
        await uow.commit()
        
        found = await uow.system_events.get_by_message_id(message_id)
        assert found is not None
        assert found.message_id == message_id
    
    @pytest.mark.asyncio
    async def test_get_by_correlation_id(self, uow):
        """Test getting events by correlation ID."""
        correlation_id = str(uuid.uuid4())
        
        for i in range(3):
            event = SystemEvent(
                id=0,
                timestamp=datetime.now(UTC).isoformat(),
                topic="test.correlation",
                source="test_service",
                message_type="CorrelationTest",
                message_id=str(uuid.uuid4()),
                correlation_id=correlation_id,
            )
            await uow.system_events.create(event)
        
        await uow.commit()
        
        correlated = await uow.system_events.get_by_correlation_id(correlation_id)
        assert len(correlated) >= 3
        for event in correlated:
            assert event.correlation_id == correlation_id
    
    @pytest.mark.asyncio
    async def test_get_by_topic(self, uow):
        """Test getting events by topic."""
        topic = "test.specific.topic"
        
        for i in range(3):
            event = SystemEvent(
                id=0,
                timestamp=datetime.now(UTC).isoformat(),
                topic=topic,
                source="test_service",
                message_type="TopicTest",
                message_id=str(uuid.uuid4()),
            )
            await uow.system_events.create(event)
        
        await uow.commit()
        
        topic_events = await uow.system_events.get_by_topic(topic)
        assert len(topic_events) >= 3
        for event in topic_events:
            assert event.topic == topic
