"""PostgreSQL repository for agency_execution_snapshots."""

from typing import List, Optional
from sqlalchemy import select, insert, update, delete, func
from sqlalchemy.ext.asyncio import AsyncSession
from aico.data.tables import agency_execution_snapshots
from aico.data.agency.execution_models import AgencyExecutionSnapshot


class PostgresAgencyExecutionSnapshotsRepository:
    """PostgreSQL repository for agency_execution_snapshots."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def create(self, entity: AgencyExecutionSnapshot) -> AgencyExecutionSnapshot:
        """Create a new execution snapshot."""
        stmt = insert(agency_execution_snapshots).values(**entity.__dict__).returning(agency_execution_snapshots)
        result = await self.session.execute(stmt)
        await self.session.commit()
        row = result.fetchone()
        return AgencyExecutionSnapshot(**dict(row._mapping))
    
    async def get_by_id(self, snapshot_id: str) -> Optional[AgencyExecutionSnapshot]:
        """Get execution snapshot by ID."""
        stmt = select(agency_execution_snapshots).where(agency_execution_snapshots.c.snapshot_id == snapshot_id)
        result = await self.session.execute(stmt)
        row = result.fetchone()
        return AgencyExecutionSnapshot(**dict(row._mapping)) if row else None
    
    async def update(self, snapshot_id: str, entity: AgencyExecutionSnapshot) -> Optional[AgencyExecutionSnapshot]:
        """Update execution snapshot."""
        stmt = (
            update(agency_execution_snapshots)
            .where(agency_execution_snapshots.c.snapshot_id == snapshot_id)
            .values(**entity.__dict__)
            .returning(agency_execution_snapshots)
        )
        result = await self.session.execute(stmt)
        await self.session.commit()
        row = result.fetchone()
        return AgencyExecutionSnapshot(**dict(row._mapping)) if row else None
    
    async def delete(self, snapshot_id: str) -> bool:
        """Delete execution snapshot."""
        stmt = delete(agency_execution_snapshots).where(agency_execution_snapshots.c.snapshot_id == snapshot_id)
        result = await self.session.execute(stmt)
        await self.session.commit()
        return result.rowcount > 0
    
    async def list(self, limit: int = 100, offset: int = 0) -> List[AgencyExecutionSnapshot]:
        """List execution snapshots."""
        stmt = select(agency_execution_snapshots).limit(limit).offset(offset)
        result = await self.session.execute(stmt)
        return [AgencyExecutionSnapshot(**dict(row._mapping)) for row in result.fetchall()]
    
    async def count(self) -> int:
        """Count total execution snapshots."""
        stmt = select(func.count()).select_from(agency_execution_snapshots)
        result = await self.session.execute(stmt)
        return result.scalar() or 0
    
    async def get_by_execution(self, execution_id: str) -> List[AgencyExecutionSnapshot]:
        """Get all snapshots for an execution."""
        stmt = select(agency_execution_snapshots).where(
            agency_execution_snapshots.c.execution_id == execution_id
        ).order_by(agency_execution_snapshots.c.created_at.desc())
        result = await self.session.execute(stmt)
        return [AgencyExecutionSnapshot(**dict(row._mapping)) for row in result.fetchall()]
