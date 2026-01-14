"""PostgreSQL repository for agency_plan_executions."""

from typing import List, Optional
from sqlalchemy import select, insert, update, delete, func
from sqlalchemy.ext.asyncio import AsyncSession
from aico.data.tables import agency_plan_executions
from aico.data.agency.execution_models import AgencyPlanExecution


class PostgresAgencyPlanExecutionsRepository:
    """PostgreSQL repository for agency_plan_executions."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def create(self, entity: AgencyPlanExecution) -> AgencyPlanExecution:
        """Create a new plan execution."""
        stmt = insert(agency_plan_executions).values(**entity.__dict__).returning(agency_plan_executions)
        result = await self.session.execute(stmt)
        await self.session.commit()
        row = result.fetchone()
        return AgencyPlanExecution(**dict(row._mapping))
    
    async def get_by_id(self, execution_id: str) -> Optional[AgencyPlanExecution]:
        """Get plan execution by ID."""
        stmt = select(agency_plan_executions).where(agency_plan_executions.c.execution_id == execution_id)
        result = await self.session.execute(stmt)
        row = result.fetchone()
        return AgencyPlanExecution(**dict(row._mapping)) if row else None
    
    async def update(self, execution_id: str, entity: AgencyPlanExecution) -> Optional[AgencyPlanExecution]:
        """Update plan execution."""
        stmt = (
            update(agency_plan_executions)
            .where(agency_plan_executions.c.execution_id == execution_id)
            .values(**entity.__dict__)
            .returning(agency_plan_executions)
        )
        result = await self.session.execute(stmt)
        await self.session.commit()
        row = result.fetchone()
        return AgencyPlanExecution(**dict(row._mapping)) if row else None
    
    async def delete(self, execution_id: str) -> bool:
        """Delete plan execution."""
        stmt = delete(agency_plan_executions).where(agency_plan_executions.c.execution_id == execution_id)
        result = await self.session.execute(stmt)
        await self.session.commit()
        return result.rowcount > 0
    
    async def list(self, limit: int = 100, offset: int = 0) -> List[AgencyPlanExecution]:
        """List plan executions."""
        stmt = select(agency_plan_executions).limit(limit).offset(offset)
        result = await self.session.execute(stmt)
        return [AgencyPlanExecution(**dict(row._mapping)) for row in result.fetchall()]
    
    async def count(self) -> int:
        """Count total plan executions."""
        stmt = select(func.count()).select_from(agency_plan_executions)
        result = await self.session.execute(stmt)
        return result.scalar() or 0
    
    async def get_user_executions(self, user_id: str, status: Optional[str] = None) -> List[AgencyPlanExecution]:
        """Get all plan executions for a user, optionally filtered by status."""
        stmt = select(agency_plan_executions).where(agency_plan_executions.c.user_id == user_id)
        if status:
            stmt = stmt.where(agency_plan_executions.c.status == status)
        stmt = stmt.order_by(agency_plan_executions.c.created_at.desc())
        result = await self.session.execute(stmt)
        return [AgencyPlanExecution(**dict(row._mapping)) for row in result.fetchall()]
