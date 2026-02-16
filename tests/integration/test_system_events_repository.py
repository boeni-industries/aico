"""
Integration tests for SystemEventsRepository.
"""

import pytest
import uuid
from datetime import datetime, UTC

from aico.data.system.event_models import SystemEvent
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


class TestSystemEventsRepository:
    
    @pytest.mark.asyncio
    async def test_create_event(self, uow):
        event = SystemEvent(
            id=0,
            timestamp=datetime.now(UTC).isoformat(),
            topic="test.topic",
            source="test_source",
            message_type="TestMessage",
            message_id=str(uuid.uuid4()),
            priority=1,
        )
        
        created = await uow.system_events.create(event)
        await uow.commit()
        
        assert created.id > 0
        assert created.topic == "test.topic"
    
    @pytest.mark.asyncio
    async def test_get_event_by_id(self, uow):
        event = SystemEvent(
            id=0,
            timestamp=datetime.now(UTC).isoformat(),
            topic="test.topic2",
            source="test_source2",
            message_type="TestMessage2",
            message_id=str(uuid.uuid4()),
            priority=2,
        )
        
        created = await uow.system_events.create(event)
        await uow.commit()
        
        found = await uow.system_events.get_by_id(str(created.id))
        assert found is not None
        assert found.topic == "test.topic2"
    
    @pytest.mark.asyncio
    async def test_update_event(self, uow):
        event = SystemEvent(
            id=0,
            timestamp=datetime.now(UTC).isoformat(),
            topic="test.topic3",
            source="test_source3",
            message_type="TestMessage3",
            message_id=str(uuid.uuid4()),
            priority=1,
        )
        
        created = await uow.system_events.create(event)
        await uow.commit()
        
        created.metadata = {"updated": True}
        updated = await uow.system_events.update(created)
        await uow.commit()
        
        assert updated.metadata == {"updated": True}
        
        found = await uow.system_events.get_by_id(str(created.id))
        assert found.metadata == {"updated": True}
    
    @pytest.mark.asyncio
    async def test_delete_event(self, uow):
        event = SystemEvent(
            id=0,
            timestamp=datetime.now(UTC).isoformat(),
            topic="test.topic4",
            source="test_source4",
            message_type="TestMessage4",
            message_id=str(uuid.uuid4()),
            priority=1,
        )
        
        created = await uow.system_events.create(event)
        await uow.commit()
        
        success = await uow.system_events.delete(str(created.id))
        await uow.commit()
        
        assert success is True
        
        found = await uow.system_events.get_by_id(str(created.id))
        assert found is None
    
    @pytest.mark.asyncio
    async def test_list_events(self, uow):
        for i in range(3):
            event = SystemEvent(
                id=0,
                timestamp=datetime.now(UTC).isoformat(),
                topic="list.topic",
                source=f"source_{i}",
                message_type="ListMessage",
                message_id=str(uuid.uuid4()),
                priority=1,
            )
            await uow.system_events.create(event)
        
        await uow.commit()
        
        all_events = await uow.system_events.list(filters={"topic": "list.topic"})
        assert len(all_events) >= 3
    
    @pytest.mark.asyncio
    async def test_count_events(self, uow):
        topic = f"count.topic.{uuid.uuid4().hex[:8]}"
        for i in range(3):
            event = SystemEvent(
                id=0,
                timestamp=datetime.now(UTC).isoformat(),
                topic=topic,
                source="count_source",
                message_type="CountMessage",
                message_id=str(uuid.uuid4()),
                priority=1,
            )
            await uow.system_events.create(event)
        
        await uow.commit()
        
        count = await uow.system_events.count(filters={"topic": topic})
        assert count >= 3
    
    @pytest.mark.asyncio
    async def test_get_by_message_id(self, uow):
        msg_id = str(uuid.uuid4())
        event = SystemEvent(
            id=0,
            timestamp=datetime.now(UTC).isoformat(),
            topic="msgid.topic",
            source="msgid_source",
            message_type="MsgIdMessage",
            message_id=msg_id,
            priority=1,
        )
        
        await uow.system_events.create(event)
        await uow.commit()
        
        found = await uow.system_events.get_by_message_id(msg_id)
        assert found is not None
        assert found.message_id == msg_id
