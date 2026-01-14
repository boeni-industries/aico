"""
UserRelationshipsRepository - PostgreSQL implementation

Handles CRUD operations for user relationships.
"""

from typing import Optional, List
from datetime import datetime, UTC
from sqlalchemy import select, update, delete, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from aico.data.user.models import UserRelationship
from aico.data.tables import user_relationships
from aico.data.repositories.base import Repository


class PostgresUserRelationshipsRepository(Repository[UserRelationship]):
    """PostgreSQL implementation of user relationships repository."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def create(self, entity: UserRelationship) -> UserRelationship:
        """Create a new user relationship."""
        stmt = user_relationships.insert().values(
            uuid=entity.uuid,
            user_uuid=entity.user_uuid,
            related_user_uuid=entity.related_user_uuid,
            relationship_type=entity.relationship_type,
            is_active=entity.is_active,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
        )
        await self.session.execute(stmt)
        return entity
    
    async def get_by_id(self, entity_id: str) -> Optional[UserRelationship]:
        """Get user relationship by ID."""
        stmt = select(user_relationships).where(user_relationships.c.uuid == entity_id)
        result = await self.session.execute(stmt)
        row = result.fetchone()
        
        if not row:
            return None
        
        return UserRelationship(
            uuid=row.uuid,
            user_uuid=row.user_uuid,
            related_user_uuid=row.related_user_uuid,
            relationship_type=row.relationship_type,
            is_active=row.is_active,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )
    
    async def update(self, entity: UserRelationship) -> UserRelationship:
        """Update an existing user relationship."""
        stmt = (
            update(user_relationships)
            .where(user_relationships.c.uuid == entity.uuid)
            .values(
                is_active=entity.is_active,
                updated_at=datetime.now(UTC),
            )
        )
        await self.session.execute(stmt)
        return entity
    
    async def delete(self, entity_id: str) -> bool:
        """Delete a user relationship."""
        stmt = delete(user_relationships).where(user_relationships.c.uuid == entity_id)
        result = await self.session.execute(stmt)
        return result.rowcount > 0
    
    async def list(self, filters: Optional[dict] = None, limit: int = 100, offset: int = 0) -> List[UserRelationship]:
        """List user relationships with optional filters."""
        stmt = select(user_relationships)
        
        if filters:
            conditions = []
            if 'user_uuid' in filters:
                conditions.append(user_relationships.c.user_uuid == filters['user_uuid'])
            if 'is_active' in filters:
                conditions.append(user_relationships.c.is_active == filters['is_active'])
            if 'relationship_type' in filters:
                conditions.append(user_relationships.c.relationship_type == filters['relationship_type'])
            
            if conditions:
                stmt = stmt.where(and_(*conditions))
        
        stmt = stmt.order_by(user_relationships.c.created_at.desc()).limit(limit).offset(offset)
        result = await self.session.execute(stmt)
        
        return [
            UserRelationship(
                uuid=row.uuid,
                user_uuid=row.user_uuid,
                related_user_uuid=row.related_user_uuid,
                relationship_type=row.relationship_type,
                is_active=row.is_active,
                created_at=row.created_at,
                updated_at=row.updated_at,
            )
            for row in result.fetchall()
        ]
    
    async def count(self, filters: Optional[dict] = None) -> int:
        """Count user relationships with optional filters."""
        stmt = select(func.count()).select_from(user_relationships)
        
        if filters:
            conditions = []
            if 'user_uuid' in filters:
                conditions.append(user_relationships.c.user_uuid == filters['user_uuid'])
            
            if conditions:
                stmt = stmt.where(and_(*conditions))
        
        result = await self.session.execute(stmt)
        return result.scalar() or 0
    
    async def get_user_relationships(self, user_uuid: str) -> List[UserRelationship]:
        """Get all relationships for a user."""
        stmt = select(user_relationships).where(
            user_relationships.c.user_uuid == user_uuid
        ).order_by(user_relationships.c.created_at.desc())
        
        result = await self.session.execute(stmt)
        
        return [
            UserRelationship(
                uuid=row.uuid,
                user_uuid=row.user_uuid,
                related_user_uuid=row.related_user_uuid,
                relationship_type=row.relationship_type,
                is_active=row.is_active,
                created_at=row.created_at,
                updated_at=row.updated_at,
            )
            for row in result.fetchall()
        ]
