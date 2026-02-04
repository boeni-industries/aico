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
    
    def test_default_preferences(self, test_db):
        """Test that default preferences are returned."""
        manager = UserPreferencesManager(test_db)
        
        # Test defaults
        assert manager.DEFAULT_PREFERENCES['enabled'] is True
        assert manager.DEFAULT_PREFERENCES['max_initiations_per_day'] == 5
        assert manager.DEFAULT_PREFERENCES['max_pending'] == 2
        assert manager.DEFAULT_PREFERENCES['min_hours_between'] == 6
    
    def test_get_preferences_for_existing_user(self, test_db, test_user):
        """Test getting preferences for existing user."""
        manager = UserPreferencesManager(test_db)
        
        prefs = manager.get_preferences(test_user)
        
        assert prefs is not None
        assert 'enabled' in prefs
        assert 'max_initiations_per_day' in prefs
        assert 'quiet_hours' in prefs
    
    def test_get_preferences_for_nonexistent_user(self, test_db):
        """Test getting preferences for non-existent user returns defaults."""
        manager = UserPreferencesManager(test_db)
        
        prefs = manager.get_preferences(str(uuid.uuid4()))
        
        assert prefs == manager.DEFAULT_PREFERENCES
    
    def test_preferences_caching(self, test_db, test_user):
        """Test that preferences are cached."""
        manager = UserPreferencesManager(test_db)
        
        # First call - loads from DB
        prefs1 = manager.get_preferences(test_user)
        
        # Second call - should use cache
        prefs2 = manager.get_preferences(test_user)
        
        assert prefs1 == prefs2
        assert test_user in manager._cache
        assert test_user in manager._cache_timestamps
    
    def test_cache_expiration(self, test_db, test_user):
        """Test that cache expires after TTL."""
        manager = UserPreferencesManager(test_db)
        manager._cache_ttl_seconds = 1  # 1 second TTL
        
        # First call
        prefs1 = manager.get_preferences(test_user)
        
        # Manually expire cache
        manager._cache_timestamps[test_user] = datetime.now(UTC) - timedelta(seconds=2)
        
        # Second call - should reload from DB
        prefs2 = manager.get_preferences(test_user)
        
        assert prefs1 == prefs2  # Same values but reloaded
    
    def test_is_quiet_hour(self, test_db, test_user):
        """Test quiet hour checking."""
        manager = UserPreferencesManager(test_db)
        
        # Default has no quiet hours
        assert manager.is_quiet_hour(test_user, 0) is False
        assert manager.is_quiet_hour(test_user, 12) is False
        assert manager.is_quiet_hour(test_user, 23) is False
    
    def test_is_quiet_hour_with_custom_hours(self, test_db, test_user):
        """Test quiet hour checking with custom hours."""
        manager = UserPreferencesManager(test_db)
        
        # Manually set quiet hours in cache
        manager._cache[test_user] = {
            **manager.DEFAULT_PREFERENCES,
            'quiet_hours': [22, 23, 0, 1, 2, 3, 4, 5, 6]  # 10pm - 6am
        }
        manager._cache_timestamps[test_user] = datetime.now(UTC)
        
        assert manager.is_quiet_hour(test_user, 23) is True
        assert manager.is_quiet_hour(test_user, 12) is False
        assert manager.is_quiet_hour(test_user, 3) is True
    
    def test_is_enabled(self, test_db, test_user):
        """Test checking if proactive conversations are enabled."""
        manager = UserPreferencesManager(test_db)
        
        # Default is enabled
        assert manager.is_enabled(test_user) is True
    
    def test_is_enabled_when_disabled(self, test_db, test_user):
        """Test checking when proactive conversations are disabled."""
        manager = UserPreferencesManager(test_db)
        
        # Manually set disabled in cache
        manager._cache[test_user] = {
            **manager.DEFAULT_PREFERENCES,
            'enabled': False
        }
        manager._cache_timestamps[test_user] = datetime.now(UTC)
        
        assert manager.is_enabled(test_user) is False
    
    def test_get_max_initiations_per_day(self, test_db, test_user):
        """Test getting max initiations per day."""
        manager = UserPreferencesManager(test_db)
        
        max_init = manager.get_max_initiations_per_day(test_user)
        
        assert max_init == 5  # Default value
    
    def test_get_max_pending(self, test_db, test_user):
        """Test getting max pending initiations."""
        manager = UserPreferencesManager(test_db)
        
        max_pending = manager.get_max_pending(test_user)
        
        assert max_pending == 2  # Default value
    
    def test_get_min_hours_between(self, test_db, test_user):
        """Test getting min hours between initiations."""
        manager = UserPreferencesManager(test_db)
        
        min_hours = manager.get_min_hours_between(test_user)
        
        assert min_hours == 6.0  # Default value
    
    def test_clear_cache_specific_user(self, test_db, test_user):
        """Test clearing cache for specific user."""
        manager = UserPreferencesManager(test_db)
        
        # Load preferences to populate cache
        manager.get_preferences(test_user)
        assert test_user in manager._cache
        
        # Clear cache for this user
        manager.clear_cache(test_user)
        
        assert test_user not in manager._cache
        assert test_user not in manager._cache_timestamps
    
    def test_clear_cache_all_users(self, test_db, test_user):
        """Test clearing cache for all users."""
        manager = UserPreferencesManager(test_db)
        
        # Load preferences for multiple users
        user2 = str(uuid.uuid4())
        manager.get_preferences(test_user)
        manager._cache[user2] = manager.DEFAULT_PREFERENCES.copy()
        manager._cache_timestamps[user2] = datetime.now(UTC)
        
        # Clear all cache
        manager.clear_cache()
        
        assert len(manager._cache) == 0
        assert len(manager._cache_timestamps) == 0
    
    def test_database_error_handling(self, test_db, test_user):
        """Test that database errors are handled gracefully."""
        manager = UserPreferencesManager(test_db)
        
        # Should return defaults without crashing
        prefs = manager.get_preferences(test_user)
        
        assert prefs == manager.DEFAULT_PREFERENCES
    
    def test_load_user_preferences_convenience_function(self, test_db, test_user):
        """Test the convenience function for loading preferences."""
        prefs = load_user_preferences(test_db, test_user)
        
        assert prefs is not None
        assert 'enabled' in prefs
        assert 'max_initiations_per_day' in prefs
    
    def test_custom_cache_ttl(self, test_db, test_user):
        """Test that custom cache TTL is respected."""
        manager = UserPreferencesManager(test_db)
        
        # Verify default TTL
        assert manager._cache_ttl_seconds == 300  # 5 minutes
        
        # Can be customized
        manager._cache_ttl_seconds = 60
        assert manager._cache_ttl_seconds == 60
