"""ConversationsRepository - PostgreSQL implementation."""

from __future__ import annotations

from datetime import datetime, UTC
from typing import Optional, List, Any

from sqlalchemy import select, update, delete, and_, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError

from aico.data.conversation.models import Conversation
from aico.data.tables import conversations
from aico.data.repositories.base import Repository


class PostgresConversationsRepository(Repository[Conversation]):
    """PostgreSQL implementation of conversations repository."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, entity: Conversation) -> Conversation:
        stmt = conversations.insert().values(
            tenant_id=entity.tenant_id,
            conversation_id=entity.conversation_id,
            user_id=entity.user_id,
            agent_id=entity.agent_id,
            title=entity.title,
            status=entity.status,
            created_at=entity.created_at or datetime.now(UTC),
            updated_at=entity.updated_at or datetime.now(UTC),
        )
        await self.session.execute(stmt)
        return entity

    async def get_by_id(self, id: str) -> Optional[Conversation]:
        raise RuntimeError("Use get_by_key(tenant_id, conversation_id)")

    async def get_by_key(self, *, tenant_id: str, conversation_id: str) -> Optional[Conversation]:
        stmt = select(conversations).where(
            and_(
                conversations.c.tenant_id == tenant_id,
                conversations.c.conversation_id == conversation_id,
            )
        )
        result = await self.session.execute(stmt)
        row = result.fetchone()
        return Conversation(**dict(row._mapping)) if row else None

    async def touch(
        self,
        *,
        tenant_id: str,
        conversation_id: str,
        user_id: str,
        agent_id: Optional[str] = None,
        title: Optional[str] = None,
        status: str = "active",
    ) -> Conversation:
        """Create conversation if missing, otherwise update updated_at (and optional fields)."""
        now = datetime.now(UTC)
        existing = await self.get_by_key(tenant_id=tenant_id, conversation_id=conversation_id)
        if existing is None:
            entity = Conversation(
                tenant_id=tenant_id,
                conversation_id=conversation_id,
                user_id=user_id,
                agent_id=agent_id,
                title=title,
                status=status,
                created_at=now,
                updated_at=now,
            )
            try:
                await self.create(entity)
                return entity
            except IntegrityError:
                # Concurrent create: fall through to update.
                pass

        values: dict[str, Any] = {
            "updated_at": now,
        }
        if agent_id is not None:
            values["agent_id"] = agent_id
        if title is not None:
            values["title"] = title
        if status is not None:
            values["status"] = status

        stmt = (
            update(conversations)
            .where(
                and_(
                    conversations.c.tenant_id == tenant_id,
                    conversations.c.conversation_id == conversation_id,
                )
            )
            .values(**values)
        )
        await self.session.execute(stmt)
        updated = await self.get_by_key(tenant_id=tenant_id, conversation_id=conversation_id)
        if updated is None:
            raise RuntimeError("Failed to touch conversation")
        return updated

    async def update(self, entity: Conversation) -> Conversation:
        now = datetime.now(UTC)
        stmt = (
            update(conversations)
            .where(
                and_(
                    conversations.c.tenant_id == entity.tenant_id,
                    conversations.c.conversation_id == entity.conversation_id,
                )
            )
            .values(
                user_id=entity.user_id,
                agent_id=entity.agent_id,
                title=entity.title,
                status=entity.status,
                updated_at=now,
            )
        )
        await self.session.execute(stmt)
        entity.updated_at = now
        return entity

    async def delete(self, id: str) -> Any:
        raise RuntimeError("Use delete_by_key(tenant_id, conversation_id)")

    async def delete_by_key(self, *, tenant_id: str, conversation_id: str) -> None:
        stmt = delete(conversations).where(
            and_(
                conversations.c.tenant_id == tenant_id,
                conversations.c.conversation_id == conversation_id,
            )
        )
        await self.session.execute(stmt)

    async def list(self, filters: Optional[dict] = None, limit: int = 100, offset: int = 0) -> List[Conversation]:
        stmt = select(conversations)

        if filters:
            conditions = []
            if "tenant_id" in filters:
                conditions.append(conversations.c.tenant_id == filters["tenant_id"])
            if "user_id" in filters:
                conditions.append(conversations.c.user_id == filters["user_id"])
            if "status" in filters:
                conditions.append(conversations.c.status == filters["status"])
            if conditions:
                stmt = stmt.where(and_(*conditions))

        stmt = stmt.order_by(conversations.c.updated_at.desc()).limit(limit).offset(offset)
        result = await self.session.execute(stmt)
        return [Conversation(**dict(row._mapping)) for row in result.fetchall()]

    async def count(self, filters: Optional[dict] = None) -> int:
        stmt = select(func.count()).select_from(conversations)

        if filters:
            conditions = []
            if "tenant_id" in filters:
                conditions.append(conversations.c.tenant_id == filters["tenant_id"])
            if "user_id" in filters:
                conditions.append(conversations.c.user_id == filters["user_id"])
            if "status" in filters:
                conditions.append(conversations.c.status == filters["status"])
            if conditions:
                stmt = stmt.where(and_(*conditions))

        result = await self.session.execute(stmt)
        return result.scalar() or 0

    async def list_by_user(
        self,
        *,
        tenant_id: str,
        user_id: str,
        limit: int = 50,
        offset: int = 0,
        status: Optional[str] = None,
    ) -> List[Conversation]:
        """List conversations for a specific user with optional status filter."""
        conditions = [
            conversations.c.tenant_id == tenant_id,
            conversations.c.user_id == user_id,
        ]
        
        if status is not None:
            conditions.append(conversations.c.status == status)
        
        stmt = (
            select(conversations)
            .where(and_(*conditions))
            .order_by(conversations.c.updated_at.desc())
            .limit(limit)
            .offset(offset)
        )
        
        result = await self.session.execute(stmt)
        return [Conversation(**dict(row._mapping)) for row in result.fetchall()]

    async def count_by_user(
        self,
        *,
        tenant_id: str,
        user_id: str,
        status: Optional[str] = None,
    ) -> int:
        """Count conversations for a specific user with optional status filter."""
        conditions = [
            conversations.c.tenant_id == tenant_id,
            conversations.c.user_id == user_id,
        ]
        
        if status is not None:
            conditions.append(conversations.c.status == status)
        
        stmt = select(func.count()).select_from(conversations).where(and_(*conditions))
        
        result = await self.session.execute(stmt)
        return result.scalar() or 0
