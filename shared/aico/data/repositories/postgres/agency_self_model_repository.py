"""PostgreSQL repository for agency_self_model."""

from typing import List, Optional
from datetime import datetime
from sqlalchemy import select, insert, update, delete, func
from sqlalchemy.ext.asyncio import AsyncSession
from aico.data.tables import agency_self_model
from aico.ai.agency.models import AgencySelfModel


class PostgresAgencySelfModelRepository:
    """PostgreSQL repository for agency_self_model."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def create(self, entity: AgencySelfModel) -> AgencySelfModel:
        """Create a new self model entry."""
        values = entity.__dict__.copy()
        for key in ['window_start', 'window_end', 'last_updated', 'created_at']:
            if isinstance(values.get(key), datetime):
                values[key] = values[key]
        
        stmt = insert(agency_self_model).values(**values).returning(agency_self_model)
        result = await self.session.execute(stmt)
        await self.session.commit()
        row = result.fetchone()
        return AgencySelfModel(**dict(row._mapping))
    
    async def get_by_id(self, model_id: str) -> Optional[AgencySelfModel]:
        """Get self model by ID."""
        stmt = select(agency_self_model).where(agency_self_model.c.model_id == model_id)
        result = await self.session.execute(stmt)
        row = result.fetchone()
        return AgencySelfModel(**dict(row._mapping)) if row else None
    
    async def update(self, model_id: str, entity: AgencySelfModel) -> Optional[AgencySelfModel]:
        """Update self model."""
        values = entity.__dict__.copy()
        for key in ['last_updated']:
            if isinstance(values.get(key), datetime):
                values[key] = values[key]
        
        stmt = (
            update(agency_self_model)
            .where(agency_self_model.c.model_id == model_id)
            .values(**values)
            .returning(agency_self_model)
        )
        result = await self.session.execute(stmt)
        await self.session.commit()
        row = result.fetchone()
        return AgencySelfModel(**dict(row._mapping)) if row else None
    
    async def delete(self, model_id: str) -> bool:
        """Delete self model."""
        stmt = delete(agency_self_model).where(agency_self_model.c.model_id == model_id)
        result = await self.session.execute(stmt)
        await self.session.commit()
        return result.rowcount > 0
    
    async def list(self, limit: int = 100, offset: int = 0) -> List[AgencySelfModel]:
        """List self models."""
        stmt = select(agency_self_model).limit(limit).offset(offset)
        result = await self.session.execute(stmt)
        return [AgencySelfModel(**dict(row._mapping)) for row in result.fetchall()]
    
    async def count(self) -> int:
        """Count total self models."""
        stmt = select(func.count()).select_from(agency_self_model)
        result = await self.session.execute(stmt)
        return result.scalar() or 0
    
    async def get_user_models(self, user_id: str, entity_type: Optional[str] = None) -> List[AgencySelfModel]:
        """Get all self models for a user, optionally filtered by entity type."""
        stmt = select(agency_self_model).where(agency_self_model.c.user_id == user_id)
        if entity_type:
            stmt = stmt.where(agency_self_model.c.entity_type == entity_type)
        stmt = stmt.order_by(agency_self_model.c.last_updated.desc())
        result = await self.session.execute(stmt)
        return [AgencySelfModel(**dict(row._mapping)) for row in result.fetchall()]
