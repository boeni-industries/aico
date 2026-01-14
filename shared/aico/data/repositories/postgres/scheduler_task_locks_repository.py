"""
SchedulerTaskLocksRepository - PostgreSQL implementation

Handles CRUD operations for scheduler task locks.
"""

from typing import Optional, List
from datetime import datetime, UTC
from sqlalchemy import select, update, delete, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from aico.data.scheduler.lock_models import SchedulerTaskLock
from aico.data.tables import scheduler_task_locks
from aico.data.repositories.base import Repository


class PostgresSchedulerTaskLocksRepository(Repository[SchedulerTaskLock]):
    """PostgreSQL implementation of scheduler task locks repository."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def create(self, entity: SchedulerTaskLock) -> SchedulerTaskLock:
        """Create a new task lock."""
        stmt = scheduler_task_locks.insert().values(
            task_id=entity.task_id,
            execution_id=entity.execution_id,
            locked_at=entity.locked_at or datetime.now(UTC),
            expires_at=entity.expires_at,
        )
        await self.session.execute(stmt)
        return entity
    
    async def get_by_id(self, entity_id: str) -> Optional[SchedulerTaskLock]:
        """Get task lock by ID."""
        stmt = select(scheduler_task_locks).where(scheduler_task_locks.c.task_id == entity_id)
        result = await self.session.execute(stmt)
        row = result.fetchone()
        
        if not row:
            return None
        
        return SchedulerTaskLock(
            task_id=row.task_id,
            execution_id=row.execution_id,
            locked_at=row.locked_at,
            expires_at=row.expires_at,
        )
    
    async def update(self, entity: SchedulerTaskLock) -> SchedulerTaskLock:
        """Update an existing task lock."""
        stmt = (
            update(scheduler_task_locks)
            .where(scheduler_task_locks.c.task_id == entity.task_id)
            .values(
                execution_id=entity.execution_id,
                expires_at=entity.expires_at,
            )
        )
        await self.session.execute(stmt)
        return entity
    
    async def delete(self, entity_id: str) -> bool:
        """Delete a task lock."""
        stmt = delete(scheduler_task_locks).where(scheduler_task_locks.c.task_id == entity_id)
        result = await self.session.execute(stmt)
        return result.rowcount > 0
    
    async def list(self, filters: Optional[dict] = None, limit: int = 100, offset: int = 0) -> List[SchedulerTaskLock]:
        """List task locks with optional filters."""
        stmt = select(scheduler_task_locks)
        
        if filters:
            conditions = []
            if 'execution_id' in filters:
                conditions.append(scheduler_task_locks.c.execution_id == filters['execution_id'])
            
            if conditions:
                stmt = stmt.where(and_(*conditions))
        
        stmt = stmt.order_by(scheduler_task_locks.c.expires_at.asc()).limit(limit).offset(offset)
        result = await self.session.execute(stmt)
        
        return [
            SchedulerTaskLock(
                task_id=row.task_id,
                execution_id=row.execution_id,
                locked_at=row.locked_at,
                expires_at=row.expires_at,
            )
            for row in result.fetchall()
        ]
    
    async def count(self, filters: Optional[dict] = None) -> int:
        """Count task locks with optional filters."""
        stmt = select(func.count()).select_from(scheduler_task_locks)
        
        if filters:
            conditions = []
            if 'execution_id' in filters:
                conditions.append(scheduler_task_locks.c.execution_id == filters['execution_id'])
            
            if conditions:
                stmt = stmt.where(and_(*conditions))
        
        result = await self.session.execute(stmt)
        return result.scalar() or 0
    
    async def get_expired_locks(self) -> List[SchedulerTaskLock]:
        """Get all expired task locks."""
        stmt = select(scheduler_task_locks).where(
            scheduler_task_locks.c.expires_at < datetime.now(UTC)
        ).order_by(scheduler_task_locks.c.expires_at.asc())
        
        result = await self.session.execute(stmt)
        
        return [
            SchedulerTaskLock(
                task_id=row.task_id,
                execution_id=row.execution_id,
                locked_at=row.locked_at,
                expires_at=row.expires_at,
            )
            for row in result.fetchall()
        ]
    
    async def cleanup_expired_locks(self) -> int:
        """Delete all expired task locks."""
        stmt = delete(scheduler_task_locks).where(
            scheduler_task_locks.c.expires_at < datetime.now(UTC)
        )
        result = await self.session.execute(stmt)
        return result.rowcount
    
    async def is_locked(self, task_id: str) -> bool:
        """Check if a task is currently locked."""
        stmt = select(func.count()).select_from(scheduler_task_locks).where(
            and_(
                scheduler_task_locks.c.task_id == task_id,
                scheduler_task_locks.c.expires_at > datetime.now(UTC)
            )
        )
        result = await self.session.execute(stmt)
        return (result.scalar() or 0) > 0
