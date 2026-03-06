"""OutboxEventsRepository - PostgreSQL implementation."""

from __future__ import annotations

from datetime import datetime, UTC
from typing import Optional, List

from sqlalchemy import select, update, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from aico.data.outbox.models import OutboxEvent
from aico.data.tables import outbox_events


class PostgresOutboxEventsRepository:
    """PostgreSQL implementation for outbox events."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def enqueue(self, event: OutboxEvent) -> OutboxEvent:
        stmt = outbox_events.insert().values(
            event_id=event.event_id,
            tenant_id=event.tenant_id,
            subject=event.subject,
            payload_bytes=event.payload_bytes,
            status=event.status,
            attempts=event.attempts,
            last_error=event.last_error,
            available_at=event.available_at or datetime.now(UTC),
            created_at=event.created_at or datetime.now(UTC),
            sent_at=event.sent_at,
        )
        await self.session.execute(stmt)
        return event

    async def fetch_pending(self, *, limit: int = 50) -> List[OutboxEvent]:
        now = datetime.now(UTC)
        stmt = (
            select(outbox_events)
            .where(
                and_(
                    outbox_events.c.status == "pending",
                    outbox_events.c.available_at <= now,
                )
            )
            .order_by(outbox_events.c.available_at.asc(), outbox_events.c.created_at.asc())
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return [OutboxEvent(**dict(row._mapping)) for row in result.fetchall()]

    async def mark_sent(self, *, event_id: str) -> None:
        stmt = (
            update(outbox_events)
            .where(outbox_events.c.event_id == event_id)
            .values(status="sent", sent_at=func.current_timestamp())
        )
        await self.session.execute(stmt)

    async def mark_failed(
        self,
        *,
        event_id: str,
        error: str,
        next_available_at: datetime,
        attempts: int,
    ) -> None:
        stmt = (
            update(outbox_events)
            .where(outbox_events.c.event_id == event_id)
            .values(
                status="pending",
                attempts=attempts,
                last_error=error,
                available_at=next_available_at,
            )
        )
        await self.session.execute(stmt)

    async def get_by_id(self, *, event_id: str) -> Optional[OutboxEvent]:
        stmt = select(outbox_events).where(outbox_events.c.event_id == event_id)
        result = await self.session.execute(stmt)
        row = result.fetchone()
        return OutboxEvent(**dict(row._mapping)) if row else None
