"""PostgreSQL repository for agency_skill_learning_data."""

from typing import List, Optional
from sqlalchemy import select, insert, update, delete, func
from sqlalchemy.ext.asyncio import AsyncSession
from aico.data.tables import agency_skill_learning_data
from aico.ai.agency.models import AgencySkillLearningData


class PostgresAgencySkillLearningDataRepository:
    """PostgreSQL repository for agency_skill_learning_data."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def create(self, entity: AgencySkillLearningData) -> AgencySkillLearningData:
        """Create a new skill learning data entry."""
        stmt = insert(agency_skill_learning_data).values(**entity.__dict__).returning(agency_skill_learning_data)
        result = await self.session.execute(stmt)
        await self.session.commit()
        row = result.fetchone()
        return AgencySkillLearningData(**dict(row._mapping))
    
    async def get_by_id(self, skill_id: str) -> Optional[AgencySkillLearningData]:
        """Get skill learning data by ID."""
        stmt = select(agency_skill_learning_data).where(agency_skill_learning_data.c.skill_id == skill_id)
        result = await self.session.execute(stmt)
        row = result.fetchone()
        return AgencySkillLearningData(**dict(row._mapping)) if row else None
    
    async def update(self, skill_id: str, entity: AgencySkillLearningData) -> Optional[AgencySkillLearningData]:
        """Update skill learning data."""
        stmt = (
            update(agency_skill_learning_data)
            .where(agency_skill_learning_data.c.skill_id == skill_id)
            .values(**entity.__dict__)
            .returning(agency_skill_learning_data)
        )
        result = await self.session.execute(stmt)
        await self.session.commit()
        row = result.fetchone()
        return AgencySkillLearningData(**dict(row._mapping)) if row else None
    
    async def delete(self, skill_id: str) -> bool:
        """Delete skill learning data."""
        stmt = delete(agency_skill_learning_data).where(agency_skill_learning_data.c.skill_id == skill_id)
        result = await self.session.execute(stmt)
        await self.session.commit()
        return result.rowcount > 0
    
    async def list(self, limit: int = 100, offset: int = 0) -> List[AgencySkillLearningData]:
        """List skill learning data."""
        stmt = select(agency_skill_learning_data).limit(limit).offset(offset)
        result = await self.session.execute(stmt)
        return [AgencySkillLearningData(**dict(row._mapping)) for row in result.fetchall()]
    
    async def count(self) -> int:
        """Count total skill learning data entries."""
        stmt = select(func.count()).select_from(agency_skill_learning_data)
        result = await self.session.execute(stmt)
        return result.scalar() or 0
