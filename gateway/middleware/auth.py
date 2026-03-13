"""
Gateway Authentication Manager

Handles JWT-based authentication for the Gateway service using the
existing AsyncSessionService pattern from shared code.

This is a thin wrapper that adapts the shared authentication services
for Gateway-specific use cases (HTTP/WebSocket protocols).
"""

import jwt
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
from dataclasses import dataclass

from aico.core.logging import get_logger
from aico.core.config import ConfigurationManager
from aico.security.key_manager import AICOKeyManager
from aico.security.async_session_service import AsyncSessionService, SessionInfo
from aico.services.user_service import UserService
from aico.data.uow import UnitOfWork


@dataclass
class AuthResult:
    """Authentication result"""
    success: bool
    user: Optional[Any] = None
    session_id: Optional[str] = None
    token: Optional[str] = None
    error: Optional[str] = None


@dataclass
class TokenPayload:
    """JWT token payload"""
    user_uuid: str
    user_id: str
    tenant_id: str
    username: Optional[str]
    roles: list
    permissions: set
    exp: datetime
    iat: datetime


class AuthenticationManager:
    """
    Gateway Authentication Manager
    
    Provides JWT-based authentication with session management.
    Uses AsyncSessionService for database-backed session storage.
    
    Responsibilities:
    - JWT token generation and validation
    - Session creation and management
    - User credential verification
    - Token refresh and revocation
    """
    
    def __init__(self, config: ConfigurationManager, get_uow_factory):
        self.config = config
        self.get_uow_factory = get_uow_factory
        self.logger = get_logger("gateway.middleware.auth")
        
        # Session service for JWT session management
        self.session_service = AsyncSessionService()
        
        # JWT configuration
        key_manager = AICOKeyManager(config)
        self.jwt_secret = key_manager.get_jwt_secret("api_gateway")
        if not isinstance(self.jwt_secret, str) or len(self.jwt_secret.encode("utf-8")) < 32:
            raise RuntimeError("JWT secret must be at least 32 bytes")

        self.jwt_algorithm = config.get("api_gateway.auth.jwt.algorithm", "HS256")
        expiry_hours = config.get("api_gateway.auth.jwt.expiry_hours", 24)
        try:
            expiry_hours = int(expiry_hours)
        except Exception:
            expiry_hours = 24
        self.jwt_expiration = max(60, expiry_hours * 3600)
        
        # Track revoked tokens (in-memory cache, backed by database sessions)
        self.revoked_tokens = set()
        
        self.logger.info("Authentication manager initialized", extra={
            "jwt_expiration": self.jwt_expiration,
            "algorithm": self.jwt_algorithm
        })
    
    def _get_jwt_secret(self) -> str:
        """Get JWT secret (for compatibility with existing code)"""
        return self.jwt_secret
    
    async def authenticate(self, credentials: Dict[str, Any], client_info: Dict[str, Any]) -> AuthResult:
        """
        Authenticate user with credentials
        
        Args:
            credentials: User credentials (username/password or token)
            client_info: Client information (IP, user agent, etc.)
        
        Returns:
            AuthResult with user info and session token
        """
        try:
            # Check if token-based auth
            if "token" in credentials:
                return await self._authenticate_with_token(credentials["token"])
            
            # Username/password authentication
            username = credentials.get("username")
            user_uuid = credentials.get("user_uuid")
            password = credentials.get("password")
            device_uuid = credentials.get("device_uuid", "unknown")
            
            if (not username and not user_uuid) or not password:
                return AuthResult(success=False, error="Missing username/user_uuid or password")
            
            # Verify credentials via UserService
            uow_factory = self.get_uow_factory()
            async with uow_factory() as uow:
                user_service = UserService(uow)
                
                # Get user by username or uuid
                if user_uuid:
                    user = await user_service.get_user(user_uuid)
                else:
                    user = await user_service.get_user_by_username(username)
                if not user:
                    self.logger.warning("Authentication failed - user not found", extra={
                        "username": username,
                        "user_uuid": user_uuid,
                        "client_ip": client_info.get("remote_addr")
                    })
                    return AuthResult(success=False, error="Invalid credentials")

                resolved_user_uuid = getattr(user, "user_uuid", None) or getattr(user, "uuid", None)
                resolved_user_id = getattr(user, "user_id", None) or resolved_user_uuid
                if not resolved_user_uuid:
                    self.logger.error("Authentication failed - user missing uuid", extra={
                        "username": username,
                        "user_uuid": user_uuid,
                    })
                    return AuthResult(success=False, error="Invalid credentials")

                user_type = getattr(user, "user_type", None)
                if resolved_user_uuid == "system_user" or str(user_type).lower() == "system":
                    self.logger.warning("Authentication blocked for system user", extra={
                        "user_uuid": resolved_user_uuid,
                        "user_type": str(user_type),
                        "client_ip": client_info.get("remote_addr"),
                    })
                    return AuthResult(success=False, error="System user login disabled")
                
                # Verify password
                credentials_obj = None
                if hasattr(uow, "auth_user_credentials"):
                    credentials_obj = await uow.auth_user_credentials.get_by_user_uuid(resolved_user_uuid)
                if credentials_obj is None:
                    credentials_obj = await user_service.get_credentials(resolved_user_id)
                if not credentials_obj or not self._verify_password(password, credentials_obj.password_hash):
                    self.logger.warning("Authentication failed - invalid password", extra={
                        "username": username,
                        "user_uuid": user_uuid,
                        "client_ip": client_info.get("remote_addr")
                    })
                    return AuthResult(success=False, error="Invalid credentials")
                
                # Generate JWT token
                token = self._generate_jwt(user)
                
                # Create session
                session_info = await self.session_service.create_session(
                    uow=uow,
                    user_uuid=resolved_user_uuid,
                    device_uuid=device_uuid,
                    jwt_token=token,
                    expires_in_minutes=self.jwt_expiration // 60
                )
                
                await uow.commit()
                
                self.logger.info("Authentication successful", extra={
                    "user_uuid": resolved_user_uuid,
                    "username": username or getattr(user, "username", None) or resolved_user_uuid,
                    "session_id": session_info.uuid
                })
                
                return AuthResult(
                    success=True,
                    user=user,
                    session_id=session_info.uuid,
                    token=token
                )
                
        except Exception as e:
            self.logger.error(f"Authentication error: {e}", extra={
                "username": credentials.get("username"),
                "error": str(e)
            })
            return AuthResult(success=False, error="Authentication failed")
    
    async def _authenticate_with_token(self, token: str) -> AuthResult:
        """Authenticate using existing JWT token"""
        try:
            # Validate token
            payload = self.validate_token(token)
            if not payload:
                return AuthResult(success=False, error="Invalid token")
            
            # Check if token is revoked
            if token in self.revoked_tokens:
                return AuthResult(success=False, error="Token has been revoked")
            
            # Verify session exists in database
            uow_factory = self.get_uow_factory()
            async with uow_factory() as uow:
                session_info = await self.session_service.get_session_by_token(uow, token)
                
                if not session_info or not session_info.is_active:
                    return AuthResult(success=False, error="Session expired or invalid")
                
                # Check session expiration
                if session_info.expires_at < datetime.now(timezone.utc):
                    return AuthResult(success=False, error="Session expired")
                
                # Get user info
                user_service = UserService(uow)
                user = await user_service.get_user(payload.user_uuid)
                
                if not user:
                    return AuthResult(success=False, error="User not found")
                
                return AuthResult(
                    success=True,
                    user=user,
                    session_id=session_info.uuid,
                    token=token
                )
                
        except Exception as e:
            self.logger.error(f"Token authentication error: {e}")
            return AuthResult(success=False, error="Token authentication failed")
    
    def validate_token(self, token: str) -> Optional[TokenPayload]:
        """
        Validate JWT token and return payload
        
        Args:
            token: JWT token string
        
        Returns:
            TokenPayload if valid, None otherwise
        """
        try:
            payload = jwt.decode(
                token,
                self.jwt_secret,
                algorithms=[self.jwt_algorithm],
                options={"verify_aud": False}
            )
            
            return TokenPayload(
                user_uuid=payload.get("user_uuid") or payload.get("sub"),
                user_id=payload.get("user_id") or payload.get("sub"),
                tenant_id=payload.get("tenant_id", "default"),
                username=payload.get("username"),
                roles=payload.get("roles", []),
                permissions=set(payload.get("permissions", [])),
                exp=datetime.fromtimestamp(payload["exp"], timezone.utc),
                iat=datetime.fromtimestamp(payload["iat"], timezone.utc)
            )
            
        except jwt.ExpiredSignatureError:
            self.logger.debug("Token validation failed - expired")
            return None
        except jwt.InvalidTokenError as e:
            self.logger.debug(f"Token validation failed - invalid: {e}")
            return None
        except Exception as e:
            self.logger.error(f"Token validation error: {e}")
            return None


    def _generate_jwt(self, user: Any) -> str:
        """Generate JWT token for user"""
        now = datetime.now(timezone.utc)
        exp = now + timedelta(seconds=self.jwt_expiration)

        user_uuid = getattr(user, "user_uuid", None) or getattr(user, "uuid", None)
        user_id = getattr(user, "user_id", None) or user_uuid
        username = getattr(user, "username", None) or user_uuid

        user_type = getattr(user, "user_type", None)
        roles = getattr(user, "roles", None)
        if not isinstance(roles, list) or not roles:
            if str(user_type).lower() == "admin":
                roles = ["admin"]
            else:
                roles = ["user"]

        payload = {
            "user_uuid": user_uuid,
            "user_id": user_id,
            "tenant_id": getattr(user, "tenant_id", "default"),
            "username": username,
            "roles": roles,
            "permissions": list(getattr(user, "permissions", [])),
            "iat": int(now.timestamp()),
            "exp": int(exp.timestamp())
        }
        
        return jwt.encode(payload, self.jwt_secret, algorithm=self.jwt_algorithm)
    
    def _verify_password(self, password: str, password_hash: str) -> bool:
        """Verify password against hash"""
        try:
            from passlib.context import CryptContext
            pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
            return pwd_context.verify(password, password_hash)
        except Exception as e:
            self.logger.error(f"Password verification error: {e}")
            return False

    async def revoke_session(self, session_id: str) -> bool:
        """
        Revoke a session

        Args:
            session_id: Session UUID to revoke

        Returns:
            True if session was revoked
        """
        try:
            uow_factory = self.get_uow_factory()
            async with uow_factory() as uow:
                session = await uow.auth_sessions.get_by_id(session_id)
                if not session:
                    return False

                # Mark session as inactive
                session.is_active = False
                session.expires_at = datetime.now(timezone.utc)
                await uow.auth_sessions.update(session)
                await uow.commit()

                # Add token to revoked set
                if hasattr(session, 'jwt_token_hash'):
                    self.revoked_tokens.add(session.jwt_token_hash)

                self.logger.info("Session revoked", extra={"session_id": session_id})
                return True

        except Exception as e:
            self.logger.error(f"Failed to revoke session: {e}", extra={"session_id": session_id})
            return False

    async def refresh_token(self, old_token: str) -> Optional[str]:
        """
        Refresh JWT token

        Args:
            old_token: Current JWT token

        Returns:
            New JWT token if successful, None otherwise
        """
        try:
            # Validate old token (allow expired tokens for refresh)
            payload = jwt.decode(
                old_token,
                self.jwt_secret,
                algorithms=[self.jwt_algorithm],
                options={"verify_exp": False, "verify_aud": False}
            )

            # Get user
            uow_factory = self.get_uow_factory()
            async with uow_factory() as uow:
                user_service = UserService(uow)
                user = await user_service.get_user(payload["user_uuid"])

                if not user:
                    return None

                # Generate new token
                new_token = self._generate_jwt(user)

                resolved_user_uuid = getattr(user, "user_uuid", None) or getattr(user, "uuid", None)
                if not resolved_user_uuid:
                    return None

                # Update session with new token
                session_info = await self.session_service.get_session_by_token(uow, old_token)

                if session_info:
                    # Create new session for new token
                    await self.session_service.create_session(
                        uow=uow,
                        user_uuid=resolved_user_uuid,
                        device_uuid=session_info.device_uuid,
                        jwt_token=new_token,
                        expires_in_minutes=self.jwt_expiration // 60,
                    )

                    # Invalidate old session
                    await self.revoke_session(session_info.uuid)

                await uow.commit()

                self.logger.info("Token refreshed", extra={"user_uuid": resolved_user_uuid})
                return new_token

        except Exception as e:
            self.logger.error(f"Token refresh error: {e}")
            return None

    def list_sessions(self, user_uuid: Optional[str] = None, admin_only: bool = False) -> list:
        """
        List active sessions (for admin endpoints)

        Args:
            user_uuid: Filter by user UUID
            admin_only: Show only admin sessions

        Returns:
            List of session info
        """
        # This would query the database for sessions
        # Placeholder for now - implement when needed
        return []

    def get_session_stats(self) -> Dict[str, Any]:
        """Get session statistics (for monitoring)"""
        return {
            "revoked_tokens_count": len(self.revoked_tokens),
            "jwt_expiration": self.jwt_expiration
        }


class AuthHeaderPresenceMiddleware:
    """Debug middleware: logs whether Authorization header is present.

    Never logs token content. Useful to determine whether clients (Studio) send
    the header or it gets lost in the middleware chain.
    """

    def __init__(self, app):
        self.app = app
        self.logger = get_logger("gateway.auth_header_presence")

    async def __call__(self, scope, receive, send):
        if scope.get("type") != "http":
            await self.app(scope, receive, send)
            return

        headers = dict(scope.get("headers") or [])
        has_auth = b"authorization" in headers
        path = scope.get("path")
        method = scope.get("method")

        # Log only actionable cases at INFO (containers usually suppress DEBUG).
        # Never log token content.
        if (
            isinstance(path, str)
            and path.startswith("/api/v1/")
            and path not in ("/api/v1/health", "/api/v1/health/detailed", "/api/v1/handshake")
            and not has_auth
        ):
            self.logger.info(f"Missing Authorization header: {method} {path}")

        await self.app(scope, receive, send)
