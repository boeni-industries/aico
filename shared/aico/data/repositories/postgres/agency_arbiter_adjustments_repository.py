"""
AgencyArbiterAdjustmentsRepository - PostgreSQL implementation

Handles CRUD operations for agency arbiter adjustments.
"""

from typing import Optional, List
from datetime import datetime, UTC
from sqlalchemy import select, update, delete, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from aico.ai.agency.models import AgencyArbiterAdjustment
from aico.data.tables import agency_arbiter_adjustments
from aico.data.repositories.base import Repository


class PostgresAgencyArbiterAdjustmentsRepository(Repository[AgencyArbiterAdjustment]):
    """PostgreSQL implementation of agency arbiter adjustments repository."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def create(self, entity: AgencyArbiterAdjustment) -> AgencyArbiterAdjustment:
        """Create a new arbiter adjustment."""
        stmt = agency_arbiter_adjustments.insert().values(
            adjustment_key=entity.adjustment_key,
            adjustment_value=entity.adjustment_value,
            lesson_id=entity.lesson_id,
            user_id=entity.user_id,
            applied_at=entity.applied_at,
            confidence=entity.confidence,
            active=entity.active,
            notes=entity.notes,
        )
        await self.session.execute(stmt)
        return entity
    
    async def get_by_id(self, entity_id: str) -> Optional[AgencyArbiterAdjustment]:
        """Get arbiter adjustment by ID."""
        stmt = select(agency_arbiter_adjustments).where(agency_arbiter_adjustments.c.adjustment_key == entity_id)
        result = await self.session.execute(stmt)
        row = result.fetchone()
        
        if not row:
            return None
        
        return AgencyArbiterAdjustment(
            adjustment_key=row.adjustment_key,
            adjustment_value=row.adjustment_value,
            lesson_id=row.lesson_id,
            user_id=row.user_id,
            applied_at=row.applied_at,
            confidence=row.confidence,
            active=row.active,
            notes=row.notes,
        )
    
    async def update(self, entity: AgencyArbiterAdjustment) -> AgencyArbiterAdjustment:
        """Update an existing arbiter adjustment."""
        stmt = (
            update(agency_arbiter_adjustments)
            .where(agency_arbiter_adjustments.c.adjustment_key == entity.adjustment_key)
            .values(
                adjustment_value=entity.adjustment_value,
                confidence=entity.confidence,
                active=entity.active,
                notes=entity.notes,
            )
        )
        await self.session.execute(stmt)
        return entity
    
    async def delete(self, entity_id: str) -> bool:
        """Delete an arbiter adjustment."""
        stmt = delete(agency_arbiter_adjustments).where(agency_arbiter_adjustments.c.adjustment_key == entity_id)
        result = await self.session.execute(stmt)
        return result.rowcount > 0
    
    async def list(self, filters: Optional[dict] = None, limit: int = 100, offset: int = 0) -> List[AgencyArbiterAdjustment]:
        """List arbiter adjustments with optional filters."""
        stmt = select(agency_arbiter_adjustments)
        
        if filters:
            conditions = []
            if 'user_id' in filters:
                conditions.append(agency_arbiter_adjustments.c.user_id == filters['user_id'])
            if 'active' in filters:
                conditions.append(agency_arbiter_adjustments.c.active == filters['active'])
            if 'lesson_id' in filters:
                conditions.append(agency_arbiter_adjustments.c.lesson_id == filters['lesson_id'])
            
            if conditions:
                stmt = stmt.where(and_(*conditions))
        
        stmt = stmt.order_by(agency_arbiter_adjustments.c.applied_at.desc()).limit(limit).offset(offset)
        result = await self.session.execute(stmt)
        
        return [
            AgencyArbiterAdjustment(
                adjustment_key=row.adjustment_key,
                adjustment_value=row.adjustment_value,
                lesson_id=row.lesson_id,
                user_id=row.user_id,
                applied_at=row.applied_at,
                confidence=row.confidence,
                active=row.active,
                notes=row.notes,
            )
            for row in result.fetchall()
        ]
    
    async def count(self, filters: Optional[dict] = None) -> int:
        """Count arbiter adjustments with optional filters."""
        stmt = select(func.count()).select_from(agency_arbiter_adjustments)
        
        if filters:
            conditions = []
            if 'user_id' in filters:
                conditions.append(agency_arbiter_adjustments.c.user_id == filters['user_id'])
            if 'active' in filters:
                conditions.append(agency_arbiter_adjustments.c.active == filters['active'])
            
            if conditions:
                stmt = stmt.where(and_(*conditions))
        
        result = await self.session.execute(stmt)
        return result.scalar() or 0
    
    async def get_active_adjustments(self, user_id: Optional[str] = None) -> List[AgencyArbiterAdjustment]:
        """Get active arbiter adjustments."""
        conditions = [agency_arbiter_adjustments.c.active == True]
        if user_id:
            conditions.append(agency_arbiter_adjustments.c.user_id == user_id)
        
        stmt = select(agency_arbiter_adjustments).where(
            and_(*conditions)
        ).order_by(agency_arbiter_adjustments.c.applied_at.desc())
        
        result = await self.session.execute(stmt)
        
        return [
            AgencyArbiterAdjustment(
                adjustment_key=row.adjustment_key,
                adjustment_value=row.adjustment_value,
                lesson_id=row.lesson_id,
                user_id=row.user_id,
                applied_at=row.applied_at,
                confidence=row.confidence,
                active=row.active,
                notes=row.notes,
            )
            for row in result.fetchall()
        ]
