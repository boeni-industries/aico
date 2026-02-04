"""
Database Test Fixtures

Connects to the actual production database for testing.
Tests can read and write, but must clean up their test data.
"""

import pytest
from pathlib import Path

from aico.security import AICOKeyManager


@pytest.fixture(scope="session")
def test_db():
    """Connect to PostgreSQL database ONCE for all tests.
    
    Session-scoped to avoid creating multiple connections.
    All tests share this single connection.
    """
    import psycopg2
    from psycopg2.extras import RealDictCursor
    from aico.core.config import ConfigurationManager
    
    config = ConfigurationManager()
    config.initialize(lightweight=True)
    key_manager = AICOKeyManager(config)
    
    pg_cfg = config.get("postgres", {})
    if not pg_cfg:
        raise RuntimeError("No PostgreSQL configuration found")
    
    password = key_manager.get_database_password("postgres", username=pg_cfg.get("user", "postgres"))
    if not password:
        raise RuntimeError("PostgreSQL password not found in keyring")
    
    # Connect to PostgreSQL
    db = psycopg2.connect(
        host=pg_cfg.get("host", "127.0.0.1"),
        port=int(pg_cfg.get("port", 5432)),
        dbname=pg_cfg.get("db_name", "aico"),
        user=pg_cfg.get("user", "postgres"),
        password=password,
        cursor_factory=RealDictCursor
    )

    cursor = db.cursor()
    cursor.execute("SET search_path TO aico_core,public")
    db.commit()
    cursor.close()
    
    yield db
    
    db.close()


@pytest.fixture
async def test_user(test_db):
    """Create a test user directly via SQL (fast, no service overhead).
    
    Returns the user UUID for use in tests.
    Uses direct SQL to avoid UserService creating additional connections.
    """
    import uuid
    
    # Create user directly via SQL (no UserService = no extra connections)
    user_uuid = str(uuid.uuid4())
    cursor = test_db.cursor()
    
    # Clean up common test IDs BEFORE creating test user to prevent UNIQUE constraint failures
    # Clean up goals with pattern-based IDs
    cursor.execute("DELETE FROM aico_core.agency_plans WHERE goal_id LIKE 'capacity-goal-%'")
    cursor.execute("DELETE FROM aico_core.agency_plans WHERE goal_id LIKE 'test-%'")
    cursor.execute("DELETE FROM aico_core.agency_plans WHERE goal_id LIKE 'goal-%'")
    cursor.execute("DELETE FROM aico_core.agency_plans WHERE goal_id LIKE '%skill%'")
    cursor.execute("DELETE FROM aico_core.agency_plans WHERE goal_id LIKE 'hist-goal-%'")
    cursor.execute("DELETE FROM aico_core.agency_goals WHERE goal_id LIKE 'capacity-goal-%'")
    cursor.execute("DELETE FROM aico_core.agency_goals WHERE goal_id LIKE 'test-%'")
    cursor.execute("DELETE FROM aico_core.agency_goals WHERE goal_id LIKE 'goal-%'")
    cursor.execute("DELETE FROM aico_core.agency_goals WHERE goal_id LIKE '%skill%'")
    cursor.execute("DELETE FROM aico_core.agency_goals WHERE goal_id LIKE 'hist-goal-%'")
    # Clean up specific common IDs
    common_test_ids = ['g1', 'g2', 'g3', 'background-goal', 'active-intention', 
                       'inactive-intention', 'hobby-signal-goal', 'knowledge-gap-goal',
                       'novelty-goal', 'self-performance-goal', 'outcome-test-1', 
                       'outcome-test-2', 'outcome-test-3', 'dep-test-1', 'dep-test-2',
                       'test-goal-get-exec-1', 'test-goal-complete-1', 'source-goal-pattern',
                       'target-goal-pattern', 'goal-filter-1', 'goal-filter-2']
    for goal_id in common_test_ids:
        cursor.execute("DELETE FROM aico_core.agency_plans WHERE goal_id = %s", (goal_id,))
        cursor.execute("DELETE FROM aico_core.agency_goals WHERE goal_id = %s", (goal_id,))
    test_db.commit()
    
    cursor = test_db.cursor()
    
    cursor.execute("""
        INSERT INTO aico_core.user_profiles (uuid, full_name, nickname, user_type, is_active, primary_language, created_at, updated_at)
        VALUES (%s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
    """, (user_uuid, "Test User (Pytest)", "pytest", "person", True, "en"))
    test_db.commit()
    
    yield user_uuid
    
    # Cleanup: Delete all data for this test user
    cursor = test_db.cursor()
    
    # Delete Phase 6.9 data (workflows & events)
    cursor.execute("DELETE FROM aico_core.system_event_metrics WHERE metric_name LIKE 'test%'")
    cursor.execute("DELETE FROM aico_core.system_event_replay_sessions WHERE user_id = %s", (user_uuid,))
    cursor.execute("DELETE FROM aico_core.agency_events_log WHERE user_id = %s", (user_uuid,))
    cursor.execute("DELETE FROM aico_core.workflow_stages WHERE execution_id IN (SELECT execution_id FROM aico_core.workflow_executions WHERE user_id = %s)", (user_uuid,))
    cursor.execute("DELETE FROM aico_core.workflow_executions WHERE user_id = %s", (user_uuid,))
    
    # Delete Phase 6.8 data (policy & ethics)
    cursor.execute("DELETE FROM aico_core.ethics_gate_audit WHERE user_id = %s", (user_uuid,))
    cursor.execute("DELETE FROM aico_core.ethics_decisions_cache WHERE user_id = %s", (user_uuid,))
    cursor.execute("DELETE FROM aico_core.consent_audit_log WHERE user_id = %s", (user_uuid,))
    cursor.execute("DELETE FROM aico_core.consent_user_consents WHERE user_id = %s", (user_uuid,))
    cursor.execute("DELETE FROM aico_core.agency_policy_rules WHERE user_id = %s", (user_uuid,))
    
    # Delete Phase 6.7 data (proactive behaviors)
    cursor.execute("DELETE FROM aico_core.proactive_analytics WHERE user_id = %s", (user_uuid,))
    cursor.execute("DELETE FROM aico_core.user_proactive_preferences WHERE user_id = %s", (user_uuid,))
    cursor.execute("DELETE FROM aico_core.proactive_reminder_clusters WHERE user_id = %s", (user_uuid,))
    cursor.execute("DELETE FROM aico_core.agency_reminders WHERE user_id = %s", (user_uuid,))
    cursor.execute("DELETE FROM aico_core.agency_followups WHERE user_id = %s", (user_uuid,))
    
    # Delete Phase 6.6 data (behavioral feedback)
    cursor.execute("DELETE FROM aico_core.user_feedback_requests WHERE user_id = %s", (user_uuid,))
    cursor.execute("DELETE FROM aico_core.agency_goal_skill_executions WHERE goal_id IN (SELECT goal_id FROM aico_core.agency_goals WHERE user_id = %s)", (user_uuid,))
    cursor.execute("DELETE FROM aico_core.agency_skill_executions WHERE user_id = %s", (user_uuid,))
    cursor.execute("DELETE FROM aico_core.ams_behavioral_feedback WHERE user_id = %s", (user_uuid,))
    
    # Delete Phase 6.5 data (arbiter advanced)
    cursor.execute("DELETE FROM aico_core.agency_goal_outcomes WHERE user_id = %s", (user_uuid,))
    cursor.execute("DELETE FROM aico_core.agency_goal_dependencies WHERE goal_id IN (SELECT goal_id FROM aico_core.agency_goals WHERE user_id = %s)", (user_uuid,))
    
    # Delete Phase 5 data (reflection)
    cursor.execute("DELETE FROM aico_core.agency_arbiter_adjustments WHERE user_id = %s", (user_uuid,))
    cursor.execute("DELETE FROM aico_core.agency_lessons WHERE user_id = %s", (user_uuid,))
    
    # Delete Phase 1-4 data
    cursor.execute("DELETE FROM aico_core.agency_events WHERE user_id = %s", (user_uuid,))
    cursor.execute(
        "DELETE FROM aico_core.agency_plans WHERE goal_id IN (SELECT goal_id FROM aico_core.agency_goals WHERE user_id = %s)",
        (user_uuid,),
    )
    cursor.execute("DELETE FROM aico_core.agency_goals WHERE user_id = %s", (user_uuid,))
    
    # Delete user authentication and user
    cursor.execute("DELETE FROM aico_core.auth_user_credentials WHERE user_uuid = %s", (user_uuid,))
    cursor.execute("DELETE FROM aico_core.user_profiles WHERE uuid = %s", (user_uuid,))
    test_db.commit()
    
    cursor.close()


@pytest.fixture
async def test_db_file():
    """Alias for test_db - returns PostgreSQL connection."""
    import psycopg2
    from psycopg2.extras import RealDictCursor
    from aico.core.config import ConfigurationManager
    
    config = ConfigurationManager()
    config.initialize(lightweight=True)
    key_manager = AICOKeyManager(config)
    
    pg_cfg = config.get("postgres", {})
    if not pg_cfg:
        raise RuntimeError("No PostgreSQL configuration found")
    
    password = key_manager.get_database_password("postgres", username=pg_cfg.get("user", "postgres"))
    if not password:
        raise RuntimeError("PostgreSQL password not found in keyring")
    
    db = psycopg2.connect(
        host=pg_cfg.get("host", "127.0.0.1"),
        port=int(pg_cfg.get("port", 5432)),
        dbname=pg_cfg.get("db_name", "aico"),
        user=pg_cfg.get("user", "postgres"),
        password=password,
        cursor_factory=RealDictCursor
    )
    yield db
    db.close()


@pytest.fixture
def test_db_empty():
    """Not applicable - we use the real database."""
    raise NotImplementedError("Use test_db instead - we use the real production database")
