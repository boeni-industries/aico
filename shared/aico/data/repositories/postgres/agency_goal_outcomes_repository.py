"""PostgreSQL repository for agency_goal_outcomes."""

from typing import List, Optional
from datetime import datetime
from sqlalchemy import select, insert, update, delete, func
from sqlalchemy.ext.asyncio import AsyncSession
from aico.data.tables import agency_goal_outcomes
from aico.data.agency.goal_models import AgencyGoalOutcome


class PostgresAgencyGoalOutcomesRepository:
    """PostgreSQL repository for agency_goal_outcomes."""

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
    
    async def create(self, entity: AgencyGoalOutcome) -> AgencyGoalOutcome:
        """Create a new goal outcome."""
        stmt = insert(agency_goal_outcomes).values(**entity.__dict__).returning(agency_goal_outcomes)
        result = await self.session.execute(stmt)
        await self.session.commit()
        row = result.fetchone()
        return AgencyGoalOutcome(**self._normalize_row(dict(row._mapping)))
    
    async def get_by_id(self, outcome_id: str) -> Optional[AgencyGoalOutcome]:
        """Get goal outcome by ID."""
        stmt = select(agency_goal_outcomes).where(agency_goal_outcomes.c.outcome_id == outcome_id)
        result = await self.session.execute(stmt)
        row = result.fetchone()
        return AgencyGoalOutcome(**self._normalize_row(dict(row._mapping))) if row else None
    
    async def update(self, outcome_id: str, entity: AgencyGoalOutcome) -> Optional[AgencyGoalOutcome]:
        """Update goal outcome."""
        stmt = (
            update(agency_goal_outcomes)
            .where(agency_goal_outcomes.c.outcome_id == outcome_id)
            .values(**entity.__dict__)
            .returning(agency_goal_outcomes)
        )
        result = await self.session.execute(stmt)
        await self.session.commit()
        row = result.fetchone()
        return AgencyGoalOutcome(**self._normalize_row(dict(row._mapping))) if row else None
    
    async def delete(self, outcome_id: str) -> bool:
        """Delete goal outcome."""
        stmt = delete(agency_goal_outcomes).where(agency_goal_outcomes.c.outcome_id == outcome_id)
        result = await self.session.execute(stmt)
        await self.session.commit()
        return result.rowcount > 0
    
    async def list(self, limit: int = 100, offset: int = 0) -> List[AgencyGoalOutcome]:
        """List goal outcomes."""
        stmt = select(agency_goal_outcomes).limit(limit).offset(offset)
        result = await self.session.execute(stmt)
        return [AgencyGoalOutcome(**self._normalize_row(dict(row._mapping))) for row in result.fetchall()]
    
    async def count(self) -> int:
        """Count total goal outcomes."""
        stmt = select(func.count()).select_from(agency_goal_outcomes)
        result = await self.session.execute(stmt)
        return result.scalar() or 0
    
    async def get_goal_outcomes(self, goal_id: str) -> List[AgencyGoalOutcome]:
        """Get all outcomes for a goal."""
        stmt = select(agency_goal_outcomes).where(
            agency_goal_outcomes.c.goal_id == goal_id
        ).order_by(agency_goal_outcomes.c.created_at.desc())
        result = await self.session.execute(stmt)
        return [AgencyGoalOutcome(**self._normalize_row(dict(row._mapping))) for row in result.fetchall()]
