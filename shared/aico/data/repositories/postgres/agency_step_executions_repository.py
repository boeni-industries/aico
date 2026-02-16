"""PostgreSQL repository for agency_step_executions."""

from typing import List, Optional
from sqlalchemy import select, insert, update, delete, func
from sqlalchemy.ext.asyncio import AsyncSession
from aico.data.tables import agency_step_executions
from aico.data.agency.execution_models import AgencyStepExecution


class PostgresAgencyStepExecutionsRepository:
    """PostgreSQL repository for agency_step_executions."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def create(self, entity: AgencyStepExecution) -> AgencyStepExecution:
        """Create a new step execution."""
        stmt = insert(agency_step_executions).values(**entity.__dict__).returning(agency_step_executions)
        result = await self.session.execute(stmt)
        await self.session.commit()
        row = result.fetchone()
        return AgencyStepExecution(**dict(row._mapping))
    
    async def get_by_id(self, step_execution_id: str) -> Optional[AgencyStepExecution]:
        """Get step execution by ID."""
        stmt = select(agency_step_executions).where(agency_step_executions.c.step_execution_id == step_execution_id)
        result = await self.session.execute(stmt)
        row = result.fetchone()
        return AgencyStepExecution(**dict(row._mapping)) if row else None
    
    async def update(self, step_execution_id: str, entity: AgencyStepExecution) -> Optional[AgencyStepExecution]:
        """Update step execution."""
        stmt = (
            update(agency_step_executions)
            .where(agency_step_executions.c.step_execution_id == step_execution_id)
            .values(**entity.__dict__)
            .returning(agency_step_executions)
        )
        result = await self.session.execute(stmt)
        await self.session.commit()
        row = result.fetchone()
        return AgencyStepExecution(**dict(row._mapping)) if row else None
    
    async def delete(self, step_execution_id: str) -> bool:
        """Delete step execution."""
        stmt = delete(agency_step_executions).where(agency_step_executions.c.step_execution_id == step_execution_id)
        result = await self.session.execute(stmt)
        await self.session.commit()
        return result.rowcount > 0
    
    async def list(self, filters: Optional[dict] = None, limit: int = 100, offset: int = 0, order_by: Optional[str] = None) -> List[AgencyStepExecution]:
        """List step executions with optional filters."""
        stmt = select(agency_step_executions)
        
        # Apply filters
        if filters:
            for key, value in filters.items():
                if hasattr(agency_step_executions.c, key):
                    stmt = stmt.where(getattr(agency_step_executions.c, key) == value)
        
        # Apply ordering
        if order_by and hasattr(agency_step_executions.c, order_by):
            stmt = stmt.order_by(getattr(agency_step_executions.c, order_by))
        
        stmt = stmt.limit(limit).offset(offset)
        result = await self.session.execute(stmt)
        return [AgencyStepExecution(**dict(row._mapping)) for row in result.fetchall()]
    
    async def count(self) -> int:
        """Count total step executions."""
        stmt = select(func.count()).select_from(agency_step_executions)
        result = await self.session.execute(stmt)
        return result.scalar() or 0
    
    async def get_execution_steps(self, execution_id: str) -> List[AgencyStepExecution]:
        """Get all step executions for a plan execution."""
        stmt = select(agency_step_executions).where(
            agency_step_executions.c.execution_id == execution_id
        ).order_by(agency_step_executions.c.step_order)
        result = await self.session.execute(stmt)
        return [AgencyStepExecution(**dict(row._mapping)) for row in result.fetchall()]
