"""PostgreSQL repository for agency_skill_executions."""

from typing import List, Optional
from sqlalchemy import select, insert, update, delete, func
from sqlalchemy.ext.asyncio import AsyncSession
from aico.data.tables import agency_skill_executions
from aico.data.agency.skill_models import AgencySkillExecution


class PostgresAgencySkillExecutionsRepository:
    """PostgreSQL repository for agency_skill_executions."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def create(self, entity: AgencySkillExecution) -> AgencySkillExecution:
        """Create a new skill execution."""
        stmt = insert(agency_skill_executions).values(**entity.__dict__).returning(agency_skill_executions)
        result = await self.session.execute(stmt)
        await self.session.commit()
        row = result.fetchone()
        return AgencySkillExecution(**dict(row._mapping))
    
    async def get_by_id(self, execution_id: str) -> Optional[AgencySkillExecution]:
        """Get skill execution by ID."""
        stmt = select(agency_skill_executions).where(agency_skill_executions.c.execution_id == execution_id)
        result = await self.session.execute(stmt)
        row = result.fetchone()
        return AgencySkillExecution(**dict(row._mapping)) if row else None
    
    async def update(self, execution_id: str, entity: AgencySkillExecution) -> Optional[AgencySkillExecution]:
        """Update skill execution."""
        stmt = (
            update(agency_skill_executions)
            .where(agency_skill_executions.c.execution_id == execution_id)
            .values(**entity.__dict__)
            .returning(agency_skill_executions)
        )
        result = await self.session.execute(stmt)
        await self.session.commit()
        row = result.fetchone()
        return AgencySkillExecution(**dict(row._mapping)) if row else None
    
    async def delete(self, execution_id: str) -> bool:
        """Delete skill execution."""
        stmt = delete(agency_skill_executions).where(agency_skill_executions.c.execution_id == execution_id)
        result = await self.session.execute(stmt)
        await self.session.commit()
        return result.rowcount > 0
    
    async def list(self, limit: int = 100, offset: int = 0) -> List[AgencySkillExecution]:
        """List skill executions."""
        stmt = select(agency_skill_executions).limit(limit).offset(offset)
        result = await self.session.execute(stmt)
        return [AgencySkillExecution(**dict(row._mapping)) for row in result.fetchall()]
    
    async def count(self) -> int:
        """Count total skill executions."""
        stmt = select(func.count()).select_from(agency_skill_executions)
        result = await self.session.execute(stmt)
        return result.scalar() or 0
    
    async def get_skill_executions(self, skill_id: str) -> List[AgencySkillExecution]:
        """Get all executions for a skill."""
        stmt = select(agency_skill_executions).where(
            agency_skill_executions.c.skill_id == skill_id
        ).order_by(agency_skill_executions.c.created_at.desc())
        result = await self.session.execute(stmt)
        return [AgencySkillExecution(**dict(row._mapping)) for row in result.fetchall()]
