"""
AgencyEventsLogRepository - PostgreSQL implementation

Handles CRUD operations for agency events log.
"""

from typing import Optional, List
from datetime import datetime, UTC
from sqlalchemy import select, update, delete, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from aico.ai.agency.models import AgencyEventLog
from aico.data.tables import agency_events_log
from aico.data.repositories.base import Repository


class PostgresAgencyEventsLogRepository(Repository[AgencyEventLog]):
    """PostgreSQL implementation of agency events log repository."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def create(self, entity: AgencyEventLog) -> AgencyEventLog:
        """Create a new agency event log entry."""
        stmt = agency_events_log.insert().values(
            event_id=entity.event_id,
            user_id=entity.user_id,
            event_type=entity.event_type,
            event_category=entity.event_category,
            source_component=entity.source_component,
            entity_type=entity.entity_type,
            entity_id=entity.entity_id,
            event_data=entity.event_data,
            workflow_trace_id=entity.workflow_trace_id,
            parent_event_id=entity.parent_event_id,
            severity=entity.severity,
            created_at=entity.created_at,
        )
        await self.session.execute(stmt)
        return entity
    
    async def get_by_id(self, entity_id: str) -> Optional[AgencyEventLog]:
        """Get agency event log by ID."""
        stmt = select(agency_events_log).where(agency_events_log.c.event_id == entity_id)
        result = await self.session.execute(stmt)
        row = result.fetchone()
        
        if not row:
            return None
        
        return AgencyEventLog(
            event_id=row.event_id,
            user_id=row.user_id,
            event_type=row.event_type,
            event_category=row.event_category,
            source_component=row.source_component,
            entity_type=row.entity_type,
            entity_id=row.entity_id,
            event_data=row.event_data,
            workflow_trace_id=row.workflow_trace_id,
            parent_event_id=row.parent_event_id,
            severity=row.severity,
            created_at=row.created_at,
        )
    
    async def update(self, entity: AgencyEventLog) -> AgencyEventLog:
        """Update an existing agency event log entry."""
        stmt = (
            update(agency_events_log)
            .where(agency_events_log.c.event_id == entity.event_id)
            .values(
                event_data=entity.event_data,
                severity=entity.severity,
            )
        )
        await self.session.execute(stmt)
        return entity
    
    async def delete(self, entity_id: str) -> bool:
        """Delete an agency event log entry."""
        stmt = delete(agency_events_log).where(agency_events_log.c.event_id == entity_id)
        result = await self.session.execute(stmt)
        return result.rowcount > 0
    
    async def list(self, filters: Optional[dict] = None, limit: int = 100, offset: int = 0) -> List[AgencyEventLog]:
        """List agency event logs with optional filters."""
        stmt = select(agency_events_log)
        
        if filters:
            conditions = []
            if 'user_id' in filters:
                conditions.append(agency_events_log.c.user_id == filters['user_id'])
            if 'event_type' in filters:
                conditions.append(agency_events_log.c.event_type == filters['event_type'])
            if 'event_category' in filters:
                conditions.append(agency_events_log.c.event_category == filters['event_category'])
            if 'entity_type' in filters:
                conditions.append(agency_events_log.c.entity_type == filters['entity_type'])
            if 'entity_id' in filters:
                conditions.append(agency_events_log.c.entity_id == filters['entity_id'])
            if 'severity' in filters:
                conditions.append(agency_events_log.c.severity == filters['severity'])
            
            if conditions:
                stmt = stmt.where(and_(*conditions))
        
        stmt = stmt.order_by(agency_events_log.c.created_at.desc()).limit(limit).offset(offset)
        result = await self.session.execute(stmt)
        
        return [
            AgencyEventLog(
                event_id=row.event_id,
                user_id=row.user_id,
                event_type=row.event_type,
                event_category=row.event_category,
                source_component=row.source_component,
                entity_type=row.entity_type,
                entity_id=row.entity_id,
                event_data=row.event_data,
                workflow_trace_id=row.workflow_trace_id,
                parent_event_id=row.parent_event_id,
                severity=row.severity,
                created_at=row.created_at,
            )
            for row in result.fetchall()
        ]
    
    async def count(self, filters: Optional[dict] = None) -> int:
        """Count agency event logs with optional filters."""
        stmt = select(func.count()).select_from(agency_events_log)
        
        if filters:
            conditions = []
            if 'user_id' in filters:
                conditions.append(agency_events_log.c.user_id == filters['user_id'])
            if 'event_category' in filters:
                conditions.append(agency_events_log.c.event_category == filters['event_category'])
            
            if conditions:
                stmt = stmt.where(and_(*conditions))
        
        result = await self.session.execute(stmt)
        return result.scalar() or 0
    
    async def get_by_workflow_trace(self, workflow_trace_id: str, limit: int = 100) -> List[AgencyEventLog]:
        """Get all events in a workflow trace."""
        stmt = select(agency_events_log).where(
            agency_events_log.c.workflow_trace_id == workflow_trace_id
        ).order_by(agency_events_log.c.created_at.asc()).limit(limit)
        
        result = await self.session.execute(stmt)
        
        return [
            AgencyEventLog(
                event_id=row.event_id,
                user_id=row.user_id,
                event_type=row.event_type,
                event_category=row.event_category,
                source_component=row.source_component,
                entity_type=row.entity_type,
                entity_id=row.entity_id,
                event_data=row.event_data,
                workflow_trace_id=row.workflow_trace_id,
                parent_event_id=row.parent_event_id,
                severity=row.severity,
                created_at=row.created_at,
            )
            for row in result.fetchall()
        ]
    
    async def get_by_entity(self, entity_type: str, entity_id: str, limit: int = 50) -> List[AgencyEventLog]:
        """Get all events for a specific entity."""
        stmt = select(agency_events_log).where(
            and_(
                agency_events_log.c.entity_type == entity_type,
                agency_events_log.c.entity_id == entity_id
            )
        ).order_by(agency_events_log.c.created_at.desc()).limit(limit)
        
        result = await self.session.execute(stmt)
        
        return [
            AgencyEventLog(
                event_id=row.event_id,
                user_id=row.user_id,
                event_type=row.event_type,
                event_category=row.event_category,
                source_component=row.source_component,
                entity_type=row.entity_type,
                entity_id=row.entity_id,
                event_data=row.event_data,
                workflow_trace_id=row.workflow_trace_id,
                parent_event_id=row.parent_event_id,
                severity=row.severity,
                created_at=row.created_at,
            )
            for row in result.fetchall()
        ]
    
    async def get_by_category(self, user_id: str, category: str, limit: int = 50) -> List[AgencyEventLog]:
        """Get events by category for a user."""
        stmt = select(agency_events_log).where(
            and_(
                agency_events_log.c.user_id == user_id,
                agency_events_log.c.event_category == category
            )
        ).order_by(agency_events_log.c.created_at.desc()).limit(limit)
        
        result = await self.session.execute(stmt)
        
        return [
            AgencyEventLog(
                event_id=row.event_id,
                user_id=row.user_id,
                event_type=row.event_type,
                event_category=row.event_category,
                source_component=row.source_component,
                entity_type=row.entity_type,
                entity_id=row.entity_id,
                event_data=row.event_data,
                workflow_trace_id=row.workflow_trace_id,
                parent_event_id=row.parent_event_id,
                severity=row.severity,
                created_at=row.created_at,
            )
            for row in result.fetchall()
        ]
