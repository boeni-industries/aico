"""
ProactiveReminderClustersRepository - PostgreSQL implementation

Handles CRUD operations for proactive reminder clusters.
"""

from typing import Optional, List
from datetime import datetime, UTC
from sqlalchemy import select, update, delete, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from aico.data.proactive.models import ProactiveReminderCluster
from aico.data.tables import proactive_reminder_clusters
from aico.data.repositories.base import Repository


class PostgresProactiveReminderClustersRepository(Repository[ProactiveReminderCluster]):
    """PostgreSQL implementation of proactive reminder clusters repository."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def create(self, entity: ProactiveReminderCluster) -> ProactiveReminderCluster:
        """Create a new reminder cluster."""
        stmt = proactive_reminder_clusters.insert().values(
            cluster_id=entity.cluster_id,
            user_id=entity.user_id,
            cluster_name=entity.cluster_name,
            reminder_ids=entity.reminder_ids,
            pattern_description=entity.pattern_description,
            confidence_score=entity.confidence_score,
            created_at=entity.created_at,
        )
        await self.session.execute(stmt)
        return entity
    
    async def get_by_id(self, entity_id: str) -> Optional[ProactiveReminderCluster]:
        """Get reminder cluster by ID."""
        stmt = select(proactive_reminder_clusters).where(proactive_reminder_clusters.c.cluster_id == entity_id)
        result = await self.session.execute(stmt)
        row = result.fetchone()
        
        if not row:
            return None
        
        return ProactiveReminderCluster(
            cluster_id=row.cluster_id,
            user_id=row.user_id,
            cluster_name=row.cluster_name,
            reminder_ids=row.reminder_ids,
            pattern_description=row.pattern_description,
            confidence_score=row.confidence_score,
            created_at=row.created_at,
        )
    
    async def update(self, entity: ProactiveReminderCluster) -> ProactiveReminderCluster:
        """Update an existing reminder cluster."""
        stmt = (
            update(proactive_reminder_clusters)
            .where(proactive_reminder_clusters.c.cluster_id == entity.cluster_id)
            .values(
                cluster_name=entity.cluster_name,
                reminder_ids=entity.reminder_ids,
                pattern_description=entity.pattern_description,
                confidence_score=entity.confidence_score,
            )
        )
        await self.session.execute(stmt)
        return entity
    
    async def delete(self, entity_id: str) -> bool:
        """Delete a reminder cluster."""
        stmt = delete(proactive_reminder_clusters).where(proactive_reminder_clusters.c.cluster_id == entity_id)
        result = await self.session.execute(stmt)
        return result.rowcount > 0
    
    async def list(self, filters: Optional[dict] = None, limit: int = 100, offset: int = 0) -> List[ProactiveReminderCluster]:
        """List reminder clusters with optional filters."""
        stmt = select(proactive_reminder_clusters)
        
        if filters:
            conditions = []
            if 'user_id' in filters:
                conditions.append(proactive_reminder_clusters.c.user_id == filters['user_id'])
            
            if conditions:
                stmt = stmt.where(and_(*conditions))
        
        stmt = stmt.order_by(proactive_reminder_clusters.c.created_at.desc()).limit(limit).offset(offset)
        result = await self.session.execute(stmt)
        
        return [
            ProactiveReminderCluster(
                cluster_id=row.cluster_id,
                user_id=row.user_id,
                cluster_name=row.cluster_name,
                reminder_ids=row.reminder_ids,
                pattern_description=row.pattern_description,
                confidence_score=row.confidence_score,
                created_at=row.created_at,
            )
            for row in result.fetchall()
        ]
    
    async def count(self, filters: Optional[dict] = None) -> int:
        """Count reminder clusters with optional filters."""
        stmt = select(func.count()).select_from(proactive_reminder_clusters)
        
        if filters:
            conditions = []
            if 'user_id' in filters:
                conditions.append(proactive_reminder_clusters.c.user_id == filters['user_id'])
            
            if conditions:
                stmt = stmt.where(and_(*conditions))
        
        result = await self.session.execute(stmt)
        return result.scalar() or 0
    
    async def get_user_clusters(self, user_id: str) -> List[ProactiveReminderCluster]:
        """Get all reminder clusters for a specific user."""
        stmt = select(proactive_reminder_clusters).where(
            proactive_reminder_clusters.c.user_id == user_id
        ).order_by(proactive_reminder_clusters.c.created_at.desc())
        
        result = await self.session.execute(stmt)
        
        return [
            ProactiveReminderCluster(
                cluster_id=row.cluster_id,
                user_id=row.user_id,
                cluster_name=row.cluster_name,
                reminder_ids=row.reminder_ids,
                pattern_description=row.pattern_description,
                confidence_score=row.confidence_score,
                created_at=row.created_at,
            )
            for row in result.fetchall()
        ]
