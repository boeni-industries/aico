"""PostgreSQL repository for agency_goal_dependencies."""

from typing import List, Optional
from sqlalchemy import select, insert, update, delete, func
from sqlalchemy.ext.asyncio import AsyncSession
from aico.data.tables import agency_goal_dependencies
from aico.data.agency.goal_models import AgencyGoalDependency


class PostgresAgencyGoalDependenciesRepository:
    """PostgreSQL repository for agency_goal_dependencies."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def create(self, entity: AgencyGoalDependency) -> AgencyGoalDependency:
        """Create a new goal dependency."""
        stmt = insert(agency_goal_dependencies).values(**entity.__dict__).returning(agency_goal_dependencies)
        result = await self.session.execute(stmt)
        await self.session.commit()
        row = result.fetchone()
        return AgencyGoalDependency(**dict(row._mapping))
    
    async def get_by_id(self, dependency_id: str) -> Optional[AgencyGoalDependency]:
        """Get goal dependency by ID."""
        stmt = select(agency_goal_dependencies).where(agency_goal_dependencies.c.dependency_id == dependency_id)
        result = await self.session.execute(stmt)
        row = result.fetchone()
        return AgencyGoalDependency(**dict(row._mapping)) if row else None
    
    async def update(self, dependency_id: str, entity: AgencyGoalDependency) -> Optional[AgencyGoalDependency]:
        """Update goal dependency."""
        stmt = (
            update(agency_goal_dependencies)
            .where(agency_goal_dependencies.c.dependency_id == dependency_id)
            .values(**entity.__dict__)
            .returning(agency_goal_dependencies)
        )
        result = await self.session.execute(stmt)
        await self.session.commit()
        row = result.fetchone()
        return AgencyGoalDependency(**dict(row._mapping)) if row else None
    
    async def delete(self, dependency_id: str) -> bool:
        """Delete goal dependency."""
        stmt = delete(agency_goal_dependencies).where(agency_goal_dependencies.c.dependency_id == dependency_id)
        result = await self.session.execute(stmt)
        await self.session.commit()
        return result.rowcount > 0
    
    async def list(self, limit: int = 100, offset: int = 0) -> List[AgencyGoalDependency]:
        """List goal dependencies."""
        stmt = select(agency_goal_dependencies).limit(limit).offset(offset)
        result = await self.session.execute(stmt)
        return [AgencyGoalDependency(**dict(row._mapping)) for row in result.fetchall()]
    
    async def count(self) -> int:
        """Count total goal dependencies."""
        stmt = select(func.count()).select_from(agency_goal_dependencies)
        result = await self.session.execute(stmt)
        return result.scalar() or 0
    
    async def get_goal_dependencies(self, goal_id: str) -> List[AgencyGoalDependency]:
        """Get all dependencies for a goal."""
        stmt = select(agency_goal_dependencies).where(
            agency_goal_dependencies.c.goal_id == goal_id,
            agency_goal_dependencies.c.active == True
        )
        result = await self.session.execute(stmt)
        return [AgencyGoalDependency(**dict(row._mapping)) for row in result.fetchall()]
