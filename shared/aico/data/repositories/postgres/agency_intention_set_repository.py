"""PostgreSQL repository for agency_intention_set."""

from typing import List, Optional
from datetime import datetime
from sqlalchemy import select, insert, update, delete, func
from sqlalchemy.ext.asyncio import AsyncSession
from aico.data.tables import agency_intention_set
from aico.ai.agency.models import AgencyIntentionSet


class PostgresAgencyIntentionSetRepository:
    """PostgreSQL repository for agency_intention_set."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def create(self, entity: AgencyIntentionSet) -> AgencyIntentionSet:
        """Create a new intention."""
        values = entity.__dict__.copy()
        if isinstance(values.get('created_at'), datetime):
            values['created_at'] = values['created_at']
        if isinstance(values.get('updated_at'), datetime):
            values['updated_at'] = values['updated_at']
        
        stmt = insert(agency_intention_set).values(**values).returning(agency_intention_set)
        result = await self.session.execute(stmt)
        await self.session.commit()
        row = result.fetchone()
        return AgencyIntentionSet(**dict(row._mapping))
    
    async def get_by_id(self, intention_id: str) -> Optional[AgencyIntentionSet]:
        """Get intention by ID."""
        stmt = select(agency_intention_set).where(agency_intention_set.c.intention_id == intention_id)
        result = await self.session.execute(stmt)
        row = result.fetchone()
        return AgencyIntentionSet(**dict(row._mapping)) if row else None
    
    async def update(self, intention_id: str, entity: AgencyIntentionSet) -> Optional[AgencyIntentionSet]:
        """Update intention."""
        values = entity.__dict__.copy()
        if isinstance(values.get('updated_at'), datetime):
            values['updated_at'] = values['updated_at']
        
        stmt = (
            update(agency_intention_set)
            .where(agency_intention_set.c.intention_id == intention_id)
            .values(**values)
            .returning(agency_intention_set)
        )
        result = await self.session.execute(stmt)
        await self.session.commit()
        row = result.fetchone()
        return AgencyIntentionSet(**dict(row._mapping)) if row else None
    
    async def delete(self, intention_id: str) -> bool:
        """Delete intention."""
        stmt = delete(agency_intention_set).where(agency_intention_set.c.intention_id == intention_id)
        result = await self.session.execute(stmt)
        await self.session.commit()
        return result.rowcount > 0
    
    async def list(self, limit: int = 100, offset: int = 0) -> List[AgencyIntentionSet]:
        """List intentions."""
        stmt = select(agency_intention_set).limit(limit).offset(offset)
        result = await self.session.execute(stmt)
        return [AgencyIntentionSet(**dict(row._mapping)) for row in result.fetchall()]
    
    async def count(self) -> int:
        """Count total intentions."""
        stmt = select(func.count()).select_from(agency_intention_set)
        result = await self.session.execute(stmt)
        return result.scalar() or 0
    
    async def get_user_intentions(self, user_id: str, status: Optional[str] = None) -> List[AgencyIntentionSet]:
        """Get all intentions for a user, optionally filtered by status."""
        stmt = select(agency_intention_set).where(agency_intention_set.c.user_id == user_id)
        if status:
            stmt = stmt.where(agency_intention_set.c.status == status)
        stmt = stmt.order_by(agency_intention_set.c.arbiter_score.desc())
        result = await self.session.execute(stmt)
        return [AgencyIntentionSet(**dict(row._mapping)) for row in result.fetchall()]
