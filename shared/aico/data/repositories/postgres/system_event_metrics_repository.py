"""
SystemEventMetricsRepository - PostgreSQL implementation

Handles CRUD operations for system event metrics.
"""

from typing import Optional, List
from datetime import datetime, UTC
from sqlalchemy import select, update, delete, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from aico.ai.system.models import SystemEventMetric
from aico.data.tables import system_event_metrics
from aico.data.repositories.base import Repository


class PostgresSystemEventMetricsRepository(Repository[SystemEventMetric]):
    """PostgreSQL implementation of system event metrics repository."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def create(self, entity: SystemEventMetric) -> SystemEventMetric:
        """Create a new system event metric."""
        stmt = system_event_metrics.insert().values(
            metric_id=entity.metric_id,
            metric_name=entity.metric_name,
            metric_type=entity.metric_type,
            event_type=entity.event_type,
            event_category=entity.event_category,
            time_bucket=entity.time_bucket,
            bucket_start=entity.bucket_start,
            value=entity.value,
            count=entity.count,
            metadata=entity.metadata,
            created_at=entity.created_at,
        )
        await self.session.execute(stmt)
        return entity
    
    async def get_by_id(self, entity_id: str) -> Optional[SystemEventMetric]:
        """Get system event metric by ID."""
        stmt = select(system_event_metrics).where(system_event_metrics.c.metric_id == entity_id)
        result = await self.session.execute(stmt)
        row = result.fetchone()
        
        if not row:
            return None
        
        return SystemEventMetric(
            metric_id=row.metric_id,
            metric_name=row.metric_name,
            metric_type=row.metric_type,
            event_type=row.event_type,
            event_category=row.event_category,
            time_bucket=row.time_bucket,
            bucket_start=row.bucket_start,
            value=row.value,
            count=row.count,
            metadata=row.metadata,
            created_at=row.created_at,
        )
    
    async def update(self, entity: SystemEventMetric) -> SystemEventMetric:
        """Update an existing system event metric."""
        stmt = (
            update(system_event_metrics)
            .where(system_event_metrics.c.metric_id == entity.metric_id)
            .values(
                value=entity.value,
                count=entity.count,
                metadata=entity.metadata,
            )
        )
        await self.session.execute(stmt)
        return entity
    
    async def delete(self, entity_id: str) -> bool:
        """Delete a system event metric."""
        stmt = delete(system_event_metrics).where(system_event_metrics.c.metric_id == entity_id)
        result = await self.session.execute(stmt)
        return result.rowcount > 0
    
    async def list(self, filters: Optional[dict] = None, limit: int = 100, offset: int = 0) -> List[SystemEventMetric]:
        """List system event metrics with optional filters."""
        stmt = select(system_event_metrics)
        
        if filters:
            conditions = []
            if 'metric_name' in filters:
                conditions.append(system_event_metrics.c.metric_name == filters['metric_name'])
            if 'event_type' in filters:
                conditions.append(system_event_metrics.c.event_type == filters['event_type'])
            if 'time_bucket' in filters:
                conditions.append(system_event_metrics.c.time_bucket == filters['time_bucket'])
            
            if conditions:
                stmt = stmt.where(and_(*conditions))
        
        stmt = stmt.order_by(system_event_metrics.c.bucket_start.desc()).limit(limit).offset(offset)
        result = await self.session.execute(stmt)
        
        return [
            SystemEventMetric(
                metric_id=row.metric_id,
                metric_name=row.metric_name,
                metric_type=row.metric_type,
                event_type=row.event_type,
                event_category=row.event_category,
                time_bucket=row.time_bucket,
                bucket_start=row.bucket_start,
                value=row.value,
                count=row.count,
                metadata=row.metadata,
                created_at=row.created_at,
            )
            for row in result.fetchall()
        ]
    
    async def count(self, filters: Optional[dict] = None) -> int:
        """Count system event metrics with optional filters."""
        stmt = select(func.count()).select_from(system_event_metrics)
        
        if filters:
            conditions = []
            if 'metric_name' in filters:
                conditions.append(system_event_metrics.c.metric_name == filters['metric_name'])
            
            if conditions:
                stmt = stmt.where(and_(*conditions))
        
        result = await self.session.execute(stmt)
        return result.scalar() or 0
    
    async def get_metrics_by_bucket(self, time_bucket: str, bucket_start: str) -> List[SystemEventMetric]:
        """Get metrics for a specific time bucket."""
        stmt = select(system_event_metrics).where(
            and_(
                system_event_metrics.c.time_bucket == time_bucket,
                system_event_metrics.c.bucket_start == bucket_start
            )
        ).order_by(system_event_metrics.c.metric_name.asc())
        
        result = await self.session.execute(stmt)
        
        return [
            SystemEventMetric(
                metric_id=row.metric_id,
                metric_name=row.metric_name,
                metric_type=row.metric_type,
                event_type=row.event_type,
                event_category=row.event_category,
                time_bucket=row.time_bucket,
                bucket_start=row.bucket_start,
                value=row.value,
                count=row.count,
                metadata=row.metadata,
                created_at=row.created_at,
            )
            for row in result.fetchall()
        ]
