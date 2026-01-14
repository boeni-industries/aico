"""
Integration tests for UserProactivePreferencesRepository.

Tests UserProactivePreferencesRepository with real PostgreSQL database.
"""

import pytest
import uuid
from datetime import datetime, UTC

from aico.data.user.proactive_models import UserProactivePreferences
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
    """Create a test user for preferences tests."""
    user = UserProfile(
        uuid=str(uuid.uuid4()),
        full_name="Proactive Prefs Test User",
        nickname="prefs_tester",
        user_type="parent",
        is_active=True,
        primary_language="en",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    await uow.users.create(user)
    await uow.commit()
    return user


class TestUserProactivePreferencesRepository:
    """Test UserProactivePreferencesRepository CRUD operations."""
    
    @pytest.mark.asyncio
    async def test_create_preferences(self, uow, test_user):
        """Test creating new user proactive preferences."""
        prefs = UserProactivePreferences(
            user_id=test_user.uuid,
            followup_enabled=True,
            reminder_enabled=True,
            max_followups_per_day=5,
            max_reminders_per_day=10,
            updated_at=datetime.now(UTC).isoformat(),
        )
        
        created = await uow.user_proactive_preferences.create(prefs)
        await uow.commit()
        
        assert created.user_id == test_user.uuid
        assert created.followup_enabled is True
        assert created.max_followups_per_day == 5
    
    @pytest.mark.asyncio
    async def test_get_preferences_by_id(self, uow, test_user):
        """Test retrieving preferences by user ID."""
        prefs = UserProactivePreferences(
            user_id=test_user.uuid,
            followup_enabled=False,
            reminder_enabled=True,
            updated_at=datetime.now(UTC).isoformat(),
        )
        
        await uow.user_proactive_preferences.create(prefs)
        await uow.commit()
        
        found = await uow.user_proactive_preferences.get_by_id(test_user.uuid)
        assert found is not None
        assert found.user_id == test_user.uuid
        assert found.followup_enabled is False
    
    @pytest.mark.asyncio
    async def test_update_preferences(self, uow, test_user):
        """Test updating user preferences."""
        prefs = UserProactivePreferences(
            user_id=test_user.uuid,
            followup_enabled=True,
            max_followups_per_day=3,
            updated_at=datetime.now(UTC).isoformat(),
        )
        
        await uow.user_proactive_preferences.create(prefs)
        await uow.commit()
        
        # Update preferences
        prefs.followup_enabled = False
        prefs.max_followups_per_day = 10
        updated = await uow.user_proactive_preferences.update(prefs)
        await uow.commit()
        
        assert updated.followup_enabled is False
        
        # Verify update persisted
        found = await uow.user_proactive_preferences.get_by_id(test_user.uuid)
        assert found.max_followups_per_day == 10
    
    @pytest.mark.asyncio
    async def test_delete_preferences(self, uow, test_user):
        """Test deleting user preferences."""
        prefs = UserProactivePreferences(
            user_id=test_user.uuid,
            followup_enabled=True,
            updated_at=datetime.now(UTC).isoformat(),
        )
        
        await uow.user_proactive_preferences.create(prefs)
        await uow.commit()
        
        # Delete preferences
        success = await uow.user_proactive_preferences.delete(test_user.uuid)
        await uow.commit()
        
        assert success is True
        
        # Verify it's gone
        found = await uow.user_proactive_preferences.get_by_id(test_user.uuid)
        assert found is None
    
    @pytest.mark.asyncio
    async def test_list_preferences(self, uow):
        """Test listing preferences with filters."""
        users = []
        for i in range(3):
            user = UserProfile(
                uuid=str(uuid.uuid4()),
                full_name=f"List Test User {i}",
                nickname=f"list_user_{i}",
                user_type="parent",
                is_active=True,
                primary_language="en",
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC),
            )
            await uow.users.create(user)
            users.append(user)
            
            prefs = UserProactivePreferences(
                user_id=user.uuid,
                followup_enabled=i < 2,
                reminder_enabled=True,
                updated_at=datetime.now(UTC).isoformat(),
            )
            await uow.user_proactive_preferences.create(prefs)
        
        await uow.commit()
        
        # List all preferences
        all_prefs = await uow.user_proactive_preferences.list()
        assert len(all_prefs) >= 3
        
        # List with followup enabled
        followup_prefs = await uow.user_proactive_preferences.list(filters={"followup_enabled": True})
        assert len(followup_prefs) >= 2
    
    @pytest.mark.asyncio
    async def test_count_preferences(self, uow):
        """Test counting preferences."""
        users = []
        for i in range(3):
            user = UserProfile(
                uuid=str(uuid.uuid4()),
                full_name=f"Count Test User {i}",
                nickname=f"count_user_{i}",
                user_type="parent",
                is_active=True,
                primary_language="en",
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC),
            )
            await uow.users.create(user)
            
            prefs = UserProactivePreferences(
                user_id=user.uuid,
                followup_enabled=True,
                updated_at=datetime.now(UTC).isoformat(),
            )
            await uow.user_proactive_preferences.create(prefs)
        
        await uow.commit()
        
        count = await uow.user_proactive_preferences.count()
        assert count >= 3
    
    @pytest.mark.asyncio
    async def test_get_users_with_followups_enabled(self, uow):
        """Test getting users with followups enabled."""
        users = []
        for i in range(3):
            user = UserProfile(
                uuid=str(uuid.uuid4()),
                full_name=f"Followup Test User {i}",
                nickname=f"followup_user_{i}",
                user_type="parent",
                is_active=True,
                primary_language="en",
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC),
            )
            await uow.users.create(user)
            
            prefs = UserProactivePreferences(
                user_id=user.uuid,
                followup_enabled=i < 2,
                updated_at=datetime.now(UTC).isoformat(),
            )
            await uow.user_proactive_preferences.create(prefs)
        
        await uow.commit()
        
        followup_users = await uow.user_proactive_preferences.get_users_with_followups_enabled()
        assert len(followup_users) >= 2
        for prefs in followup_users:
            assert prefs.followup_enabled is True
    
    @pytest.mark.asyncio
    async def test_get_users_with_reminders_enabled(self, uow):
        """Test getting users with reminders enabled."""
        users = []
        for i in range(3):
            user = UserProfile(
                uuid=str(uuid.uuid4()),
                full_name=f"Reminder Test User {i}",
                nickname=f"reminder_user_{i}",
                user_type="parent",
                is_active=True,
                primary_language="en",
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC),
            )
            await uow.users.create(user)
            
            prefs = UserProactivePreferences(
                user_id=user.uuid,
                reminder_enabled=i < 2,
                updated_at=datetime.now(UTC).isoformat(),
            )
            await uow.user_proactive_preferences.create(prefs)
        
        await uow.commit()
        
        reminder_users = await uow.user_proactive_preferences.get_users_with_reminders_enabled()
        assert len(reminder_users) >= 2
        for prefs in reminder_users:
            assert prefs.reminder_enabled is True
