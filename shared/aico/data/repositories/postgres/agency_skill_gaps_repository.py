"""PostgreSQL repository for agency_skill_gaps."""

from typing import List, Optional
from sqlalchemy import select, insert, update, delete, func
from sqlalchemy.ext.asyncio import AsyncSession
from aico.data.tables import agency_skill_gaps
from aico.ai.agency.models import AgencySkillGap


class PostgresAgencySkillGapsRepository:
    """PostgreSQL repository for agency_skill_gaps."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def create(self, entity: AgencySkillGap) -> AgencySkillGap:
        """Create a new skill gap."""
        stmt = insert(agency_skill_gaps).values(**entity.__dict__).returning(agency_skill_gaps)
        result = await self.session.execute(stmt)
        await self.session.commit()
        row = result.fetchone()
        return AgencySkillGap(**dict(row._mapping))
    
    async def get_by_id(self, gap_id: str) -> Optional[AgencySkillGap]:
        """Get skill gap by ID."""
        stmt = select(agency_skill_gaps).where(agency_skill_gaps.c.gap_id == gap_id)
        result = await self.session.execute(stmt)
        row = result.fetchone()
        return AgencySkillGap(**dict(row._mapping)) if row else None
    
    async def update(self, gap_id: str, entity: AgencySkillGap) -> Optional[AgencySkillGap]:
        """Update skill gap."""
        stmt = (
            update(agency_skill_gaps)
            .where(agency_skill_gaps.c.gap_id == gap_id)
            .values(**entity.__dict__)
            .returning(agency_skill_gaps)
        )
        result = await self.session.execute(stmt)
        await self.session.commit()
        row = result.fetchone()
        return AgencySkillGap(**dict(row._mapping)) if row else None
    
    async def delete(self, gap_id: str) -> bool:
        """Delete skill gap."""
        stmt = delete(agency_skill_gaps).where(agency_skill_gaps.c.gap_id == gap_id)
        result = await self.session.execute(stmt)
        await self.session.commit()
        return result.rowcount > 0
    
    async def list(self, limit: int = 100, offset: int = 0) -> List[AgencySkillGap]:
        """List skill gaps."""
        stmt = select(agency_skill_gaps).limit(limit).offset(offset)
        result = await self.session.execute(stmt)
        return [AgencySkillGap(**dict(row._mapping)) for row in result.fetchall()]
    
    async def count(self) -> int:
        """Count total skill gaps."""
        stmt = select(func.count()).select_from(agency_skill_gaps)
        result = await self.session.execute(stmt)
        return result.scalar() or 0
    
    async def get_top_gaps(self, limit: int = 10) -> List[AgencySkillGap]:
        """Get top skill gaps by priority score."""
        stmt = select(agency_skill_gaps).order_by(
            agency_skill_gaps.c.priority_score.desc()
        ).limit(limit)
        result = await self.session.execute(stmt)
        return [AgencySkillGap(**dict(row._mapping)) for row in result.fetchall()]
