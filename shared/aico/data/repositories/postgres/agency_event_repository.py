"""
AgencyEventRepository - PostgreSQL implementation

Handles CRUD operations for agency events.
"""

from typing import Optional, List
from datetime import datetime, UTC
from sqlalchemy import select, update, delete, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from aico.data.agency.models import AgencyEvent
from aico.data.tables import agency_events
from aico.data.repositories.base import Repository

import json

class PostgresAgencyEventRepository(Repository[AgencyEvent]):
    """PostgreSQL implementation of agency event repository."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def create(self, entity: AgencyEvent) -> AgencyEvent:
        """Create a new agency event."""
        stmt = agency_events.insert().values(
            user_id=entity.user_id,
            goal_id=entity.goal_id,
            plan_id=entity.plan_id,
            event_type=entity.event_type,
            source=entity.source,
            payload_json=json.dumps(entity.payload) if entity.payload else None,
            created_at=entity.created_at or datetime.now(UTC),
        ).returning(agency_events.c.id)
        
        result = await self.session.execute(stmt)
        row = result.fetchone()
        entity.id = row.id
        return entity
    
    async def get_by_id(self, entity_id: int) -> Optional[AgencyEvent]:
        """Get agency event by ID."""
        stmt = select(agency_events).where(agency_events.c.id == entity_id)
        result = await self.session.execute(stmt)
        row = result.fetchone()
        
        if not row:
            return None
        
        return AgencyEvent(
            id=row.id,
            user_id=row.user_id,
            goal_id=row.goal_id,
            plan_id=row.plan_id,
            event_type=row.event_type,
            source=row.source,
            payload=json.loads(row.payload_json) if row.payload_json else {},
            created_at=row.created_at,
        )
    
    async def update(self, entity: AgencyEvent) -> AgencyEvent:
        """Update an existing agency event."""
        stmt = (
            update(agency_events)
            .where(agency_events.c.id == entity.id)
            .values(
                payload_json=json.dumps(entity.payload) if entity.payload else None,
            )
        )
        await self.session.execute(stmt)
        return entity
    
    async def delete(self, entity_id: int) -> bool:
        """Delete an agency event."""
        stmt = delete(agency_events).where(agency_events.c.id == entity_id)
        result = await self.session.execute(stmt)
        return result.rowcount > 0
    
    async def list(self, filters: Optional[dict] = None, limit: int = 100, offset: int = 0) -> List[AgencyEvent]:
        """List agency events with optional filters."""
        stmt = select(agency_events)
        
        if filters:
            conditions = []
            if 'user_id' in filters:
                conditions.append(agency_events.c.user_id == filters['user_id'])
            if 'goal_id' in filters:
                conditions.append(agency_events.c.goal_id == filters['goal_id'])
            if 'plan_id' in filters:
                conditions.append(agency_events.c.plan_id == filters['plan_id'])
            if 'event_type' in filters:
                conditions.append(agency_events.c.event_type == filters['event_type'])
            if 'source' in filters:
                conditions.append(agency_events.c.source == filters['source'])
            
            if conditions:
                stmt = stmt.where(and_(*conditions))
        
        stmt = stmt.order_by(agency_events.c.created_at.desc()).limit(limit).offset(offset)
        result = await self.session.execute(stmt)
        
        return [
            AgencyEvent(
                id=row.id,
                user_id=row.user_id,
                goal_id=row.goal_id,
                plan_id=row.plan_id,
                event_type=row.event_type,
                source=row.source,
                payload_json=row.payload_json,
                created_at=row.created_at,
            )
            for row in result.fetchall()
        ]
    
    async def count(self, filters: Optional[dict] = None) -> int:
        """Count agency events with optional filters."""
        stmt = select(func.count()).select_from(agency_events)
        
        if filters:
            conditions = []
            if 'user_id' in filters:
                conditions.append(agency_events.c.user_id == filters['user_id'])
            if 'event_type' in filters:
                conditions.append(agency_events.c.event_type == filters['event_type'])
            
            if conditions:
                stmt = stmt.where(and_(*conditions))
        
        result = await self.session.execute(stmt)
        return result.scalar() or 0
    
    async def get_events_for_goal(self, goal_id: str, limit: int = 50) -> List[AgencyEvent]:
        """Get all events for a specific goal."""
        stmt = select(agency_events).where(
            agency_events.c.goal_id == goal_id
        ).order_by(agency_events.c.created_at.desc()).limit(limit)
        
        result = await self.session.execute(stmt)
        
        return [
            AgencyEvent(
                id=row.id,
                user_id=row.user_id,
                goal_id=row.goal_id,
                plan_id=row.plan_id,
                event_type=row.event_type,
                source=row.source,
                payload_json=row.payload_json,
                created_at=row.created_at,
            )
            for row in result.fetchall()
        ]
    
    async def get_events_by_type(self, user_id: str, event_type: str, limit: int = 50) -> List[AgencyEvent]:
        """Get events by type for a user."""
        stmt = select(agency_events).where(
            and_(
                agency_events.c.user_id == user_id,
                agency_events.c.event_type == event_type
            )
        ).order_by(agency_events.c.created_at.desc()).limit(limit)
        
        result = await self.session.execute(stmt)
        
        return [
            AgencyEvent(
                id=row.id,
                user_id=row.user_id,
                goal_id=row.goal_id,
                plan_id=row.plan_id,
                event_type=row.event_type,
                source=row.source,
                payload_json=row.payload_json,
                created_at=row.created_at,
            )
            for row in result.fetchall()
        ]
