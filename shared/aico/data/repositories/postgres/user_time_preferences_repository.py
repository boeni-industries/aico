"""
UserTimePreferencesRepository - PostgreSQL implementation

Handles CRUD operations for user time preferences.
"""

from typing import Optional, List
from datetime import datetime, UTC
from sqlalchemy import select, update, delete, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from aico.data.user.relationship_models import UserTimePreference
from aico.data.tables import user_time_preferences
from aico.data.repositories.base import Repository


class PostgresUserTimePreferencesRepository(Repository[UserTimePreference]):
    """PostgreSQL implementation of user time preferences repository."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def create(self, entity: UserTimePreference) -> UserTimePreference:
        """Create a new user time preference."""
        stmt = user_time_preferences.insert().values(
            preference_id=entity.preference_id,
            user_id=entity.user_id,
            time_period=entity.time_period,
            productivity_score=entity.productivity_score,
            active=entity.active,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
        )
        await self.session.execute(stmt)
        return entity
    
    async def get_by_id(self, entity_id: str) -> Optional[UserTimePreference]:
        """Get user time preference by ID."""
        stmt = select(user_time_preferences).where(user_time_preferences.c.preference_id == entity_id)
        result = await self.session.execute(stmt)
        row = result.fetchone()
        
        if not row:
            return None
        
        return UserTimePreference(
            preference_id=row.preference_id,
            user_id=row.user_id,
            time_period=row.time_period,
            productivity_score=row.productivity_score,
            active=row.active,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )
    
    async def update(self, entity: UserTimePreference) -> UserTimePreference:
        """Update an existing user time preference."""
        stmt = (
            update(user_time_preferences)
            .where(user_time_preferences.c.preference_id == entity.preference_id)
            .values(
                productivity_score=entity.productivity_score,
                active=entity.active,
                updated_at=datetime.now(UTC).isoformat(),
            )
        )
        await self.session.execute(stmt)
        return entity
    
    async def delete(self, entity_id: str) -> bool:
        """Delete a user time preference."""
        stmt = delete(user_time_preferences).where(user_time_preferences.c.preference_id == entity_id)
        result = await self.session.execute(stmt)
        return result.rowcount > 0
    
    async def list(self, filters: Optional[dict] = None, limit: int = 100, offset: int = 0) -> List[UserTimePreference]:
        """List user time preferences with optional filters."""
        stmt = select(user_time_preferences)
        
        if filters:
            conditions = []
            if 'user_id' in filters:
                conditions.append(user_time_preferences.c.user_id == filters['user_id'])
            if 'active' in filters:
                conditions.append(user_time_preferences.c.active == filters['active'])
            
            if conditions:
                stmt = stmt.where(and_(*conditions))
        
        stmt = stmt.order_by(user_time_preferences.c.productivity_score.desc()).limit(limit).offset(offset)
        result = await self.session.execute(stmt)
        
        return [
            UserTimePreference(
                preference_id=row.preference_id,
                user_id=row.user_id,
                time_period=row.time_period,
                productivity_score=row.productivity_score,
                active=row.active,
                created_at=row.created_at,
                updated_at=row.updated_at,
            )
            for row in result.fetchall()
        ]
    
    async def count(self, filters: Optional[dict] = None) -> int:
        """Count user time preferences with optional filters."""
        stmt = select(func.count()).select_from(user_time_preferences)
        
        if filters:
            conditions = []
            if 'user_id' in filters:
                conditions.append(user_time_preferences.c.user_id == filters['user_id'])
            
            if conditions:
                stmt = stmt.where(and_(*conditions))
        
        result = await self.session.execute(stmt)
        return result.scalar() or 0
    
    async def get_user_preferences(self, user_id: str) -> List[UserTimePreference]:
        """Get all time preferences for a user."""
        stmt = select(user_time_preferences).where(
            user_time_preferences.c.user_id == user_id
        ).order_by(user_time_preferences.c.productivity_score.desc())
        
        result = await self.session.execute(stmt)
        
        return [
            UserTimePreference(
                preference_id=row.preference_id,
                user_id=row.user_id,
                time_period=row.time_period,
                productivity_score=row.productivity_score,
                active=row.active,
                created_at=row.created_at,
                updated_at=row.updated_at,
            )
            for row in result.fetchall()
        ]
