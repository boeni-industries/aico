import uuid

import pytest

from aico.data.outbox.models import OutboxEvent
from aico.data.uow import UnitOfWork
from backend.services.outbox_publisher import OutboxPublisherConfig, OutboxPublisherService


class _DedupeJetStreamManager:
    """Fake JS manager that simulates JetStream msg-id dedupe by ignoring duplicate Nats-Msg-Id publishes."""

    def __init__(self, _nats):
        self.publishes: list[dict] = []
        self._seen_msg_ids: set[str] = set()

    async def publish(self, subject: str, payload: bytes, *, headers=None):
        msg_id = (headers or {}).get("Nats-Msg-Id")
        if msg_id and msg_id in self._seen_msg_ids:
            return
        if msg_id:
            self._seen_msg_ids.add(msg_id)
        self.publishes.append({"subject": subject, "payload": payload, "headers": headers})


class _FakeBus:
    def __init__(self):
        self._nats = object()


@pytest.mark.asyncio
async def test_outbox_publisher_crash_restart_no_duplicate_side_effects(monkeypatch, session_factory):
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

    js = _DedupeJetStreamManager(object())

    async def _fake_get_session_factory():
        return session_factory

    monkeypatch.setattr("backend.services.outbox_publisher.get_session_factory", _fake_get_session_factory)
    monkeypatch.setattr("backend.services.outbox_publisher.JetStreamManager", lambda _nats: js)

    svc1 = OutboxPublisherService(
        "outbox_publisher",
        container=None,
        config=OutboxPublisherConfig(poll_interval_seconds=0.01, base_backoff_seconds=0.0, max_backoff_seconds=0.0),
    )
    svc1._bus = _FakeBus()

    orig_publish = svc1._publish_outbox_event

    async def _crash_after_publish(*args, **kwargs):
        await orig_publish(*args, **kwargs)
        raise RuntimeError("simulated crash after publish before mark_sent")

    monkeypatch.setattr(svc1, "_publish_outbox_event", _crash_after_publish)

    await svc1._publish_batch_once()

    async with UnitOfWork(session_factory) as uow:
        stored = await uow.outbox_events.get_by_id(event_id=event_id)
        assert stored is not None
        assert stored.status == "pending"
        assert (stored.attempts or 0) >= 1

    assert len(js.publishes) == 2

    svc2 = OutboxPublisherService(
        "outbox_publisher",
        container=None,
        config=OutboxPublisherConfig(poll_interval_seconds=0.01, base_backoff_seconds=0.0, max_backoff_seconds=0.0),
    )
    svc2._bus = _FakeBus()

    await svc2._publish_batch_once()

    async with UnitOfWork(session_factory) as uow:
        stored2 = await uow.outbox_events.get_by_id(event_id=event_id)
        assert stored2 is not None
        assert stored2.status == "sent"

    assert len(js.publishes) == 2
    assert js.publishes[0]["headers"] == {"Nats-Msg-Id": event_id}
    assert js.publishes[1]["headers"]["Nats-Msg-Id"] == f"audit:{event_id}"
