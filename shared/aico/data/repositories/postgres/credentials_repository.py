"""
CredentialsRepository - PostgreSQL implementation

Handles CRUD operations for user credentials (PIN authentication).
"""

from typing import Optional, List
from datetime import datetime, UTC
from sqlalchemy import select, update, delete, and_
from sqlalchemy.ext.asyncio import AsyncSession

from aico.data.auth.models import AuthUserCredentials as UserCredentials
from aico.data.tables import auth_user_credentials
from aico.data.repositories.base import Repository


class PostgresCredentialsRepository(Repository[UserCredentials]):
    """PostgreSQL implementation of credentials repository."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def create(self, entity: UserCredentials) -> UserCredentials:
        """Create new user credentials."""
        stmt = auth_user_credentials.insert().values(
            uuid=entity.uuid,
            user_uuid=entity.user_uuid,
            password_hash=entity.password_hash,
            failed_attempts=entity.failed_attempts,
            locked_until=entity.locked_until,
            last_login=entity.last_login,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
        )
        await self.session.execute(stmt)
        return entity
    
    async def get_by_id(self, entity_id: str) -> Optional[UserCredentials]:
        """Get credentials by UUID."""
        stmt = select(auth_user_credentials).where(auth_user_credentials.c.uuid == entity_id)
        result = await self.session.execute(stmt)
        row = result.fetchone()
        
        if not row:
            return None
        
        return UserCredentials(
            uuid=row.uuid,
            user_uuid=row.user_uuid,
            password_hash=row.password_hash,
            failed_attempts=row.failed_attempts,
            locked_until=row.locked_until,
            last_login=row.last_login,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )
    
    async def update(self, entity: UserCredentials) -> UserCredentials:
        """Update user credentials."""
        stmt = (
            update(auth_user_credentials)
            .where(auth_user_credentials.c.uuid == entity.uuid)
            .values(
                password_hash=entity.password_hash,
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
    
    async def list(self, filters: Optional[dict] = None, limit: int = 100, offset: int = 0) -> List[UserCredentials]:
        """List credentials with optional filters."""
        stmt = select(auth_user_credentials)
        
        if filters:
            conditions = []
            if 'user_uuid' in filters:
                conditions.append(auth_user_credentials.c.user_uuid == filters['user_uuid'])
            
            if conditions:
                stmt = stmt.where(and_(*conditions))
        
        stmt = stmt.limit(limit).offset(offset)
        result = await self.session.execute(stmt)
        
        return [
            UserCredentials(
                uuid=row.uuid,
                user_uuid=row.user_uuid,
                password_hash=row.password_hash,
                failed_attempts=row.failed_attempts,
                locked_until=row.locked_until,
                last_login=row.last_login,
                created_at=row.created_at,
                updated_at=row.updated_at,
            )
            for row in result.fetchall()
        ]
    
    async def count(self, filters: Optional[dict] = None) -> int:
        """Count credentials with optional filters."""
        from sqlalchemy import func
        
        stmt = select(func.count()).select_from(auth_user_credentials)
        
        if filters:
            conditions = []
            if 'user_uuid' in filters:
                conditions.append(auth_user_credentials.c.user_uuid == filters['user_uuid'])
            
            if conditions:
                stmt = stmt.where(and_(*conditions))
        
        result = await self.session.execute(stmt)
        return result.scalar() or 0
    
    async def get_by_user_uuid(self, user_uuid: str) -> Optional[UserCredentials]:
        """Get credentials by user UUID."""
        stmt = select(auth_user_credentials).where(auth_user_credentials.c.user_uuid == user_uuid)
        result = await self.session.execute(stmt)
        row = result.fetchone()
        
        if not row:
            return None
        
        return UserCredentials(
            uuid=row.uuid,
            user_uuid=row.user_uuid,
            password_hash=row.password_hash,
            failed_attempts=row.failed_attempts,
            locked_until=row.locked_until,
            last_login=row.last_login,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )
    
    async def increment_failed_attempts(self, user_uuid: str) -> int:
        """Increment failed login attempts. Returns new count."""
        stmt = (
            update(auth_user_credentials)
            .where(auth_user_credentials.c.user_uuid == user_uuid)
            .values(
                failed_attempts=auth_user_credentials.c.failed_attempts + 1,
                updated_at=datetime.now(UTC)
            )
            .returning(auth_user_credentials.c.failed_attempts)
        )
        result = await self.session.execute(stmt)
        row = result.fetchone()
        return row[0] if row else 0
    
    async def reset_failed_attempts(self, user_uuid: str) -> bool:
        """Reset failed login attempts to 0."""
        stmt = (
            update(auth_user_credentials)
            .where(auth_user_credentials.c.user_uuid == user_uuid)
            .values(
                failed_attempts=0,
                locked_until=None,
                updated_at=datetime.now(UTC)
            )
        )
        result = await self.session.execute(stmt)
        return result.rowcount > 0
    
    async def lock_account(self, user_uuid: str, locked_until: datetime) -> bool:
        """Lock user account until specified time."""
        stmt = (
            update(auth_user_credentials)
            .where(auth_user_credentials.c.user_uuid == user_uuid)
            .values(
                locked_until=locked_until,
                updated_at=datetime.now(UTC)
            )
        )
        result = await self.session.execute(stmt)
        return result.rowcount > 0
    
    async def unlock_account(self, user_uuid: str) -> bool:
        """Unlock user account."""
        stmt = (
            update(auth_user_credentials)
            .where(auth_user_credentials.c.user_uuid == user_uuid)
            .values(
                locked_until=None,
                failed_attempts=0,
                updated_at=datetime.now(UTC)
            )
        )
        result = await self.session.execute(stmt)
        return result.rowcount > 0
    
    async def update_last_login(self, user_uuid: str) -> bool:
        """Update last login timestamp."""
        stmt = (
            update(auth_user_credentials)
            .where(auth_user_credentials.c.user_uuid == user_uuid)
            .values(
                last_login=datetime.now(UTC),
                updated_at=datetime.now(UTC)
            )
        )
        result = await self.session.execute(stmt)
        return result.rowcount > 0
