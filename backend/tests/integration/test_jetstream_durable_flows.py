import pytest

from google.protobuf.struct_pb2 import Struct

from aico.core.bus import MessageBusClient
from backend.services.outbox_publisher import OutboxPublisherService


class _FakeJetStream:
    def __init__(self):
        self.streams = []
        self.publishes = []

    async def ensure_stream(self, spec):
        self.streams.append(spec)

    async def publish(self, subject, payload, *, headers=None):
        self.publishes.append({"subject": subject, "payload": payload, "headers": headers})


@pytest.mark.asyncio
async def test_outbox_publisher_emits_durable_and_audit_copies():
    svc = OutboxPublisherService("outbox_publisher", container=None)
    js = _FakeJetStream()

    await svc._publish_outbox_event(
        js,
        event_id="evt-123",
        subject="conversation.response.v1",
        payload_bytes=b"hello",
    )

    assert len(js.publishes) == 2

    assert js.publishes[0]["subject"] == "conversation.response.v1"
    assert js.publishes[0]["headers"] == {"Nats-Msg-Id": "evt-123"}

    assert js.publishes[1]["subject"] == "audit.events.outbox"
    assert js.publishes[1]["headers"]["Nats-Msg-Id"] == "audit:evt-123"
    assert js.publishes[1]["headers"]["aico-original-subject"] == "conversation.response.v1"
    assert js.publishes[1]["headers"]["aico-event-id"] == "evt-123"


@pytest.mark.asyncio
async def test_message_bus_publish_durable_sets_nats_msg_id_and_audit(monkeypatch):
    fake = _FakeJetStream()

    class _FakeJetStreamManager:
        def __init__(self, _nats):
            pass

        async def ensure_stream(self, spec):
            await fake.ensure_stream(spec)

        async def publish(self, subject, payload, *, headers=None):
            await fake.publish(subject, payload, headers=headers)

    monkeypatch.setattr("aico.core.jetstream.JetStreamManager", _FakeJetStreamManager)

    bus = MessageBusClient("test")
    bus.running = True
    bus._nats = object()

    payload = Struct()
    payload.update({"k": "v"})

    await bus.publish_durable(
        "interaction.notifications.user-1",
        payload,
        correlation_id="corr-1",
        audit_subject="audit.events.interaction",
    )

    assert len(fake.publishes) == 2
    assert fake.publishes[0]["subject"] == "interaction.notifications.user-1"
    assert "Nats-Msg-Id" in (fake.publishes[0]["headers"] or {})

    assert fake.publishes[1]["subject"] == "audit.events.interaction"
    assert (fake.publishes[1]["headers"] or {}).get("aico-original-subject") == "interaction.notifications.user-1"
    assert "Nats-Msg-Id" in (fake.publishes[1]["headers"] or {})
