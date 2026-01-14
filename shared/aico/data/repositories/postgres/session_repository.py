"""
SessionRepository - PostgreSQL implementation

Handles CRUD operations for authentication sessions.
"""

from typing import Optional, List
from datetime import datetime, UTC
from sqlalchemy import select, update, delete, and_
from sqlalchemy.ext.asyncio import AsyncSession

from aico.data.auth.models import Session
from aico.data.tables import auth_sessions
from aico.data.repositories.base import Repository


class PostgresSessionRepository(Repository[Session]):
    """PostgreSQL implementation of session repository."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def create(self, entity: Session) -> Session:
        """Create a new session."""
        stmt = auth_sessions.insert().values(
            uuid=entity.session_id,
            user_uuid=entity.user_id,
            device_uuid=entity.device_id,
            jwt_token_hash=getattr(entity, 'jwt_token_hash', None),
            expires_at=entity.expires_at,
            created_at=entity.created_at,
            is_active=entity.is_active,
            session_type=getattr(entity, 'session_type', 'web'),
        )
        await self.session.execute(stmt)
        return entity
    
    async def get_by_id(self, entity_id: str) -> Optional[Session]:
        """Get session by UUID."""
        stmt = select(auth_sessions).where(auth_sessions.c.uuid == entity_id)
        result = await self.session.execute(stmt)
        row = result.fetchone()
        
        if not row:
            return None
        
        return Session(
            session_id=row.uuid,
            user_id=row.user_uuid,
            device_id=row.device_uuid,
            jwt_token_hash=row.jwt_token_hash,
            expires_at=row.expires_at,
            created_at=row.created_at,
            is_active=row.is_active,
            session_type=row.session_type,
        )
    
    async def update(self, entity: Session) -> Session:
        """Update an existing session."""
        stmt = (
            update(auth_sessions)
            .where(auth_sessions.c.uuid == entity.session_id)
            .values(
                jwt_token_hash=entity.jwt_token_hash,
                is_active=entity.is_active,
                expires_at=entity.expires_at,
            )
        )
        await self.session.execute(stmt)
        return entity
    
    async def delete(self, entity_id: str) -> bool:
        """Delete a session (hard delete)."""
        stmt = delete(auth_sessions).where(auth_sessions.c.uuid == entity_id)
        result = await self.session.execute(stmt)
        return result.rowcount > 0
    
    async def list(self, filters: Optional[dict] = None, limit: int = 100, offset: int = 0) -> List[Session]:
        """List sessions with optional filters."""
        stmt = select(auth_sessions)
        
        if filters:
            conditions = []
            if 'user_uuid' in filters:
                conditions.append(auth_sessions.c.user_uuid == filters['user_uuid'])
            if 'is_active' in filters:
                conditions.append(auth_sessions.c.is_active == filters['is_active'])
            if 'device_uuid' in filters:
                conditions.append(auth_sessions.c.device_uuid == filters['device_uuid'])
            
            if conditions:
                stmt = stmt.where(and_(*conditions))
        
        stmt = stmt.limit(limit).offset(offset)
        result = await self.session.execute(stmt)
        
        return [
            Session(
                uuid=row.uuid,
                user_uuid=row.user_uuid,
                device_uuid=row.device_uuid,
                jwt_token_hash=row.jwt_token_hash,
                expires_at=row.expires_at,
                created_at=row.created_at,
                is_active=row.is_active,
                session_type=row.session_type,
            )
            for row in result.fetchall()
        ]
    
    async def count(self, filters: Optional[dict] = None) -> int:
        """Count sessions with optional filters."""
        from sqlalchemy import func
        
        stmt = select(func.count()).select_from(auth_sessions)
        
        if filters:
            conditions = []
            if 'user_uuid' in filters:
                conditions.append(auth_sessions.c.user_uuid == filters['user_uuid'])
            if 'is_active' in filters:
                conditions.append(auth_sessions.c.is_active == filters['is_active'])
            
            if conditions:
                stmt = stmt.where(and_(*conditions))
        
        result = await self.session.execute(stmt)
        return result.scalar() or 0
    
    async def get_active_sessions_for_user(self, user_uuid: str) -> List[Session]:
        """Get all active sessions for a user."""
        stmt = select(auth_sessions).where(
            and_(
                auth_sessions.c.user_uuid == user_uuid,
                auth_sessions.c.is_active == True,
                auth_sessions.c.expires_at > datetime.now(UTC)
            )
        )
        result = await self.session.execute(stmt)
        
        return [
            Session(
                uuid=row.uuid,
                user_uuid=row.user_uuid,
                device_uuid=row.device_uuid,
                jwt_token_hash=row.jwt_token_hash,
                expires_at=row.expires_at,
                created_at=row.created_at,
                is_active=row.is_active,
                session_type=row.session_type,
            )
            for row in result.fetchall()
        ]
    
    async def invalidate_session(self, session_uuid: str) -> bool:
        """Invalidate (deactivate) a session."""
        stmt = (
            update(auth_sessions)
            .where(auth_sessions.c.uuid == session_uuid)
            .values(is_active=False)
        )
        result = await self.session.execute(stmt)
        return result.rowcount > 0
    
    async def invalidate_all_user_sessions(self, user_uuid: str) -> int:
        """Invalidate all sessions for a user. Returns count of invalidated sessions."""
        stmt = (
            update(auth_sessions)
            .where(
                and_(
                    auth_sessions.c.user_uuid == user_uuid,
                    auth_sessions.c.is_active == True
                )
            )
            .values(is_active=False)
        )
        result = await self.session.execute(stmt)
        return result.rowcount
