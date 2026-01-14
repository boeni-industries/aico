"""
User Service

Completes migration of shared/aico/data/user/service.py with repository-based implementation.
Provides high-level user operations using the 8 user/auth repositories.
"""

from __future__ import annotations

from datetime import datetime, UTC
from typing import Any, Dict, List, Optional

from aico.core.logging import get_logger
from aico.data.uow import UnitOfWork

logger = get_logger("shared.services.user")


class UserService:
    """
    Service layer for user and authentication operations.
    
    Handles user profiles, sessions, credentials, devices, and access policies.
    Uses user/auth repositories through Unit of Work pattern.
    """

    def __init__(self, uow: UnitOfWork):
        self.uow = uow

    # ==================== User Profile Operations ====================

    async def create_user(self, user_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new user profile."""
        try:
            from aico.ai.user.models import UserProfile
            
            user = UserProfile(**user_data)
            created = await self.uow.users.create(user)
            await self.uow.commit()
            
            logger.info("[USER_SERVICE] Created user", extra={"user_id": created.uuid})
            return created
        except Exception as e:
            logger.error(f"[USER_SERVICE] Failed to create user: {e}")
            await self.uow.rollback()
            raise

    async def get_user(self, user_id: str) -> Optional[Any]:
        """Retrieve a user by ID."""
        try:
            return await self.uow.users.get_by_id(user_id)
        except Exception as e:
            logger.error(f"[USER_SERVICE] Failed to retrieve user: {e}", extra={"user_id": user_id})
            raise

    async def get_user_by_email(self, email: str) -> Optional[Any]:
        """Retrieve a user by email."""
        try:
            users = await self.uow.users.list(filters={"email": email})
            return users[0] if users else None
        except Exception as e:
            logger.error(f"[USER_SERVICE] Failed to retrieve user by email: {e}", extra={"email": email})
            raise

    async def list_users(self, filters: Optional[Dict[str, Any]] = None, limit: int = 100) -> List[Any]:
        """List users with optional filters."""
        try:
            return await self.uow.users.list(filters=filters or {}, limit=limit)
        except Exception as e:
            logger.error(f"[USER_SERVICE] Failed to list users: {e}")
            raise

    async def update_user(self, user_data: Dict[str, Any]) -> Dict[str, Any]:
        """Update a user profile."""
        try:
            from aico.ai.user.models import UserProfile
            
            user = UserProfile(**user_data)
            user.updated_at = datetime.now(UTC)
            updated = await self.uow.users.update(user)
            await self.uow.commit()
            
            logger.info("[USER_SERVICE] Updated user", extra={"user_id": user.uuid})
            return updated
        except Exception as e:
            logger.error(f"[USER_SERVICE] Failed to update user: {e}")
            await self.uow.rollback()
            raise

    async def delete_user(self, user_id: str) -> bool:
        """Delete a user (soft delete - set is_active=False)."""
        try:
            user = await self.get_user(user_id)
            if not user:
                return False
            
            # Update is_active directly on the user object
            user.is_active = False
            updated = await self.uow.users.update(user)
            await self.uow.commit()
            
            logger.info("[USER_SERVICE] Deleted user", extra={"user_id": user_id})
            return True
        except Exception as e:
            logger.error(f"[USER_SERVICE] Failed to delete user: {e}", extra={"user_id": user_id})
            await self.uow.rollback()
            raise

    async def get_active_users(self) -> List[Any]:
        """Get all active users."""
        try:
            return await self.uow.users.list(filters={"is_active": True})
        except Exception as e:
            logger.error(f"[USER_SERVICE] Failed to get active users: {e}")
            raise

    # ==================== Session Operations ====================

    async def create_session(self, session_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new user session."""
        try:
            from aico.ai.auth.models import Session
            
            session = Session(**session_data)
            created = await self.uow.sessions.create(session)
            await self.uow.commit()
            
            logger.info("[USER_SERVICE] Created session", extra={"session_id": created.session_id, "user_id": created.user_id})
            return created
        except Exception as e:
            logger.error(f"[USER_SERVICE] Failed to create session: {e}")
            await self.uow.rollback()
            raise

    async def get_session(self, session_id: str) -> Optional[Any]:
        """Retrieve a session by ID."""
        try:
            return await self.uow.sessions.get_by_id(session_id)
        except Exception as e:
            logger.error(f"[USER_SERVICE] Failed to retrieve session: {e}", extra={"session_id": session_id})
            raise

    async def get_user_sessions(self, user_id: str, active_only: bool = True) -> List[Any]:
        """Get sessions for a user."""
        try:
            filters = {"user_id": user_id}
            if active_only:
                filters["is_active"] = True
            
            return await self.uow.sessions.list(filters=filters)
        except Exception as e:
            logger.error(f"[USER_SERVICE] Failed to get user sessions: {e}", extra={"user_id": user_id})
            raise

    async def invalidate_session(self, session_id: str) -> bool:
        """Invalidate a session."""
        try:
            session = await self.get_session(session_id)
            if not session:
                return False
            
            session.is_active = False
            session.expires_at = datetime.now(UTC)
            await self.uow.sessions.update(session)
            await self.uow.commit()
            
            logger.info("[USER_SERVICE] Invalidated session", extra={"session_id": session_id})
            return True
        except Exception as e:
            logger.error(f"[USER_SERVICE] Failed to invalidate session: {e}", extra={"session_id": session_id})
            await self.uow.rollback()
            raise

    async def invalidate_user_sessions(self, user_id: str) -> int:
        """Invalidate all sessions for a user."""
        try:
            sessions = await self.get_user_sessions(user_id, active_only=True)
            count = 0
            
            for session in sessions:
                await self.invalidate_session(session.session_id)
                count += 1
            
            logger.info(f"[USER_SERVICE] Invalidated {count} sessions for user", extra={"user_id": user_id})
            return count
        except Exception as e:
            logger.error(f"[USER_SERVICE] Failed to invalidate user sessions: {e}", extra={"user_id": user_id})
            raise

    # ==================== Credentials Operations ====================

    async def create_credentials(self, credentials_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create user credentials."""
        try:
            from aico.data.auth.models import UserCredentials
            
            credentials = UserCredentials(**credentials_data)
            created = await self.uow.credentials.create(credentials)
            await self.uow.commit()
            
            logger.info("[USER_SERVICE] Created credentials", extra={"user_id": created.user_id})
            return created
        except Exception as e:
            logger.error(f"[USER_SERVICE] Failed to create credentials: {e}")
            await self.uow.rollback()
            raise

    async def get_credentials(self, user_id: str) -> Optional[Any]:
        """Get credentials for a user."""
        try:
            return await self.uow.credentials.get_by_id(user_id)
        except Exception as e:
            logger.error(f"[USER_SERVICE] Failed to get credentials: {e}", extra={"user_id": user_id})
            raise

    async def update_credentials(self, credentials_data: Dict[str, Any]) -> Dict[str, Any]:
        """Update user credentials."""
        try:
            from aico.data.auth.models import UserCredentials
            
            credentials = UserCredentials(**credentials_data)
            credentials.updated_at = datetime.now(UTC)
            updated = await self.uow.credentials.update(credentials)
            await self.uow.commit()
            
            logger.info("[USER_SERVICE] Updated credentials", extra={"user_id": credentials.user_id})
            return updated
        except Exception as e:
            logger.error(f"[USER_SERVICE] Failed to update credentials: {e}")
            await self.uow.rollback()
            raise

    # ==================== Device Operations ====================

    async def register_device(self, device_data: Dict[str, Any]) -> Dict[str, Any]:
        """Register a user device."""
        try:
            from aico.data.auth.models import Device
            
            device = Device(**device_data)
            created = await self.uow.devices.create(device)
            await self.uow.commit()
            
            logger.info("[USER_SERVICE] Registered device", extra={"device_id": created.device_id, "user_id": created.user_id})
            return created
        except Exception as e:
            logger.error(f"[USER_SERVICE] Failed to register device: {e}")
            await self.uow.rollback()
            raise

    async def get_user_devices(self, user_id: str) -> List[Any]:
        """Get all devices for a user."""
        try:
            return await self.uow.devices.list(filters={"user_id": user_id})
        except Exception as e:
            logger.error(f"[USER_SERVICE] Failed to get user devices: {e}", extra={"user_id": user_id})
            raise

    async def revoke_device(self, device_id: str) -> bool:
        """Revoke a device."""
        try:
            success = await self.uow.devices.delete(device_id)
            await self.uow.commit()
            
            logger.info("[USER_SERVICE] Revoked device", extra={"device_id": device_id})
            return success
        except Exception as e:
            logger.error(f"[USER_SERVICE] Failed to revoke device: {e}", extra={"device_id": device_id})
            await self.uow.rollback()
            raise

    # ==================== Access Policy Operations ====================

    async def create_access_policy(self, policy_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create an access policy."""
        try:
            from aico.data.auth.access_models import AuthAccessPolicy
            
            policy = AuthAccessPolicy(**policy_data)
            created = await self.uow.auth_access_policies.create(policy)
            await self.uow.commit()
            
            logger.info("[USER_SERVICE] Created access policy", extra={"policy_id": created.uuid, "user_id": created.user_uuid})
            return created
        except Exception as e:
            logger.error(f"[USER_SERVICE] Failed to create access policy: {e}")
            await self.uow.rollback()
            raise

    async def get_user_policies(self, user_id: str, resource_type: Optional[str] = None) -> List[Any]:
        """Get access policies for a user."""
        try:
            filters = {"user_uuid": user_id, "is_active": True}
            if resource_type:
                filters["resource_type"] = resource_type
            
            return await self.uow.auth_access_policies.list(filters=filters)
        except Exception as e:
            logger.error(f"[USER_SERVICE] Failed to get user policies: {e}", extra={"user_id": user_id})
            raise

    async def check_permission(self, user_id: str, resource_type: str, permission: str, resource_uuid: Optional[str] = None) -> bool:
        """Check if user has permission for a resource."""
        try:
            filters = {
                "user_uuid": user_id,
                "resource_type": resource_type,
                "permission": permission,
                "is_active": True
            }
            if resource_uuid:
                filters["resource_uuid"] = resource_uuid
            
            policies = await self.uow.auth_access_policies.list(filters=filters)
            return len(policies) > 0
        except Exception as e:
            logger.error(f"[USER_SERVICE] Failed to check permission: {e}", extra={"user_id": user_id})
            raise

    # ==================== Analytics Operations ====================

    async def get_user_count(self) -> int:
        """Get total user count."""
        try:
            return await self.uow.users.count()
        except Exception as e:
            logger.error(f"[USER_SERVICE] Failed to count users: {e}")
            raise

    async def get_active_user_count(self) -> int:
        """Get active user count."""
        try:
            return await self.uow.users.count(filters={"is_active": True})
        except Exception as e:
            logger.error(f"[USER_SERVICE] Failed to count active users: {e}")
            raise

    async def get_active_session_count(self) -> int:
        """Get active session count."""
        try:
            return await self.uow.sessions.count(filters={"is_active": True})
        except Exception as e:
            logger.error(f"[USER_SERVICE] Failed to count active sessions: {e}")
            raise
