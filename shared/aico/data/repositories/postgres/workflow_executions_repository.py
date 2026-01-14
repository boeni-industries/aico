"""
WorkflowExecutionsRepository - PostgreSQL implementation

Handles CRUD operations for workflow executions.
"""

from typing import Optional, List
from datetime import datetime, UTC
from sqlalchemy import select, update, delete, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from aico.ai.workflow.models import WorkflowExecution
from aico.data.tables import workflow_executions
from aico.data.repositories.base import Repository


class PostgresWorkflowExecutionsRepository(Repository[WorkflowExecution]):
    """PostgreSQL implementation of workflow executions repository."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def create(self, entity: WorkflowExecution) -> WorkflowExecution:
        """Create a new workflow execution."""
        stmt = workflow_executions.insert().values(
            execution_id=entity.execution_id,
            workflow_type=entity.workflow_type,
            user_id=entity.user_id,
            status=entity.status,
            started_at=entity.started_at,
            completed_at=entity.completed_at,
            current_stage=entity.current_stage,
            total_stages=entity.total_stages,
            metadata=entity.metadata,
            error_message=entity.error_message,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
        )
        await self.session.execute(stmt)
        return entity
    
    async def get_by_id(self, entity_id: str) -> Optional[WorkflowExecution]:
        """Get workflow execution by ID."""
        stmt = select(workflow_executions).where(workflow_executions.c.execution_id == entity_id)
        result = await self.session.execute(stmt)
        row = result.fetchone()
        
        if not row:
            return None
        
        return WorkflowExecution(
            execution_id=row.execution_id,
            workflow_type=row.workflow_type,
            user_id=row.user_id,
            status=row.status,
            started_at=row.started_at,
            completed_at=row.completed_at,
            current_stage=row.current_stage,
            total_stages=row.total_stages,
            metadata=row.metadata,
            error_message=row.error_message,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )
    
    async def update(self, entity: WorkflowExecution) -> WorkflowExecution:
        """Update an existing workflow execution."""
        stmt = (
            update(workflow_executions)
            .where(workflow_executions.c.execution_id == entity.execution_id)
            .values(
                status=entity.status,
                completed_at=entity.completed_at,
                current_stage=entity.current_stage,
                error_message=entity.error_message,
                updated_at=datetime.now(UTC).isoformat(),
            )
        )
        await self.session.execute(stmt)
        return entity
    
    async def delete(self, entity_id: str) -> bool:
        """Delete a workflow execution."""
        stmt = delete(workflow_executions).where(workflow_executions.c.execution_id == entity_id)
        result = await self.session.execute(stmt)
        return result.rowcount > 0
    
    async def list(self, filters: Optional[dict] = None, limit: int = 100, offset: int = 0) -> List[WorkflowExecution]:
        """List workflow executions with optional filters."""
        stmt = select(workflow_executions)
        
        if filters:
            conditions = []
            if 'user_id' in filters:
                conditions.append(workflow_executions.c.user_id == filters['user_id'])
            if 'status' in filters:
                conditions.append(workflow_executions.c.status == filters['status'])
            if 'workflow_type' in filters:
                conditions.append(workflow_executions.c.workflow_type == filters['workflow_type'])
            
            if conditions:
                stmt = stmt.where(and_(*conditions))
        
        stmt = stmt.order_by(workflow_executions.c.created_at.desc()).limit(limit).offset(offset)
        result = await self.session.execute(stmt)
        
        return [
            WorkflowExecution(
                execution_id=row.execution_id,
                workflow_type=row.workflow_type,
                user_id=row.user_id,
                status=row.status,
                started_at=row.started_at,
                completed_at=row.completed_at,
                current_stage=row.current_stage,
                total_stages=row.total_stages,
                metadata=row.metadata,
                error_message=row.error_message,
                created_at=row.created_at,
                updated_at=row.updated_at,
            )
            for row in result.fetchall()
        ]
    
    async def count(self, filters: Optional[dict] = None) -> int:
        """Count workflow executions with optional filters."""
        stmt = select(func.count()).select_from(workflow_executions)
        
        if filters:
            conditions = []
            if 'user_id' in filters:
                conditions.append(workflow_executions.c.user_id == filters['user_id'])
            if 'status' in filters:
                conditions.append(workflow_executions.c.status == filters['status'])
            
            if conditions:
                stmt = stmt.where(and_(*conditions))
        
        result = await self.session.execute(stmt)
        return result.scalar() or 0
    
    async def get_active_executions(self, user_id: str) -> List[WorkflowExecution]:
        """Get active workflow executions for user."""
        stmt = select(workflow_executions).where(
            and_(
                workflow_executions.c.user_id == user_id,
                workflow_executions.c.status == 'running'
            )
        ).order_by(workflow_executions.c.created_at.desc())
        
        result = await self.session.execute(stmt)
        
        return [
            WorkflowExecution(
                execution_id=row.execution_id,
                workflow_type=row.workflow_type,
                user_id=row.user_id,
                status=row.status,
                started_at=row.started_at,
                completed_at=row.completed_at,
                current_stage=row.current_stage,
                total_stages=row.total_stages,
                metadata=row.metadata,
                error_message=row.error_message,
                created_at=row.created_at,
                updated_at=row.updated_at,
            )
            for row in result.fetchall()
        ]
