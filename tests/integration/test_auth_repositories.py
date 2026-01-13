"""
Integration tests for authentication repositories (Session and Credentials).

Tests the SessionRepository and CredentialsRepository with real PostgreSQL database.
"""

import pytest
import uuid
from datetime import datetime, timedelta, UTC

from aico.data.auth.models import Session, UserCredentials
from aico.data.user.models import UserProfile
from aico.data.postgres.connection import get_session_factory
from aico.data.uow import UnitOfWork


@pytest.fixture
async def session_factory():
    """Create async session factory for tests."""
    factory = await get_session_factory()
    return factory


@pytest.fixture
async def uow(session_factory):
    """Create Unit of Work for tests."""
    uow = UnitOfWork(session_factory)
    async with uow:
        yield uow


@pytest.fixture
async def test_user(uow):
    """Create a test user for auth tests."""
    user = UserProfile(
        uuid=str(uuid.uuid4()),
        full_name="Auth Test User",
        nickname="auth_tester",
        user_type="parent",
        is_active=True,
        primary_language="en",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    await uow.users.create(user)
    await uow.commit()
    return user


class TestSessionRepository:
    """Test SessionRepository CRUD operations."""
    
    @pytest.mark.asyncio
    async def test_create_session(self, uow, test_user):
        """Test creating a new session."""
        session = Session(
            uuid=str(uuid.uuid4()),
            user_uuid=test_user.uuid,
            device_uuid=str(uuid.uuid4()),
            jwt_token_hash="test_hash_123",
            expires_at=datetime.now(UTC) + timedelta(hours=24),
            created_at=datetime.now(UTC),
            is_active=True,
            session_type="unified",
        )
        
        created = await uow.sessions.create(session)
        await uow.commit()
        
        assert created.uuid == session.uuid
        assert created.user_uuid == test_user.uuid
    
    @pytest.mark.asyncio
    async def test_get_session_by_id(self, uow, test_user):
        """Test retrieving session by ID."""
        session = Session(
            uuid=str(uuid.uuid4()),
            user_uuid=test_user.uuid,
            device_uuid=str(uuid.uuid4()),
            jwt_token_hash="test_hash_456",
            expires_at=datetime.now(UTC) + timedelta(hours=24),
            created_at=datetime.now(UTC),
        )
        
        await uow.sessions.create(session)
        await uow.commit()
        
        found = await uow.sessions.get_by_id(session.uuid)
        assert found is not None
        assert found.uuid == session.uuid
        assert found.jwt_token_hash == "test_hash_456"
    
    @pytest.mark.asyncio
    async def test_get_active_sessions_for_user(self, uow, test_user):
        """Test getting all active sessions for a user."""
        # Create multiple sessions
        for i in range(3):
            session = Session(
                uuid=str(uuid.uuid4()),
                user_uuid=test_user.uuid,
                device_uuid=str(uuid.uuid4()),
                jwt_token_hash=f"hash_{i}",
                expires_at=datetime.now(UTC) + timedelta(hours=24),
                created_at=datetime.now(UTC),
                is_active=True,
            )
            await uow.sessions.create(session)
        
        await uow.commit()
        
        active_sessions = await uow.sessions.get_active_sessions_for_user(test_user.uuid)
        assert len(active_sessions) >= 3
        assert all(s.is_active for s in active_sessions)
    
    @pytest.mark.asyncio
    async def test_invalidate_session(self, uow, test_user):
        """Test invalidating a session."""
        session = Session(
            uuid=str(uuid.uuid4()),
            user_uuid=test_user.uuid,
            device_uuid=str(uuid.uuid4()),
            jwt_token_hash="test_hash_789",
            expires_at=datetime.now(UTC) + timedelta(hours=24),
            created_at=datetime.now(UTC),
            is_active=True,
        )
        
        await uow.sessions.create(session)
        await uow.commit()
        
        # Invalidate the session
        success = await uow.sessions.invalidate_session(session.uuid)
        await uow.commit()
        
        assert success is True
        
        # Verify it's invalidated
        found = await uow.sessions.get_by_id(session.uuid)
        assert found.is_active is False
    
    @pytest.mark.asyncio
    async def test_invalidate_all_user_sessions(self, uow, test_user):
        """Test invalidating all sessions for a user."""
        # Create multiple sessions
        session_ids = []
        for i in range(3):
            session = Session(
                uuid=str(uuid.uuid4()),
                user_uuid=test_user.uuid,
                device_uuid=str(uuid.uuid4()),
                jwt_token_hash=f"test_hash_{i}",
                expires_at=datetime.now(UTC) + timedelta(hours=24),
                created_at=datetime.now(UTC),
            )
            await uow.sessions.create(session)
            session_ids.append(session.uuid)
        
        await uow.commit()
        
        # Invalidate all sessions
        count = await uow.sessions.invalidate_all_user_sessions(test_user.uuid)
        await uow.commit()
        
        assert count >= 3
        
        # Verify all sessions are inactive
        for session_id in session_ids:
            session = await uow.sessions.get_by_id(session_id)
            assert session.is_active is False
    
    @pytest.mark.asyncio
    async def test_update_session(self, uow, test_user):
        """Test updating a session."""
        session = Session(
            uuid=str(uuid.uuid4()),
            user_uuid=test_user.uuid,
            device_uuid=str(uuid.uuid4()),
            jwt_token_hash="original_hash",
            expires_at=datetime.now(UTC) + timedelta(hours=24),
            created_at=datetime.now(UTC),
        )
        
        await uow.sessions.create(session)
        await uow.commit()
        
        # Update the session
        session.jwt_token_hash = "updated_hash"
        session.is_active = False
        updated = await uow.sessions.update(session)
        await uow.commit()
        
        assert updated.jwt_token_hash == "updated_hash"
        
        # Verify update persisted
        found = await uow.sessions.get_by_id(session.uuid)
        assert found.jwt_token_hash == "updated_hash"
        assert found.is_active is False
    
    @pytest.mark.asyncio
    async def test_delete_session(self, uow, test_user):
        """Test deleting a session."""
        session = Session(
            uuid=str(uuid.uuid4()),
            user_uuid=test_user.uuid,
            device_uuid=str(uuid.uuid4()),
            jwt_token_hash="to_delete",
            expires_at=datetime.now(UTC) + timedelta(hours=24),
            created_at=datetime.now(UTC),
        )
        
        await uow.sessions.create(session)
        await uow.commit()
        
        # Delete the session
        success = await uow.sessions.delete(session.uuid)
        await uow.commit()
        
        assert success is True
        
        # Verify it's gone
        found = await uow.sessions.get_by_id(session.uuid)
        assert found is None
    
    @pytest.mark.asyncio
    async def test_list_sessions(self, uow, test_user):
        """Test listing sessions with filters."""
        # Create multiple sessions with different states
        for i in range(3):
            session = Session(
                uuid=str(uuid.uuid4()),
                user_uuid=test_user.uuid,
                device_uuid=str(uuid.uuid4()),
                jwt_token_hash=f"list_hash_{i}",
                expires_at=datetime.now(UTC) + timedelta(hours=24),
                created_at=datetime.now(UTC),
                is_active=i < 2,  # First 2 active, last one inactive
            )
            await uow.sessions.create(session)
        
        await uow.commit()
        
        # List all sessions for user
        all_sessions = await uow.sessions.list(filters={"user_uuid": test_user.uuid})
        assert len(all_sessions) >= 3
        
        # List only active sessions
        active_sessions = await uow.sessions.list(filters={"user_uuid": test_user.uuid, "is_active": True})
        assert len(active_sessions) >= 2
    
    @pytest.mark.asyncio
    async def test_count_sessions(self, uow, test_user):
        """Test counting sessions."""
        # Create multiple sessions
        for i in range(3):
            session = Session(
                uuid=str(uuid.uuid4()),
                user_uuid=test_user.uuid,
                device_uuid=str(uuid.uuid4()),
                jwt_token_hash=f"count_hash_{i}",
                expires_at=datetime.now(UTC) + timedelta(hours=24),
                created_at=datetime.now(UTC),
            )
            await uow.sessions.create(session)
        
        await uow.commit()
        
        # Count all sessions for user
        count = await uow.sessions.count(filters={"user_uuid": test_user.uuid})
        assert count >= 3


class TestCredentialsRepository:
    """Test CredentialsRepository CRUD operations."""
    
    @pytest.mark.asyncio
    async def test_create_credentials(self, uow, test_user):
        """Test creating user credentials."""
        credentials = UserCredentials(
            uuid=str(uuid.uuid4()),
            user_uuid=test_user.uuid,
            pin_hash="hashed_pin_123",
            failed_attempts=0,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        
        created = await uow.credentials.create(credentials)
        await uow.commit()
        
        assert created.uuid == credentials.uuid
        assert created.user_uuid == test_user.uuid
        assert created.pin_hash == "hashed_pin_123"
    
    @pytest.mark.asyncio
    async def test_get_credentials_by_user_uuid(self, uow, test_user):
        """Test retrieving credentials by user UUID."""
        credentials = UserCredentials(
            uuid=str(uuid.uuid4()),
            user_uuid=test_user.uuid,
            pin_hash="hashed_pin_456",
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        
        await uow.credentials.create(credentials)
        await uow.commit()
        
        found = await uow.credentials.get_by_user_uuid(test_user.uuid)
        assert found is not None
        assert found.user_uuid == test_user.uuid
        assert found.pin_hash == "hashed_pin_456"
    
    @pytest.mark.asyncio
    async def test_increment_failed_attempts(self, uow, test_user):
        """Test incrementing failed login attempts."""
        credentials = UserCredentials(
            uuid=str(uuid.uuid4()),
            user_uuid=test_user.uuid,
            pin_hash="hashed_pin_789",
            failed_attempts=0,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        
        await uow.credentials.create(credentials)
        await uow.commit()
        
        # Increment attempts
        new_count = await uow.credentials.increment_failed_attempts(test_user.uuid)
        await uow.commit()
        
        assert new_count == 1
        
        # Verify it was incremented
        found = await uow.credentials.get_by_user_uuid(test_user.uuid)
        assert found.failed_attempts == 1
    
    @pytest.mark.asyncio
    async def test_reset_failed_attempts(self, uow, test_user):
        """Test resetting failed login attempts."""
        credentials = UserCredentials(
            uuid=str(uuid.uuid4()),
            user_uuid=test_user.uuid,
            pin_hash="hashed_pin_reset",
            failed_attempts=5,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        
        await uow.credentials.create(credentials)
        await uow.commit()
        
        # Reset attempts
        success = await uow.credentials.reset_failed_attempts(test_user.uuid)
        await uow.commit()
        
        assert success is True
        
        # Verify it was reset
        found = await uow.credentials.get_by_user_uuid(test_user.uuid)
        assert found.failed_attempts == 0
    
    @pytest.mark.asyncio
    async def test_lock_and_unlock_account(self, uow, test_user):
        """Test locking and unlocking user account."""
        credentials = UserCredentials(
            uuid=str(uuid.uuid4()),
            user_uuid=test_user.uuid,
            pin_hash="hashed_pin_lock",
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        
        await uow.credentials.create(credentials)
        await uow.commit()
        
        # Lock account
        lock_until = datetime.now(UTC) + timedelta(hours=1)
        success = await uow.credentials.lock_account(test_user.uuid, lock_until)
        await uow.commit()
        
        assert success is True
        
        # Verify it's locked
        found = await uow.credentials.get_by_user_uuid(test_user.uuid)
        assert found.locked_until is not None
        
        # Unlock account
        success = await uow.credentials.unlock_account(test_user.uuid)
        await uow.commit()
        
        assert success is True
        
        # Verify it's unlocked
        found = await uow.credentials.get_by_user_uuid(test_user.uuid)
        assert found.locked_until is None
        assert found.failed_attempts == 0
    
    @pytest.mark.asyncio
    async def test_update_last_login(self, uow, test_user):
        """Test updating last login timestamp."""
        credentials = UserCredentials(
            uuid=str(uuid.uuid4()),
            user_uuid=test_user.uuid,
            pin_hash="hashed_pin_login",
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        
        await uow.credentials.create(credentials)
        await uow.commit()
        
        # Update last login
        success = await uow.credentials.update_last_login(test_user.uuid)
        await uow.commit()
        
        assert success is True
        
        # Verify it was updated
        found = await uow.credentials.get_by_user_uuid(test_user.uuid)
        assert found.last_login is not None
    
    @pytest.mark.asyncio
    async def test_update_credentials(self, uow, test_user):
        """Test updating credentials."""
        credentials = UserCredentials(
            uuid=str(uuid.uuid4()),
            user_uuid=test_user.uuid,
            pin_hash="original_hash",
            failed_attempts=0,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        
        await uow.credentials.create(credentials)
        await uow.commit()
        
        # Update the credentials
        credentials.pin_hash = "new_hash"
        credentials.failed_attempts = 2
        updated = await uow.credentials.update(credentials)
        await uow.commit()
        
        assert updated.pin_hash == "new_hash"
        
        # Verify update persisted
        found = await uow.credentials.get_by_user_uuid(test_user.uuid)
        assert found.pin_hash == "new_hash"
        assert found.failed_attempts == 2
    
    @pytest.mark.asyncio
    async def test_delete_credentials(self, uow, test_user):
        """Test deleting credentials."""
        credentials = UserCredentials(
            uuid=str(uuid.uuid4()),
            user_uuid=test_user.uuid,
            pin_hash="to_delete",
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        
        await uow.credentials.create(credentials)
        await uow.commit()
        
        # Delete the credentials
        success = await uow.credentials.delete(credentials.uuid)
        await uow.commit()
        
        assert success is True
        
        # Verify it's gone
        found = await uow.credentials.get_by_id(credentials.uuid)
        assert found is None
    
    @pytest.mark.asyncio
    async def test_list_credentials(self, uow):
        """Test listing credentials with filters."""
        # Create multiple users with credentials
        user_ids = []
        for i in range(3):
            user = UserProfile(
                uuid=str(uuid.uuid4()),
                full_name=f"Creds List User {i}",
                nickname=f"creds_list_{i}",
                user_type="parent",
                is_active=True,
                primary_language="en",
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC),
            )
            await uow.users.create(user)
            user_ids.append(user.uuid)
            
            credentials = UserCredentials(
                uuid=str(uuid.uuid4()),
                user_uuid=user.uuid,
                pin_hash=f"list_hash_{i}",
                failed_attempts=i,
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC),
            )
            await uow.credentials.create(credentials)
        
        await uow.commit()
        
        # List all credentials
        all_creds = await uow.credentials.list(limit=10)
        assert len(all_creds) >= 3
    
    @pytest.mark.asyncio
    async def test_count_credentials(self, uow):
        """Test counting credentials."""
        # Create multiple users with credentials
        for i in range(3):
            user = UserProfile(
                uuid=str(uuid.uuid4()),
                full_name=f"Creds Count User {i}",
                nickname=f"creds_count_{i}",
                user_type="parent",
                is_active=True,
                primary_language="en",
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC),
            )
            await uow.users.create(user)
            
            credentials = UserCredentials(
                uuid=str(uuid.uuid4()),
                user_uuid=user.uuid,
                pin_hash=f"count_hash_{i}",
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC),
            )
            await uow.credentials.create(credentials)
        
        await uow.commit()
        
        # Count all credentials
        count = await uow.credentials.count()
        assert count >= 3
