"""OutboxPublisherService

Background publisher that retries publication of outbox events.

Design goals:
- Never impact streaming TTFB
- Only used as fallback when inline publish fails
- Simple polling loop (low frequency) with exponential backoff per event
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import datetime, timedelta, UTC

from aico.core.bus import MessageBusClient
from aico.data.postgres.connection import get_session_factory
from aico.data.uow import UnitOfWork

from backend.core.service_container import BaseService


@dataclass
class OutboxPublisherConfig:
    poll_interval_seconds: float = 0.5
    batch_size: int = 50
    max_attempts: int = 25
    base_backoff_seconds: float = 0.5
    max_backoff_seconds: float = 30.0


class OutboxPublisherService(BaseService):
    def __init__(self, name: str, container, config: OutboxPublisherConfig | None = None):
        super().__init__(name, container)
        self.config = config or OutboxPublisherConfig()

        self._task: asyncio.Task | None = None
        self._stop_event = asyncio.Event()
        self._bus: MessageBusClient | None = None

    async def initialize(self) -> None:
        return

    async def start(self) -> None:
        if self._task and not self._task.done():
            return

        self._stop_event.clear()
        self._bus = MessageBusClient("outbox_publisher")
        await self._bus.connect()

        self._task = asyncio.create_task(self._run_loop())
        self.logger.info(
            "Outbox publisher started",
            extra={
                "poll_interval_seconds": self.config.poll_interval_seconds,
                "batch_size": self.config.batch_size,
            },
        )

    async def stop(self) -> None:
        self._stop_event.set()
        if self._task:
            try:
                await asyncio.wait_for(self._task, timeout=5.0)
            except Exception:
                pass
        if self._bus:
            await self._bus.disconnect()
            self._bus = None
        self.logger.info("Outbox publisher stopped")

    async def _run_loop(self) -> None:
        while not self._stop_event.is_set():
            try:
                await self._publish_batch_once()
            except Exception as e:
                self.logger.error(f"Outbox publisher loop error: {e}")

            try:
                await asyncio.wait_for(self._stop_event.wait(), timeout=self.config.poll_interval_seconds)
            except asyncio.TimeoutError:
                pass

    async def _publish_batch_once(self) -> None:
        if not self._bus:
            return

        session_factory = await get_session_factory()
        async with UnitOfWork(session_factory) as uow:
            events = await uow.outbox_events.fetch_pending(limit=self.config.batch_size)
            if not events:
                return

            for event in events:
                attempts_next = int(event.attempts or 0) + 1

                if attempts_next > self.config.max_attempts:
                    # Stop retrying; leave record for inspection.
                    await uow.outbox_events.mark_failed(
                        event_id=event.event_id,
                        error=f"Max attempts exceeded ({self.config.max_attempts})",
                        next_available_at=datetime.now(UTC) + timedelta(days=365),
                        attempts=attempts_next,
                    )
                    continue

                try:
                    await self._bus._nats.publish(event.subject, event.payload_bytes)
                    await uow.outbox_events.mark_sent(event_id=event.event_id)
                except Exception as e:
                    backoff = min(
                        self.config.max_backoff_seconds,
                        self.config.base_backoff_seconds * (2 ** max(0, attempts_next - 1)),
                    )
                    await uow.outbox_events.mark_failed(
                        event_id=event.event_id,
                        error=str(e),
                        next_available_at=datetime.now(UTC) + timedelta(seconds=backoff),
                        attempts=attempts_next,
                    )
