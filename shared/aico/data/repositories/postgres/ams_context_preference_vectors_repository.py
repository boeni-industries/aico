"""
AMSContextPreferenceVectorsRepository - PostgreSQL implementation

Handles CRUD operations for AMS context preference vectors.
"""

from typing import Optional, List
from datetime import datetime, UTC
from sqlalchemy import select, update, delete, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from aico.ai.ams.models import AMSContextPreferenceVector
from aico.data.tables import ams_context_preference_vectors
from aico.data.repositories.base import Repository


class PostgresAMSContextPreferenceVectorsRepository(Repository[AMSContextPreferenceVector]):
    """PostgreSQL implementation of AMS context preference vectors repository."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def create(self, entity: AMSContextPreferenceVector) -> AMSContextPreferenceVector:
        """Create a new context preference vector."""
        stmt = ams_context_preference_vectors.insert().values(
            user_id=entity.user_id,
            context_bucket=entity.context_bucket,
            dimensions=entity.dimensions,
            last_updated_at=entity.last_updated_at,
        )
        await self.session.execute(stmt)
        return entity
    
    async def get_by_id(self, entity_id: str) -> Optional[AMSContextPreferenceVector]:
        """Get context preference vector by composite ID (user_id, context_bucket)."""
        user_id, context_bucket = entity_id.split(":", 1)
        stmt = select(ams_context_preference_vectors).where(
            and_(
                ams_context_preference_vectors.c.user_id == user_id,
                ams_context_preference_vectors.c.context_bucket == int(context_bucket)
            )
        )
        result = await self.session.execute(stmt)
        row = result.fetchone()
        
        if not row:
            return None
        
        return AMSContextPreferenceVector(
            user_id=row.user_id,
            context_bucket=row.context_bucket,
            dimensions=row.dimensions,
            last_updated_at=row.last_updated_at,
        )
    
    async def update(self, entity: AMSContextPreferenceVector) -> AMSContextPreferenceVector:
        """Update an existing context preference vector."""
        stmt = (
            update(ams_context_preference_vectors)
            .where(
                and_(
                    ams_context_preference_vectors.c.user_id == entity.user_id,
                    ams_context_preference_vectors.c.context_bucket == entity.context_bucket
                )
            )
            .values(
                dimensions=entity.dimensions,
                last_updated_at=datetime.now(UTC),
            )
        )
        await self.session.execute(stmt)
        return entity
    
    async def delete(self, entity_id: str) -> bool:
        """Delete a context preference vector."""
        user_id, context_bucket = entity_id.split(":", 1)
        stmt = delete(ams_context_preference_vectors).where(
            and_(
                ams_context_preference_vectors.c.user_id == user_id,
                ams_context_preference_vectors.c.context_bucket == int(context_bucket)
            )
        )
        result = await self.session.execute(stmt)
        return result.rowcount > 0
    
    async def list(self, filters: Optional[dict] = None, limit: int = 100, offset: int = 0) -> List[AMSContextPreferenceVector]:
        """List context preference vectors with optional filters."""
        stmt = select(ams_context_preference_vectors)
        
        if filters:
            conditions = []
            if 'user_id' in filters:
                conditions.append(ams_context_preference_vectors.c.user_id == filters['user_id'])
            
            if conditions:
                stmt = stmt.where(and_(*conditions))
        
        stmt = stmt.order_by(ams_context_preference_vectors.c.last_updated_at.desc()).limit(limit).offset(offset)
        result = await self.session.execute(stmt)
        
        return [
            AMSContextPreferenceVector(
                user_id=row.user_id,
                context_bucket=row.context_bucket,
                dimensions=row.dimensions,
                last_updated_at=row.last_updated_at,
            )
            for row in result.fetchall()
        ]
    
    async def count(self, filters: Optional[dict] = None) -> int:
        """Count context preference vectors with optional filters."""
        stmt = select(func.count()).select_from(ams_context_preference_vectors)
        
        if filters:
            conditions = []
            if 'user_id' in filters:
                conditions.append(ams_context_preference_vectors.c.user_id == filters['user_id'])
            
            if conditions:
                stmt = stmt.where(and_(*conditions))
        
        result = await self.session.execute(stmt)
        return result.scalar() or 0
    
    async def get_user_vectors(self, user_id: str) -> List[AMSContextPreferenceVector]:
        """Get all context preference vectors for a user."""
        stmt = select(ams_context_preference_vectors).where(
            ams_context_preference_vectors.c.user_id == user_id
        ).order_by(ams_context_preference_vectors.c.context_bucket.asc())
        
        result = await self.session.execute(stmt)
        
        return [
            AMSContextPreferenceVector(
                user_id=row.user_id,
                context_bucket=row.context_bucket,
                dimensions=row.dimensions,
                last_updated_at=row.last_updated_at,
            )
            for row in result.fetchall()
        ]
