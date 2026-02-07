"""InteractionEventsRepository - PostgreSQL implementation."""

from __future__ import annotations

from typing import Optional, List, Any
from datetime import datetime, UTC

from sqlalchemy import select, delete, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from aico.data.interaction.models import InteractionEvent
from aico.data.tables import interaction_events
from aico.data.repositories.base import Repository


class PostgresInteractionEventsRepository(Repository[InteractionEvent]):
    """PostgreSQL implementation of interaction events repository."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, entity: InteractionEvent) -> InteractionEvent:
        stmt = interaction_events.insert().values(
            event_id=entity.event_id,
            interaction_id=entity.interaction_id,
            user_id=entity.user_id,
            correlation_id=entity.correlation_id,
            actor=entity.actor,
            event_type=entity.event_type,
            from_status=entity.from_status,
            to_status=entity.to_status,
            payload_json=entity.payload_json,
            created_at=entity.created_at or datetime.now(UTC),
        )
        await self.session.execute(stmt)
        return entity

    async def get_by_id(self, id: str) -> Optional[InteractionEvent]:
        stmt = select(interaction_events).where(interaction_events.c.event_id == id)
        result = await self.session.execute(stmt)
        row = result.fetchone()
        return InteractionEvent(**dict(row._mapping)) if row else None

    async def update(self, entity: InteractionEvent) -> InteractionEvent:
        raise NotImplementedError("interaction_events are append-only")

    async def delete(self, id: str) -> Any:
        stmt = delete(interaction_events).where(interaction_events.c.event_id == id)
        await self.session.execute(stmt)

    async def list(
        self,
        filters: Optional[dict] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[InteractionEvent]:
        stmt = select(interaction_events)

        if filters:
            conditions = []
            if 'interaction_id' in filters:
                conditions.append(interaction_events.c.interaction_id == filters['interaction_id'])
            if 'user_id' in filters:
                conditions.append(interaction_events.c.user_id == filters['user_id'])
            if 'correlation_id' in filters:
                conditions.append(interaction_events.c.correlation_id == filters['correlation_id'])
            if conditions:
                stmt = stmt.where(and_(*conditions))

        stmt = stmt.order_by(interaction_events.c.created_at.asc()).limit(limit).offset(offset)
        result = await self.session.execute(stmt)
        return [InteractionEvent(**dict(row._mapping)) for row in result.fetchall()]

    async def count(self, filters: Optional[dict] = None) -> int:
        stmt = select(func.count()).select_from(interaction_events)

        if filters:
            conditions = []
            if 'interaction_id' in filters:
                conditions.append(interaction_events.c.interaction_id == filters['interaction_id'])
            if 'user_id' in filters:
                conditions.append(interaction_events.c.user_id == filters['user_id'])
            if conditions:
                stmt = stmt.where(and_(*conditions))

        result = await self.session.execute(stmt)
        return result.scalar() or 0
