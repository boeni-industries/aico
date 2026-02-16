"""
PostgreSQL User Repository

Repository implementation for user_profiles table using SQLAlchemy Core.
"""

from typing import Optional, List, Dict, Any
from datetime import datetime, UTC
from sqlalchemy import select, insert, update, delete, func
from sqlalchemy.ext.asyncio import AsyncSession

from aico.data.repositories.base import Repository
from aico.data.tables import user_profiles
from aico.data.user.models import UserProfile
from aico.core.logging import get_logger

logger = get_logger("shared.data.repositories.postgres.user")


class PostgresUserRepository(Repository[UserProfile]):
    """
    PostgreSQL implementation of User repository.
    
    Handles CRUD operations for user_profiles table using SQLAlchemy Core.
    """
    
    def __init__(self, session: AsyncSession):
        """
        Initialize repository with database session.
        
        Args:
            session: SQLAlchemy async session
        """
        self.session = session
    
    async def create(self, entity: UserProfile) -> UserProfile:
        """
        Create a new user.
        
        Args:
            entity: UserProfile instance
            
        Returns:
            Created UserProfile with timestamps populated
        """
        now = datetime.now(UTC)
        
        stmt = insert(user_profiles).values(
            uuid=entity.uuid,
            full_name=entity.full_name,
            nickname=entity.nickname,
            user_type=entity.user_type,
            is_active=entity.is_active,
            primary_language=entity.primary_language,
            created_at=now,
            updated_at=now,
        ).returning(user_profiles)
        
        result = await self.session.execute(stmt)
        row = result.fetchone()
        
        logger.info(f"Created user: {entity.uuid}", extra={
            "user_uuid": entity.uuid,
            "full_name": entity.full_name,
        })
        
        return self._row_to_user(row)
    
    async def get_by_id(self, id: str) -> Optional[UserProfile]:
        """
        Get user by UUID.
        
        Args:
            id: User UUID
            
        Returns:
            UserProfile if found, None otherwise
        """
        stmt = select(user_profiles).where(
            user_profiles.c.uuid == id
        )
        
        result = await self.session.execute(stmt)
        row = result.fetchone()
        
        if row is None:
            return None
        
        return self._row_to_user(row)
    
    async def update(self, entity: UserProfile) -> UserProfile:
        """
        Update existing user.
        
        Args:
            entity: UserProfile with updated values
            
        Returns:
            Updated UserProfile
        """
        now = datetime.now(UTC)
        
        stmt = update(user_profiles).where(
            user_profiles.c.uuid == entity.uuid
        ).values(
            full_name=entity.full_name,
            nickname=entity.nickname,
            user_type=entity.user_type,
            is_active=entity.is_active,
            primary_language=entity.primary_language,
            updated_at=now,
        ).returning(user_profiles)
        
        result = await self.session.execute(stmt)
        row = result.fetchone()
        
        if row is None:
            raise ValueError(f"User not found: {entity.uuid}")
        
        logger.info(f"Updated user: {entity.uuid}")
        
        return self._row_to_user(row)
    
    async def delete(self, entity_id: str) -> bool:
        """Delete a user (hard delete)."""
        stmt = delete(user_profiles).where(user_profiles.c.uuid == entity_id)
        result = await self.session.execute(stmt)
        if result.rowcount == 0:
            raise ValueError(f"User not found: {entity_id}")
        logger.info(f"Deleted user: {entity_id}")
        return True
    
    async def list(self, filters: Optional[Dict[str, Any]] = None, limit: Optional[int] = None) -> List[UserProfile]:
        """
        List users with optional filtering.
        
        Args:
            filters: Optional filters (e.g., {'user_type': 'parent', 'is_active': True})
            limit: Optional maximum results
            
        Returns:
            List of UserProfile instances
        """
        stmt = select(user_profiles)
        
        # Apply filters
        if filters:
            if 'user_type' in filters:
                stmt = stmt.where(user_profiles.c.user_type == filters['user_type'])
            if 'primary_language' in filters:
                stmt = stmt.where(user_profiles.c.primary_language == filters['primary_language'])
            if 'is_active' in filters:
                stmt = stmt.where(user_profiles.c.is_active == filters['is_active'])
        
        # Apply limit
        if limit:
            stmt = stmt.limit(limit)
        
        # Order by created_at descending
        stmt = stmt.order_by(user_profiles.c.created_at.desc())
        
        result = await self.session.execute(stmt)
        rows = result.fetchall()
        
        return [self._row_to_user(row) for row in rows]
    
    async def count(self, filters: Optional[Dict[str, Any]] = None) -> int:
        """
        Count users matching filters.
        
        Args:
            filters: Optional filters
            
        Returns:
            Number of users
        """
        stmt = select(func.count()).select_from(user_profiles)
        
        # Apply filters
        if filters:
            if 'user_type' in filters:
                stmt = stmt.where(user_profiles.c.user_type == filters['user_type'])
            if 'primary_language' in filters:
                stmt = stmt.where(user_profiles.c.primary_language == filters['primary_language'])
            if 'is_active' in filters:
                stmt = stmt.where(user_profiles.c.is_active == filters['is_active'])
        
        result = await self.session.execute(stmt)
        return result.scalar()
    
    async def get_by_full_name(self, full_name: str) -> Optional[UserProfile]:
        """
        Get user by full name (case-insensitive).
        
        Args:
            full_name: User's full name
            
        Returns:
            UserProfile if found, None otherwise
        """
        stmt = select(user_profiles).where(
            func.lower(user_profiles.c.full_name) == full_name.lower(),
            user_profiles.c.is_active == True
        )
        
        result = await self.session.execute(stmt)
        row = result.fetchone()
        
        if row is None:
            return None
        
        return self._row_to_user(row)
    
    def _row_to_user(self, row) -> UserProfile:
        """
        Map database row to UserProfile domain model.
        
        Args:
            row: SQLAlchemy Row object
            
        Returns:
            UserProfile instance
        """
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
