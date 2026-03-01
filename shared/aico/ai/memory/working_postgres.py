from __future__ import annotations

from datetime import datetime, timedelta, UTC
from typing import Any, Callable, Dict, List, Optional

from sqlalchemy import and_, delete, func, insert, or_, select, update

from aico.core.config import ConfigurationManager
from aico.core.logging import get_logger
from aico.data.tables import working_memory_messages

logger = get_logger("shared.ai.memory.working_postgres")


class PostgresWorkingMemoryStore:
    def __init__(
        self,
        config_manager: ConfigurationManager,
        *,
        uow_factory: Optional[Callable[[], Any]] = None,
    ):
        self.config = config_manager
        if uow_factory is None:
            raise RuntimeError("PostgresWorkingMemoryStore requires uow_factory")
        self._uow_factory = uow_factory
        self._initialized = False
        self._ttl_seconds = self.config.get("memory.working.ttl_seconds", 2592000)

    async def initialize(self) -> None:
        self._initialized = True

    async def store_message(self, conversation_id: str, message: Dict[str, Any]) -> bool:
        if not self._initialized:
            await self.initialize()

        now = datetime.now(UTC)
        expires_at = None if self._ttl_seconds is None else (now + timedelta(seconds=self._ttl_seconds))

        payload = dict(message)
        payload.setdefault("conversation_id", conversation_id)

        stmt = insert(working_memory_messages).values(
            conversation_id=conversation_id,
            user_id=message.get("user_id"),
            message_id=message.get("message_id"),
            role=message.get("role"),
            content=message.get("content"),
            language=message.get("language"),
            message_type=message.get("message_type"),
            payload_json=payload,
            stored_at=now,
            expires_at=expires_at,
            last_accessed_at=now,
            access_count=0,
        )

        try:
            async with self._uow_factory() as uow:  # type: ignore[misc]
                await uow._session.execute(stmt)
                await uow.commit()
            return True
        except Exception as e:
            logger.error(f"Failed to store working memory message: {e}")
            return False

    async def retrieve_conversation_history(self, conversation_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        if not self._initialized:
            await self.initialize()

        now = datetime.now(UTC)
        stmt = (
            select(working_memory_messages)
            .where(
                and_(
                    working_memory_messages.c.conversation_id == conversation_id,
                    or_(working_memory_messages.c.expires_at.is_(None), working_memory_messages.c.expires_at > now),
                )
            )
            .order_by(working_memory_messages.c.stored_at.desc())
            .limit(limit)
        )

        async with self._uow_factory() as uow:  # type: ignore[misc]
            result = await uow._session.execute(stmt)
            rows = result.fetchall()

            ids = [r._mapping["id"] for r in rows]
            if ids:
                await uow._session.execute(
                    update(working_memory_messages)
                    .where(working_memory_messages.c.id.in_(ids))
                    .values(
                        last_accessed_at=now,
                        access_count=working_memory_messages.c.access_count + 1,
                    )
                )
                await uow.commit()

        return [dict(r._mapping.get("payload_json") or {}) for r in rows]

    async def retrieve_user_history(self, user_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        if not self._initialized:
            await self.initialize()

        now = datetime.now(UTC)
        stmt = (
            select(working_memory_messages)
            .where(
                and_(
                    working_memory_messages.c.user_id == user_id,
                    or_(working_memory_messages.c.expires_at.is_(None), working_memory_messages.c.expires_at > now),
                )
            )
            .order_by(working_memory_messages.c.stored_at.desc())
            .limit(limit)
        )

        async with self._uow_factory() as uow:  # type: ignore[misc]
            result = await uow._session.execute(stmt)
            rows = result.fetchall()

            ids = [r._mapping["id"] for r in rows]
            if ids:
                await uow._session.execute(
                    update(working_memory_messages)
                    .where(working_memory_messages.c.id.in_(ids))
                    .values(
                        last_accessed_at=now,
                        access_count=working_memory_messages.c.access_count + 1,
                    )
                )
                await uow.commit()

        return [dict(r._mapping.get("payload_json") or {}) for r in rows]

    async def cleanup_expired(self) -> int:
        if not self._initialized:
            await self.initialize()

        now = datetime.now(UTC)
        stmt = delete(working_memory_messages).where(
            and_(working_memory_messages.c.expires_at.is_not(None), working_memory_messages.c.expires_at <= now)
        )

        async with self._uow_factory() as uow:  # type: ignore[misc]
            result = await uow._session.execute(stmt)
            await uow.commit()

        return int(getattr(result, "rowcount", 0) or 0)

    async def get_stats(self) -> Dict[str, Any]:
        if not self._initialized:
            await self.initialize()

        now = datetime.now(UTC)
        async with self._uow_factory() as uow:  # type: ignore[misc]
            active_stmt = select(func.count()).select_from(working_memory_messages).where(
                or_(working_memory_messages.c.expires_at.is_(None), working_memory_messages.c.expires_at > now)
            )
            expired_stmt = select(func.count()).select_from(working_memory_messages).where(
                and_(working_memory_messages.c.expires_at.is_not(None), working_memory_messages.c.expires_at <= now)
            )

            active = (await uow._session.execute(active_stmt)).scalar() or 0
            expired = (await uow._session.execute(expired_stmt)).scalar() or 0

            # Get recent activity (last 10 messages)
            recent_stmt = (
                select(working_memory_messages)
                .where(
                    or_(working_memory_messages.c.expires_at.is_(None), working_memory_messages.c.expires_at > now)
                )
                .order_by(working_memory_messages.c.stored_at.desc())
                .limit(10)
            )
            recent_result = await uow._session.execute(recent_stmt)
            recent_rows = recent_result.fetchall()

        capacity = max(10000, int(active) * 2)
        utilization_percent = (active / capacity) * 100 if capacity else 0.0

        # Build recent_activity list
        recent_activity = []
        for row in recent_rows:
            mapping = row._mapping
            recent_activity.append({
                "id": f"{mapping['conversation_id']}:{mapping['stored_at'].isoformat()}",
                "timestamp": mapping["stored_at"].isoformat(),
                "action": "stored",
                "conversation_id": mapping["conversation_id"],
                "role": mapping["role"],
                "preview": mapping["content"] or "",
            })

        return {
            "active_items": int(active),
            "expired_items": int(expired),
            "capacity": capacity,
            "utilization_percent": round(utilization_percent, 2),
            "ttl_utilization_percent": round(utilization_percent, 2),  # Simplified for now
            "eviction_rate_per_min": round(expired / 60.0, 2) if expired > 0 else 0.0,
            "recent_activity": recent_activity,
        }
