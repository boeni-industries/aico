"""
Core User Management Service

Provides user CRUD operations and authentication functionality
that can be used by both CLI and API Gateway components.
"""

import hashlib
import secrets
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any

# Fix bcrypt compatibility with passlib
import bcrypt
bcrypt.__about__ = bcrypt

from aico.core.logging import get_logger
from aico.core.config import ConfigurationManager
from aico.data.libsql.connection import LibSQLConnection
from passlib.context import CryptContext

from .models import UserProfile, AuthenticationData


class UserService:
    """
    Core user management service providing CRUD operations and authentication
    """
    
    def __init__(self, db_connection: LibSQLConnection):
        self.db = db_connection
        self.logger = get_logger("shared", "user_service.core")
        
        # Load configuration
        self.config = ConfigurationManager()
        security_config = self.config.config_cache.get('security', {})
        auth_config = security_config.get('authentication', {})
        
        # Password context for PIN hashing with configurable rounds
        bcrypt_rounds = auth_config.get('password_hashing', {}).get('rounds', 12)
        self.pwd_context = CryptContext(
            schemes=["bcrypt"], 
            deprecated="auto",
            bcrypt__rounds=bcrypt_rounds
        )
        
        # Configurable authentication settings
        self.max_failed_attempts = auth_config.get('max_failed_attempts', 5)
        self.lockout_duration_minutes = auth_config.get('lockout_duration', 300) // 60  # Convert seconds to minutes
        
        self.logger.info("User service initialized")
    
    # User CRUD Operations
    
    async def create_user(self, full_name: str, nickname: str = None, 
                         user_type: str = 'parent', pin: str = None) -> UserProfile:
        """
        Create a new user with optional PIN authentication
        
        Args:
            full_name: User's full name
            nickname: Optional nickname
            user_type: User type (person)
            pin: Optional PIN for authentication
            
        Returns:
            Created user profile
        """
        user_uuid = str(uuid.uuid4())
        
        try:
            with self.db.transaction():
                # Create user profile
                self.db.execute("""
                    INSERT INTO users (uuid, full_name, nickname, user_type, is_active, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                """, (user_uuid, full_name, nickname, user_type, True))
                
                # Create authentication record if PIN provided
                if pin:
                    auth_uuid = str(uuid.uuid4())
                    pin_hash = self.pwd_context.hash(pin)
                    
                    self.db.execute("""
                        INSERT INTO user_authentication 
                        (uuid, user_uuid, pin_hash, failed_attempts, created_at, updated_at)
                        VALUES (?, ?, ?, 0, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                    """, (auth_uuid, user_uuid, pin_hash))
                
                self.logger.info("User created", extra={
                    "module": "user_service",
                    "function": "create_user",
                    "topic": "user_management",
                    "zmq_topic": "logs",
                    "user_uuid": user_uuid,
                    "full_name": full_name,
                    "user_type": user_type,
                    "has_pin": bool(pin)
                })
                
                return await self.get_user(user_uuid)
                
        except Exception as e:
            self.logger.error(f"Failed to create user: {e}", extra={
                "module": "user_service",
                "function": "create_user", 
                "topic": "user_management",
                "zmq_topic": "logs",
                "full_name": full_name,
                "error": str(e)
            })
            raise
    
    async def get_user(self, user_uuid: str) -> Optional[UserProfile]:
        """
        Get user by UUID
        
        Args:
            user_uuid: User UUID
            
        Returns:
            User profile or None if not found
        """
        try:
            result = self.db.fetch_one("""
                SELECT uuid, full_name, nickname, user_type, is_active, created_at, updated_at
                FROM users WHERE uuid = ? AND is_active = TRUE
            """, (user_uuid,))
            
            if not result:
                return None
                
            from datetime import datetime
            
            # Convert string timestamps to datetime objects if needed
            created_at = result['created_at']
            if isinstance(created_at, str):
                created_at = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
            
            updated_at = result['updated_at']
            if isinstance(updated_at, str):
                updated_at = datetime.fromisoformat(updated_at.replace('Z', '+00:00'))
            
            return UserProfile(
                uuid=result['uuid'],
                full_name=result['full_name'],
                nickname=result['nickname'],
                user_type=result['user_type'],
                is_active=result['is_active'],
                created_at=created_at,
                updated_at=updated_at
            )
            
        except Exception as e:
            self.logger.error(f"Failed to get user: {e}", extra={
                "module": "user_service",
                "function": "get_user",
                "topic": "user_management", 
                "zmq_topic": "logs",
                "user_uuid": user_uuid,
                "error": str(e)
            })
            return None
    
    async def update_user(self, user_uuid: str, updates: Dict[str, Any]) -> Optional[UserProfile]:
        """
        Update user profile
        
        Args:
            user_uuid: User UUID
            updates: Dictionary of fields to update
            
        Returns:
            Updated user profile or None if not found
        """
        allowed_fields = {'full_name', 'nickname', 'user_type'}
        update_fields = {k: v for k, v in updates.items() if k in allowed_fields}
        
        if not update_fields:
            return await self.get_user(user_uuid)
        
        try:
            # Build dynamic UPDATE query
            set_clause = ", ".join([f"{field} = ?" for field in update_fields.keys()])
            values = list(update_fields.values()) + [user_uuid]
            
            with self.db.transaction():
                result = self.db.execute(f"""
                    UPDATE users 
                    SET {set_clause}, updated_at = CURRENT_TIMESTAMP
                    WHERE uuid = ? AND is_active = TRUE
                """, values)
                
                if result.rowcount == 0:
                    return None
                
                self.logger.info("User updated", extra={
                    "module": "user_service",
                    "function": "update_user",
                    "topic": "user_management",
                    "zmq_topic": "logs", 
                    "user_uuid": user_uuid,
                    "updated_fields": list(update_fields.keys())
                })
                
                return await self.get_user(user_uuid)
                
        except Exception as e:
            self.logger.error(f"Failed to update user: {e}", extra={
                "module": "user_service",
                "function": "update_user",
                "topic": "user_management",
                "zmq_topic": "logs",
                "user_uuid": user_uuid,
                "updates": update_fields,
                "error": str(e)
            })
            raise
    
    async def delete_user(self, user_uuid: str) -> bool:
        """
        Soft delete user (mark as inactive)
        
        Args:
            user_uuid: User UUID
            
        Returns:
            True if user was deleted, False if not found
        """
        try:
            with self.db.transaction():
                result = self.db.execute("""
                    UPDATE users 
                    SET is_active = FALSE, updated_at = CURRENT_TIMESTAMP
                    WHERE uuid = ? AND is_active = TRUE
                """, (user_uuid,))
                
                if result.rowcount == 0:
                    return False
                
                self.logger.info("User deleted", extra={
                    "module": "user_service",
                    "function": "delete_user",
                    "topic": "user_management",
                    "zmq_topic": "logs",
                    "user_uuid": user_uuid
                })
                
                return True
                
        except Exception as e:
            self.logger.error(f"Failed to delete user: {e}", extra={
                "module": "user_service", 
                "function": "delete_user",
                "topic": "user_management",
                "zmq_topic": "logs",
                "user_uuid": user_uuid,
                "error": str(e)
            })
            raise
    
    async def hard_delete_user(self, user_uuid: str) -> bool:
        """
        Permanently delete user and all related data (IRREVERSIBLE)
        
        Args:
            user_uuid: User UUID
            
        Returns:
            True if user was permanently deleted, False if not found
        """
        try:
            with self.db.transaction():
                # Check if user exists
                user = self.db.execute("SELECT uuid FROM users WHERE uuid = ?", (user_uuid,)).fetchone()
                if not user:
                    return False
                
                # Delete in order to respect foreign key constraints
                self.db.execute("DELETE FROM user_relationships WHERE user_uuid = ? OR related_user_uuid = ?", (user_uuid, user_uuid))
                self.db.execute("DELETE FROM access_policies WHERE user_uuid = ?", (user_uuid,))
                self.db.execute("DELETE FROM user_authentication WHERE user_uuid = ?", (user_uuid,))
                self.db.execute("DELETE FROM users WHERE uuid = ?", (user_uuid,))
                
                self.logger.warning("User permanently deleted", extra={
                    "module": "user_service",
                    "function": "hard_delete_user",
                    "topic": "user_management",
                    "zmq_topic": "logs",
                    "user_uuid": user_uuid,
                    "action": "PERMANENT_DELETE"
                })
                
                return True
                
        except Exception as e:
            self.logger.error(f"Failed to permanently delete user: {e}", extra={
                "module": "user_service", 
                "function": "hard_delete_user",
                "topic": "user_management",
                "zmq_topic": "logs",
                "user_uuid": user_uuid,
                "error": str(e)
            })
            raise
    
    async def set_pin(self, user_uuid: str, new_pin: str, old_pin: str = None) -> bool:
        """
        Set or update user PIN
        
        Args:
            user_uuid: User UUID
            new_pin: New PIN to set
            old_pin: Current PIN (required for updates, optional for first-time setup)
            
        Returns:
            True if PIN was set successfully, False if old PIN verification failed
        """
        try:
            with self.db.transaction():
                # Check if user exists
                user = await self.get_user(user_uuid)
                if not user:
                    raise ValueError(f"User not found: {user_uuid}")
                
                # Check if user already has authentication data
                auth_data = self.db.execute("""
                    SELECT pin_hash FROM user_authentication WHERE user_uuid = ?
                """, (user_uuid,)).fetchone()
                
                # If user has existing PIN, verify old PIN
                if auth_data and auth_data['pin_hash']:
                    if not old_pin:
                        raise ValueError("Old PIN required to update existing PIN")
                    
                    if not self.pwd_context.verify(old_pin, auth_data['pin_hash']):
                        self.logger.warning("Failed PIN update attempt", extra={
                            "module": "user_service",
                            "function": "set_pin",
                            "topic": "authentication",
                            "zmq_topic": "logs",
                            "user_uuid": user_uuid,
                            "reason": "invalid_old_pin"
                        })
                        return False
                
                # Hash new PIN
                pin_hash = self.pwd_context.hash(new_pin)
                
                # Update or insert authentication data
                if auth_data:
                    self.db.execute("""
                        UPDATE user_authentication 
                        SET pin_hash = ?, updated_at = CURRENT_TIMESTAMP
                        WHERE user_uuid = ?
                    """, (pin_hash, user_uuid))
                else:
                    import uuid as uuid_lib
                    auth_uuid = str(uuid_lib.uuid4())
                    self.db.execute("""
                        INSERT INTO user_authentication (uuid, user_uuid, pin_hash, failed_attempts, created_at, updated_at)
                        VALUES (?, ?, ?, 0, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                    """, (auth_uuid, user_uuid, pin_hash))
                
                self.logger.info("User PIN updated", extra={
                    "module": "user_service",
                    "function": "set_pin",
                    "topic": "authentication",
                    "zmq_topic": "logs",
                    "user_uuid": user_uuid,
                    "action": "pin_set"
                })
                
                return True
                
        except Exception as e:
            self.logger.error(f"Failed to set PIN: {e}", extra={
                "module": "user_service", 
                "function": "set_pin",
                "topic": "authentication",
                "zmq_topic": "logs",
                "user_uuid": user_uuid,
                "error": str(e)
            })
            raise
    
    async def list_users(self, user_type: str = None, limit: int = 100, include_inactive: bool = True) -> List[UserProfile]:
        """
        List users with optional filtering
        
        Args:
            user_type: Optional filter by user type
            limit: Maximum number of users to return
            include_inactive: Include soft-deleted users (default: True)
            
        Returns:
            List of user profiles
        """
        try:
            # Build WHERE clause based on filters
            where_conditions = []
            params = []
            
            if not include_inactive:
                where_conditions.append("is_active = TRUE")
            
            if user_type:
                where_conditions.append("user_type = ?")
                params.append(user_type)
            
            where_clause = "WHERE " + " AND ".join(where_conditions) if where_conditions else ""
            params.append(limit)
            
            results = self.db.fetch_all(f"""
                SELECT uuid, full_name, nickname, user_type, is_active, created_at, updated_at
                FROM users 
                {where_clause}
                ORDER BY created_at DESC
                LIMIT ?
            """, tuple(params))
            
            from datetime import datetime
            
            users = []
            for row in results:
                # Convert string timestamps to datetime objects if needed
                created_at = row['created_at']
                if isinstance(created_at, str):
                    created_at = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                
                updated_at = row['updated_at']
                if isinstance(updated_at, str):
                    updated_at = datetime.fromisoformat(updated_at.replace('Z', '+00:00'))
                
                users.append(UserProfile(
                    uuid=row['uuid'],
                    full_name=row['full_name'],
                    nickname=row['nickname'],
                    user_type=row['user_type'],
                    is_active=row['is_active'],
                    created_at=created_at,
                    updated_at=updated_at
                ))
            
            return users
            
        except Exception as e:
            self.logger.error(f"Failed to list users: {e}", extra={
                "module": "user_service",
                "function": "list_users", 
                "topic": "user_management",
                "zmq_topic": "logs",
                "user_type": user_type,
                "limit": limit,
                "error": str(e)
            })
            raise
    
    # Authentication Operations
    
    async def authenticate_user(self, user_uuid: str, pin: str) -> Dict[str, Any]:
        """
        Authenticate user with PIN
        
        Args:
            user_uuid: User UUID
            pin: User's PIN
            
        Returns:
            Authentication result with success status and user info
        """
        try:
            # Get user and authentication data
            user = await self.get_user(user_uuid)
            if not user:
                return {"success": False, "error": "User not found"}
            
            auth_data = self.db.fetch_one("""
                SELECT uuid, pin_hash, failed_attempts, locked_until, last_login
                FROM user_authentication WHERE user_uuid = ?
            """, (user_uuid,))
            
            if not auth_data:
                return {"success": False, "error": "No authentication configured"}
            
            # Check if account is locked
            if auth_data['locked_until']:
                locked_until = datetime.fromisoformat(auth_data['locked_until'])
                if datetime.now() < locked_until:
                    return {
                        "success": False, 
                        "error": "Account locked",
                        "locked_until": locked_until.isoformat()
                    }
            
            # Verify PIN
            if not self.pwd_context.verify(pin, auth_data['pin_hash']):
                # Increment failed attempts
                failed_attempts = auth_data['failed_attempts'] + 1
                locked_until = None
                
                if failed_attempts >= self.max_failed_attempts:
                    locked_until = datetime.now() + timedelta(minutes=self.lockout_duration_minutes)
                
                self.db.execute("""
                    UPDATE user_authentication 
                    SET failed_attempts = ?, locked_until = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE user_uuid = ?
                """, (failed_attempts, locked_until.isoformat() if locked_until else None, user_uuid))
                
                self.logger.warning("Authentication failed", extra={
                    "module": "user_service",
                    "function": "authenticate_user",
                    "topic": "authentication",
                    "zmq_topic": "logs",
                    "user_uuid": user_uuid,
                    "failed_attempts": failed_attempts,
                    "locked": bool(locked_until)
                })
                
                return {
                    "success": False, 
                    "error": "Invalid PIN",
                    "failed_attempts": failed_attempts,
                    "locked": bool(locked_until)
                }
            
            # Successful authentication - reset failed attempts
            self.db.execute("""
                UPDATE user_authentication 
                SET failed_attempts = 0, locked_until = NULL, last_login = CURRENT_TIMESTAMP, updated_at = CURRENT_TIMESTAMP
                WHERE user_uuid = ?
            """, (user_uuid,))
            
            self.logger.info("User authenticated successfully", extra={
                "module": "user_service",
                "function": "authenticate_user",
                "topic": "authentication",
                "zmq_topic": "logs",
                "user_uuid": user_uuid,
                "full_name": user.full_name
            })
            
            return {
                "success": True,
                "user": user,
                "last_login": auth_data['last_login']
            }
            
        except Exception as e:
            self.logger.error(f"Authentication error: {e}", extra={
                "module": "user_service",
                "function": "authenticate_user",
                "topic": "authentication", 
                "zmq_topic": "logs",
                "user_uuid": user_uuid,
                "error": str(e)
            })
            return {"success": False, "error": "Authentication system error"}
    
    async def set_user_pin(self, user_uuid: str, new_pin: str) -> bool:
        """
        Set or update user's PIN
        
        Args:
            user_uuid: User UUID
            new_pin: New PIN
            
        Returns:
            True if PIN was set successfully
        """
        try:
            user = await self.get_user(user_uuid)
            if not user:
                return False
            
            pin_hash = self.pwd_context.hash(new_pin)
            
            with self.db.transaction():
                # Check if authentication record exists
                existing = self.db.fetch_one("""
                    SELECT uuid FROM user_authentication WHERE user_uuid = ?
                """, (user_uuid,))
                
                if existing:
                    # Update existing
                    self.db.execute("""
                        UPDATE user_authentication 
                        SET pin_hash = ?, failed_attempts = 0, locked_until = NULL, updated_at = CURRENT_TIMESTAMP
                        WHERE user_uuid = ?
                    """, (pin_hash, user_uuid))
                else:
                    # Create new
                    auth_uuid = str(uuid.uuid4())
                    self.db.execute("""
                        INSERT INTO user_authentication 
                        (uuid, user_uuid, pin_hash, failed_attempts, created_at, updated_at)
                        VALUES (?, ?, ?, 0, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                    """, (auth_uuid, user_uuid, pin_hash))
                
                self.logger.info("User PIN updated", extra={
                    "module": "user_service",
                    "function": "set_user_pin",
                    "topic": "authentication",
                    "zmq_topic": "logs",
                    "user_uuid": user_uuid
                })
                
                return True
                
        except Exception as e:
            self.logger.error(f"Failed to set user PIN: {e}", extra={
                "module": "user_service",
                "function": "set_user_pin",
                "topic": "authentication",
                "zmq_topic": "logs", 
                "user_uuid": user_uuid,
                "error": str(e)
            })
            return False
    
    async def unlock_user(self, user_uuid: str) -> bool:
        """
        Unlock user account (admin function)
        
        Args:
            user_uuid: User UUID
            
        Returns:
            True if user was unlocked
        """
        try:
            result = self.db.execute("""
                UPDATE user_authentication 
                SET failed_attempts = 0, locked_until = NULL, updated_at = CURRENT_TIMESTAMP
                WHERE user_uuid = ?
            """, (user_uuid,))
            
            if result.rowcount > 0:
                self.logger.info("User unlocked", extra={
                    "module": "user_service",
                    "function": "unlock_user",
                    "topic": "authentication",
                    "zmq_topic": "logs",
                    "user_uuid": user_uuid
                })
                return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"Failed to unlock user: {e}", extra={
                "module": "user_service",
                "function": "unlock_user", 
                "topic": "authentication",
                "zmq_topic": "logs",
                "user_uuid": user_uuid,
                "error": str(e)
            })
            return False
    
    async def get_user_stats(self) -> Dict[str, Any]:
        """
        Get user statistics
        
        Returns:
            Dictionary with user statistics
        """
        try:
            stats = {}
            
            # Total users
            result = self.db.fetch_one("SELECT COUNT(*) as total FROM users WHERE is_active = TRUE")
            stats['total_users'] = result['total']
            
            # Users by type
            results = self.db.fetch_all("""
                SELECT user_type, COUNT(*) as count 
                FROM users WHERE is_active = TRUE 
                GROUP BY user_type
            """)
            stats['users_by_type'] = {row['user_type']: row['count'] for row in results}
            
            # Authentication stats
            result = self.db.fetch_one("""
                SELECT 
                    COUNT(*) as total_with_auth,
                    SUM(CASE WHEN locked_until IS NOT NULL AND locked_until > datetime('now') THEN 1 ELSE 0 END) as locked_accounts
                FROM user_authentication ua
                JOIN users u ON ua.user_uuid = u.uuid
                WHERE u.is_active = TRUE
            """)
            stats['authentication'] = {
                'total_with_auth': result['total_with_auth'],
                'locked_accounts': result['locked_accounts']
            }
            
            return stats
            
        except Exception as e:
            self.logger.error(f"Failed to get user stats: {e}", extra={
                "module": "user_service",
                "function": "get_user_stats",
                "topic": "user_management",
                "zmq_topic": "logs",
                "error": str(e)
            })
            return {}
    
    async def get_user_authentication(self, user_uuid: str) -> Optional[Dict[str, Any]]:
        """
        Get user authentication data
        
        Args:
            user_uuid: User UUID
            
        Returns:
            Dictionary with authentication data or None if not found
        """
        try:
            result = self.db.fetch_one("""
                SELECT pin_hash, failed_attempts, locked_until, last_login, created_at, updated_at
                FROM user_authentication WHERE user_uuid = ?
            """, (user_uuid,))
            
            if not result:
                return None
                
            return {
                'has_pin': bool(result['pin_hash']),
                'is_locked': bool(result['locked_until'] and datetime.fromisoformat(result['locked_until']) > datetime.now()),
                'failed_attempts': result['failed_attempts'],
                'last_login': result['last_login'],
                'created_at': result['created_at'],
                'updated_at': result['updated_at']
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get user authentication: {e}", extra={
                "module": "user_service",
                "function": "get_user_authentication",
                "topic": "authentication",
                "zmq_topic": "logs",
                "user_uuid": user_uuid,
                "error": str(e)
            })
            return None
    
    async def get_user_relationships(self, user_uuid: str) -> List[Dict[str, Any]]:
        """
        Get user relationships
        
        Args:
            user_uuid: User UUID
            
        Returns:
            List of relationship dictionaries
        """
        try:
            results = self.db.fetch_all("""
                SELECT 
                    ur.relationship_type,
                    ur.related_user_uuid,
                    u.full_name as related_user_name,
                    ur.created_at
                FROM user_relationships ur
                JOIN users u ON ur.related_user_uuid = u.uuid
                WHERE ur.user_uuid = ? AND u.is_active = TRUE
                ORDER BY ur.created_at DESC
            """, (user_uuid,))
            
            return [
                {
                    'relationship_type': row['relationship_type'],
                    'related_user_uuid': row['related_user_uuid'],
                    'related_user_name': row['related_user_name'],
                    'created_at': row['created_at']
                }
                for row in results
            ]
            
        except Exception as e:
            self.logger.error(f"Failed to get user relationships: {e}", extra={
                "module": "user_service",
                "function": "get_user_relationships",
                "topic": "user_management",
                "zmq_topic": "logs",
                "user_uuid": user_uuid,
                "error": str(e)
            })
            return []
