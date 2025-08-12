"""
Session Management Models for AICO API Gateway

Provides data models and management for user sessions with comprehensive
tracking and security features.
"""

import secrets
import time
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from enum import Enum

from aico.core.logging import get_logger


class SessionStatus(Enum):
    """Session status enumeration"""
    ACTIVE = "active"
    EXPIRED = "expired"
    REVOKED = "revoked"
    INVALID = "invalid"


@dataclass
class SessionInfo:
    """Comprehensive session information"""
    session_id: str
    user_id: str
    username: str
    roles: List[str]
    created_at: datetime
    last_activity: datetime
    expires_at: datetime
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    is_admin: bool = False
    status: SessionStatus = SessionStatus.ACTIVE
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
    
    def is_expired(self) -> bool:
        """Check if session is expired"""
        return datetime.now(timezone.utc) > self.expires_at
    
    def is_active(self) -> bool:
        """Check if session is active and valid"""
        return (
            self.status == SessionStatus.ACTIVE and 
            not self.is_expired()
        )
    
    def update_activity(self):
        """Update last activity timestamp"""
        self.last_activity = datetime.now(timezone.utc)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses"""
        data = asdict(self)
        # Convert datetime objects to ISO strings
        data['created_at'] = self.created_at.isoformat()
        data['last_activity'] = self.last_activity.isoformat()
        data['expires_at'] = self.expires_at.isoformat()
        data['status'] = self.status.value
        return data


class SessionManager:
    """
    Enhanced session management with comprehensive tracking
    """
    
    def __init__(self, config_manager=None):
        self.logger = get_logger("api_gateway", "session")
        self.sessions: Dict[str, SessionInfo] = {}
        
        # Configuration
        self.default_session_hours = 24
        self.admin_session_hours = 8  # Shorter for admin sessions
        self.max_sessions_per_user = 5
        
        if config_manager:
            self.default_session_hours = config_manager.get(
                "api_gateway.security.sessions.default_hours", 24
            )
            self.admin_session_hours = config_manager.get(
                "api_gateway.security.sessions.admin_hours", 8
            )
            self.max_sessions_per_user = config_manager.get(
                "api_gateway.security.sessions.max_per_user", 5
            )
    
    def create_session(
        self, 
        user_id: str, 
        username: str, 
        roles: List[str],
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        expires_hours: Optional[int] = None
    ) -> SessionInfo:
        """Create a new session for user"""
        
        # Determine session duration based on roles
        is_admin = "admin" in roles
        default_hours = self.admin_session_hours if is_admin else self.default_session_hours
        expires_hours = expires_hours or default_hours
        
        # Generate secure session ID
        session_id = secrets.token_urlsafe(32)
        
        # Create session info
        now = datetime.now(timezone.utc)
        session_info = SessionInfo(
            session_id=session_id,
            user_id=user_id,
            username=username,
            roles=roles,
            created_at=now,
            last_activity=now,
            expires_at=now + timedelta(hours=expires_hours),
            ip_address=ip_address,
            user_agent=user_agent,
            is_admin=is_admin,
            status=SessionStatus.ACTIVE
        )
        
        # Clean up old sessions for this user
        self._cleanup_user_sessions(user_id)
        
        # Store session
        self.sessions[session_id] = session_info
        
        self.logger.info("Session created", extra={
            "session_id": session_id,
            "user_id": user_id,
            "username": username,
            "is_admin": is_admin,
            "expires_at": session_info.expires_at.isoformat(),
            "ip_address": ip_address
        })
        
        return session_info
    
    def get_session(self, session_id: str) -> Optional[SessionInfo]:
        """Get session by ID"""
        session = self.sessions.get(session_id)
        if session and session.is_active():
            session.update_activity()
            return session
        elif session:
            # Mark as expired if found but not active
            session.status = SessionStatus.EXPIRED
        return None
    
    def list_sessions(
        self, 
        user_id: Optional[str] = None,
        include_expired: bool = False,
        admin_only: bool = False
    ) -> List[SessionInfo]:
        """List sessions with optional filtering"""
        sessions = []
        
        for session in self.sessions.values():
            # Filter by user if specified
            if user_id and session.user_id != user_id:
                continue
            
            # Filter by admin status if specified
            if admin_only and not session.is_admin:
                continue
            
            # Filter expired sessions unless requested
            if not include_expired and not session.is_active():
                continue
            
            sessions.append(session)
        
        # Sort by last activity (most recent first)
        sessions.sort(key=lambda s: s.last_activity, reverse=True)
        return sessions
    
    def revoke_session(self, session_id: str) -> bool:
        """Revoke a specific session"""
        session = self.sessions.get(session_id)
        if session:
            session.status = SessionStatus.REVOKED
            self.logger.info("Session revoked", extra={
                "session_id": session_id,
                "user_id": session.user_id,
                "username": session.username
            })
            return True
        return False
    
    def revoke_user_sessions(self, user_id: str, except_session: Optional[str] = None) -> int:
        """Revoke all sessions for a user (except optionally one)"""
        revoked_count = 0
        
        for session in self.sessions.values():
            if (session.user_id == user_id and 
                session.session_id != except_session and 
                session.status == SessionStatus.ACTIVE):
                
                session.status = SessionStatus.REVOKED
                revoked_count += 1
        
        if revoked_count > 0:
            self.logger.info("User sessions revoked", extra={
                "user_id": user_id,
                "revoked_count": revoked_count,
                "except_session": except_session
            })
        
        return revoked_count
    
    def cleanup_expired_sessions(self) -> int:
        """Remove expired sessions from storage"""
        expired_sessions = []
        
        for session_id, session in self.sessions.items():
            if session.is_expired():
                session.status = SessionStatus.EXPIRED
                expired_sessions.append(session_id)
        
        # Remove expired sessions
        for session_id in expired_sessions:
            del self.sessions[session_id]
        
        if expired_sessions:
            self.logger.info("Expired sessions cleaned up", extra={
                "cleaned_count": len(expired_sessions)
            })
        
        return len(expired_sessions)
    
    def get_session_stats(self) -> Dict[str, Any]:
        """Get session statistics"""
        active_sessions = [s for s in self.sessions.values() if s.is_active()]
        admin_sessions = [s for s in active_sessions if s.is_admin]
        
        return {
            "total_sessions": len(self.sessions),
            "active_sessions": len(active_sessions),
            "admin_sessions": len(admin_sessions),
            "expired_sessions": len([s for s in self.sessions.values() if s.is_expired()]),
            "revoked_sessions": len([s for s in self.sessions.values() if s.status == SessionStatus.REVOKED])
        }
    
    def _cleanup_user_sessions(self, user_id: str):
        """Clean up old sessions for user to enforce max limit"""
        user_sessions = [
            s for s in self.sessions.values() 
            if s.user_id == user_id and s.is_active()
        ]
        
        if len(user_sessions) >= self.max_sessions_per_user:
            # Sort by last activity and revoke oldest
            user_sessions.sort(key=lambda s: s.last_activity)
            sessions_to_revoke = user_sessions[:-self.max_sessions_per_user + 1]
            
            for session in sessions_to_revoke:
                session.status = SessionStatus.REVOKED
                self.logger.info("Old session revoked due to limit", extra={
                    "session_id": session.session_id,
                    "user_id": user_id,
                    "max_sessions": self.max_sessions_per_user
                })
