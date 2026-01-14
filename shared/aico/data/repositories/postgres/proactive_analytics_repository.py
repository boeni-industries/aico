"""
ProactiveAnalyticsRepository - PostgreSQL implementation

Handles CRUD operations for proactive analytics.
"""

from typing import Optional, List
from datetime import datetime, UTC
from sqlalchemy import select, update, delete, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from aico.data.proactive.models import ProactiveAnalytics
from aico.data.tables import proactive_analytics
from aico.data.repositories.base import Repository


class PostgresProactiveAnalyticsRepository(Repository[ProactiveAnalytics]):
    """PostgreSQL implementation of proactive analytics repository."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def create(self, entity: ProactiveAnalytics) -> ProactiveAnalytics:
        """Create a new analytics entry."""
        stmt = proactive_analytics.insert().values(
            id=entity.id,
            user_id=entity.user_id,
            event_type=entity.event_type,
            event_data=entity.event_data,
            confidence_score=entity.confidence_score,
            triggered_action=entity.triggered_action,
            created_at=entity.created_at,
        )
        await self.session.execute(stmt)
        return entity
    
    async def get_by_id(self, entity_id: str) -> Optional[ProactiveAnalytics]:
        """Get analytics entry by ID."""
        stmt = select(proactive_analytics).where(proactive_analytics.c.id == entity_id)
        result = await self.session.execute(stmt)
        row = result.fetchone()
        
        if not row:
            return None
        
        return ProactiveAnalytics(
            id=row.id,
            user_id=row.user_id,
            event_type=row.event_type,
            event_data=row.event_data,
            confidence_score=row.confidence_score,
            triggered_action=row.triggered_action,
            created_at=row.created_at,
        )
    
    async def update(self, entity: ProactiveAnalytics) -> ProactiveAnalytics:
        """Update an existing analytics entry."""
        stmt = (
            update(proactive_analytics)
            .where(proactive_analytics.c.id == entity.id)
            .values(
                event_data=entity.event_data,
                confidence_score=entity.confidence_score,
                triggered_action=entity.triggered_action,
            )
        )
        await self.session.execute(stmt)
        return entity
    
    async def delete(self, entity_id: str) -> bool:
        """Delete an analytics entry."""
        stmt = delete(proactive_analytics).where(proactive_analytics.c.id == entity_id)
        result = await self.session.execute(stmt)
        return result.rowcount > 0
    
    async def list(self, filters: Optional[dict] = None, limit: int = 100, offset: int = 0) -> List[ProactiveAnalytics]:
        """List analytics entries with optional filters."""
        stmt = select(proactive_analytics)
        
        if filters:
            conditions = []
            if 'user_id' in filters:
                conditions.append(proactive_analytics.c.user_id == filters['user_id'])
            if 'event_type' in filters:
                conditions.append(proactive_analytics.c.event_type == filters['event_type'])
            
            if conditions:
                stmt = stmt.where(and_(*conditions))
        
        stmt = stmt.order_by(proactive_analytics.c.created_at.desc()).limit(limit).offset(offset)
        result = await self.session.execute(stmt)
        
        return [
            ProactiveAnalytics(
                id=row.id,
                user_id=row.user_id,
                event_type=row.event_type,
                event_data=row.event_data,
                confidence_score=row.confidence_score,
                triggered_action=row.triggered_action,
                created_at=row.created_at,
            )
            for row in result.fetchall()
        ]
    
    async def count(self, filters: Optional[dict] = None) -> int:
        """Count analytics entries with optional filters."""
        stmt = select(func.count()).select_from(proactive_analytics)
        
        if filters:
            conditions = []
            if 'user_id' in filters:
                conditions.append(proactive_analytics.c.user_id == filters['user_id'])
            
            if conditions:
                stmt = stmt.where(and_(*conditions))
        
        result = await self.session.execute(stmt)
        return result.scalar() or 0
    
    async def get_user_analytics(self, user_id: str, event_type: Optional[str] = None, limit: int = 100) -> List[ProactiveAnalytics]:
        """Get analytics for a specific user."""
        conditions = [proactive_analytics.c.user_id == user_id]
        
        if event_type:
            conditions.append(proactive_analytics.c.event_type == event_type)
        
        stmt = select(proactive_analytics).where(and_(*conditions)).order_by(proactive_analytics.c.created_at.desc()).limit(limit)
        
        result = await self.session.execute(stmt)
        
        return [
            ProactiveAnalytics(
                id=row.id,
                user_id=row.user_id,
                event_type=row.event_type,
                event_data=row.event_data,
                confidence_score=row.confidence_score,
                triggered_action=row.triggered_action,
                created_at=row.created_at,
            )
            for row in result.fetchall()
        ]
