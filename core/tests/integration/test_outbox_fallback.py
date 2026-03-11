import uuid

import pytest

from aico.data.outbox.models import OutboxEvent
from aico.data.uow import UnitOfWork


@pytest.mark.asyncio
async def test_outbox_enqueue_and_fetch_pending(session_factory):
    tenant_id = "test-tenant"

    async with UnitOfWork(session_factory) as uow:
        event = OutboxEvent(
            event_id=str(uuid.uuid4()),
            tenant_id=tenant_id,
            subject="conversation.response.v1",
            payload_bytes=b"dummy",
            status="pending",
            attempts=0,
        )
        await uow.outbox_events.enqueue(event)

    async with UnitOfWork(session_factory) as uow:
        pending = await uow.outbox_events.fetch_pending(limit=10)
        assert any(e.event_id == event.event_id for e in pending)
