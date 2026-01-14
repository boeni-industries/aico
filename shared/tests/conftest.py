"""
Shared test configuration for pytest.

Mocks logging to avoid initialization requirements during testing.
"""

import sys
from unittest.mock import MagicMock

# Create a mock logger
mock_logger = MagicMock()

# Mock the entire logging module before AICO imports
sys.modules['aico.core.logging'] = MagicMock(
    get_logger=lambda *args, **kwargs: mock_logger,
    initialize_logging=MagicMock(),
    initialize_cli_logging=MagicMock()
)

# Reset ConfigurationManager singleton before tests to prevent pollution
def pytest_sessionstart(session):
    """Reset configuration singleton at test session start."""
    import os
    # Set environment variable to prevent config persistence during tests
    os.environ['AICO_TEST_MODE'] = '1'
    
    from aico.core.config import ConfigurationManager
    ConfigurationManager._instance = None
    ConfigurationManager._initialized = False
    ConfigurationManager._watchers_started = False

def pytest_sessionfinish(session, exitstatus):
    """Clean up after test session."""
    import os
    os.environ.pop('AICO_TEST_MODE', None)
    
    # Clean up any remaining test users from the database
    try:
        from aico.core.paths import AICOPaths
        from aico.core.config import ConfigurationManager
        from aico.security import AICOKeyManager
                import keyring
        
        db_path = AICOPaths.resolve_database_path("aico.db", "auto")
        config = ConfigurationManager()
        key_manager = AICOKeyManager(config)
        
        # Try to get cached session key
        cached_key = key_manager._get_cached_session()
        if cached_key:
            master_key = cached_key
        else:
            # Try keyring
            stored_key = keyring.get_password(key_manager.service_name, "master_key")
            if stored_key:
                master_key = bytes.fromhex(stored_key)
            else:
                # No key available, skip cleanup
                return
        
        encryption_key = key_manager.derive_database_key(master_key, "libsql", str(db_path))
        db = None          
        # Delete all test users (nickname='pytest')
        cursor = db.execute("SELECT COUNT(*) FROM user_profiles WHERE nickname = 'pytest'")
        count = cursor.fetchone()[0]
        
        if count > 0:
            print(f"\n🧹 Cleaning up {count} test users from database...")
            db.execute("DELETE FROM user_profiles WHERE nickname = 'pytest'")
            db.commit()
            print(f"✅ Deleted {count} test users")
    except Exception as e:
        # Don't fail the test session if cleanup fails
        print(f"⚠️  Warning: Could not clean up test users: {e}")
