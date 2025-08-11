"""
Authentication and Authorization Management for AICO API Gateway

Implements middleware-based auth patterns following industry best practices:
- JWT tokens for REST/WebSocket
- API keys for service-to-service
- Session-based for admin UI
"""

import asyncio
import hashlib
import hmac
import json
import secrets
import time
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Set, Any
from enum import Enum
from dataclasses import dataclass, asdict

import jwt
from passlib.context import CryptContext

from aico.core.logging import get_logger
from aico.core.config import ConfigurationManager
from aico.security.key_manager import AICOKeyManager

# Initialize logger
logger = get_logger("api_gateway", "auth")


class AuthMethod(Enum):
    """Supported authentication methods"""
    JWT = "jwt"
    API_KEY = "api_key"
    SESSION = "session"
    NONE = "none"


@dataclass
class AuthResult:
    """Authentication result"""
    success: bool
    user: Optional['User'] = None
    method: Optional[AuthMethod] = None
    error: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class AuthzResult:
    """Authorization result"""
    success: bool
    allowed_actions: Optional[Set[str]] = None
    error: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class User:
    """User identity and attributes"""
    user_id: str
    username: str
    roles: List[str]
    permissions: Set[str]
    metadata: Dict[str, Any]
    session_id: Optional[str] = None
    
    def has_role(self, role: str) -> bool:
        """Check if user has specific role"""
        return role in self.roles
    
    def has_permission(self, permission: str) -> bool:
        """Check if user has specific permission"""
        return permission in self.permissions or "*" in self.permissions


class AuthenticationManager:
    """
    Handles authentication for API Gateway requests using AICO security infrastructure
    """
    
    def __init__(self, config: ConfigurationManager):
        self.config = config
        self.logger = get_logger("api_gateway", "auth")
        
        # Use AICO security infrastructure
        self.key_manager = AICOKeyManager()
        
        # JWT configuration - secrets managed by AICOKeyManager
        self.jwt_algorithm = config.get("api_gateway.security.auth.jwt.algorithm", "HS256")
        self.jwt_expiry_hours = config.get("api_gateway.security.auth.jwt.expiry_hours", 24)
        
        # Get JWT secret from AICOKeyManager (zero-effort security)
        self.jwt_secret = self._get_jwt_secret()
        
        # API key storage (in production, use database)
        self.api_keys: Dict[str, Dict[str, Any]] = {}
        
        # Session storage (in production, use Redis or database)
        self.sessions: Dict[str, Dict[str, Any]] = {}
        
        # Password context for API key hashing
        self.pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        
        # In-memory stores (in production, these would be in database)
        self.api_keys: Dict[str, Dict[str, Any]] = {}
        self.sessions: Dict[str, Dict[str, Any]] = {}
        self.revoked_tokens: Set[str] = set()
        
        # Initialize default service accounts
        self._initialize_service_accounts()
    
    def generate_jwt_token(self, user_id: str, username: str = None, roles: List[str] = None, 
                          permissions: Set[str] = None, expires_hours: int = None) -> str:
        """Generate JWT token for user (zero-effort security)"""
        import time
        from datetime import datetime, timedelta
        
        expires_hours = expires_hours or self.jwt_expiry_hours
        exp_time = datetime.utcnow() + timedelta(hours=expires_hours)
        
        payload = {
            "sub": user_id,
            "username": username or user_id,
            "roles": roles or ["user"],
            "permissions": list(permissions or set()),
            "iat": int(time.time()),
            "exp": int(exp_time.timestamp()),
            "iss": "aico-api-gateway"
        }
        
        token = jwt.encode(payload, self.jwt_secret, algorithm=self.jwt_algorithm)
        
        logger.info("JWT token generated", extra={
            "module": "api_gateway",
            "function": "generate_jwt_token",
            "topic": "auth.jwt.token_generated",
            "user_id": user_id,
            "expires": exp_time.isoformat()
        })
        
        return token
    
    def generate_cli_token(self) -> str:
        """Generate JWT token for CLI access (zero-effort security)"""
        return self.generate_jwt_token(
            user_id="cli_user",
            username="AICO CLI",
            roles=["admin"],  # CLI gets admin access
            permissions={"*"},  # Full access for CLI
            expires_hours=24 * 7  # 7 days for CLI convenience
        )
    
    def revoke_token(self, token: str) -> None:
        """Revoke JWT token"""
        self.revoked_tokens.add(token)
        logger.info("JWT token revoked", extra={
            "module": "api_gateway",
            "function": "revoke_token", 
            "topic": "auth.jwt.token_revoked"
        })
        
        self.logger.info("Authentication manager initialized", extra={
            "methods": list(auth_config.keys()),
            "jwt_enabled": self.jwt_config.get("enabled", False),
            "api_key_enabled": self.api_key_config.get("enabled", False),
            "session_enabled": self.session_config.get("enabled", False)
        })
    
    def _get_jwt_secret(self) -> str:
        """Get JWT secret from AICOKeyManager"""
        try:
            # Use AICOKeyManager for JWT secret management
            return self.key_manager.get_jwt_secret("api_gateway")
        except Exception as e:
            logger.error("Failed to get JWT secret from key manager", extra={
                "module": "api_gateway",
                "function": "_get_jwt_secret",
                "topic": "auth.jwt.secret_error",
                "error": str(e)
            })
            raise
    
    def _initialize_service_accounts(self):
        """Initialize default service accounts"""
        # Create default admin API key
        admin_key = secrets.token_urlsafe(32)
        admin_user = User(
            user_id="admin",
            username="admin",
            roles=["admin"],
            permissions={"*"},  # Full access
            metadata={"type": "service_account", "created": datetime.utcnow().isoformat()}
        )
        self.api_keys[admin_key] = admin_user
        
        # Create default service API key for internal services
        service_key = secrets.token_urlsafe(32)
        service_user = User(
            user_id="system",
            username="system",
            roles=["service"],
            permissions={"system.*", "admin.*"},
            metadata={"type": "service_account", "created": datetime.utcnow().isoformat()}
        )
        self.api_keys[service_key] = service_user
        
        self.logger.info("Default service accounts created", extra={
            "admin_key": admin_key[:8] + "...",
            "service_key": service_key[:8] + "..."
        })
    
    async def authenticate(self, request_data: Any, client_info: Dict[str, Any]) -> AuthResult:
        """
        Authenticate request using appropriate method
        
        Determines authentication method based on request headers/data
        and validates credentials accordingly.
        """
        try:
            # Extract authentication data from request
            auth_data = self._extract_auth_data(request_data, client_info)
            
            if not auth_data:
                return AuthResult(success=False, error="No authentication provided")
            
            # Try authentication methods in order of preference
            for method, data in auth_data.items():
                result = await self._authenticate_method(method, data, client_info)
                if result.success:
                    self.logger.debug(f"Authentication successful via {method}", extra={
                        "user_id": result.user.user_id,
                        "client": client_info.get("client_id", "unknown")
                    })
                    return result
            
            return AuthResult(success=False, error="Authentication failed")
            
        except Exception as e:
            self.logger.error(f"Authentication error: {e}")
            return AuthResult(success=False, error=str(e))
    
    def _extract_auth_data(self, request_data: Any, client_info: Dict[str, Any]) -> Dict[AuthMethod, str]:
        """Extract authentication data from request"""
        auth_data = {}
        
        # Extract from headers (REST/WebSocket)
        headers = client_info.get("headers", {})
        
        # JWT from Authorization header
        auth_header = headers.get("authorization", "")
        if auth_header.startswith("Bearer "):
            auth_data[AuthMethod.JWT] = auth_header[7:]
        
        # API Key from custom header
        api_key = headers.get(self.api_key_header.lower(), "")
        if api_key:
            auth_data[AuthMethod.API_KEY] = api_key
        
        # Session from cookies
        cookies = client_info.get("cookies", {})
        session_id = cookies.get(self.session_cookie, "")
        if session_id:
            auth_data[AuthMethod.SESSION] = session_id
        
        # For ZeroMQ IPC, use client certificate or local user
        if client_info.get("protocol") == "zeromq_ipc":
            # Local IPC connections are trusted by default
            auth_data[AuthMethod.NONE] = "local_ipc"
        
        return auth_data
    
    async def _authenticate_method(self, method: AuthMethod, data: str, client_info: Dict[str, Any]) -> AuthResult:
        """Authenticate using specific method"""
        
        if method == AuthMethod.JWT:
            return await self._authenticate_jwt(data, client_info)
        elif method == AuthMethod.API_KEY:
            return await self._authenticate_api_key(data, client_info)
        elif method == AuthMethod.SESSION:
            return await self._authenticate_session(data, client_info)
        elif method == AuthMethod.NONE:
            return await self._authenticate_local(data, client_info)
        else:
            return AuthResult(success=False, error=f"Unsupported auth method: {method}")
    
    async def _authenticate_jwt(self, token: str, client_info: Dict[str, Any]) -> AuthResult:
        """Authenticate JWT token"""
        try:
            # Check if token is revoked
            if token in self.revoked_tokens:
                return AuthResult(success=False, error="Token revoked")
            
            # Decode and validate JWT
            payload = jwt.decode(token, self.jwt_secret, algorithms=[self.jwt_algorithm])
            
            # Extract user information
            user = User(
                user_id=payload["sub"],
                username=payload.get("username", payload["sub"]),
                roles=payload.get("roles", ["user"]),
                permissions=set(payload.get("permissions", [])),
                metadata=payload.get("metadata", {})
            )
            
            return AuthResult(
                success=True,
                user=user,
                method=AuthMethod.JWT,
                metadata={"token_exp": payload.get("exp")}
            )
            
        except jwt.ExpiredSignatureError:
            return AuthResult(success=False, error="Token expired")
        except jwt.InvalidTokenError as e:
            return AuthResult(success=False, error=f"Invalid token: {e}")
        except Exception as e:
            return AuthResult(success=False, error=f"JWT authentication error: {e}")
    
    async def _authenticate_api_key(self, api_key: str, client_info: Dict[str, Any]) -> AuthResult:
        """Authenticate API key"""
        try:
            user = self.api_keys.get(api_key)
            if not user:
                return AuthResult(success=False, error="Invalid API key")
            
            return AuthResult(
                success=True,
                user=user,
                method=AuthMethod.API_KEY,
                metadata={"api_key_hash": hashlib.sha256(api_key.encode()).hexdigest()[:8]}
            )
            
        except Exception as e:
            return AuthResult(success=False, error=f"API key authentication error: {e}")
    
    async def _authenticate_session(self, session_id: str, client_info: Dict[str, Any]) -> AuthResult:
        """Authenticate session"""
        try:
            user = self.sessions.get(session_id)
            if not user:
                return AuthResult(success=False, error="Invalid session")
            
            return AuthResult(
                success=True,
                user=user,
                method=AuthMethod.SESSION,
                metadata={"session_id": session_id}
            )
            
        except Exception as e:
            return AuthResult(success=False, error=f"Session authentication error: {e}")
    
    async def _authenticate_local(self, data: str, client_info: Dict[str, Any]) -> AuthResult:
        """Authenticate local IPC connection"""
        try:
            # Local IPC connections are trusted
            user = User(
                user_id="local_user",
                username="local_user",
                roles=["user"],
                permissions={"conversation.*", "personality.read", "memory.read"},
                metadata={"type": "local_ipc", "client_info": client_info}
            )
            
            return AuthResult(
                success=True,
                user=user,
                method=AuthMethod.NONE,
                metadata={"connection_type": "local_ipc"}
            )
            
        except Exception as e:
            return AuthResult(success=False, error=f"Local authentication error: {e}")
    
    def create_jwt_token(self, user: User) -> str:
        """Create JWT token for user"""
        payload = {
            "sub": user.user_id,
            "username": user.username,
            "roles": user.roles,
            "permissions": list(user.permissions),
            "metadata": user.metadata,
            "iat": datetime.utcnow(),
            "exp": datetime.utcnow() + self.jwt_expiration
        }
        
        return jwt.encode(payload, self.jwt_secret, algorithm=self.jwt_algorithm)
    
    def revoke_token(self, token: str):
        """Revoke JWT token"""
        self.revoked_tokens.add(token)
    
    def create_session(self, user: User) -> str:
        """Create session for user"""
        session_id = secrets.token_urlsafe(32)
        user.session_id = session_id
        self.sessions[session_id] = user
        return session_id
    
    def revoke_session(self, session_id: str):
        """Revoke session"""
        self.sessions.pop(session_id, None)


class AuthorizationManager:
    """
    Handles authorization using Role-Based Access Control (RBAC)
    
    Implements fine-grained permissions with:
    - Role-based access control
    - Resource-level permissions
    - Context-aware authorization
    - Topic-based message routing permissions
    """
    
    def __init__(self, authz_config: Dict[str, Any]):
        self.logger = get_logger("api_gateway", "authz")
        self.config = authz_config
        
        # RBAC configuration
        self.rbac_config = authz_config.get("rbac", {})
        self.default_policy = authz_config.get("default_policy", "deny")
        
        # Role definitions
        self.roles = self.rbac_config.get("roles", {})
        
        # Permission cache
        self.permission_cache: Dict[str, Set[str]] = {}
        
        self.logger.info("Authorization manager initialized", extra={
            "default_policy": self.default_policy,
            "roles": list(self.roles.keys())
        })
    
    async def authorize(self, user: User, action: str, resource: Any = None) -> AuthzResult:
        """
        Authorize user action on resource
        
        Args:
            user: Authenticated user
            action: Action being performed (e.g., "conversation.start", "admin.system.stats")
            resource: Optional resource context (e.g., AICOMessage)
        """
        try:
            # Check if user has explicit permission
            if self._check_explicit_permission(user, action):
                return AuthzResult(success=True, allowed_actions={action})
            
            # Check role-based permissions
            if self._check_role_permissions(user, action):
                return AuthzResult(success=True, allowed_actions={action})
            
            # Check context-specific permissions
            if resource and self._check_context_permissions(user, action, resource):
                return AuthzResult(success=True, allowed_actions={action})
            
            # Default policy
            if self.default_policy == "allow":
                return AuthzResult(success=True, allowed_actions={action})
            else:
                return AuthzResult(
                    success=False, 
                    error=f"Access denied: {user.username} cannot perform {action}"
                )
                
        except Exception as e:
            self.logger.error(f"Authorization error: {e}")
            return AuthzResult(success=False, error=str(e))
    
    def _check_explicit_permission(self, user: User, action: str) -> bool:
        """Check if user has explicit permission"""
        # Wildcard permission
        if "*" in user.permissions:
            return True
        
        # Exact match
        if action in user.permissions:
            return True
        
        # Pattern matching (e.g., "conversation.*" matches "conversation.start")
        for permission in user.permissions:
            if permission.endswith("*"):
                prefix = permission[:-1]
                if action.startswith(prefix):
                    return True
        
        return False
    
    def _check_role_permissions(self, user: User, action: str) -> bool:
        """Check if user's roles grant permission"""
        for role in user.roles:
            role_permissions = self.roles.get(role, [])
            for permission in role_permissions:
                if permission == "*" or action == permission:
                    return True
                if permission.endswith("*") and action.startswith(permission[:-1]):
                    return True
        
        return False
    
    def _check_context_permissions(self, user: User, action: str, resource: Any) -> bool:
        """Check context-specific permissions"""
        # Example: Allow users to access their own data
        if isinstance(resource, AICOMessage):
            # Check if user is accessing their own conversation
            if action.startswith("conversation.") and resource.metadata.source == user.user_id:
                return True
        
        return False
    
    def get_user_permissions(self, user: User) -> Set[str]:
        """Get all permissions for user"""
        cache_key = f"{user.user_id}:{':'.join(user.roles)}"
        
        if cache_key in self.permission_cache:
            return self.permission_cache[cache_key]
        
        permissions = set(user.permissions)
        
        # Add role-based permissions
        for role in user.roles:
            role_permissions = self.roles.get(role, [])
            permissions.update(role_permissions)
        
        self.permission_cache[cache_key] = permissions
        return permissions
    
    def clear_permission_cache(self):
        """Clear permission cache"""
        self.permission_cache.clear()
