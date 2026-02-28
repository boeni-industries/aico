from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Optional

from nats.aio.client import Client as NATS
from nats.js.api import (
    StreamConfig,
    ConsumerConfig,
    RetentionPolicy,
    StorageType,
    DeliverPolicy,
    AckPolicy,
)


@dataclass(frozen=True)
class JetStreamStreamSpec:
    name: str
    subjects: list[str]
    retention: RetentionPolicy = RetentionPolicy.WORK_QUEUE
    storage: StorageType = StorageType.FILE
    max_age_seconds: Optional[int] = None
    duplicate_window_seconds: Optional[int] = None


@dataclass(frozen=True)
class JetStreamConsumerSpec:
    stream: str
    durable_name: str
    filter_subject: str
    ack_wait_seconds: int = 60
    max_deliver: int = 20


class JetStreamManager:
    def __init__(self, nats_client: NATS):
        self._nc = nats_client
        self._js = self._nc.jetstream()

    async def ensure_stream(self, spec: JetStreamStreamSpec) -> None:
        existing = None
        try:
            existing = await self._js.stream_info(spec.name)
        except Exception:
            existing = None

        if existing is not None:
            return

        cfg_params = {
            "name": spec.name,
            "subjects": spec.subjects,
            "retention": spec.retention,
            "storage": spec.storage,
        }
        
        # Only add optional fields if they have values
        # Note: NATS Python client expects seconds (float), not nanoseconds
        # The library handles nanosecond conversion internally
        if spec.max_age_seconds is not None:
            cfg_params["max_age"] = float(spec.max_age_seconds)
        if spec.duplicate_window_seconds is not None:
            cfg_params["duplicate_window"] = float(spec.duplicate_window_seconds)
        
        cfg = StreamConfig(**cfg_params)
        await self._js.add_stream(cfg)

    async def ensure_consumer(self, spec: JetStreamConsumerSpec) -> None:
        existing = None
        try:
            existing = await self._js.consumer_info(spec.stream, spec.durable_name)
        except Exception:
            existing = None

        if existing is not None:
            return

        cfg = ConsumerConfig(
            durable_name=spec.durable_name,
            filter_subject=spec.filter_subject,
            deliver_policy=DeliverPolicy.ALL,
            ack_policy=AckPolicy.EXPLICIT,
            ack_wait=spec.ack_wait_seconds,
            max_deliver=spec.max_deliver,
        )
        await self._js.add_consumer(spec.stream, cfg)

    async def publish(self, subject: str, payload: bytes, *, headers: dict[str, str] | None = None) -> None:
        await self._js.publish(subject, payload, headers=headers)
