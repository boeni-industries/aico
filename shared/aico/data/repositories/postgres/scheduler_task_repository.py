"""
SchedulerTaskRepository - PostgreSQL implementation

Handles CRUD operations for scheduler tasks.
"""

from typing import Optional, List
from datetime import datetime, UTC
from sqlalchemy import select, update, delete, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from aico.ai.scheduler.models import SchedulerTask
from aico.data.tables import scheduler_tasks
from aico.data.repositories.base import Repository


class PostgresSchedulerTaskRepository(Repository[SchedulerTask]):
    """PostgreSQL implementation of scheduler task repository."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def create(self, entity: SchedulerTask) -> SchedulerTask:
        """Create a new scheduler task."""
        stmt = scheduler_tasks.insert().values(
            task_id=entity.task_id,
            task_class=entity.task_class,
            schedule=entity.schedule,
            config=entity.config,
            enabled=entity.enabled,
            created_at=entity.created_at or datetime.now(UTC),
            updated_at=entity.updated_at or datetime.now(UTC),
        )
        await self.session.execute(stmt)
        return entity
    
    async def get_by_id(self, entity_id: str) -> Optional[SchedulerTask]:
        """Get task by ID."""
        stmt = select(scheduler_tasks).where(scheduler_tasks.c.task_id == entity_id)
        result = await self.session.execute(stmt)
        row = result.fetchone()
        
        if not row:
            return None
        
        return SchedulerTask(
            task_id=row.task_id,
            task_class=row.task_class,
            schedule=row.schedule,
            config=row.config,
            enabled=row.enabled,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )
    
    async def update(self, entity: SchedulerTask) -> SchedulerTask:
        """Update an existing task."""
        stmt = (
            update(scheduler_tasks)
            .where(scheduler_tasks.c.task_id == entity.task_id)
            .values(
                schedule=entity.schedule,
                config=entity.config,
                enabled=entity.enabled,
                updated_at=datetime.now(UTC),
            )
        )
        await self.session.execute(stmt)
        return entity
    
    async def delete(self, entity_id: str) -> bool:
        """Delete a task."""
        stmt = delete(scheduler_tasks).where(scheduler_tasks.c.task_id == entity_id)
        result = await self.session.execute(stmt)
        return result.rowcount > 0
    
    async def list(self, filters: Optional[dict] = None, limit: int = 100, offset: int = 0) -> List[SchedulerTask]:
        """List tasks with optional filters."""
        stmt = select(scheduler_tasks)
        
        if filters:
            conditions = []
            if 'enabled' in filters:
                conditions.append(scheduler_tasks.c.enabled == filters['enabled'])
            if 'task_class' in filters:
                conditions.append(scheduler_tasks.c.task_class == filters['task_class'])
            
            if conditions:
                stmt = stmt.where(and_(*conditions))
        
        stmt = stmt.order_by(scheduler_tasks.c.created_at.desc()).limit(limit).offset(offset)
        result = await self.session.execute(stmt)
        
        return [
            SchedulerTask(
                task_id=row.task_id,
                task_class=row.task_class,
                schedule=row.schedule,
                config=row.config,
                enabled=row.enabled,
                created_at=row.created_at,
                updated_at=row.updated_at,
            )
            for row in result.fetchall()
        ]
    
    async def count(self, filters: Optional[dict] = None) -> int:
        """Count tasks with optional filters."""
        stmt = select(func.count()).select_from(scheduler_tasks)
        
        if filters:
            conditions = []
            if 'enabled' in filters:
                conditions.append(scheduler_tasks.c.enabled == filters['enabled'])
            
            if conditions:
                stmt = stmt.where(and_(*conditions))
        
        result = await self.session.execute(stmt)
        return result.scalar() or 0
    
    async def get_enabled_tasks(self) -> List[SchedulerTask]:
        """Get all enabled tasks."""
        stmt = select(scheduler_tasks).where(
            scheduler_tasks.c.enabled == True
        ).order_by(scheduler_tasks.c.task_id)
        
        result = await self.session.execute(stmt)
        
        return [
            SchedulerTask(
                task_id=row.task_id,
                task_class=row.task_class,
                schedule=row.schedule,
                config=row.config,
                enabled=row.enabled,
                created_at=row.created_at,
                updated_at=row.updated_at,
            )
            for row in result.fetchall()
        ]
