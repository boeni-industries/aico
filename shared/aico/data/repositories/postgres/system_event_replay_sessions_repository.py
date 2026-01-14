"""
SystemEventReplaySessionsRepository - PostgreSQL implementation

Handles CRUD operations for system event replay sessions.
"""

from typing import Optional, List
from datetime import datetime, UTC
from sqlalchemy import select, update, delete, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from aico.ai.system.models import SystemEventReplaySession
from aico.data.tables import system_event_replay_sessions
from aico.data.repositories.base import Repository


class PostgresSystemEventReplaySessionsRepository(Repository[SystemEventReplaySession]):
    """PostgreSQL implementation of system event replay sessions repository."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def create(self, entity: SystemEventReplaySession) -> SystemEventReplaySession:
        """Create a new replay session."""
        stmt = system_event_replay_sessions.insert().values(
            session_id=entity.session_id,
            user_id=entity.user_id,
            replay_name=entity.replay_name,
            start_time=entity.start_time,
            end_time=entity.end_time,
            event_filters=entity.event_filters,
            replay_speed=entity.replay_speed,
            status=entity.status,
            started_at=entity.started_at,
            events_replayed=entity.events_replayed,
            completed_at=entity.completed_at,
            created_at=entity.created_at,
        )
        await self.session.execute(stmt)
        return entity
    
    async def get_by_id(self, entity_id: str) -> Optional[SystemEventReplaySession]:
        """Get replay session by ID."""
        stmt = select(system_event_replay_sessions).where(system_event_replay_sessions.c.session_id == entity_id)
        result = await self.session.execute(stmt)
        row = result.fetchone()
        
        if not row:
            return None
        
        return SystemEventReplaySession(
            session_id=row.session_id,
            user_id=row.user_id,
            replay_name=row.replay_name,
            start_time=row.start_time,
            end_time=row.end_time,
            event_filters=row.event_filters,
            replay_speed=row.replay_speed,
            status=row.status,
            started_at=row.started_at,
            events_replayed=row.events_replayed,
            completed_at=row.completed_at,
            created_at=row.created_at,
        )
    
    async def update(self, entity: SystemEventReplaySession) -> SystemEventReplaySession:
        """Update an existing replay session."""
        stmt = (
            update(system_event_replay_sessions)
            .where(system_event_replay_sessions.c.session_id == entity.session_id)
            .values(
                status=entity.status,
                events_replayed=entity.events_replayed,
                completed_at=entity.completed_at,
            )
        )
        await self.session.execute(stmt)
        return entity
    
    async def delete(self, entity_id: str) -> bool:
        """Delete a replay session."""
        stmt = delete(system_event_replay_sessions).where(system_event_replay_sessions.c.session_id == entity_id)
        result = await self.session.execute(stmt)
        return result.rowcount > 0
    
    async def list(self, filters: Optional[dict] = None, limit: int = 100, offset: int = 0) -> List[SystemEventReplaySession]:
        """List replay sessions with optional filters."""
        stmt = select(system_event_replay_sessions)
        
        if filters:
            conditions = []
            if 'user_id' in filters:
                conditions.append(system_event_replay_sessions.c.user_id == filters['user_id'])
            if 'status' in filters:
                conditions.append(system_event_replay_sessions.c.status == filters['status'])
            
            if conditions:
                stmt = stmt.where(and_(*conditions))
        
        stmt = stmt.order_by(system_event_replay_sessions.c.created_at.desc()).limit(limit).offset(offset)
        result = await self.session.execute(stmt)
        
        return [
            SystemEventReplaySession(
                session_id=row.session_id,
                user_id=row.user_id,
                replay_name=row.replay_name,
                start_time=row.start_time,
                end_time=row.end_time,
                event_filters=row.event_filters,
                replay_speed=row.replay_speed,
                status=row.status,
                started_at=row.started_at,
                events_replayed=row.events_replayed,
                completed_at=row.completed_at,
                created_at=row.created_at,
            )
            for row in result.fetchall()
        ]
    
    async def count(self, filters: Optional[dict] = None) -> int:
        """Count replay sessions with optional filters."""
        stmt = select(func.count()).select_from(system_event_replay_sessions)
        
        if filters:
            conditions = []
            if 'user_id' in filters:
                conditions.append(system_event_replay_sessions.c.user_id == filters['user_id'])
            
            if conditions:
                stmt = stmt.where(and_(*conditions))
        
        result = await self.session.execute(stmt)
        return result.scalar() or 0
    
    async def get_active_sessions(self) -> List[SystemEventReplaySession]:
        """Get all active replay sessions."""
        stmt = select(system_event_replay_sessions).where(
            system_event_replay_sessions.c.status == 'running'
        ).order_by(system_event_replay_sessions.c.created_at.asc())
        
        result = await self.session.execute(stmt)
        
        return [
            SystemEventReplaySession(
                session_id=row.session_id,
                user_id=row.user_id,
                replay_name=row.replay_name,
                start_time=row.start_time,
                end_time=row.end_time,
                event_filters=row.event_filters,
                replay_speed=row.replay_speed,
                status=row.status,
                started_at=row.started_at,
                events_replayed=row.events_replayed,
                completed_at=row.completed_at,
                created_at=row.created_at,
            )
            for row in result.fetchall()
        ]
