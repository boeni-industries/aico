"""
UserSkillConfidenceRepository - PostgreSQL implementation

Handles CRUD operations for user skill confidence.
"""

from typing import Optional, List
from datetime import datetime, UTC
from sqlalchemy import select, update, delete, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from aico.ai.user.models import UserSkillConfidence
from aico.data.tables import user_skill_confidence
from aico.data.repositories.base import Repository


class PostgresUserSkillConfidenceRepository(Repository[UserSkillConfidence]):
    """PostgreSQL implementation of user skill confidence repository."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def create(self, entity: UserSkillConfidence) -> UserSkillConfidence:
        """Create a new user skill confidence record."""
        from datetime import datetime
        last_used_dt = datetime.fromisoformat(entity.last_used) if entity.last_used else None
        stmt = user_skill_confidence.insert().values(
            user_id=entity.user_id,
            skill_id=entity.skill_id,
            confidence_score=entity.confidence_level,
            usage_count=entity.usage_count,
            last_used_at=last_used_dt,
        )
        await self.session.execute(stmt)
        return entity
    
    async def get_by_id(self, entity_id: str) -> Optional[UserSkillConfidence]:
        """Get user skill confidence by composite ID (user_id, skill_id)."""
        user_id, skill_id = entity_id.split(":", 1)
        stmt = select(user_skill_confidence).where(
            and_(
                user_skill_confidence.c.user_id == user_id,
                user_skill_confidence.c.skill_id == skill_id
            )
        )
        result = await self.session.execute(stmt)
        row = result.fetchone()
        
        if not row:
            return None
        
        return UserSkillConfidence(
            user_id=row.user_id,
            skill_id=row.skill_id,
            confidence_level=row.confidence_score,
            usage_count=row.usage_count,
            last_used=row.last_used_at.isoformat() if row.last_used_at else None,
        )
    
    async def update(self, entity: UserSkillConfidence) -> UserSkillConfidence:
        """Update an existing user skill confidence record."""
        from datetime import datetime
        last_used_dt = datetime.fromisoformat(entity.last_used) if entity.last_used else None
        stmt = (
            update(user_skill_confidence)
            .where(
                and_(
                    user_skill_confidence.c.user_id == entity.user_id,
                    user_skill_confidence.c.skill_id == entity.skill_id
                )
            )
            .values(
                confidence_score=entity.confidence_level,
                usage_count=entity.usage_count,
                last_used_at=last_used_dt,
            )
        )
        await self.session.execute(stmt)
        return entity
    
    async def delete(self, entity_id: str) -> bool:
        """Delete a user skill confidence record."""
        user_id, skill_id = entity_id.split(":", 1)
        stmt = delete(user_skill_confidence).where(
            and_(
                user_skill_confidence.c.user_id == user_id,
                user_skill_confidence.c.skill_id == skill_id
            )
        )
        result = await self.session.execute(stmt)
        return result.rowcount > 0
    
    async def list(self, filters: Optional[dict] = None, limit: int = 100, offset: int = 0) -> List[UserSkillConfidence]:
        """List user skill confidence records with optional filters."""
        stmt = select(user_skill_confidence)
        
        if filters:
            conditions = []
            if 'user_id' in filters:
                conditions.append(user_skill_confidence.c.user_id == filters['user_id'])
            
            if conditions:
                stmt = stmt.where(and_(*conditions))
        
        stmt = stmt.order_by(user_skill_confidence.c.confidence_score.desc()).limit(limit).offset(offset)
        result = await self.session.execute(stmt)
        
        return [
            UserSkillConfidence(
                user_id=row.user_id,
                skill_id=row.skill_id,
                confidence_level=row.confidence_score,
                usage_count=row.usage_count,
                last_used=row.last_used_at.isoformat() if row.last_used_at else None,
            )
            for row in result.fetchall()
        ]
    
    async def count(self, filters: Optional[dict] = None) -> int:
        """Count user skill confidence records with optional filters."""
        stmt = select(func.count()).select_from(user_skill_confidence)
        
        if filters:
            conditions = []
            if 'user_id' in filters:
                conditions.append(user_skill_confidence.c.user_id == filters['user_id'])
            
            if conditions:
                stmt = stmt.where(and_(*conditions))
        
        result = await self.session.execute(stmt)
        return result.scalar() or 0
    
    async def get_user_skills(self, user_id: str) -> List[UserSkillConfidence]:
        """Get all skill confidence records for a user."""
        stmt = select(user_skill_confidence).where(
            user_skill_confidence.c.user_id == user_id
        ).order_by(user_skill_confidence.c.confidence_score.desc())
        
        result = await self.session.execute(stmt)
        
        return [
            UserSkillConfidence(
                user_id=row.user_id,
                skill_id=row.skill_id,
                confidence_level=row.confidence_score,
                usage_count=row.usage_count,
                last_used=row.last_used_at.isoformat() if row.last_used_at else None,
            )
            for row in result.fetchall()
        ]
