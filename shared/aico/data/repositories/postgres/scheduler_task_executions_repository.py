"""
SchedulerTaskExecutionsRepository - PostgreSQL implementation

Handles CRUD operations for scheduler task executions.
"""

from typing import Optional, List
from datetime import datetime, UTC
import json
from sqlalchemy import select, update, delete, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from aico.data.scheduler.models import TaskExecution
from aico.data.tables import scheduler_task_executions
from aico.data.repositories.base import Repository


class PostgresSchedulerTaskExecutionsRepository(Repository[TaskExecution]):
    """PostgreSQL implementation of scheduler task executions repository."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def create(self, entity: TaskExecution) -> TaskExecution:
        """Create a new task execution."""
        # Serialize result to TEXT for the database column. The domain model
        # may treat result as a dictionary; we persist JSON to Postgres.
        db_result: Optional[str]
        if entity.result is None:
            db_result = None
        elif isinstance(entity.result, str):
            db_result = entity.result
        else:
            db_result = json.dumps(entity.result)

        stmt = scheduler_task_executions.insert().values(
            task_id=entity.task_id,
            execution_id=entity.execution_id,
            status=entity.status,
            started_at=entity.started_at,
            completed_at=entity.completed_at,
            result=db_result,
            error_message=entity.error_message,
            duration_seconds=entity.duration_seconds,
            acknowledged=entity.acknowledged,
        )
        result = await self.session.execute(stmt)
        entity.id = result.inserted_primary_key[0]
        return entity
    
    async def get_by_id(self, entity_id: str) -> Optional[TaskExecution]:
        """Get task execution by ID."""
        stmt = select(scheduler_task_executions).where(scheduler_task_executions.c.id == int(entity_id))
        result = await self.session.execute(stmt)
        row = result.fetchone()
        
        if not row:
            return None
        
        return TaskExecution(
            id=row.id,
            task_id=row.task_id,
            execution_id=row.execution_id,
            status=row.status,
            started_at=row.started_at,
            completed_at=row.completed_at,
            result=row.result,
            error_message=row.error_message,
            duration_seconds=row.duration_seconds,
            acknowledged=row.acknowledged,
        )
    
    async def update(self, entity: TaskExecution) -> TaskExecution:
        """Update an existing task execution.
        
        Raises:
            ValueError: If entity has no database ID
            RuntimeError: If update matches zero rows (indicates data integrity issue)
        
        Note: Exceptions are raised to make failures visible, but caller should
        handle them gracefully to avoid crashing the system.
        """
        # Validate entity has required ID
        if not hasattr(entity, 'id') or entity.id is None:
            error_msg = (
                f"❌ Cannot update TaskExecution without database ID. "
                f"execution_id={getattr(entity, 'execution_id', 'unknown')}, "
                f"task_id={getattr(entity, 'task_id', 'unknown')}"
            )
            print(f"\n{error_msg}\n")
            raise ValueError(error_msg)
        
        # Same serialization rules as in create(): always store TEXT/JSON.
        db_result: Optional[str]
        if entity.result is None:
            db_result = None
        elif isinstance(entity.result, str):
            db_result = entity.result
        else:
            db_result = json.dumps(entity.result)

        stmt = (
            update(scheduler_task_executions)
            .where(scheduler_task_executions.c.id == entity.id)
            .values(
                status=entity.status,
                completed_at=entity.completed_at,
                result=db_result,
                error_message=entity.error_message,
                duration_seconds=entity.duration_seconds,
                acknowledged=entity.acknowledged,
            )
        )
        result = await self.session.execute(stmt)
        
        # CRITICAL: Verify update actually modified a row
        if result.rowcount == 0:
            error_msg = (
                f"❌ CRITICAL: Update matched zero rows for TaskExecution with id={entity.id}. "
                f"This indicates the record doesn't exist or the WHERE clause failed. "
                f"execution_id={getattr(entity, 'execution_id', 'unknown')}, "
                f"task_id={getattr(entity, 'task_id', 'unknown')}"
            )
            print(f"\n{error_msg}\n")
            raise RuntimeError(error_msg)
        
        return entity
    
    async def delete(self, entity_id: str) -> bool:
        """Delete a task execution."""
        stmt = delete(scheduler_task_executions).where(scheduler_task_executions.c.id == int(entity_id))
        result = await self.session.execute(stmt)
        return result.rowcount > 0
    
    async def list(self, filters: Optional[dict] = None, limit: int = 100, offset: int = 0) -> List[TaskExecution]:
        """List task executions with optional filters."""
        stmt = select(scheduler_task_executions)
        
        if filters:
            conditions = []
            if 'task_id' in filters:
                conditions.append(scheduler_task_executions.c.task_id == filters['task_id'])
            if 'status' in filters:
                conditions.append(scheduler_task_executions.c.status == filters['status'])
            if 'acknowledged' in filters:
                conditions.append(scheduler_task_executions.c.acknowledged == filters['acknowledged'])
            
            if conditions:
                stmt = stmt.where(and_(*conditions))
        
        stmt = stmt.order_by(scheduler_task_executions.c.started_at.desc()).limit(limit).offset(offset)
        result = await self.session.execute(stmt)
        
        return [
            TaskExecution(
                id=row.id,
                task_id=row.task_id,
                execution_id=row.execution_id,
                status=row.status,
                started_at=row.started_at,
                completed_at=row.completed_at,
                result=row.result,
                error_message=row.error_message,
                duration_seconds=row.duration_seconds,
                acknowledged=row.acknowledged,
            )
            for row in result.fetchall()
        ]
    
    async def count(self, filters: Optional[dict] = None) -> int:
        """Count task executions with optional filters."""
        stmt = select(func.count()).select_from(scheduler_task_executions)
        
        if filters:
            conditions = []
            if 'task_id' in filters:
                conditions.append(scheduler_task_executions.c.task_id == filters['task_id'])
            
            if conditions:
                stmt = stmt.where(and_(*conditions))
        
        result = await self.session.execute(stmt)
        return result.scalar() or 0
    
    async def get_task_executions(self, task_id: str, limit: int = 100) -> List[TaskExecution]:
        """Get executions for a specific task."""
        stmt = select(scheduler_task_executions).where(
            scheduler_task_executions.c.task_id == task_id
        ).order_by(scheduler_task_executions.c.started_at.desc()).limit(limit)
        
        result = await self.session.execute(stmt)
        
        return [
            TaskExecution(
                id=row.id,
                task_id=row.task_id,
                execution_id=row.execution_id,
                status=row.status,
                started_at=row.started_at,
                completed_at=row.completed_at,
                result=row.result,
                error_message=row.error_message,
                duration_seconds=row.duration_seconds,
                acknowledged=row.acknowledged,
            )
            for row in result.fetchall()
        ]
