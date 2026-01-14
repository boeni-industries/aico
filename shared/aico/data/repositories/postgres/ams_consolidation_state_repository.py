"""
AMSConsolidationStateRepository - PostgreSQL implementation

Handles CRUD operations for AMS consolidation state.
"""

from typing import Optional, List
from datetime import datetime, UTC
from sqlalchemy import select, update, delete, func
from sqlalchemy.ext.asyncio import AsyncSession

from aico.data.ams.consolidation_models import AMSConsolidationState
from aico.data.tables import ams_consolidation_state
from aico.data.repositories.base import Repository


class PostgresAMSConsolidationStateRepository(Repository[AMSConsolidationState]):
    """PostgreSQL implementation of AMS consolidation state repository."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def create(self, entity: AMSConsolidationState) -> AMSConsolidationState:
        """Create a new consolidation state."""
        stmt = ams_consolidation_state.insert().values(
            id=entity.id,
            state_json=entity.state_json,
            updated_at=entity.updated_at,
        )
        await self.session.execute(stmt)
        return entity
    
    async def get_by_id(self, entity_id: str) -> Optional[AMSConsolidationState]:
        """Get consolidation state by ID."""
        stmt = select(ams_consolidation_state).where(ams_consolidation_state.c.id == entity_id)
        result = await self.session.execute(stmt)
        row = result.fetchone()
        
        if not row:
            return None
        
        return AMSConsolidationState(
            id=row.id,
            state_json=row.state_json,
            updated_at=row.updated_at,
        )
    
    async def update(self, entity: AMSConsolidationState) -> AMSConsolidationState:
        """Update an existing consolidation state."""
        stmt = (
            update(ams_consolidation_state)
            .where(ams_consolidation_state.c.id == entity.id)
            .values(
                state_json=entity.state_json,
                updated_at=datetime.now(UTC),
            )
        )
        await self.session.execute(stmt)
        return entity
    
    async def delete(self, entity_id: str) -> bool:
        """Delete a consolidation state."""
        stmt = delete(ams_consolidation_state).where(ams_consolidation_state.c.id == entity_id)
        result = await self.session.execute(stmt)
        return result.rowcount > 0
    
    async def list(self, filters: Optional[dict] = None, limit: int = 100, offset: int = 0) -> List[AMSConsolidationState]:
        """List consolidation states with optional filters."""
        stmt = select(ams_consolidation_state)
        stmt = stmt.order_by(ams_consolidation_state.c.updated_at.desc()).limit(limit).offset(offset)
        result = await self.session.execute(stmt)
        
        return [
            AMSConsolidationState(
                id=row.id,
                state_json=row.state_json,
                updated_at=row.updated_at,
            )
            for row in result.fetchall()
        ]
    
    async def count(self, filters: Optional[dict] = None) -> int:
        """Count consolidation states with optional filters."""
        stmt = select(func.count()).select_from(ams_consolidation_state)
        result = await self.session.execute(stmt)
        return result.scalar() or 0
    
    async def get_latest(self) -> Optional[AMSConsolidationState]:
        """Get the most recently updated consolidation state."""
        stmt = select(ams_consolidation_state).order_by(ams_consolidation_state.c.updated_at.desc()).limit(1)
        result = await self.session.execute(stmt)
        row = result.fetchone()
        
        if not row:
            return None
        
        return AMSConsolidationState(
            id=row.id,
            state_json=row.state_json,
            updated_at=row.updated_at,
        )
