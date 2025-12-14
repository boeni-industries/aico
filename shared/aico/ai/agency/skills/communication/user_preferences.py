"""
User Preferences for Proactive Conversations

Loads and manages user preferences for conversation initiation timing,
frequency limits, and boundary settings.
"""

from typing import Dict, Any, Optional, List
from datetime import datetime

from aico.core.logging import get_logger
from aico.data.libsql import EncryptedLibSQLConnection


logger = get_logger("shared", "ai.agency.skills.communication.user_preferences")


class UserPreferencesManager:
    """Manages user preferences for proactive conversation initiation."""
    
    # Default preferences if not set by user
    DEFAULT_PREFERENCES = {
        'quiet_hours': [],  # List of hours (0-23) when not to initiate
        'max_initiations_per_day': 5,  # Maximum proactive initiations per day
        'max_pending': 2,  # Maximum pending initiations at once
        'preferred_times': [],  # Preferred hours for initiations
        'enabled': True,  # Whether proactive conversations are enabled
        'min_hours_between': 6,  # Minimum hours between initiations
    }
    
    def __init__(self, db: EncryptedLibSQLConnection):
        self.db = db
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._cache_timestamps: Dict[str, datetime] = {}
        self._cache_ttl_seconds = 300  # 5 minutes
    
    def get_preferences(self, user_id: str) -> Dict[str, Any]:
        """Get user preferences with caching.
        
        Args:
            user_id: User UUID
            
        Returns:
            Dictionary of user preferences
        """
        # Check cache
        if user_id in self._cache:
            cache_age = (datetime.utcnow() - self._cache_timestamps[user_id]).total_seconds()
            if cache_age < self._cache_ttl_seconds:
                logger.debug(f"Using cached preferences for user {user_id[:8]}")
                return self._cache[user_id]
        
        # Load from database
        try:
            # Check if user has custom preferences stored
            # For now, we'll use a simple JSON column in users table
            # In production, might want a separate user_preferences table
            
            cursor = self.db.execute(
                "SELECT uuid FROM users WHERE uuid = ?",
                (user_id,)
            )
            user = cursor.fetchone()
            
            if not user:
                logger.warning(f"User not found: {user_id[:8]}, using defaults")
                return self.DEFAULT_PREFERENCES.copy()
            
            # TODO: Load actual preferences from database
            # For now, return defaults
            # In future: SELECT preferences FROM user_preferences WHERE user_id = ?
            
            preferences = self.DEFAULT_PREFERENCES.copy()
            
            # Cache the result
            self._cache[user_id] = preferences
            self._cache_timestamps[user_id] = datetime.utcnow()
            
            logger.debug(f"Loaded preferences for user {user_id[:8]}")
            return preferences
            
        except Exception as e:
            logger.error(f"Error loading preferences for user {user_id[:8]}: {e}")
            return self.DEFAULT_PREFERENCES.copy()
    
    def is_quiet_hour(self, user_id: str, hour: int) -> bool:
        """Check if given hour is a quiet hour for user.
        
        Args:
            user_id: User UUID
            hour: Hour of day (0-23)
            
        Returns:
            True if it's a quiet hour
        """
        prefs = self.get_preferences(user_id)
        quiet_hours = prefs.get('quiet_hours', [])
        return hour in quiet_hours
    
    def is_enabled(self, user_id: str) -> bool:
        """Check if proactive conversations are enabled for user.
        
        Args:
            user_id: User UUID
            
        Returns:
            True if enabled
        """
        prefs = self.get_preferences(user_id)
        return prefs.get('enabled', True)
    
    def get_max_initiations_per_day(self, user_id: str) -> int:
        """Get maximum initiations per day for user.
        
        Args:
            user_id: User UUID
            
        Returns:
            Maximum initiations per day
        """
        prefs = self.get_preferences(user_id)
        return prefs.get('max_initiations_per_day', 5)
    
    def get_max_pending(self, user_id: str) -> int:
        """Get maximum pending initiations for user.
        
        Args:
            user_id: User UUID
            
        Returns:
            Maximum pending initiations
        """
        prefs = self.get_preferences(user_id)
        return prefs.get('max_pending', 2)
    
    def get_min_hours_between(self, user_id: str) -> float:
        """Get minimum hours between initiations for user.
        
        Args:
            user_id: User UUID
            
        Returns:
            Minimum hours between initiations
        """
        prefs = self.get_preferences(user_id)
        return prefs.get('min_hours_between', 6.0)
    
    def clear_cache(self, user_id: Optional[str] = None):
        """Clear preference cache.
        
        Args:
            user_id: Specific user to clear, or None for all
        """
        if user_id:
            self._cache.pop(user_id, None)
            self._cache_timestamps.pop(user_id, None)
            logger.debug(f"Cleared cache for user {user_id[:8]}")
        else:
            self._cache.clear()
            self._cache_timestamps.clear()
            logger.debug("Cleared all preference cache")


def load_user_preferences(db: EncryptedLibSQLConnection, user_id: str) -> Dict[str, Any]:
    """Convenience function to load user preferences.
    
    Args:
        db: Database connection
        user_id: User UUID
        
    Returns:
        Dictionary of user preferences
    """
    manager = UserPreferencesManager(db)
    return manager.get_preferences(user_id)
