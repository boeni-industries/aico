"""
Async Session Management Service for AICO Authentication

Provides session-backed JWT token management with PostgreSQL persistence,
using the repository pattern and UnitOfWork for proper async database access.
"""

import uuid
import hashlib
from datetime import datetime, timedelta, UTC
from typing import Optional, List, Dict, Any
from dataclasses import dataclass

from aico.data.auth.models import AuthSession
from aico.data.uow import UnitOfWork


@dataclass
class SessionInfo:
    """Session information data class"""
    uuid: str
    user_uuid: str
    device_uuid: str
    jwt_token_hash: str
    expires_at: datetime
    created_at: datetime
    is_active: bool
    session_type: str = "unified"


class AsyncSessionService:
    """
    Async session management service for JWT token lifecycle.
    
    Implements session-backed JWT approach with PostgreSQL:
    - Database-persisted sessions for revocation and management
    - Short-lived JWTs (15 minutes) with refresh capability
    - Secure session cleanup and expiration
    - Uses UnitOfWork pattern for proper async transactions
    """
    
    async def create_session(
        self,
        uow: UnitOfWork,
        user_uuid: str,
        device_uuid: str,
        jwt_token: str,
        expires_in_minutes: int = 15,
        session_type: str = "unified"
    ) -> SessionInfo:
        """
        Create a new authentication session.
    
        Args:
            uow: Unit of Work for database transaction
            user_uuid: User identifier
            device_uuid: Device identifier
            jwt_token: JWT token to associate with session
            expires_in_minutes: Token expiration time in minutes
            session_type: Session type (e.g., 'rest', 'websocket', or 'unified')
    
        Returns:
            SessionInfo: Created session information
        """
        session_uuid = str(uuid.uuid4())
        jwt_token_hash = self._hash_token(jwt_token)
        expires_at = datetime.now(UTC) + timedelta(minutes=expires_in_minutes)
        created_at = datetime.now(UTC)
    
        # Create AuthSession entity
        auth_session = AuthSession(
            uuid=session_uuid,
            user_uuid=user_uuid,
            device_uuid=device_uuid,
            jwt_token_hash=jwt_token_hash,
            expires_at=expires_at,
            is_active=True,
            session_type=session_type,
            created_at=created_at
        )
        
        # Insert via repository
        await uow.auth_sessions.create(auth_session)
        
        return SessionInfo(
            uuid=session_uuid,
            user_uuid=user_uuid,
            device_uuid=device_uuid,
            jwt_token_hash=jwt_token_hash,
            expires_at=expires_at,
            created_at=created_at,
            is_active=True,
            session_type=session_type
        )
    
    async def get_session_by_token(self, uow: UnitOfWork, jwt_token: str) -> Optional[SessionInfo]:
        """
        Retrieve session by JWT token.
        
        Args:
            uow: Unit of Work for database access
            jwt_token: JWT token to look up
            
        Returns:
            SessionInfo if found and active, None otherwise
        """
        jwt_token_hash = self._hash_token(jwt_token)
        
        # Query via repository
        sessions = await uow.auth_sessions.list(
            filters={'jwt_token_hash': jwt_token_hash, 'is_active': True},
            limit=1
        )
        
        if not sessions:
            return None
        
        session = sessions[0]
        return SessionInfo(
            uuid=session.uuid,
            user_uuid=session.user_uuid,
            device_uuid=session.device_uuid,
            jwt_token_hash=session.jwt_token_hash,
            expires_at=session.expires_at,
            created_at=session.created_at,
            is_active=session.is_active,
            session_type=session.session_type
        )
    
    async def is_token_valid(self, uow: UnitOfWork, jwt_token: str) -> bool:
        """
        Check if JWT token is valid (exists in active session and not expired).
        
        Args:
            uow: Unit of Work for database access
            jwt_token: JWT token to validate
            
        Returns:
            bool: True if token is valid, False otherwise
        """
        session = await self.get_session_by_token(uow, jwt_token)
        if not session:
            return False
            
        # Check if session is expired
        if session.expires_at <= datetime.now(UTC):
            # Mark expired session as inactive
            await self.revoke_session(uow, session.uuid)
            return False
            
        return True
    
    async def revoke_session(self, uow: UnitOfWork, session_uuid: str) -> bool:
        """
        Revoke a session by marking it inactive.
        
        Args:
            uow: Unit of Work for database transaction
            session_uuid: Session UUID to revoke
            
        Returns:
            bool: True if session was revoked, False if not found
        """
        session = await uow.auth_sessions.get_by_id(session_uuid)
        if not session:
            return False
        
        session.is_active = False
        await uow.auth_sessions.update(session)
        return True
    
    async def revoke_token(self, uow: UnitOfWork, jwt_token: str) -> bool:
        """
        Revoke a session by JWT token.
        
        Args:
            uow: Unit of Work for database transaction
            jwt_token: JWT token to revoke
            
        Returns:
            bool: True if session was revoked, False if not found
        """
        session = await self.get_session_by_token(uow, jwt_token)
        if not session:
            return False
            
        return await self.revoke_session(uow, session.uuid)
    
    async def delete_session(self, uow: UnitOfWork, session_uuid: str) -> bool:
        """
        Delete a session completely from database.
        
        Args:
            uow: Unit of Work for database transaction
            session_uuid: Session UUID to delete
            
        Returns:
            bool: True if session was deleted, False if not found
        """
        return await uow.auth_sessions.delete(session_uuid)
    
    async def delete_token(self, uow: UnitOfWork, jwt_token: str) -> bool:
        """
        Delete a session by JWT token.
        
        Args:
            uow: Unit of Work for database transaction
            jwt_token: JWT token to delete
            
        Returns:
            bool: True if session was deleted, False if not found
        """
        session = await self.get_session_by_token(uow, jwt_token)
        if not session:
            return False
            
        return await self.delete_session(uow, session.uuid)
    
    async def get_user_sessions(self, uow: UnitOfWork, user_uuid: str, active_only: bool = True) -> List[SessionInfo]:
        """
        Get all sessions for a user.
        
        Args:
            uow: Unit of Work for database access
            user_uuid: User UUID
            active_only: If True, only return active sessions
            
        Returns:
            List[SessionInfo]: List of user sessions
        """
        filters = {'user_uuid': user_uuid}
        if active_only:
            filters['is_active'] = True
        
        sessions = await uow.auth_sessions.list(filters=filters, limit=1000)
        
        return [
            SessionInfo(
                uuid=session.uuid,
                user_uuid=session.user_uuid,
                device_uuid=session.device_uuid,
                jwt_token_hash=session.jwt_token_hash,
                expires_at=session.expires_at,
                created_at=session.created_at,
                is_active=session.is_active,
                session_type=session.session_type
            )
            for session in sessions
        ]
    
    async def get_active_sessions(self, uow: UnitOfWork, user_uuid: str) -> List[SessionInfo]:
        """
        Get active sessions for a user (convenience method).
        
        Args:
            uow: Unit of Work for database access
            user_uuid: User UUID
            
        Returns:
            List[SessionInfo]: List of active sessions
        """
        sessions = await uow.auth_sessions.get_active_sessions(user_uuid)
        
        return [
            SessionInfo(
                uuid=session.uuid,
                user_uuid=session.user_uuid,
                device_uuid=session.device_uuid,
                jwt_token_hash=session.jwt_token_hash,
                expires_at=session.expires_at,
                created_at=session.created_at,
                is_active=session.is_active,
                session_type=session.session_type
            )
            for session in sessions
        ]
    
    async def cleanup_expired_sessions(self, uow: UnitOfWork) -> int:
        """
        Clean up expired sessions from database.
        
        Args:
            uow: Unit of Work for database transaction
            
        Returns:
            int: Number of sessions cleaned up
        """
        # Get all active sessions
        sessions = await uow.auth_sessions.list(
            filters={'is_active': True},
            limit=10000
        )
        
        count = 0
        current_time = datetime.now(UTC)
        
        for session in sessions:
            if session.expires_at <= current_time:
                await uow.auth_sessions.delete(session.uuid)
                count += 1
        
        return count
    
    async def get_session_stats(self, uow: UnitOfWork) -> Dict[str, Any]:
        """
        Get session statistics.
        
        Args:
            uow: Unit of Work for database access
        
        Returns:
            Dict with session statistics
        """
        # Total sessions
        total_sessions = await uow.auth_sessions.count()
        
        # Active sessions
        active_sessions = await uow.auth_sessions.count(filters={'is_active': True})
        
        # Expired but not cleaned up (active sessions past expiry)
        all_active = await uow.auth_sessions.list(
            filters={'is_active': True},
            limit=10000
        )
        current_time = datetime.now(UTC)
        expired_sessions = sum(1 for s in all_active if s.expires_at <= current_time)
        
        return {
            "total_sessions": total_sessions,
            "active_sessions": active_sessions,
            "expired_sessions": expired_sessions
        }
    
    def _hash_token(self, token: str) -> str:
        """
        Hash JWT token for secure storage.
        
        Args:
            token: JWT token to hash
            
        Returns:
            str: SHA-256 hash of token
        """
        return hashlib.sha256(token.encode('utf-8')).hexdigest()
