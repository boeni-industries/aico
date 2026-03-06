"""PostgreSQL repository for agency_goal_skill_executions."""

from typing import List, Optional
from datetime import datetime
from sqlalchemy import select, insert, update, delete, func
from sqlalchemy.ext.asyncio import AsyncSession
from aico.data.tables import agency_goal_skill_executions
from aico.data.agency.goal_models import AgencyGoalSkillExecution


class PostgresAgencyGoalSkillExecutionsRepository:
    """PostgreSQL repository for agency_goal_skill_executions."""

    @staticmethod
    def _normalize_dt(value):
        if value is None:
            return None
        if isinstance(value, datetime):
            return value
        if isinstance(value, str):
            s = value.strip()
            if s.endswith("+00"):
                s = s + ":00"
            try:
                return datetime.fromisoformat(s)
            except ValueError:
                return value
        return value

    @classmethod
    def _normalize_row(cls, row_mapping: dict) -> dict:
        out = dict(row_mapping)
        if "created_at" in out:
            out["created_at"] = cls._normalize_dt(out.get("created_at"))
        return out
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def create(self, entity: AgencyGoalSkillExecution) -> AgencyGoalSkillExecution:
        """Create a new goal skill execution."""
        stmt = insert(agency_goal_skill_executions).values(**entity.__dict__).returning(agency_goal_skill_executions)
        result = await self.session.execute(stmt)
        await self.session.commit()
        row = result.fetchone()
        return AgencyGoalSkillExecution(**self._normalize_row(dict(row._mapping)))
    
    async def get_by_id(self, link_id: str) -> Optional[AgencyGoalSkillExecution]:
        """Get goal skill execution by ID."""
        stmt = select(agency_goal_skill_executions).where(agency_goal_skill_executions.c.link_id == link_id)
        result = await self.session.execute(stmt)
        row = result.fetchone()
        return AgencyGoalSkillExecution(**self._normalize_row(dict(row._mapping))) if row else None
    
    async def update(self, link_id: str, entity: AgencyGoalSkillExecution) -> Optional[AgencyGoalSkillExecution]:
        """Update goal skill execution."""
        stmt = (
            update(agency_goal_skill_executions)
            .where(agency_goal_skill_executions.c.link_id == link_id)
            .values(**entity.__dict__)
            .returning(agency_goal_skill_executions)
        )
        result = await self.session.execute(stmt)
        await self.session.commit()
        row = result.fetchone()
        return AgencyGoalSkillExecution(**self._normalize_row(dict(row._mapping))) if row else None
    
    async def delete(self, link_id: str) -> bool:
        """Delete goal skill execution."""
        stmt = delete(agency_goal_skill_executions).where(agency_goal_skill_executions.c.link_id == link_id)
        result = await self.session.execute(stmt)
        await self.session.commit()
        return result.rowcount > 0
    
    async def list(self, limit: int = 100, offset: int = 0) -> List[AgencyGoalSkillExecution]:
        """List goal skill executions."""
        stmt = select(agency_goal_skill_executions).limit(limit).offset(offset)
        result = await self.session.execute(stmt)
        return [AgencyGoalSkillExecution(**self._normalize_row(dict(row._mapping))) for row in result.fetchall()]
    
    async def count(self) -> int:
        """Count total goal skill executions."""
        stmt = select(func.count()).select_from(agency_goal_skill_executions)
        result = await self.session.execute(stmt)
        return result.scalar() or 0
    
    async def get_goal_executions(self, goal_id: str) -> List[AgencyGoalSkillExecution]:
        """Get all skill executions for a goal."""
        stmt = select(agency_goal_skill_executions).where(
            agency_goal_skill_executions.c.goal_id == goal_id
        ).order_by(agency_goal_skill_executions.c.execution_order)
        result = await self.session.execute(stmt)
        return [AgencyGoalSkillExecution(**self._normalize_row(dict(row._mapping))) for row in result.fetchall()]
