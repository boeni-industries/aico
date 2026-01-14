"""
SystemEventRepository - PostgreSQL implementation

Handles CRUD operations for system events.
"""

from typing import Optional, List
from datetime import datetime, UTC
from sqlalchemy import select, update, delete, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from aico.data.system.models import SystemEvent
from aico.data.tables import system_events
from aico.data.repositories.base import Repository


class PostgresSystemEventRepository(Repository[SystemEvent]):
    """PostgreSQL implementation of system event repository."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def create(self, entity: SystemEvent) -> SystemEvent:
        """Create a new system event."""
        stmt = system_events.insert().values(
            timestamp=entity.timestamp,
            topic=entity.topic,
            source=entity.source,
            message_type=entity.message_type,
            message_id=entity.message_id,
            priority=entity.priority,
            correlation_id=entity.correlation_id,
            payload=entity.payload,
            metadata=entity.metadata,
            created_at=entity.created_at or datetime.now(UTC),
        ).returning(system_events.c.id)
        
        result = await self.session.execute(stmt)
        row = result.fetchone()
        entity.id = row.id
        return entity
    
    async def get_by_id(self, entity_id: int) -> Optional[SystemEvent]:
        """Get system event by ID."""
        stmt = select(system_events).where(system_events.c.id == entity_id)
        result = await self.session.execute(stmt)
        row = result.fetchone()
        
        if not row:
            return None
        
        return SystemEvent(
            id=row.id,
            timestamp=row.timestamp,
            topic=row.topic,
            source=row.source,
            message_type=row.message_type,
            message_id=row.message_id,
            priority=row.priority,
            correlation_id=row.correlation_id,
            payload=row.payload,
            metadata=row.metadata,
            created_at=row.created_at,
        )
    
    async def update(self, entity: SystemEvent) -> SystemEvent:
        """Update an existing system event."""
        stmt = (
            update(system_events)
            .where(system_events.c.id == entity.id)
            .values(
                metadata=entity.metadata,
                priority=entity.priority,
            )
        )
        await self.session.execute(stmt)
        return entity
    
    async def delete(self, entity_id: int) -> bool:
        """Delete a system event."""
        stmt = delete(system_events).where(system_events.c.id == entity_id)
        result = await self.session.execute(stmt)
        return result.rowcount > 0
    
    async def list(self, filters: Optional[dict] = None, limit: int = 100, offset: int = 0) -> List[SystemEvent]:
        """List system events with optional filters."""
        stmt = select(system_events)
        
        if filters:
            conditions = []
            if 'topic' in filters:
                conditions.append(system_events.c.topic == filters['topic'])
            if 'source' in filters:
                conditions.append(system_events.c.source == filters['source'])
            if 'message_type' in filters:
                conditions.append(system_events.c.message_type == filters['message_type'])
            if 'correlation_id' in filters:
                conditions.append(system_events.c.correlation_id == filters['correlation_id'])
            
            if conditions:
                stmt = stmt.where(and_(*conditions))
        
        stmt = stmt.order_by(system_events.c.created_at.desc()).limit(limit).offset(offset)
        result = await self.session.execute(stmt)
        
        return [
            SystemEvent(
                id=row.id,
                timestamp=row.timestamp,
                topic=row.topic,
                source=row.source,
                message_type=row.message_type,
                message_id=row.message_id,
                priority=row.priority,
                correlation_id=row.correlation_id,
                payload=row.payload,
                metadata=row.metadata,
                created_at=row.created_at,
            )
            for row in result.fetchall()
        ]
    
    async def count(self, filters: Optional[dict] = None) -> int:
        """Count system events with optional filters."""
        stmt = select(func.count()).select_from(system_events)
        
        if filters:
            conditions = []
            if 'topic' in filters:
                conditions.append(system_events.c.topic == filters['topic'])
            if 'source' in filters:
                conditions.append(system_events.c.source == filters['source'])
            
            if conditions:
                stmt = stmt.where(and_(*conditions))
        
        result = await self.session.execute(stmt)
        return result.scalar() or 0
    
    async def get_by_message_id(self, message_id: str) -> Optional[SystemEvent]:
        """Get event by message ID."""
        stmt = select(system_events).where(system_events.c.message_id == message_id)
        result = await self.session.execute(stmt)
        row = result.fetchone()
        
        if not row:
            return None
        
        return SystemEvent(
            id=row.id,
            timestamp=row.timestamp,
            topic=row.topic,
            source=row.source,
            message_type=row.message_type,
            message_id=row.message_id,
            priority=row.priority,
            correlation_id=row.correlation_id,
            payload=row.payload,
            metadata=row.metadata,
            created_at=row.created_at,
        )
    
    async def get_by_correlation_id(self, correlation_id: str, limit: int = 50) -> List[SystemEvent]:
        """Get all events with the same correlation ID."""
        stmt = select(system_events).where(
            system_events.c.correlation_id == correlation_id
        ).order_by(system_events.c.created_at.asc()).limit(limit)
        
        result = await self.session.execute(stmt)
        
        return [
            SystemEvent(
                id=row.id,
                timestamp=row.timestamp,
                topic=row.topic,
                source=row.source,
                message_type=row.message_type,
                message_id=row.message_id,
                priority=row.priority,
                correlation_id=row.correlation_id,
                payload=row.payload,
                metadata=row.metadata,
                created_at=row.created_at,
            )
            for row in result.fetchall()
        ]
    
    async def get_by_topic(self, topic: str, limit: int = 100) -> List[SystemEvent]:
        """Get events by topic."""
        stmt = select(system_events).where(
            system_events.c.topic == topic
        ).order_by(system_events.c.created_at.desc()).limit(limit)
        
        result = await self.session.execute(stmt)
        
        return [
            SystemEvent(
                id=row.id,
                timestamp=row.timestamp,
                topic=row.topic,
                source=row.source,
                message_type=row.message_type,
                message_id=row.message_id,
                priority=row.priority,
                correlation_id=row.correlation_id,
                payload=row.payload,
                metadata=row.metadata,
                created_at=row.created_at,
            )
            for row in result.fetchall()
        ]
