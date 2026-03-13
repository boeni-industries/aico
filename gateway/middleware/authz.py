"""
Gateway Authorization Manager

Handles role-based access control (RBAC) and permission checking for the Gateway service.
Uses the existing AuthorizationService from shared code.

This is a thin wrapper that adapts the shared authorization service
for Gateway-specific use cases (HTTP/WebSocket protocols).
"""

from typing import Optional, Dict, Any, Set
from dataclasses import dataclass

from aico.core.logging import get_logger
from aico.core.config import ConfigurationManager
from aico.core.authorization import AuthorizationService


@dataclass
class AuthzResult:
    """Authorization result"""
    success: bool
    error: Optional[str] = None
    required_permission: Optional[str] = None
    user_permissions: Optional[Set[str]] = None


class AuthorizationManager:
    """
    Gateway Authorization Manager
    
    Provides role-based access control and permission checking.
    Uses AuthorizationService for database-backed policy storage.
    
    Responsibilities:
    - Check user permissions
    - Validate role assignments
    - Enforce resource-level access control
    - Policy evaluation
    """
    
    def __init__(self, config: ConfigurationManager, db_connection):
        self.config = config
        self.logger = get_logger("gateway.middleware.authz")
        
        # Use shared AuthorizationService
        self.authz_service = AuthorizationService(db_connection)
        
        # Load RBAC configuration
        self.rbac_config = config.get("security.rbac", {})
        self.roles_config = self.rbac_config.get("roles", {})
        
        self.logger.info("Authorization manager initialized", extra={
            "available_roles": list(self.roles_config.keys())
        })
    
    async def authorize(
        self,
        user: Dict[str, Any],
        action: str,
        resource: Optional[Dict[str, Any]] = None
    ) -> AuthzResult:
        """
        Authorize user action on resource
        
        Args:
            user: User information (must contain user_uuid)
            action: Action to authorize (e.g., "read", "write", "admin.logs")
            resource: Optional resource information for resource-level checks
        
        Returns:
            AuthzResult indicating success or failure
        """
        try:
            user_uuid = user.get("user_uuid") or user.get("user_id")
            if not user_uuid:
                return AuthzResult(
                    success=False,
                    error="User UUID not found in user object"
                )
            
            # Get user permissions
            user_permissions = self.authz_service.get_user_permissions(user_uuid)
            
            # Check if user has required permission
            has_permission = self._check_permission(action, user_permissions)
            
            if has_permission:
                self.logger.debug("Authorization successful", extra={
                    "user_uuid": user_uuid,
                    "action": action,
                    "resource": resource.get("type") if resource else None
                })
                return AuthzResult(
                    success=True,
                    user_permissions=user_permissions
                )
            else:
                self.logger.warning("Authorization failed - insufficient permissions", extra={
                    "user_uuid": user_uuid,
                    "action": action,
                    "required_permission": action,
                    "user_permissions": list(user_permissions)
                })
                return AuthzResult(
                    success=False,
                    error="Insufficient permissions",
                    required_permission=action,
                    user_permissions=user_permissions
                )
                
        except Exception as e:
            self.logger.error(f"Authorization error: {e}", extra={
                "user_uuid": user.get("user_uuid"),
                "action": action
            })
            return AuthzResult(
                success=False,
                error=f"Authorization failed: {str(e)}"
            )
    
    def _check_permission(self, required_permission: str, user_permissions: Set[str]) -> bool:
        """
        Check if user has required permission
        
        Supports:
        - Exact match: "admin.logs" matches "admin.logs"
        - Wildcard: "admin.*" matches "admin.logs"
        - Super admin: "*" matches everything
        """
        # Check for super admin wildcard
        if "*" in user_permissions:
            return True
        
        # Check exact match
        if required_permission in user_permissions:
            return True
        
        # Check wildcard patterns
        for perm in user_permissions:
            if perm.endswith("*"):
                prefix = perm[:-1]
                if required_permission.startswith(prefix):
                    return True
        
        return False
    
    async def check_permission(self, user_uuid: str, permission: str) -> bool:
        """
        Check if user has specific permission
        
        Args:
            user_uuid: User UUID
            permission: Permission string (e.g., "admin.logs", "config.read")
        
        Returns:
            True if user has permission
        """
        try:
            return self.authz_service.has_permission(user_uuid, permission)
        except Exception as e:
            self.logger.error(f"Permission check error: {e}", extra={
                "user_uuid": user_uuid,
                "permission": permission
            })
            return False
    
    async def check_role(self, user_uuid: str, role: str) -> bool:
        """
        Check if user has specific role
        
        Args:
            user_uuid: User UUID
            role: Role name (e.g., "admin", "user")
        
        Returns:
            True if user has role
        """
        try:
            return self.authz_service.has_role(user_uuid, role)
        except Exception as e:
            self.logger.error(f"Role check error: {e}", extra={
                "user_uuid": user_uuid,
                "role": role
            })
            return False
    
    def get_user_roles(self, user_uuid: str) -> list:
        """
        Get all roles for user
        
        Args:
            user_uuid: User UUID
        
        Returns:
            List of role names
        """
        try:
            return self.authz_service.get_user_roles(user_uuid)
        except Exception as e:
            self.logger.error(f"Get roles error: {e}", extra={"user_uuid": user_uuid})
            return ["user"]  # Default role
    
    def get_user_permissions(self, user_uuid: str) -> Set[str]:
        """
        Get all permissions for user based on roles
        
        Args:
            user_uuid: User UUID
        
        Returns:
            Set of permission strings
        """
        try:
            return self.authz_service.get_user_permissions(user_uuid)
        except Exception as e:
            self.logger.error(f"Get permissions error: {e}", extra={"user_uuid": user_uuid})
            return set()
    
    async def assign_role(self, user_uuid: str, role: str, granted_by: str = "system") -> bool:
        """
        Assign role to user
        
        Args:
            user_uuid: User UUID
            role: Role name
            granted_by: Who granted the role
        
        Returns:
            True if role was assigned
        """
        try:
            success = self.authz_service.assign_role(user_uuid, role, granted_by)
            if success:
                self.logger.info("Role assigned", extra={
                    "user_uuid": user_uuid,
                    "role": role,
                    "granted_by": granted_by
                })
            return success
        except Exception as e:
            self.logger.error(f"Assign role error: {e}", extra={
                "user_uuid": user_uuid,
                "role": role
            })
            return False
    
    async def revoke_role(self, user_uuid: str, role: str) -> bool:
        """
        Revoke role from user
        
        Args:
            user_uuid: User UUID
            role: Role name
        
        Returns:
            True if role was revoked
        """
        try:
            success = self.authz_service.revoke_role(user_uuid, role)
            if success:
                self.logger.info("Role revoked", extra={
                    "user_uuid": user_uuid,
                    "role": role
                })
            return success
        except Exception as e:
            self.logger.error(f"Revoke role error: {e}", extra={
                "user_uuid": user_uuid,
                "role": role
            })
            return False
    
    def list_all_roles(self) -> Dict[str, list]:
        """
        List all available roles and their permissions
        
        Returns:
            Dict mapping role names to permission lists
        """
        return self.authz_service.list_all_roles()
    
    def require_permission(self, permission: str):
        """
        Decorator factory for requiring specific permission
        
        Usage:
            @require_permission("admin.logs")
            async def view_logs(user: dict):
                ...
        """
        def decorator(func):
            async def wrapper(user: Dict[str, Any], *args, **kwargs):
                result = await self.authorize(user, permission)
                if not result.success:
                    raise PermissionError(f"Permission denied: {permission}")
                return await func(user, *args, **kwargs)
            return wrapper
        return decorator
    
    def require_role(self, role: str):
        """
        Decorator factory for requiring specific role
        
        Usage:
            @require_role("admin")
            async def admin_operation(user: dict):
                ...
        """
        def decorator(func):
            async def wrapper(user: Dict[str, Any], *args, **kwargs):
                user_uuid = user.get("user_uuid") or user.get("user_id")
                if not await self.check_role(user_uuid, role):
                    raise PermissionError(f"Role required: {role}")
                return await func(user, *args, **kwargs)
            return wrapper
        return decorator
