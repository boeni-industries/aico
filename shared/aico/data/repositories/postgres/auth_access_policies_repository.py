"""
AuthAccessPoliciesRepository - PostgreSQL implementation

Handles CRUD operations for auth access policies.
"""

from typing import Optional, List
from datetime import datetime, UTC
from sqlalchemy import select, update, delete, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from aico.data.auth.models import AuthAccessPolicy
from aico.data.tables import auth_access_policies
from aico.data.repositories.base import Repository


class PostgresAuthAccessPoliciesRepository(Repository[AuthAccessPolicy]):
    """PostgreSQL implementation of auth access policies repository."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def create(self, entity: AuthAccessPolicy) -> AuthAccessPolicy:
        """Create a new access policy."""
        stmt = auth_access_policies.insert().values(
            uuid=entity.uuid,
            user_uuid=entity.user_uuid,
            resource_type=entity.resource_type,
            resource_uuid=entity.resource_uuid,
            permission=entity.permission,
            is_active=entity.is_active,
            created_at=entity.created_at,
        )
        await self.session.execute(stmt)
        return entity
    
    async def get_by_id(self, entity_id: str) -> Optional[AuthAccessPolicy]:
        """Get access policy by ID."""
        stmt = select(auth_access_policies).where(auth_access_policies.c.uuid == entity_id)
        result = await self.session.execute(stmt)
        row = result.fetchone()
        
        if not row:
            return None
        
        return AuthAccessPolicy(
            uuid=row.uuid,
            user_uuid=row.user_uuid,
            resource_type=row.resource_type,
            resource_uuid=row.resource_uuid,
            permission=row.permission,
            is_active=row.is_active,
            created_at=row.created_at,
        )
    
    async def update(self, entity: AuthAccessPolicy) -> AuthAccessPolicy:
        """Update an existing access policy."""
        stmt = (
            update(auth_access_policies)
            .where(auth_access_policies.c.uuid == entity.uuid)
            .values(
                resource_uuid=entity.resource_uuid,
                permission=entity.permission,
                is_active=entity.is_active,
            )
        )
        await self.session.execute(stmt)
        return entity
    
    async def delete(self, entity_id: str) -> bool:
        """Delete an access policy."""
        stmt = delete(auth_access_policies).where(auth_access_policies.c.uuid == entity_id)
        result = await self.session.execute(stmt)
        return result.rowcount > 0
    
    async def list(self, filters: Optional[dict] = None, limit: int = 100, offset: int = 0) -> List[AuthAccessPolicy]:
        """List access policies with optional filters."""
        stmt = select(auth_access_policies)
        
        if filters:
            conditions = []
            if 'user_uuid' in filters:
                conditions.append(auth_access_policies.c.user_uuid == filters['user_uuid'])
            if 'resource_type' in filters:
                conditions.append(auth_access_policies.c.resource_type == filters['resource_type'])
            if 'is_active' in filters:
                conditions.append(auth_access_policies.c.is_active == filters['is_active'])
            
            if conditions:
                stmt = stmt.where(and_(*conditions))
        
        stmt = stmt.order_by(auth_access_policies.c.created_at.desc()).limit(limit).offset(offset)
        result = await self.session.execute(stmt)
        
        return [
            AuthAccessPolicy(
                uuid=row.uuid,
                user_uuid=row.user_uuid,
                resource_type=row.resource_type,
                resource_uuid=row.resource_uuid,
                permission=row.permission,
                is_active=row.is_active,
                created_at=row.created_at,
            )
            for row in result.fetchall()
        ]
    
    async def count(self, filters: Optional[dict] = None) -> int:
        """Count access policies with optional filters."""
        stmt = select(func.count()).select_from(auth_access_policies)
        
        if filters:
            conditions = []
            if 'user_uuid' in filters:
                conditions.append(auth_access_policies.c.user_uuid == filters['user_uuid'])
            if 'is_active' in filters:
                conditions.append(auth_access_policies.c.is_active == filters['is_active'])
            
            if conditions:
                stmt = stmt.where(and_(*conditions))
        
        result = await self.session.execute(stmt)
        return result.scalar() or 0
    
    async def get_user_policies(self, user_uuid: str, resource_type: Optional[str] = None) -> List[AuthAccessPolicy]:
        """Get active policies for a specific user."""
        conditions = [
            auth_access_policies.c.user_uuid == user_uuid,
            auth_access_policies.c.is_active == True
        ]
        
        if resource_type:
            conditions.append(auth_access_policies.c.resource_type == resource_type)
        
        stmt = select(auth_access_policies).where(and_(*conditions)).order_by(auth_access_policies.c.created_at.desc())
        
        result = await self.session.execute(stmt)
        
        return [
            AuthAccessPolicy(
                uuid=row.uuid,
                user_uuid=row.user_uuid,
                resource_type=row.resource_type,
                resource_uuid=row.resource_uuid,
                permission=row.permission,
                is_active=row.is_active,
                created_at=row.created_at,
            )
            for row in result.fetchall()
        ]
