"""
Database Test Fixtures

Connects to the actual production database for testing.
Tests can read and write, but must clean up their test data.
"""

import pytest
from pathlib import Path

from aico.data.libsql.encrypted import EncryptedLibSQLConnection
from aico.security import AICOKeyManager


@pytest.fixture(scope="session")
def test_db():
    """Connect to the actual production database ONCE for all tests.
    
    Session-scoped to avoid creating multiple connections.
    All tests share this single connection.
    """
    # Get the actual database path using AICOPaths (same as CLI)
    from aico.core.paths import AICOPaths
    from aico.core.config import ConfigurationManager
    
    db_path = AICOPaths.resolve_database_path("aico.db", "auto")
    
    # Get the actual encryption key (use cached session or keyring)
    config = ConfigurationManager()
    key_manager = AICOKeyManager(config)
    
    # Try to get cached session key
    import keyring
    cached_key = key_manager._get_cached_session()
    if cached_key:
        master_key = cached_key
    else:
        # Try keyring
        stored_key = keyring.get_password(key_manager.service_name, "master_key")
        if stored_key:
            master_key = bytes.fromhex(stored_key)
        else:
            raise RuntimeError("No master key available. Run 'aico security setup' first.")
    
    encryption_key = key_manager.derive_database_key(master_key, "libsql", str(db_path))
    
    # Connect to the real database ONCE
    db = EncryptedLibSQLConnection(str(db_path), encryption_key=encryption_key)
    
    yield db
    
    # Connection will be closed when session ends


@pytest.fixture
async def test_user(test_db):
    """Create a test user directly via SQL (fast, no service overhead).
    
    Returns the user UUID for use in tests.
    Uses direct SQL to avoid UserService creating additional connections.
    """
    import uuid
    
    # Create user directly via SQL (no UserService = no extra connections)
    user_uuid = str(uuid.uuid4())
    
    test_db.execute("""
        INSERT INTO users (uuid, full_name, nickname, user_type, is_active, primary_language, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
    """, (user_uuid, "Test User (Pytest)", "pytest", "person", True, "en"))
    test_db.commit()
    
    yield user_uuid
    
    # Cleanup: Delete all data for this test user
    # Temporarily disable foreign keys for cleanup
    test_db.execute("PRAGMA foreign_keys = OFF")
    
    # Delete Phase 6.7 data (proactive behaviors)
    test_db.execute("DELETE FROM proactive_analytics WHERE user_id = ?", (user_uuid,))
    test_db.execute("DELETE FROM user_proactive_preferences WHERE user_id = ?", (user_uuid,))
    test_db.execute("DELETE FROM reminder_clusters WHERE user_id = ?", (user_uuid,))
    test_db.execute("DELETE FROM agency_reminders WHERE user_id = ?", (user_uuid,))
    test_db.execute("DELETE FROM agency_followups WHERE user_id = ?", (user_uuid,))
    
    # Delete Phase 6.6 data (behavioral feedback)
    test_db.execute("DELETE FROM user_feedback_requests WHERE user_id = ?", (user_uuid,))
    test_db.execute("DELETE FROM goal_skill_executions WHERE goal_id IN (SELECT goal_id FROM agency_goals WHERE user_id = ?)", (user_uuid,))
    test_db.execute("DELETE FROM skill_executions WHERE user_id = ?", (user_uuid,))
    test_db.execute("DELETE FROM ams_behavioral_feedback WHERE user_id = ?", (user_uuid,))
    
    # Delete Phase 6.5 data (arbiter advanced)
    test_db.execute("DELETE FROM goal_outcomes WHERE user_id = ?", (user_uuid,))
    test_db.execute("DELETE FROM arbiter_scoring_history WHERE user_id = ?", (user_uuid,))
    test_db.execute("DELETE FROM arbiter_context_snapshots WHERE user_id = ?", (user_uuid,))
    test_db.execute("DELETE FROM goal_dependencies WHERE goal_id IN (SELECT goal_id FROM agency_goals WHERE user_id = ?)", (user_uuid,))
    test_db.execute("DELETE FROM user_time_preferences WHERE user_id = ?", (user_uuid,))
    
    # Delete Phase 5 data (reflection)
    test_db.execute("DELETE FROM agency_arbiter_adjustments WHERE user_id = ?", (user_uuid,))
    test_db.execute("DELETE FROM agency_lessons WHERE user_id = ?", (user_uuid,))
    
    # Delete Phase 1-4 data
    test_db.execute("DELETE FROM agency_events WHERE user_id = ?", (user_uuid,))
    test_db.execute("DELETE FROM agency_plans WHERE goal_id IN (SELECT goal_id FROM agency_goals WHERE user_id = ?)", (user_uuid,))
    test_db.execute("DELETE FROM agency_goals WHERE user_id = ?", (user_uuid,))
    
    # Delete user authentication and user
    test_db.execute("DELETE FROM user_authentication WHERE user_uuid = ?", (user_uuid,))
    test_db.execute("DELETE FROM users WHERE uuid = ?", (user_uuid,))
    test_db.commit()
    
    # Re-enable foreign keys
    test_db.execute("PRAGMA foreign_keys = ON")


@pytest.fixture
async def test_db_file():
    """Alias for test_db."""
    # Just use the same real database
    from aico.core.paths import AICOPaths
    from aico.core.config import ConfigurationManager
    
    db_path = AICOPaths.resolve_database_path("aico.db", "auto")
    
    config = ConfigurationManager()
    key_manager = AICOKeyManager(config)
    
    # Try to get cached session key
    import keyring
    cached_key = key_manager._get_cached_session()
    if cached_key:
        master_key = cached_key
    else:
        # Try keyring
        stored_key = keyring.get_password(key_manager.service_name, "master_key")
        if stored_key:
            master_key = bytes.fromhex(stored_key)
        else:
            raise RuntimeError("No master key available. Run 'aico security setup' first.")
    
    encryption_key = key_manager.derive_database_key(master_key, "libsql", str(db_path))
    
    db = EncryptedLibSQLConnection(str(db_path), encryption_key=encryption_key)
    yield db


@pytest.fixture
def test_db_empty():
    """Not applicable - we use the real database."""
    raise NotImplementedError("Use test_db instead - we use the real production database")
