"""
AuthUserCredentialsRepository - PostgreSQL implementation

Handles CRUD operations for auth user credentials.
"""

from typing import Optional, List
from datetime import datetime, UTC
from sqlalchemy import select, update, delete, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from aico.data.auth.credentials_models import AuthUserCredentials
from aico.data.tables import auth_user_credentials
from aico.data.repositories.base import Repository


class PostgresAuthUserCredentialsRepository(Repository[AuthUserCredentials]):
    """PostgreSQL implementation of auth user credentials repository."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def create(self, entity: AuthUserCredentials) -> AuthUserCredentials:
        """Create new user credentials."""
        stmt = auth_user_credentials.insert().values(
            uuid=entity.uuid,
            user_uuid=entity.user_uuid,
            pin_hash=entity.pin_hash,
            failed_attempts=entity.failed_attempts,
            locked_until=entity.locked_until,
            last_login=entity.last_login,
        )
        await self.session.execute(stmt)
        return entity
    
    async def get_by_id(self, entity_id: str) -> Optional[AuthUserCredentials]:
        """Get user credentials by ID."""
        stmt = select(auth_user_credentials).where(auth_user_credentials.c.uuid == entity_id)
        result = await self.session.execute(stmt)
        row = result.fetchone()
        
        if not row:
            return None
        
        return AuthUserCredentials(
            uuid=row.uuid,
            user_uuid=row.user_uuid,
            pin_hash=row.pin_hash,
            failed_attempts=row.failed_attempts,
            locked_until=row.locked_until,
            last_login=row.last_login,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )
    
    async def update(self, entity: AuthUserCredentials) -> AuthUserCredentials:
        """Update existing user credentials."""
        stmt = (
            update(auth_user_credentials)
            .where(auth_user_credentials.c.uuid == entity.uuid)
            .values(
                pin_hash=entity.pin_hash,
                failed_attempts=entity.failed_attempts,
                locked_until=entity.locked_until,
                last_login=entity.last_login,
                updated_at=datetime.now(UTC),
            )
        )
        await self.session.execute(stmt)
        return entity
    
    async def delete(self, entity_id: str) -> bool:
        """Delete user credentials."""
        stmt = delete(auth_user_credentials).where(auth_user_credentials.c.uuid == entity_id)
        result = await self.session.execute(stmt)
        return result.rowcount > 0
    
    async def list(self, filters: Optional[dict] = None, limit: int = 100, offset: int = 0) -> List[AuthUserCredentials]:
        """List user credentials with optional filters."""
        stmt = select(auth_user_credentials)
        
        if filters:
            conditions = []
            if 'user_uuid' in filters:
                conditions.append(auth_user_credentials.c.user_uuid == filters['user_uuid'])
            
            if conditions:
                stmt = stmt.where(and_(*conditions))
        
        stmt = stmt.order_by(auth_user_credentials.c.created_at.desc()).limit(limit).offset(offset)
        result = await self.session.execute(stmt)
        
        return [
            AuthUserCredentials(
                uuid=row.uuid,
                user_uuid=row.user_uuid,
                pin_hash=row.pin_hash,
                failed_attempts=row.failed_attempts,
                locked_until=row.locked_until,
                last_login=row.last_login,
                created_at=row.created_at,
                updated_at=row.updated_at,
            )
            for row in result.fetchall()
        ]
    
    async def count(self, filters: Optional[dict] = None) -> int:
        """Count user credentials with optional filters."""
        stmt = select(func.count()).select_from(auth_user_credentials)
        
        if filters:
            conditions = []
            if 'user_uuid' in filters:
                conditions.append(auth_user_credentials.c.user_uuid == filters['user_uuid'])
            
            if conditions:
                stmt = stmt.where(and_(*conditions))
        
        result = await self.session.execute(stmt)
        return result.scalar() or 0
    
    async def get_by_user_uuid(self, user_uuid: str) -> Optional[AuthUserCredentials]:
        """Get credentials by user UUID."""
        stmt = select(auth_user_credentials).where(auth_user_credentials.c.user_uuid == user_uuid)
        result = await self.session.execute(stmt)
        row = result.fetchone()
        
        if not row:
            return None
        
        return AuthUserCredentials(
            uuid=row.uuid,
            user_uuid=row.user_uuid,
            pin_hash=row.pin_hash,
            failed_attempts=row.failed_attempts,
            locked_until=row.locked_until,
            last_login=row.last_login,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )
