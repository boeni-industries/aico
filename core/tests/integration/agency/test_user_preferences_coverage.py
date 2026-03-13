"""
User Preferences Coverage Tests

Tests for UserPreferencesManager to improve coverage.
"""

import pytest
from datetime import datetime, UTC, timedelta
import uuid

from aico.ai.agency.skills.communication.user_preferences import (
    UserPreferencesManager,
    load_user_preferences
)


@pytest.mark.asyncio
class TestUserPreferencesManager:
    """Test suite for UserPreferencesManager."""
    
    async def test_default_preferences(self, test_db):
        """Test that default preferences are returned."""
        from aico.data.postgres.connection import get_session_factory
        session_factory = await get_session_factory()
        manager = UserPreferencesManager(session_factory)
        
        # Test defaults
        assert manager.DEFAULT_PREFERENCES['enabled'] is True
        assert manager.DEFAULT_PREFERENCES['max_initiations_per_day'] == 5
        assert manager.DEFAULT_PREFERENCES['max_pending'] == 2
        assert manager.DEFAULT_PREFERENCES['min_hours_between'] == 6
    
    async def test_get_preferences_for_existing_user(self, test_db, test_user):
        """Test getting preferences for existing user."""
        from aico.data.postgres.connection import get_session_factory
        session_factory = await get_session_factory()
        manager = UserPreferencesManager(session_factory)
        
        prefs = await manager.get_preferences(test_user)
        
        assert prefs is not None
        assert 'enabled' in prefs
        assert 'max_initiations_per_day' in prefs
        assert 'quiet_hours' in prefs
    
    async def test_get_preferences_for_nonexistent_user(self, test_db):
        """Test getting preferences for non-existent user returns defaults."""
        from aico.data.postgres.connection import get_session_factory
        session_factory = await get_session_factory()
        manager = UserPreferencesManager(session_factory)
        
        prefs = await manager.get_preferences(str(uuid.uuid4()))
        
        assert prefs == manager.DEFAULT_PREFERENCES
    
    async def test_preferences_caching(self, test_db, test_user):
        """Test that preferences are cached."""
        from aico.data.postgres.connection import get_session_factory
        session_factory = await get_session_factory()
        manager = UserPreferencesManager(session_factory)
        
        # First call - loads from DB
        prefs1 = await manager.get_preferences(test_user)
        
        # Second call - should use cache
        prefs2 = await manager.get_preferences(test_user)
        
        assert prefs1 == prefs2
        assert test_user in manager._cache
        assert test_user in manager._cache_timestamps
    
    async def test_cache_expiration(self, test_db, test_user):
        """Test that cache expires after TTL."""
        from aico.data.postgres.connection import get_session_factory
        session_factory = await get_session_factory()
        manager = UserPreferencesManager(session_factory)
        manager._cache_ttl_seconds = 1  # 1 second TTL
        
        # First call
        prefs1 = await manager.get_preferences(test_user)
        
        # Manually expire cache
        manager._cache_timestamps[test_user] = datetime.now(UTC) - timedelta(seconds=2)
        
        # Second call - should reload from DB
        prefs2 = await manager.get_preferences(test_user)
        
        assert prefs1 == prefs2  # Same values but reloaded
    
    async def test_is_quiet_hour(self, test_db, test_user):
        """Test quiet hour checking."""
        from aico.data.postgres.connection import get_session_factory
        session_factory = await get_session_factory()
        manager = UserPreferencesManager(session_factory)
        
        # Default has no quiet hours
        assert await manager.is_quiet_hour(test_user, 0) is False
        assert await manager.is_quiet_hour(test_user, 12) is False
        assert await manager.is_quiet_hour(test_user, 23) is False
    
    async def test_is_quiet_hour_with_custom_hours(self, test_db, test_user):
        """Test quiet hour checking with custom hours."""
        from aico.data.postgres.connection import get_session_factory
        session_factory = await get_session_factory()
        manager = UserPreferencesManager(session_factory)
        
        # Manually set quiet hours in cache
        manager._cache[test_user] = {
            **manager.DEFAULT_PREFERENCES,
            'quiet_hours': [22, 23, 0, 1, 2, 3, 4, 5, 6]  # 10pm - 6am
        }
        manager._cache_timestamps[test_user] = datetime.now(UTC)
        
        assert await manager.is_quiet_hour(test_user, 23) is True
        assert await manager.is_quiet_hour(test_user, 12) is False
        assert await manager.is_quiet_hour(test_user, 3) is True
    
    async def test_is_enabled(self, test_db, test_user):
        """Test checking if proactive conversations are enabled."""
        from aico.data.postgres.connection import get_session_factory
        session_factory = await get_session_factory()
        manager = UserPreferencesManager(session_factory)
        
        # Default is enabled
        assert await manager.is_enabled(test_user) is True
    
    async def test_is_enabled_when_disabled(self, test_db, test_user):
        """Test checking when proactive conversations are disabled."""
        from aico.data.postgres.connection import get_session_factory
        session_factory = await get_session_factory()
        manager = UserPreferencesManager(session_factory)
        
        # Manually set disabled in cache
        manager._cache[test_user] = {
            **manager.DEFAULT_PREFERENCES,
            'enabled': False
        }
        manager._cache_timestamps[test_user] = datetime.now(UTC)
        
        assert await manager.is_enabled(test_user) is False
    
    async def test_get_max_initiations_per_day(self, test_db, test_user):
        """Test getting max initiations per day."""
        from aico.data.postgres.connection import get_session_factory
        session_factory = await get_session_factory()
        manager = UserPreferencesManager(session_factory)
        
        max_init = await manager.get_max_initiations_per_day(test_user)
        
        assert max_init == 5  # Default value
    
    async def test_get_max_pending(self, test_db, test_user):
        """Test getting max pending initiations."""
        from aico.data.postgres.connection import get_session_factory
        session_factory = await get_session_factory()
        manager = UserPreferencesManager(session_factory)
        
        max_pending = await manager.get_max_pending(test_user)
        
        assert max_pending == 2  # Default value
    
    async def test_get_min_hours_between(self, test_db, test_user):
        """Test getting min hours between initiations."""
        from aico.data.postgres.connection import get_session_factory
        session_factory = await get_session_factory()
        manager = UserPreferencesManager(session_factory)
        
        min_hours = await manager.get_min_hours_between(test_user)
        
        assert min_hours == 6.0  # Default value
    
    async def test_clear_cache_specific_user(self, test_db, test_user):
        """Test clearing cache for specific user."""
        from aico.data.postgres.connection import get_session_factory
        session_factory = await get_session_factory()
        manager = UserPreferencesManager(session_factory)
        
        # Load preferences to populate cache
        await manager.get_preferences(test_user)
        assert test_user in manager._cache
        
        # Clear cache for this user
        manager.clear_cache(test_user)
        
        assert test_user not in manager._cache
        assert test_user not in manager._cache_timestamps
    
    async def test_clear_cache_all_users(self, test_db, test_user):
        """Test clearing cache for all users."""
        from aico.data.postgres.connection import get_session_factory
        session_factory = await get_session_factory()
        manager = UserPreferencesManager(session_factory)
        
        # Load preferences for multiple users
        user2 = str(uuid.uuid4())
        await manager.get_preferences(test_user)
        manager._cache[user2] = manager.DEFAULT_PREFERENCES.copy()
        manager._cache_timestamps[user2] = datetime.now(UTC)
        
        # Clear all cache
        manager.clear_cache()
        
        assert len(manager._cache) == 0
        assert len(manager._cache_timestamps) == 0
    
    async def test_database_error_handling(self, test_db, test_user):
        """Test that database errors are handled gracefully."""
        from aico.data.postgres.connection import get_session_factory
        session_factory = await get_session_factory()
        manager = UserPreferencesManager(session_factory)
        
        # Should return defaults without crashing
        prefs = await manager.get_preferences(test_user)
        
        assert prefs == manager.DEFAULT_PREFERENCES
    
    async def test_load_user_preferences_convenience_function(self, test_db, test_user):
        """Test the convenience function for loading preferences."""
        from aico.data.postgres.connection import get_session_factory
        session_factory = await get_session_factory()
        prefs = await load_user_preferences(session_factory, test_user)
        
        assert prefs is not None
        assert 'enabled' in prefs
        assert 'max_initiations_per_day' in prefs
    
    async def test_custom_cache_ttl(self, test_db, test_user):
        """Test that custom cache TTL is respected."""
        from aico.data.postgres.connection import get_session_factory
        session_factory = await get_session_factory()
        manager = UserPreferencesManager(session_factory)
        
        # Verify default TTL
        assert manager._cache_ttl_seconds == 300  # 5 minutes
        
        # Can be customized
        manager._cache_ttl_seconds = 60
        assert manager._cache_ttl_seconds == 60
