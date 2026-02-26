"""ConversationMessagesRepository - PostgreSQL implementation."""

from __future__ import annotations

from datetime import datetime, UTC
from typing import Optional, List, Any

from sqlalchemy import select, update, delete, and_, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError

from aico.data.conversation.models import ConversationMessage
from aico.data.tables import conversation_messages
from aico.data.repositories.base import Repository


class PostgresConversationMessagesRepository(Repository[ConversationMessage]):
    """PostgreSQL implementation of conversation messages repository."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, entity: ConversationMessage) -> ConversationMessage:
        stmt = conversation_messages.insert().values(
            message_id=entity.message_id,
            tenant_id=entity.tenant_id,
            conversation_id=entity.conversation_id,
            user_id=entity.user_id,
            agent_id=entity.agent_id,
            actor_type=entity.actor_type,
            actor_id=entity.actor_id,
            message_type=entity.message_type,
            content=entity.content,
            metadata_json=entity.metadata_json,
            correlation_id=entity.correlation_id,
            request_id=entity.request_id,
            created_at=entity.created_at or datetime.now(UTC),
        )
        await self.session.execute(stmt)
        return entity

    async def create_idempotent(self, entity: ConversationMessage) -> ConversationMessage:
        """Insert a message; if the (tenant_id,user_id,request_id,message_type) already exists, do nothing."""
        try:
            await self.create(entity)
            return entity
        except IntegrityError:
            existing = await self.get_by_request(
                tenant_id=entity.tenant_id,
                user_id=entity.user_id,
                request_id=entity.request_id,
                message_type=entity.message_type,
            )
            if existing is None:
                raise
            return existing

    async def get_by_id(self, id: str) -> Optional[ConversationMessage]:
        stmt = select(conversation_messages).where(conversation_messages.c.message_id == id)
        result = await self.session.execute(stmt)
        row = result.fetchone()
        return ConversationMessage(**dict(row._mapping)) if row else None

    async def get_by_request(
        self,
        *,
        tenant_id: str,
        user_id: str,
        request_id: str,
        message_type: str,
    ) -> Optional[ConversationMessage]:
        stmt = select(conversation_messages).where(
            and_(
                conversation_messages.c.tenant_id == tenant_id,
                conversation_messages.c.user_id == user_id,
                conversation_messages.c.request_id == request_id,
                conversation_messages.c.message_type == message_type,
            )
        )
        result = await self.session.execute(stmt)
        row = result.fetchone()
        return ConversationMessage(**dict(row._mapping)) if row else None

    async def update(self, entity: ConversationMessage) -> ConversationMessage:
        stmt = (
            update(conversation_messages)
            .where(conversation_messages.c.message_id == entity.message_id)
            .values(
                content=entity.content,
                metadata_json=entity.metadata_json,
                correlation_id=entity.correlation_id,
            )
        )
        await self.session.execute(stmt)
        return entity

    async def delete(self, id: str) -> Any:
        stmt = delete(conversation_messages).where(conversation_messages.c.message_id == id)
        await self.session.execute(stmt)

    async def list(self, filters: Optional[dict] = None, limit: int = 100, offset: int = 0) -> List[ConversationMessage]:
        stmt = select(conversation_messages)

        if filters:
            conditions = []
            if "tenant_id" in filters:
                conditions.append(conversation_messages.c.tenant_id == filters["tenant_id"])
            if "user_id" in filters:
                conditions.append(conversation_messages.c.user_id == filters["user_id"])
            if "conversation_id" in filters:
                conditions.append(conversation_messages.c.conversation_id == filters["conversation_id"])
            if "created_after" in filters and filters["created_after"] is not None:
                conditions.append(conversation_messages.c.created_at >= filters["created_after"])
            if "created_before" in filters and filters["created_before"] is not None:
                conditions.append(conversation_messages.c.created_at <= filters["created_before"])
            if conditions:
                stmt = stmt.where(and_(*conditions))

        stmt = stmt.order_by(conversation_messages.c.created_at.desc()).limit(limit).offset(offset)
        result = await self.session.execute(stmt)
        return [ConversationMessage(**dict(row._mapping)) for row in result.fetchall()]

    async def count(self, filters: Optional[dict] = None) -> int:
        stmt = select(func.count()).select_from(conversation_messages)

        if filters:
            conditions = []
            if "tenant_id" in filters:
                conditions.append(conversation_messages.c.tenant_id == filters["tenant_id"])
            if "user_id" in filters:
                conditions.append(conversation_messages.c.user_id == filters["user_id"])
            if "conversation_id" in filters:
                conditions.append(conversation_messages.c.conversation_id == filters["conversation_id"])
            if conditions:
                stmt = stmt.where(and_(*conditions))

        result = await self.session.execute(stmt)
        return result.scalar() or 0

    async def list_since(
        self,
        *,
        tenant_id: str,
        user_id: str,
        conversation_id: Optional[str] = None,
        since: Optional[datetime] = None,
        limit: int = 100,
    ) -> List[ConversationMessage]:
        stmt = select(conversation_messages).where(
            and_(
                conversation_messages.c.tenant_id == tenant_id,
                conversation_messages.c.user_id == user_id,
            )
        )
        if conversation_id:
            stmt = stmt.where(conversation_messages.c.conversation_id == conversation_id)
        if since is not None:
            stmt = stmt.where(conversation_messages.c.created_at > since)

        stmt = stmt.order_by(conversation_messages.c.created_at.asc()).limit(limit)
        result = await self.session.execute(stmt)
        return [ConversationMessage(**dict(row._mapping)) for row in result.fetchall()]
