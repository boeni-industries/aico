"""
AICO Authorization Service

Manages user roles and permissions using the access_policies database table.
Separates authorization from user_type - roles are assigned independently.
"""

from typing import List, Set, Optional, Dict, Any
from dataclasses import dataclass
from datetime import datetime
import uuid

from .logging import AICOLogger
from .config import ConfigurationManager


@dataclass
class UserRole:
    """User role assignment"""
    user_uuid: str
    role: str
    granted_by: str
    granted_at: datetime
    is_active: bool = True


class AuthorizationService:
    """
    Manages user roles and permissions using database storage.
    
    This service handles:
    - Role assignment and revocation
    - Permission checking
    - Role-based access control
    """
    
    def __init__(self, db_connection):
        self.db = db_connection
        self.config_manager = ConfigurationManager()
        self.logger = AICOLogger("authorization", "authorization", self.config_manager)
        
        # Load RBAC configuration
        self.rbac_config = self.config_manager.get("security.rbac", {})
        self.roles_config = self.rbac_config.get("roles", {})
        
        self.logger.info("Authorization service initialized", extra={
            "available_roles": list(self.roles_config.keys())
        })
    
    def assign_role(self, user_uuid: str, role: str, granted_by: str = "system") -> bool:
        """
        Assign a role to a user.
        
        Args:
            user_uuid: User UUID
            role: Role name (must exist in RBAC config)
            granted_by: Who granted the role
            
        Returns:
            True if role was assigned successfully
        """
        if role not in self.roles_config:
            self.logger.warning(f"Attempted to assign unknown role: {role}")
            return False
        
        try:
            # Check if role assignment already exists
            existing = self.db.execute("""
                SELECT uuid FROM access_policies 
                WHERE user_uuid = ? AND resource_type = 'role' AND permission = ? AND is_active = 1
            """, (user_uuid, role)).fetchone()
            
            if existing:
                self.logger.info(f"Role {role} already assigned to user {user_uuid}")
                return True
            
            # Create new role assignment
            policy_uuid = str(uuid.uuid4())
            self.db.execute("""
                INSERT INTO access_policies (uuid, user_uuid, resource_type, permission, is_active, created_at)
                VALUES (?, ?, 'role', ?, 1, ?)
            """, (policy_uuid, user_uuid, role, datetime.utcnow().isoformat()))
            
            # Commit the transaction
            self.db.commit()
            
            self.logger.info(f"Assigned role {role} to user {user_uuid}", extra={
                "user_uuid": user_uuid,
                "role": role,
                "granted_by": granted_by
            })
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to assign role {role} to user {user_uuid}: {e}")
            return False
    
    def revoke_role(self, user_uuid: str, role: str) -> bool:
        """
        Revoke a role from a user.
        
        Args:
            user_uuid: User UUID
            role: Role name to revoke
            
        Returns:
            True if role was revoked successfully
        """
        try:
            # Deactivate role assignment
            result = self.db.execute("""
                UPDATE access_policies 
                SET is_active = 0 
                WHERE user_uuid = ? AND resource_type = 'role' AND permission = ? AND is_active = 1
            """, (user_uuid, role))
            
            # Commit the transaction
            self.db.commit()
            
            if result.rowcount > 0:
                self.logger.info(f"Revoked role {role} from user {user_uuid}", extra={
                    "user_uuid": user_uuid,
                    "role": role
                })
                return True
            else:
                self.logger.warning(f"No active role {role} found for user {user_uuid}")
                return False
                
        except Exception as e:
            self.logger.error(f"Failed to revoke role {role} from user {user_uuid}: {e}")
            return False
    
    def get_user_roles(self, user_uuid: str) -> List[str]:
        """
        Get all active roles for a user.
        
        Args:
            user_uuid: User UUID
            
        Returns:
            List of role names
        """
        try:
            rows = self.db.execute("""
                SELECT permission FROM access_policies 
                WHERE user_uuid = ? AND resource_type = 'role' AND is_active = 1
            """, (user_uuid,)).fetchall()
            
            roles = [row[0] for row in rows]
            
            # Add default 'user' role if no roles assigned
            if not roles:
                roles = ["user"]
            
            return roles
            
        except Exception as e:
            self.logger.error(f"Failed to get roles for user {user_uuid}: {e}")
            return ["user"]  # Default role
    
    def get_user_permissions(self, user_uuid: str) -> Set[str]:
        """
        Get all permissions for a user based on their roles.
        
        Args:
            user_uuid: User UUID
            
        Returns:
            Set of permission strings
        """
        roles = self.get_user_roles(user_uuid)
        permissions = set()
        
        for role in roles:
            role_permissions = self.roles_config.get(role, [])
            permissions.update(role_permissions)
        
        return permissions
    
    def has_permission(self, user_uuid: str, permission: str) -> bool:
        """
        Check if user has a specific permission.
        
        Args:
            user_uuid: User UUID
            permission: Permission string (e.g., "admin.logs", "config.read")
            
        Returns:
            True if user has permission
        """
        user_permissions = self.get_user_permissions(user_uuid)
        
        # Check for wildcard permission
        if "*" in user_permissions:
            return True
        
        # Check exact match
        if permission in user_permissions:
            return True
        
        # Check pattern matching (e.g., "admin.*" matches "admin.logs")
        for perm in user_permissions:
            if perm.endswith("*"):
                prefix = perm[:-1]
                if permission.startswith(prefix):
                    return True
        
        return False
    
    def has_role(self, user_uuid: str, role: str) -> bool:
        """
        Check if user has a specific role.
        
        Args:
            user_uuid: User UUID
            role: Role name
            
        Returns:
            True if user has role
        """
        return role in self.get_user_roles(user_uuid)
    
    def list_all_roles(self) -> Dict[str, List[str]]:
        """
        List all available roles and their permissions.
        
        Returns:
            Dict mapping role names to permission lists
        """
        return self.roles_config.copy()
    
    def bootstrap_admin_user(self, user_uuid: str) -> bool:
        """
        Bootstrap the first admin user for initial setup.
        
        Args:
            user_uuid: User UUID to make admin
            
        Returns:
            True if successful
        """
        success = self.assign_role(user_uuid, "admin", "bootstrap")
        
        if success:
            self.logger.info(f"Bootstrapped admin user: {user_uuid}", extra={
                "user_uuid": user_uuid,
                "operation": "bootstrap_admin"
            })
        
        return success
