"""
Database Test Fixtures

Connects to the dedicated test database for testing.
Tests can read and write, but must clean up their test data.
"""

import pytest
import pytest_asyncio
from pathlib import Path
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

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

    import os
    expected_db_name = os.environ.get("AICO_TEST_DB_NAME", "aico_test")
    maintenance_db_name = os.environ.get("AICO_TEST_DB_MAINTENANCE_DB", "aico")
    pg_container_name = os.environ.get("AICO_TEST_DB_CONTAINER", "aico-postgres")
    
    password = key_manager.get_database_password("postgres", username=pg_cfg.get("user", "postgres"))
    if not password:
        raise RuntimeError("PostgreSQL password not found in keyring")
    
    def _connect(dbname: str):
        return psycopg2.connect(
            host=pg_cfg.get("host", "127.0.0.1"),
            port=int(pg_cfg.get("port", 5432)),
            dbname=dbname,
            user=pg_cfg.get("user", "postgres"),
            password=password,
            cursor_factory=RealDictCursor,
        )

    def _apply_schema_sql() -> None:
        import subprocess

        root = Path(__file__).resolve().parents[3]
        schema_path = root / "shared" / "aico" / "data" / "postgres" / "schema.sql"
        if not schema_path.exists():
            raise RuntimeError(f"Schema file not found: {schema_path}")

        with open(schema_path, "r") as f:
            sql_text = f.read()

        sql_text = "SET statement_timeout = 0;\nSET lock_timeout = 0;\n" + sql_text

        cmd = [
            "docker",
            "exec",
            "-i",
            "-e",
            f"PGPASSWORD={password}",
            pg_container_name,
            "psql",
            "-h",
            "localhost",
            "-U",
            pg_cfg.get("user", "postgres"),
            "-d",
            expected_db_name,
            "-v",
            "ON_ERROR_STOP=1",
        ]
        result = subprocess.run(
            cmd,
            input=sql_text,
            text=True,
            capture_output=True,
            check=False,
            timeout=int(os.environ.get("AICO_TEST_SCHEMA_APPLY_TIMEOUT_SECONDS", "300")),
        )
        if result.returncode != 0:
            raise RuntimeError(
                "Failed to apply schema.sql:\n"
                + (result.stderr or "")
                + ("\n" + result.stdout if result.stdout else "")
            )

    maint = _connect(maintenance_db_name)
    maint.set_session(autocommit=True)
    try:
        cur = maint.cursor()

        cur.execute("ALTER DATABASE template1 REFRESH COLLATION VERSION")
        cur.execute(f"ALTER DATABASE {maintenance_db_name} REFRESH COLLATION VERSION")

        cur.execute(
            "SELECT 1 FROM pg_database WHERE datname = %s",
            (expected_db_name,),
        )
        exists = cur.fetchone()
        if exists:
            cur.execute(f"DROP DATABASE {expected_db_name} WITH (FORCE)")
        cur.execute(f"CREATE DATABASE {expected_db_name}")
        cur.close()
    finally:
        maint.close()

    _apply_schema_sql()

    db = _connect(expected_db_name)

    cursor = db.cursor()
    cursor.execute("SELECT current_database() AS db")
    row = cursor.fetchone()
    current_db = (row or {}).get("db")
    if current_db != expected_db_name:
        cursor.close()
        db.close()
        raise RuntimeError(
            f"Refusing to run tests against non-test database: '{current_db}'. "
            f"Expected '{expected_db_name}'. Set AICO_TEST_DB_NAME if needed."
        )
    cursor.execute("CREATE SCHEMA IF NOT EXISTS aico_core")
    cursor.execute("SET search_path TO aico_core,public")
    # Ensure test DB schema is up-to-date enough for the current codebase.
    # This is intentionally minimal and idempotent: only add columns that newer
    # code expects but older test DBs may not yet have.
    cursor.execute(
        "ALTER TABLE IF EXISTS ethics_value_profiles "
        "ADD COLUMN IF NOT EXISTS autonomy_level TEXT DEFAULT 'balanced'"
    )

    cursor.execute(
        "ALTER TABLE IF EXISTS user_feedback_requests "
        "ALTER COLUMN responded_at TYPE TIMESTAMPTZ USING NULLIF(responded_at::text, '')::timestamptz"
    )
    cursor.execute(
        "ALTER TABLE IF EXISTS user_feedback_requests "
        "ALTER COLUMN created_at TYPE TIMESTAMPTZ USING NULLIF(created_at::text, '')::timestamptz"
    )
    
    # Create scheduler tables if missing (needed for distributed scheduler idempotency)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS scheduler_tasks (
            task_id TEXT PRIMARY KEY,
            task_class TEXT NOT NULL,
            schedule TEXT NOT NULL,
            config TEXT,
            enabled BOOLEAN DEFAULT TRUE,
            created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS scheduler_task_executions (
            id BIGSERIAL PRIMARY KEY,
            task_id TEXT NOT NULL,
            execution_id TEXT NOT NULL,
            run_key TEXT,
            status TEXT NOT NULL,
            started_at TIMESTAMPTZ NOT NULL,
            completed_at TIMESTAMPTZ,
            result TEXT,
            error_message TEXT,
            duration_seconds DOUBLE PRECISION,
            acknowledged BOOLEAN DEFAULT FALSE
        )
    """)

    cursor.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS uq_scheduler_task_executions_run_key
        ON scheduler_task_executions (task_id, run_key)
        WHERE run_key IS NOT NULL
    """)

    # Create interaction_requests table if missing
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS interaction_requests (
            interaction_id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            correlation_id TEXT NOT NULL,
            interaction_type TEXT NOT NULL,
            requirement TEXT NOT NULL,
            status TEXT NOT NULL,
            category TEXT NOT NULL,
            severity TEXT NOT NULL,
            title TEXT,
            prompt TEXT,
            context_json JSONB,
            allowed_options JSONB,
            expected_answer_type TEXT,
            answer_text TEXT,
            answer_json JSONB,
            answered_at TIMESTAMPTZ,
            expires_at TIMESTAMPTZ,
            idempotency_key TEXT NOT NULL,
            created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    cursor.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS uq_interaction_requests_idempotency_key
        ON interaction_requests (user_id, idempotency_key)
    """)
    
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_interaction_requests_user_status
        ON interaction_requests (user_id, status, created_at DESC)
    """)
    
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_interaction_requests_correlation
        ON interaction_requests (correlation_id)
    """)
    
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_interaction_requests_expires
        ON interaction_requests (expires_at)
        WHERE expires_at IS NOT NULL
    """)
    
    # Create interaction_events table if missing
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS interaction_events (
            event_id TEXT PRIMARY KEY,
            interaction_id TEXT NOT NULL,
            user_id TEXT NOT NULL,
            correlation_id TEXT NOT NULL,
            actor TEXT NOT NULL,
            event_type TEXT NOT NULL,
            from_status TEXT,
            to_status TEXT,
            payload_json JSONB,
            created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_interaction_events_interaction
        ON interaction_events (interaction_id, created_at ASC)
    """)
    
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_interaction_events_user_time
        ON interaction_events (user_id, created_at DESC)
    """)
    
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_interaction_events_correlation
        ON interaction_events (correlation_id, created_at ASC)
    """)

    # Create outbox_events table if missing (used for durable publication fallback)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS outbox_events (
            event_id TEXT PRIMARY KEY,
            tenant_id TEXT NOT NULL,
            subject TEXT NOT NULL,
            payload_bytes BYTEA NOT NULL,
            status TEXT NOT NULL DEFAULT 'pending',
            attempts INTEGER NOT NULL DEFAULT 0,
            last_error TEXT,
            available_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
            created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
            sent_at TIMESTAMPTZ
        )
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_outbox_events_pending
        ON outbox_events (status, available_at, created_at)
        WHERE status = 'pending'
    """)

    # Working memory table (Postgres-backed LMDB replacement)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS working_memory_messages (
            id BIGSERIAL PRIMARY KEY,
            conversation_id TEXT NOT NULL,
            user_id TEXT,
            message_id TEXT,
            role TEXT,
            content TEXT,
            language TEXT,
            message_type TEXT,
            payload_json JSONB,
            stored_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
            expires_at TIMESTAMPTZ,
            last_accessed_at TIMESTAMPTZ,
            access_count INTEGER NOT NULL DEFAULT 0
        )
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_working_memory_conversation_stored_at
        ON working_memory_messages (conversation_id, stored_at DESC)
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_working_memory_user_stored_at
        ON working_memory_messages (user_id, stored_at DESC)
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_working_memory_expires_at
        ON working_memory_messages (expires_at)
        WHERE expires_at IS NOT NULL
    """)

    db.commit()
    cursor.close()
    
    yield db
    
    db.close()

    maint = _connect(maintenance_db_name)
    maint.set_session(autocommit=True)
    try:
        cur = maint.cursor()
        cur.execute(f"DROP DATABASE IF EXISTS {expected_db_name} WITH (FORCE)")
        cur.close()
    finally:
        maint.close()


@pytest_asyncio.fixture(scope="session")
async def session_factory(test_db):
    """
    Create async SQLAlchemy session factory for tests.
    
    Uses the same test database connection info as test_db fixture.
    """
    from aico.core.config import ConfigurationManager
    
    config = ConfigurationManager()
    config.initialize(lightweight=True)
    key_manager = AICOKeyManager(config)
    
    pg_cfg = config.get("postgres", {})
    password = key_manager.get_database_password("postgres", username=pg_cfg.get("user", "postgres"))
    
    import os
    expected_db_name = os.environ.get("AICO_TEST_DB_NAME", "aico_test")
    
    # Create async engine
    database_url = f"postgresql+asyncpg://{pg_cfg.get('user', 'postgres')}:{password}@{pg_cfg.get('host', '127.0.0.1')}:{pg_cfg.get('port', 5432)}/{expected_db_name}"
    
    engine = create_async_engine(
        database_url,
        echo=False,
        pool_pre_ping=True,
    )
    
    # Create session factory
    factory = async_sessionmaker(
        engine,
        expire_on_commit=False,
    )
    
    yield factory

    await engine.dispose()


@pytest.fixture
async def test_user(test_db):
    """Create a test user directly via SQL (fast, no service overhead).
    
    Returns the user UUID for use in tests.
    Uses direct SQL to avoid UserService creating additional connections.
    """
    import uuid

    # The session-scoped psycopg2 connection can be left in an aborted transaction
    # state after any earlier SQL error. Always reset before executing statements.
    try:
        test_db.rollback()
    except Exception:
        pass
    
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
    cursor.execute("DELETE FROM aico_core.ethics_value_profiles WHERE user_id = %s", (user_uuid,))
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
    import os
    
    config = ConfigurationManager()
    config.initialize(lightweight=True)
    key_manager = AICOKeyManager(config)
    
    pg_cfg = config.get("postgres", {})
    if not pg_cfg:
        raise RuntimeError("No PostgreSQL configuration found")

    expected_db_name = os.environ.get("AICO_TEST_DB_NAME", "aico_test")
    
    password = key_manager.get_database_password("postgres", username=pg_cfg.get("user", "postgres"))
    if not password:
        raise RuntimeError("PostgreSQL password not found in keyring")
    
    db = psycopg2.connect(
        host=pg_cfg.get("host", "127.0.0.1"),
        port=int(pg_cfg.get("port", 5432)),
        dbname=expected_db_name,
        user=pg_cfg.get("user", "postgres"),
        password=password,
        cursor_factory=RealDictCursor
    )

    cursor = db.cursor()
    cursor.execute("SELECT current_database() AS db")
    row = cursor.fetchone()
    current_db = (row or {}).get("db")
    if current_db != expected_db_name:
        cursor.close()
        db.close()
        raise RuntimeError(
            f"Refusing to run tests against non-test database: '{current_db}'. "
            f"Expected '{expected_db_name}'. Set AICO_TEST_DB_NAME if needed."
        )
    cursor.close()
    yield db
    db.close()


@pytest.fixture
def test_db_empty():
    """Not applicable - we use the real database."""
    raise NotImplementedError("Use test_db instead - we use the dedicated test database")
