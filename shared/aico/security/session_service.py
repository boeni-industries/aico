"""
Session Management Service for AICO Authentication

Provides session-backed JWT token management with database persistence,
refresh token rotation, and secure session lifecycle management.
"""

import uuid
import hashlib
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from dataclasses import dataclass

from ..data.libsql.connection import LibSQLConnection


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


class SessionService:
    """
    Session management service for JWT token lifecycle.
    
    Implements session-backed JWT approach:
    - Database-persisted sessions for revocation and management
    - Short-lived JWTs (15 minutes) with refresh capability
    - Secure session cleanup and expiration
    """
    
    def __init__(self, db_connection: LibSQLConnection):
        self.db = db_connection
    
    def create_session(
        self, 
        user_uuid: str, 
        device_uuid: str, 
        jwt_token: str,
        expires_in_minutes: int = 15
    ) -> SessionInfo:
        """
        Create a new authentication session.
        
        Args:
            user_uuid: User identifier
            device_uuid: Device identifier
            jwt_token: JWT token to associate with session
            expires_in_minutes: Token expiration time in minutes
            
        Returns:
            SessionInfo: Created session information
        """
        session_uuid = str(uuid.uuid4())
        jwt_token_hash = self._hash_token(jwt_token)
        expires_at = datetime.utcnow() + timedelta(minutes=expires_in_minutes)
        created_at = datetime.utcnow()
        
        # Insert session into database
        self.db.execute("""
            INSERT INTO auth_sessions (
                uuid, user_uuid, device_uuid, jwt_token_hash, 
                expires_at, created_at, is_active
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            session_uuid, user_uuid, device_uuid, jwt_token_hash,
            expires_at.isoformat(), created_at.isoformat(), True
        ))
        self.db.commit()
        
        return SessionInfo(
            uuid=session_uuid,
            user_uuid=user_uuid,
            device_uuid=device_uuid,
            jwt_token_hash=jwt_token_hash,
            expires_at=expires_at,
            created_at=created_at,
            is_active=True
        )
    
    def get_session_by_token(self, jwt_token: str) -> Optional[SessionInfo]:
        """
        Retrieve session by JWT token.
        
        Args:
            jwt_token: JWT token to look up
            
        Returns:
            SessionInfo if found and active, None otherwise
        """
        jwt_token_hash = self._hash_token(jwt_token)
        
        result = self.db.execute("""
            SELECT uuid, user_uuid, device_uuid, jwt_token_hash,
                   expires_at, created_at, is_active
            FROM auth_sessions
            WHERE jwt_token_hash = ? AND is_active = 1
        """, (jwt_token_hash,)).fetchone()
        
        if not result:
            return None
            
        return SessionInfo(
            uuid=result[0],
            user_uuid=result[1],
            device_uuid=result[2],
            jwt_token_hash=result[3],
            expires_at=datetime.fromisoformat(result[4]),
            created_at=datetime.fromisoformat(result[5]),
            is_active=bool(result[6])
        )
    
    def is_token_valid(self, jwt_token: str) -> bool:
        """
        Check if JWT token is valid (exists in active session and not expired).
        Triggers cleanup of expired sessions as a side effect.
        
        Args:
            jwt_token: JWT token to validate
            
        Returns:
            bool: True if token is valid, False otherwise
        """
        # Cleanup expired sessions on every validation (lightweight operation)
        self.cleanup_expired_sessions()
        
        session = self.get_session_by_token(jwt_token)
        if not session:
            return False
            
        # Check if session is expired (should be caught by cleanup above)
        if session.expires_at <= datetime.utcnow():
            # Mark expired session as inactive
            self.revoke_session(session.uuid)
            return False
            
        return True
    
    def revoke_session(self, session_uuid: str) -> bool:
        """
        Revoke a session by marking it inactive.
        
        Args:
            session_uuid: Session UUID to revoke
            
        Returns:
            bool: True if session was revoked, False if not found
        """
        result = self.db.execute("""
            UPDATE auth_sessions 
            SET is_active = 0 
            WHERE uuid = ?
        """, (session_uuid,))
        self.db.commit()
        
        return result.rowcount > 0
    
    def revoke_token(self, jwt_token: str) -> bool:
        """
        Revoke a session by JWT token.
        
        Args:
            jwt_token: JWT token to revoke
            
        Returns:
            bool: True if session was revoked, False if not found
        """
        session = self.get_session_by_token(jwt_token)
        if not session:
            return False
            
        return self.revoke_session(session.uuid)
    
    def delete_session(self, session_uuid: str) -> bool:
        """
        Delete a session completely from database.
        
        Args:
            session_uuid: Session UUID to delete
            
        Returns:
            bool: True if session was deleted, False if not found
        """
        result = self.db.execute("""
            DELETE FROM auth_sessions 
            WHERE uuid = ?
        """, (session_uuid,))
        self.db.commit()
        
        return result.rowcount > 0
    
    def delete_token(self, jwt_token: str) -> bool:
        """
        Delete a session by JWT token.
        
        Args:
            jwt_token: JWT token to delete
            
        Returns:
            bool: True if session was deleted, False if not found
        """
        session = self.get_session_by_token(jwt_token)
        if not session:
            return False
            
        return self.delete_session(session.uuid)
    
    def revoke_all_user_sessions(self, user_uuid: str) -> int:
        """
        Revoke all active sessions for a user.
        
        Args:
            user_uuid: User UUID
            
        Returns:
            int: Number of sessions revoked
        """
        result = self.db.execute("""
            UPDATE auth_sessions 
            SET is_active = 0 
            WHERE user_uuid = ? AND is_active = 1
        """, (user_uuid,))
        
        return result.rowcount
    
    def get_user_sessions(self, user_uuid: str, active_only: bool = True) -> List[SessionInfo]:
        """
        Get all sessions for a user.
        
        Args:
            user_uuid: User UUID
            active_only: If True, only return active sessions
            
        Returns:
            List[SessionInfo]: List of user sessions
        """
        query = """
            SELECT uuid, user_uuid, device_uuid, jwt_token_hash,
                   expires_at, created_at, is_active
            FROM auth_sessions
            WHERE user_uuid = ?
        """
        params = [user_uuid]
        
        if active_only:
            query += " AND is_active = 1"
            
        query += " ORDER BY created_at DESC"
        
        results = self.db.execute(query, params).fetchall()
        
        return [
            SessionInfo(
                uuid=row[0],
                user_uuid=row[1],
                device_uuid=row[2],
                jwt_token_hash=row[3],
                expires_at=datetime.fromisoformat(row[4]),
                created_at=datetime.fromisoformat(row[5]),
                is_active=bool(row[6])
            )
            for row in results
        ]
    
    def cleanup_expired_sessions(self) -> int:
        """
        Clean up expired sessions from database.
        
        Returns:
            int: Number of sessions cleaned up
        """
        result = self.db.execute("""
            DELETE FROM auth_sessions 
            WHERE expires_at <= ?
        """, (datetime.utcnow().isoformat(),))
        self.db.commit()
        
        return result.rowcount
    
    def cleanup_old_revoked_sessions(self, days_old: int = 30) -> int:
        """
        Clean up old revoked sessions (audit trail cleanup).
        
        Args:
            days_old: Delete revoked sessions older than this many days
            
        Returns:
            int: Number of sessions cleaned up
        """
        cutoff_date = datetime.utcnow() - timedelta(days=days_old)
        result = self.db.execute("""
            DELETE FROM auth_sessions 
            WHERE is_active = 0 AND created_at <= ?
        """, (cutoff_date.isoformat(),))
        self.db.commit()
        
        return result.rowcount
    
    def get_session_stats(self) -> Dict[str, Any]:
        """
        Get session statistics.
        
        Returns:
            Dict with session statistics
        """
        # Total sessions
        total_result = self.db.execute(
            "SELECT COUNT(*) FROM auth_sessions"
        ).fetchone()
        
        # Active sessions
        active_result = self.db.execute(
            "SELECT COUNT(*) FROM auth_sessions WHERE is_active = 1"
        ).fetchone()
        
        # Expired but not cleaned up
        current_time = datetime.utcnow().isoformat()
        expired_result = self.db.execute("""
            SELECT COUNT(*) FROM auth_sessions 
            WHERE expires_at <= ? AND is_active = 1
        """, (current_time,)).fetchone()
        
        return {
            "total_sessions": total_result[0] if total_result else 0,
            "active_sessions": active_result[0] if active_result else 0,
            "expired_sessions": expired_result[0] if expired_result else 0
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
