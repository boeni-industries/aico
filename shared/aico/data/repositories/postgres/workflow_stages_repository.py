"""
WorkflowStagesRepository - PostgreSQL implementation

Handles CRUD operations for workflow stages.
"""

from typing import Optional, List
from datetime import datetime, UTC
from sqlalchemy import select, update, delete, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from aico.data.workflow.models import WorkflowStage
from aico.data.tables import workflow_stages
from aico.data.repositories.base import Repository


class PostgresWorkflowStagesRepository(Repository[WorkflowStage]):
    """PostgreSQL implementation of workflow stages repository."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def create(self, entity: WorkflowStage) -> WorkflowStage:
        """Create a new workflow stage."""
        stmt = workflow_stages.insert().values(
            stage_id=entity.stage_id,
            execution_id=entity.execution_id,
            stage_name=entity.stage_name,
            stage_order=entity.stage_order,
            status=entity.status,
            started_at=entity.started_at,
            completed_at=entity.completed_at,
            input_data=entity.input_data,
            output_data=entity.output_data,
            error_message=entity.error_message,
            retry_count=entity.retry_count,
            created_at=entity.created_at,
        )
        await self.session.execute(stmt)
        return entity
    
    async def get_by_id(self, entity_id: str) -> Optional[WorkflowStage]:
        """Get workflow stage by ID."""
        stmt = select(workflow_stages).where(workflow_stages.c.stage_id == entity_id)
        result = await self.session.execute(stmt)
        row = result.fetchone()
        
        if not row:
            return None
        
        return WorkflowStage(
            stage_id=row.stage_id,
            execution_id=row.execution_id,
            stage_name=row.stage_name,
            stage_order=row.stage_order,
            status=row.status,
            started_at=row.started_at,
            completed_at=row.completed_at,
            input_data=row.input_data,
            output_data=row.output_data,
            error_message=row.error_message,
            retry_count=row.retry_count,
            created_at=row.created_at,
        )
    
    async def update(self, entity: WorkflowStage) -> WorkflowStage:
        """Update an existing workflow stage."""
        stmt = (
            update(workflow_stages)
            .where(workflow_stages.c.stage_id == entity.stage_id)
            .values(
                status=entity.status,
                started_at=entity.started_at,
                completed_at=entity.completed_at,
                output_data=entity.output_data,
                error_message=entity.error_message,
                retry_count=entity.retry_count,
            )
        )
        await self.session.execute(stmt)
        return entity
    
    async def delete(self, entity_id: str) -> bool:
        """Delete a workflow stage."""
        stmt = delete(workflow_stages).where(workflow_stages.c.stage_id == entity_id)
        result = await self.session.execute(stmt)
        return result.rowcount > 0
    
    async def list(self, filters: Optional[dict] = None, limit: int = 100, offset: int = 0) -> List[WorkflowStage]:
        """List workflow stages with optional filters."""
        stmt = select(workflow_stages)
        
        if filters:
            conditions = []
            if 'execution_id' in filters:
                conditions.append(workflow_stages.c.execution_id == filters['execution_id'])
            if 'status' in filters:
                conditions.append(workflow_stages.c.status == filters['status'])
            
            if conditions:
                stmt = stmt.where(and_(*conditions))
        
        stmt = stmt.order_by(workflow_stages.c.stage_order.asc()).limit(limit).offset(offset)
        result = await self.session.execute(stmt)
        
        return [
            WorkflowStage(
                stage_id=row.stage_id,
                execution_id=row.execution_id,
                stage_name=row.stage_name,
                stage_order=row.stage_order,
                status=row.status,
                started_at=row.started_at,
                completed_at=row.completed_at,
                input_data=row.input_data,
                output_data=row.output_data,
                error_message=row.error_message,
                retry_count=row.retry_count,
                created_at=row.created_at,
            )
            for row in result.fetchall()
        ]
    
    async def count(self, filters: Optional[dict] = None) -> int:
        """Count workflow stages with optional filters."""
        stmt = select(func.count()).select_from(workflow_stages)
        
        if filters:
            conditions = []
            if 'execution_id' in filters:
                conditions.append(workflow_stages.c.execution_id == filters['execution_id'])
            
            if conditions:
                stmt = stmt.where(and_(*conditions))
        
        result = await self.session.execute(stmt)
        return result.scalar() or 0
    
    async def get_execution_stages(self, execution_id: str) -> List[WorkflowStage]:
        """Get all stages for a workflow execution."""
        stmt = select(workflow_stages).where(
            workflow_stages.c.execution_id == execution_id
        ).order_by(workflow_stages.c.stage_order.asc())
        
        result = await self.session.execute(stmt)
        
        return [
            WorkflowStage(
                stage_id=row.stage_id,
                execution_id=row.execution_id,
                stage_name=row.stage_name,
                stage_order=row.stage_order,
                status=row.status,
                started_at=row.started_at,
                completed_at=row.completed_at,
                input_data=row.input_data,
                output_data=row.output_data,
                error_message=row.error_message,
                retry_count=row.retry_count,
                created_at=row.created_at,
            )
            for row in result.fetchall()
        ]
