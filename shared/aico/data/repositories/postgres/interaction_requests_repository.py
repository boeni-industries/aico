"""InteractionRequestsRepository - PostgreSQL implementation."""

from __future__ import annotations

from typing import Optional, List, Any
from datetime import datetime, UTC

from sqlalchemy import select, update, delete, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from aico.data.interaction.models import InteractionRequest
from aico.data.tables import interaction_requests
from aico.data.repositories.base import Repository


class PostgresInteractionRequestsRepository(Repository[InteractionRequest]):
    """PostgreSQL implementation of interaction requests repository."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, entity: InteractionRequest) -> InteractionRequest:
        stmt = interaction_requests.insert().values(
            interaction_id=entity.interaction_id,
            user_id=entity.user_id,
            correlation_id=entity.correlation_id,
            interaction_type=entity.interaction_type,
            requirement=entity.requirement,
            status=entity.status,
            category=entity.category,
            severity=entity.severity,
            title=entity.title,
            prompt=entity.prompt,
            context_json=entity.context_json,
            allowed_options=entity.allowed_options,
            expected_answer_type=entity.expected_answer_type,
            answer_text=entity.answer_text,
            answer_json=entity.answer_json,
            answered_at=entity.answered_at,
            expires_at=entity.expires_at,
            idempotency_key=entity.idempotency_key,
            created_at=entity.created_at or datetime.now(UTC),
            updated_at=entity.updated_at or datetime.now(UTC),
        )
        await self.session.execute(stmt)
        return entity

    async def get_by_id(self, id: str) -> Optional[InteractionRequest]:
        stmt = select(interaction_requests).where(interaction_requests.c.interaction_id == id)
        result = await self.session.execute(stmt)
        row = result.fetchone()
        return InteractionRequest(**dict(row._mapping)) if row else None

    async def update(self, entity: InteractionRequest) -> InteractionRequest:
        stmt = (
            update(interaction_requests)
            .where(interaction_requests.c.interaction_id == entity.interaction_id)
            .values(
                status=entity.status,
                severity=entity.severity,
                title=entity.title,
                prompt=entity.prompt,
                context_json=entity.context_json,
                allowed_options=entity.allowed_options,
                expected_answer_type=entity.expected_answer_type,
                answer_text=entity.answer_text,
                answer_json=entity.answer_json,
                answered_at=entity.answered_at,
                expires_at=entity.expires_at,
                updated_at=datetime.now(UTC),
            )
        )
        await self.session.execute(stmt)
        return entity

    async def delete(self, id: str) -> Any:
        stmt = delete(interaction_requests).where(interaction_requests.c.interaction_id == id)
        await self.session.execute(stmt)

    async def list(
        self,
        filters: Optional[dict] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[InteractionRequest]:
        stmt = select(interaction_requests)

        if filters:
            conditions = []
            if 'user_id' in filters:
                conditions.append(interaction_requests.c.user_id == filters['user_id'])
            if 'status' in filters:
                conditions.append(interaction_requests.c.status == filters['status'])
            if 'correlation_id' in filters:
                conditions.append(interaction_requests.c.correlation_id == filters['correlation_id'])
            if conditions:
                stmt = stmt.where(and_(*conditions))

        stmt = stmt.order_by(interaction_requests.c.created_at.desc()).limit(limit).offset(offset)
        result = await self.session.execute(stmt)
        return [InteractionRequest(**dict(row._mapping)) for row in result.fetchall()]

    async def count(self, filters: Optional[dict] = None) -> int:
        stmt = select(func.count()).select_from(interaction_requests)

        if filters:
            conditions = []
            if 'user_id' in filters:
                conditions.append(interaction_requests.c.user_id == filters['user_id'])
            if 'status' in filters:
                conditions.append(interaction_requests.c.status == filters['status'])
            if conditions:
                stmt = stmt.where(and_(*conditions))

        result = await self.session.execute(stmt)
        return result.scalar() or 0

    async def get_by_idempotency_key(self, user_id: str, idempotency_key: str) -> Optional[InteractionRequest]:
        stmt = select(interaction_requests).where(
            and_(
                interaction_requests.c.user_id == user_id,
                interaction_requests.c.idempotency_key == idempotency_key,
            )
        )
        result = await self.session.execute(stmt)
        row = result.fetchone()
        return InteractionRequest(**dict(row._mapping)) if row else None
