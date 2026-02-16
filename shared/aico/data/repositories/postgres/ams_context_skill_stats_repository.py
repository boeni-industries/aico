"""
AMSContextSkillStatsRepository - PostgreSQL implementation

Handles CRUD operations for AMS context skill stats.
"""

from typing import Optional, List
from datetime import datetime, UTC
from sqlalchemy import select, update, delete, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from aico.data.ams.context_models import AMSContextSkillStats
from aico.data.tables import ams_context_skill_stats
from aico.data.repositories.base import Repository


class PostgresAMSContextSkillStatsRepository(Repository[AMSContextSkillStats]):
    """PostgreSQL implementation of AMS context skill stats repository."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def create(self, entity: AMSContextSkillStats) -> AMSContextSkillStats:
        """Create a new context skill stat."""
        stmt = ams_context_skill_stats.insert().values(
            user_id=entity.user_id,
            context_bucket=entity.context_bucket,
            skill_id=entity.skill_id,
            alpha=entity.alpha,
            beta=entity.beta,
            last_updated_at=entity.last_updated_at,
        )
        await self.session.execute(stmt)
        return entity
    
    async def get_by_id(self, entity_id: str) -> Optional[AMSContextSkillStats]:
        """Get context skill stat by composite ID (user_id, context_bucket, skill_id)."""
        parts = entity_id.split(":", 2)
        user_id, context_bucket, skill_id = parts[0], int(parts[1]), parts[2]
        stmt = select(ams_context_skill_stats).where(
            and_(
                ams_context_skill_stats.c.user_id == user_id,
                ams_context_skill_stats.c.context_bucket == context_bucket,
                ams_context_skill_stats.c.skill_id == skill_id
            )
        )
        result = await self.session.execute(stmt)
        row = result.fetchone()
        
        if not row:
            return None
        
        return AMSContextSkillStats(
            user_id=row.user_id,
            context_bucket=row.context_bucket,
            skill_id=row.skill_id,
            alpha=row.alpha,
            beta=row.beta,
            last_updated_at=row.last_updated_at,
        )
    
    async def update(self, entity: AMSContextSkillStats) -> AMSContextSkillStats:
        """Update an existing context skill stat."""
        stmt = (
            update(ams_context_skill_stats)
            .where(
                and_(
                    ams_context_skill_stats.c.user_id == entity.user_id,
                    ams_context_skill_stats.c.context_bucket == entity.context_bucket,
                    ams_context_skill_stats.c.skill_id == entity.skill_id
                )
            )
            .values(
                alpha=entity.alpha,
                beta=entity.beta,
                last_updated_at=datetime.now(UTC),
            )
        )
        await self.session.execute(stmt)
        return entity
    
    async def delete(self, entity_id: str) -> bool:
        """Delete a context skill stat."""
        parts = entity_id.split(":", 2)
        user_id, context_bucket, skill_id = parts[0], int(parts[1]), parts[2]
        stmt = delete(ams_context_skill_stats).where(
            and_(
                ams_context_skill_stats.c.user_id == user_id,
                ams_context_skill_stats.c.context_bucket == context_bucket,
                ams_context_skill_stats.c.skill_id == skill_id
            )
        )
        result = await self.session.execute(stmt)
        return result.rowcount > 0
    
    async def list(self, filters: Optional[dict] = None, limit: int = 100, offset: int = 0) -> List[AMSContextSkillStats]:
        """List context skill stats with optional filters."""
        stmt = select(ams_context_skill_stats)
        
        if filters:
            conditions = []
            if 'user_id' in filters:
                conditions.append(ams_context_skill_stats.c.user_id == filters['user_id'])
            if 'context_bucket' in filters:
                conditions.append(ams_context_skill_stats.c.context_bucket == filters['context_bucket'])
            
            if conditions:
                stmt = stmt.where(and_(*conditions))
        
        stmt = stmt.order_by(ams_context_skill_stats.c.last_updated_at.desc()).limit(limit).offset(offset)
        result = await self.session.execute(stmt)
        
        return [
            AMSContextSkillStats(
                user_id=row.user_id,
                context_bucket=row.context_bucket,
                skill_id=row.skill_id,
                alpha=row.alpha,
                beta=row.beta,
                last_updated_at=row.last_updated_at,
            )
            for row in result.fetchall()
        ]
    
    async def count(self, filters: Optional[dict] = None) -> int:
        """Count context skill stats with optional filters."""
        stmt = select(func.count()).select_from(ams_context_skill_stats)
        
        if filters:
            conditions = []
            if 'user_id' in filters:
                conditions.append(ams_context_skill_stats.c.user_id == filters['user_id'])
            
            if conditions:
                stmt = stmt.where(and_(*conditions))
        
        result = await self.session.execute(stmt)
        return result.scalar() or 0
    
    async def get_user_context_stats(self, user_id: str, context_bucket: int) -> List[AMSContextSkillStats]:
        """Get all skill stats for a user's context bucket."""
        stmt = select(ams_context_skill_stats).where(
            and_(
                ams_context_skill_stats.c.user_id == user_id,
                ams_context_skill_stats.c.context_bucket == context_bucket
            )
        ).order_by(ams_context_skill_stats.c.skill_id.asc())
        
        result = await self.session.execute(stmt)
        
        return [
            AMSContextSkillStats(
                user_id=row.user_id,
                context_bucket=row.context_bucket,
                skill_id=row.skill_id,
                alpha=row.alpha,
                beta=row.beta,
                last_updated_at=row.last_updated_at,
            )
            for row in result.fetchall()
        ]
