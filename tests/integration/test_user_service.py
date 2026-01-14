"""
Integration tests for UserService.

Tests user management service layer using actual repositories and database.
"""

import pytest
import uuid
from datetime import datetime, UTC

from aico.services.user_service import UserService
from aico.ai.user.models import UserProfile


@pytest.fixture
async def user_service(uow):
    """Create UserService with UnitOfWork."""
    return UserService(uow)


class TestUserService:
    """Test suite for UserService."""

    @pytest.mark.asyncio
    async def test_get_user(self, user_service, test_user):
        """Test retrieving a user."""
        retrieved = await user_service.get_user(test_user.uuid)
        
        assert retrieved is not None
        assert retrieved.uuid == test_user.uuid
        assert retrieved.full_name == test_user.full_name

    @pytest.mark.asyncio
    async def test_get_user_by_email(self, user_service, test_user):
        """Test retrieving user by email."""
        if test_user.email:
            retrieved = await user_service.get_user_by_email(test_user.email)
            assert retrieved is not None
            assert retrieved.uuid == test_user.uuid

    @pytest.mark.asyncio
    async def test_list_users(self, user_service, test_user):
        """Test listing all users."""
        users = await user_service.list_users()
        
        assert len(users) >= 1
        assert any(u.uuid == test_user.uuid for u in users)

    @pytest.mark.asyncio
    async def test_get_active_users(self, user_service, test_user):
        """Test getting active users."""
        users = await user_service.get_active_users()
        
        assert len(users) >= 1
        assert any(u.uuid == test_user.uuid for u in users)

    @pytest.mark.asyncio
    async def test_create_user(self, user_service):
        """Test creating a new user."""
        from aico.ai.user.models import UserType
        
        user_data = {
            "uuid": str(uuid.uuid4()),
            "full_name": "New Test User",
            "nickname": "newuser",
            "user_type": UserType.HUMAN,
            "email": f"newuser_{uuid.uuid4().hex[:8]}@test.com",
            "primary_language": "en",
            "is_active": True,
            "created_at": datetime.now(UTC),
            "updated_at": datetime.now(UTC),
        }
        
        created = await user_service.create_user(user_data)
        assert created.uuid == user_data["uuid"]
        assert created.full_name == "New Test User"

    @pytest.mark.asyncio
    async def test_update_user(self, user_service, test_user):
        """Test updating a user."""
        user_data = {
            "uuid": test_user.uuid,
            "full_name": "Updated Name",
            "nickname": test_user.nickname,
            "user_type": test_user.user_type,
            "primary_language": test_user.primary_language,
            "is_active": test_user.is_active,
        }
        
        updated = await user_service.update_user(user_data)
        assert updated.full_name == "Updated Name"

    @pytest.mark.asyncio
    async def test_delete_user(self, user_service):
        """Test deleting (deactivating) a user."""
        from aico.ai.user.models import UserType
        
        user_data = {
            "uuid": str(uuid.uuid4()),
            "full_name": "User to Delete",
            "user_type": UserType.HUMAN,
            "primary_language": "en",
            "is_active": True,
            "created_at": datetime.now(UTC),
            "updated_at": datetime.now(UTC),
        }
        created = await user_service.create_user(user_data)
        
        success = await user_service.delete_user(created.uuid)
        assert success is True
        
        # Verify user is deactivated by fetching again
        deactivated = await user_service.get_user(created.uuid)
        assert deactivated is not None
        assert deactivated.is_active is False

    @pytest.mark.asyncio
    async def test_create_session(self, user_service, test_user):
        """Test creating a user session."""
        from datetime import timedelta
        session_data = {
            "session_id": str(uuid.uuid4()),
            "user_id": test_user.uuid,
            "device_id": str(uuid.uuid4()),
            "is_active": True,
            "jwt_token_hash": "test_hash_" + str(uuid.uuid4()),
            "expires_at": datetime.now(UTC) + timedelta(hours=24),
            "created_at": datetime.now(UTC),
        }
        
        created = await user_service.create_session(session_data)
        assert created.session_id == session_data["session_id"]
        assert created.user_id == test_user.uuid

    @pytest.mark.asyncio
    async def test_invalidate_session(self, user_service, test_user):
        """Test invalidating a session."""
        from datetime import timedelta
        session_data = {
            "session_id": str(uuid.uuid4()),
            "user_id": test_user.uuid,
            "device_id": str(uuid.uuid4()),
            "is_active": True,
            "jwt_token_hash": "test_hash_" + str(uuid.uuid4()),
            "expires_at": datetime.now(UTC) + timedelta(hours=24),
            "created_at": datetime.now(UTC),
        }
        created = await user_service.create_session(session_data)
        
        success = await user_service.invalidate_session(created.session_id)
        assert success is True
        
        invalidated = await user_service.get_session(created.session_id)
        assert invalidated.is_active is False
