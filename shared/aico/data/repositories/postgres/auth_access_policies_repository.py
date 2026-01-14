"""
AuthAccessPoliciesRepository - PostgreSQL implementation

Handles CRUD operations for auth access policies.
"""

from typing import Optional, List
from datetime import datetime, UTC
from sqlalchemy import select, update, delete, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from aico.data.auth.access_models import AuthAccessPolicy
from aico.data.tables import auth_access_policies
from aico.data.repositories.base import Repository


class PostgresAuthAccessPoliciesRepository(Repository[AuthAccessPolicy]):
    """PostgreSQL implementation of auth access policies repository."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def create(self, entity: AuthAccessPolicy) -> AuthAccessPolicy:
        """Create a new access policy."""
        stmt = auth_access_policies.insert().values(
            policy_id=entity.policy_id,
            resource_type=entity.resource_type,
            action=entity.action,
            effect=entity.effect,
            conditions_json=entity.conditions_json,
            priority=entity.priority,
            enabled=entity.enabled,
        )
        await self.session.execute(stmt)
        return entity
    
    async def get_by_id(self, entity_id: str) -> Optional[AuthAccessPolicy]:
        """Get access policy by ID."""
        stmt = select(auth_access_policies).where(auth_access_policies.c.policy_id == entity_id)
        result = await self.session.execute(stmt)
        row = result.fetchone()
        
        if not row:
            return None
        
        return AuthAccessPolicy(
            policy_id=row.policy_id,
            resource_type=row.resource_type,
            action=row.action,
            effect=row.effect,
            conditions_json=row.conditions_json,
            priority=row.priority,
            enabled=row.enabled,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )
    
    async def update(self, entity: AuthAccessPolicy) -> AuthAccessPolicy:
        """Update an existing access policy."""
        stmt = (
            update(auth_access_policies)
            .where(auth_access_policies.c.policy_id == entity.policy_id)
            .values(
                effect=entity.effect,
                conditions_json=entity.conditions_json,
                priority=entity.priority,
                enabled=entity.enabled,
                updated_at=datetime.now(UTC),
            )
        )
        await self.session.execute(stmt)
        return entity
    
    async def delete(self, entity_id: str) -> bool:
        """Delete an access policy."""
        stmt = delete(auth_access_policies).where(auth_access_policies.c.policy_id == entity_id)
        result = await self.session.execute(stmt)
        return result.rowcount > 0
    
    async def list(self, filters: Optional[dict] = None, limit: int = 100, offset: int = 0) -> List[AuthAccessPolicy]:
        """List access policies with optional filters."""
        stmt = select(auth_access_policies)
        
        if filters:
            conditions = []
            if 'resource_type' in filters:
                conditions.append(auth_access_policies.c.resource_type == filters['resource_type'])
            if 'action' in filters:
                conditions.append(auth_access_policies.c.action == filters['action'])
            if 'enabled' in filters:
                conditions.append(auth_access_policies.c.enabled == filters['enabled'])
            
            if conditions:
                stmt = stmt.where(and_(*conditions))
        
        stmt = stmt.order_by(auth_access_policies.c.priority.asc()).limit(limit).offset(offset)
        result = await self.session.execute(stmt)
        
        return [
            AuthAccessPolicy(
                policy_id=row.policy_id,
                resource_type=row.resource_type,
                action=row.action,
                effect=row.effect,
                conditions_json=row.conditions_json,
                priority=row.priority,
                enabled=row.enabled,
                created_at=row.created_at,
                updated_at=row.updated_at,
            )
            for row in result.fetchall()
        ]
    
    async def count(self, filters: Optional[dict] = None) -> int:
        """Count access policies with optional filters."""
        stmt = select(func.count()).select_from(auth_access_policies)
        
        if filters:
            conditions = []
            if 'enabled' in filters:
                conditions.append(auth_access_policies.c.enabled == filters['enabled'])
            
            if conditions:
                stmt = stmt.where(and_(*conditions))
        
        result = await self.session.execute(stmt)
        return result.scalar() or 0
    
    async def get_active_policies(self, resource_type: str, action: str) -> List[AuthAccessPolicy]:
        """Get active policies for a specific resource and action."""
        stmt = select(auth_access_policies).where(
            and_(
                auth_access_policies.c.resource_type == resource_type,
                auth_access_policies.c.action == action,
                auth_access_policies.c.enabled == True
            )
        ).order_by(auth_access_policies.c.priority.asc())
        
        result = await self.session.execute(stmt)
        
        return [
            AuthAccessPolicy(
                policy_id=row.policy_id,
                resource_type=row.resource_type,
                action=row.action,
                effect=row.effect,
                conditions_json=row.conditions_json,
                priority=row.priority,
                enabled=row.enabled,
                created_at=row.created_at,
                updated_at=row.updated_at,
            )
            for row in result.fetchall()
        ]
