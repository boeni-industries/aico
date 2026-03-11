import uuid

import pytest

from aico.data.outbox.models import OutboxEvent
from aico.data.uow import UnitOfWork
from core.services.outbox_publisher import OutboxPublisherService


class _FakeJetStreamManager:
    def __init__(self, _nats):
        self.publishes: list[dict] = []

    async def publish(self, subject: str, payload: bytes, *, headers=None):
        self.publishes.append({"subject": subject, "payload": payload, "headers": headers})


class _FakeBus:
    def __init__(self):
        self._nats = object()


@pytest.mark.asyncio
async def test_outbox_publisher_restart_is_idempotent(monkeypatch, session_factory):
    event_id = f"evt-{uuid.uuid4().hex}"

    async with UnitOfWork(session_factory) as uow:
        await uow.outbox_events.enqueue(
            OutboxEvent(
                event_id=event_id,
                tenant_id="test-tenant",
                subject="conversation.response.v1",
                payload_bytes=b"dummy",
                status="pending",
                attempts=0,
            )
        )
        await uow.commit()

    svc = OutboxPublisherService("outbox_publisher", container=None)
    svc._bus = _FakeBus()

    js = _FakeJetStreamManager(svc._bus._nats)

    async def _fake_get_session_factory():
        return session_factory

    monkeypatch.setattr("backend.services.outbox_publisher.get_session_factory", _fake_get_session_factory)
    monkeypatch.setattr("backend.services.outbox_publisher.JetStreamManager", lambda _nats: js)

    await svc._publish_batch_once()

    async with UnitOfWork(session_factory) as uow:
        stored = await uow.outbox_events.get_by_id(event_id=event_id)
        assert stored is not None
        assert stored.status == "sent"

    assert len(js.publishes) == 2
    assert js.publishes[0]["subject"] == "conversation.response.v1"
    assert js.publishes[0]["headers"] == {"Nats-Msg-Id": event_id}
    assert js.publishes[1]["subject"] == "audit.events.outbox"

    await svc._publish_batch_once()

    assert len(js.publishes) == 2
