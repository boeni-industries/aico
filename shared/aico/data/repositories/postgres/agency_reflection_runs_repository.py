"""PostgreSQL repository for agency_reflection_runs."""

from typing import List, Optional
from datetime import datetime
from sqlalchemy import select, insert, update, delete, func
from sqlalchemy.ext.asyncio import AsyncSession
from aico.data.tables import agency_reflection_runs
from aico.ai.agency.models import AgencyReflectionRun


class PostgresAgencyReflectionRunsRepository:
    """PostgreSQL repository for agency_reflection_runs."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def create(self, entity: AgencyReflectionRun) -> AgencyReflectionRun:
        """Create a new reflection run."""
        values = entity.__dict__.copy()
        for key in ['analysis_window_start', 'analysis_window_end', 'started_at', 'completed_at', 'created_at']:
            if isinstance(values.get(key), datetime):
                values[key] = values[key]
        
        stmt = insert(agency_reflection_runs).values(**values).returning(agency_reflection_runs)
        result = await self.session.execute(stmt)
        await self.session.commit()
        row = result.fetchone()
        return AgencyReflectionRun(**dict(row._mapping))
    
    async def get_by_id(self, run_id: str) -> Optional[AgencyReflectionRun]:
        """Get reflection run by ID."""
        stmt = select(agency_reflection_runs).where(agency_reflection_runs.c.run_id == run_id)
        result = await self.session.execute(stmt)
        row = result.fetchone()
        return AgencyReflectionRun(**dict(row._mapping)) if row else None
    
    async def update(self, run_id: str, entity: AgencyReflectionRun) -> Optional[AgencyReflectionRun]:
        """Update reflection run."""
        values = entity.__dict__.copy()
        for key in ['completed_at']:
            if isinstance(values.get(key), datetime):
                values[key] = values[key]
        
        stmt = (
            update(agency_reflection_runs)
            .where(agency_reflection_runs.c.run_id == run_id)
            .values(**values)
            .returning(agency_reflection_runs)
        )
        result = await self.session.execute(stmt)
        await self.session.commit()
        row = result.fetchone()
        return AgencyReflectionRun(**dict(row._mapping)) if row else None
    
    async def delete(self, run_id: str) -> bool:
        """Delete reflection run."""
        stmt = delete(agency_reflection_runs).where(agency_reflection_runs.c.run_id == run_id)
        result = await self.session.execute(stmt)
        await self.session.commit()
        return result.rowcount > 0
    
    async def list(self, limit: int = 100, offset: int = 0) -> List[AgencyReflectionRun]:
        """List reflection runs."""
        stmt = select(agency_reflection_runs).limit(limit).offset(offset)
        result = await self.session.execute(stmt)
        return [AgencyReflectionRun(**dict(row._mapping)) for row in result.fetchall()]
    
    async def count(self) -> int:
        """Count total reflection runs."""
        stmt = select(func.count()).select_from(agency_reflection_runs)
        result = await self.session.execute(stmt)
        return result.scalar() or 0
    
    async def get_user_runs(self, user_id: str) -> List[AgencyReflectionRun]:
        """Get all reflection runs for a user."""
        stmt = select(agency_reflection_runs).where(
            agency_reflection_runs.c.user_id == user_id
        ).order_by(agency_reflection_runs.c.started_at.desc())
        result = await self.session.execute(stmt)
        return [AgencyReflectionRun(**dict(row._mapping)) for row in result.fetchall()]
