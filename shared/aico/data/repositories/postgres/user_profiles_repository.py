"""
UserProfilesRepository - PostgreSQL implementation

Handles CRUD operations for user profiles.
"""

from typing import Optional, List
from datetime import datetime, UTC
from sqlalchemy import select, update, delete, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from aico.data.user.models import UserProfile
from aico.data.tables import user_profiles
from aico.data.repositories.base import Repository


class PostgresUserProfilesRepository(Repository[UserProfile]):
    """PostgreSQL implementation of user profiles repository."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def create(self, entity: UserProfile) -> UserProfile:
        """Create a new user profile."""
        stmt = user_profiles.insert().values(
            uuid=entity.uuid,
            full_name=entity.full_name,
            nickname=entity.nickname,
            user_type=entity.user_type,
            is_active=entity.is_active,
            primary_language=entity.primary_language,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
        )
        await self.session.execute(stmt)
        return entity
    
    async def get_by_id(self, entity_id: str) -> Optional[UserProfile]:
        """Get user profile by ID."""
        stmt = select(user_profiles).where(user_profiles.c.uuid == entity_id)
        result = await self.session.execute(stmt)
        row = result.fetchone()
        
        if not row:
            return None
        
        return UserProfile(
            uuid=row.uuid,
            full_name=row.full_name,
            nickname=row.nickname,
            user_type=row.user_type,
            is_active=row.is_active,
            primary_language=row.primary_language,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )
    
    async def update(self, entity: UserProfile) -> UserProfile:
        """Update an existing user profile."""
        stmt = (
            update(user_profiles)
            .where(user_profiles.c.uuid == entity.uuid)
            .values(
                full_name=entity.full_name,
                nickname=entity.nickname,
                user_type=entity.user_type,
                is_active=entity.is_active,
                primary_language=entity.primary_language,
                updated_at=datetime.now(UTC),
            )
        )
        await self.session.execute(stmt)
        return entity
    
    async def delete(self, entity_id: str) -> bool:
        """Delete a user (hard delete)."""
        stmt = delete(user_profiles).where(user_profiles.c.uuid == entity_id)
        result = await self.session.execute(stmt)
        return result.rowcount > 0
    
    async def list(self, filters: Optional[dict] = None, limit: int = 100, offset: int = 0) -> List[UserProfile]:
        """List user profiles with optional filters."""
        stmt = select(user_profiles)
        
        if filters:
            conditions = []
            if 'user_type' in filters:
                conditions.append(user_profiles.c.user_type == filters['user_type'])
            if 'is_active' in filters:
                conditions.append(user_profiles.c.is_active == filters['is_active'])
            
            if conditions:
                stmt = stmt.where(and_(*conditions))
        
        stmt = stmt.order_by(user_profiles.c.created_at.desc()).limit(limit).offset(offset)
        result = await self.session.execute(stmt)
        
        return [
            UserProfile(
                uuid=row.uuid,
                full_name=row.full_name,
                nickname=row.nickname,
                user_type=row.user_type,
                is_active=row.is_active,
                primary_language=row.primary_language,
                created_at=row.created_at,
                updated_at=row.updated_at,
            )
            for row in result.fetchall()
        ]
    
    async def count(self, filters: Optional[dict] = None) -> int:
        """Count user profiles with optional filters."""
        stmt = select(func.count()).select_from(user_profiles)
        
        if filters:
            conditions = []
            if 'is_active' in filters:
                conditions.append(user_profiles.c.is_active == filters['is_active'])
            
            if conditions:
                stmt = stmt.where(and_(*conditions))
        
        result = await self.session.execute(stmt)
        return result.scalar() or 0
    
    async def get_active_users(self) -> List[UserProfile]:
        """Get all active user profiles."""
        stmt = select(user_profiles).where(
            user_profiles.c.is_active == True
        ).order_by(user_profiles.c.full_name.asc())
        
        result = await self.session.execute(stmt)
        
        return [
            UserProfile(
                uuid=row.uuid,
                full_name=row.full_name,
                nickname=row.nickname,
                user_type=row.user_type,
                is_active=row.is_active,
                primary_language=row.primary_language,
                created_at=row.created_at,
                updated_at=row.updated_at,
            )
            for row in result.fetchall()
        ]
