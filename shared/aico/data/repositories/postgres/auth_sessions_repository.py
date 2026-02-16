"""
AuthSessionsRepository - PostgreSQL implementation

Handles CRUD operations for auth sessions.
"""

from typing import Optional, List
from datetime import datetime, UTC
from sqlalchemy import select, update, delete, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from aico.data.auth.models import AuthSession
from aico.data.tables import auth_sessions
from aico.data.repositories.base import Repository


class PostgresAuthSessionsRepository(Repository[AuthSession]):
    """PostgreSQL implementation of auth sessions repository."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def create(self, entity: AuthSession) -> AuthSession:
        """Create a new auth session."""
        stmt = auth_sessions.insert().values(
            uuid=entity.uuid,
            user_uuid=entity.user_uuid,
            device_uuid=entity.device_uuid,
            jwt_token_hash=entity.jwt_token_hash,
            expires_at=entity.expires_at,
            is_active=entity.is_active,
            session_type=entity.session_type,
        )
        await self.session.execute(stmt)
        return entity
    
    async def get_by_id(self, entity_id: str) -> Optional[AuthSession]:
        """Get auth session by ID."""
        stmt = select(auth_sessions).where(auth_sessions.c.uuid == entity_id)
        result = await self.session.execute(stmt)
        row = result.fetchone()
        
        if not row:
            return None
        
        return AuthSession(
            uuid=row.uuid,
            user_uuid=row.user_uuid,
            device_uuid=row.device_uuid,
            jwt_token_hash=row.jwt_token_hash,
            expires_at=row.expires_at,
            is_active=row.is_active,
            session_type=row.session_type,
            created_at=row.created_at,
        )
    
    async def update(self, entity: AuthSession) -> AuthSession:
        """Update an existing auth session."""
        stmt = (
            update(auth_sessions)
            .where(auth_sessions.c.uuid == entity.uuid)
            .values(
                is_active=entity.is_active,
                expires_at=entity.expires_at,
            )
        )
        await self.session.execute(stmt)
        return entity
    
    async def delete(self, entity_id: str) -> bool:
        """Delete an auth session."""
        stmt = delete(auth_sessions).where(auth_sessions.c.uuid == entity_id)
        result = await self.session.execute(stmt)
        return result.rowcount > 0
    
    async def list(self, filters: Optional[dict] = None, limit: int = 100, offset: int = 0) -> List[AuthSession]:
        """List auth sessions with optional filters."""
        stmt = select(auth_sessions)
        
        if filters:
            conditions = []
            if 'user_uuid' in filters:
                conditions.append(auth_sessions.c.user_uuid == filters['user_uuid'])
            if 'is_active' in filters:
                conditions.append(auth_sessions.c.is_active == filters['is_active'])
            
            if conditions:
                stmt = stmt.where(and_(*conditions))
        
        stmt = stmt.order_by(auth_sessions.c.created_at.desc()).limit(limit).offset(offset)
        result = await self.session.execute(stmt)
        
        return [
            AuthSession(
                uuid=row.uuid,
                user_uuid=row.user_uuid,
                device_uuid=row.device_uuid,
                jwt_token_hash=row.jwt_token_hash,
                expires_at=row.expires_at,
                is_active=row.is_active,
                session_type=row.session_type,
                created_at=row.created_at,
            )
            for row in result.fetchall()
        ]
    
    async def count(self, filters: Optional[dict] = None) -> int:
        """Count auth sessions with optional filters."""
        stmt = select(func.count()).select_from(auth_sessions)
        
        if filters:
            conditions = []
            if 'user_uuid' in filters:
                conditions.append(auth_sessions.c.user_uuid == filters['user_uuid'])
            
            if conditions:
                stmt = stmt.where(and_(*conditions))
        
        result = await self.session.execute(stmt)
        return result.scalar() or 0
    
    async def get_active_sessions(self, user_uuid: str) -> List[AuthSession]:
        """Get active sessions for a user."""
        stmt = select(auth_sessions).where(
            and_(
                auth_sessions.c.user_uuid == user_uuid,
                auth_sessions.c.is_active == True,
                auth_sessions.c.expires_at > datetime.now(UTC)
            )
        ).order_by(auth_sessions.c.created_at.desc())
        
        result = await self.session.execute(stmt)
        
        return [
            AuthSession(
                uuid=row.uuid,
                user_uuid=row.user_uuid,
                device_uuid=row.device_uuid,
                jwt_token_hash=row.jwt_token_hash,
                expires_at=row.expires_at,
                is_active=row.is_active,
                session_type=row.session_type,
                created_at=row.created_at,
            )
            for row in result.fetchall()
        ]
