"""
Shared test fixtures for integration tests.

Provides:
- Database session management
- Test data cleanup
- Common fixtures for users, goals, plans, etc.
"""

import os
import shutil

import pytest
import uuid
from datetime import datetime, UTC
from pathlib import Path
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.pool import NullPool

from aico.data.postgres.connection import get_session_factory
from aico.data.uow import UnitOfWork
from aico.ai.user.models import UserProfile


@pytest.fixture(scope="session", autouse=True)
def _isolate_runtime_config_dir(tmp_path_factory):
    config_root = tmp_path_factory.mktemp("aico_test") / "config"
    os.environ["AICO_CONFIG_DIR"] = str(config_root)

    project_root = Path(__file__).parent.parent.parent
    project_config_dir = project_root / "config"

    for subdir, pattern in (
        ("defaults", "*.yaml"),
        ("environments", "*.yaml"),
        ("schemas", "*.schema.json"),
        ("modelfiles", "Modelfile.*"),
    ):
        src = project_config_dir / subdir
        dst = config_root / subdir
        if not src.exists():
            continue
        dst.mkdir(parents=True, exist_ok=True)
        for p in src.glob(pattern):
            shutil.copy2(p, dst / p.name)

    yield

    os.environ.pop("AICO_CONFIG_DIR", None)


@pytest.fixture(scope="session", autouse=True)
def setup_test_database():
    """
    Automatically create and setup test database before all tests.
    
    This fixture:
    1. Creates a fresh 'aico_test' database
    2. Applies the schema from schema.sql
    3. Runs before any tests (autouse=True)
    4. Optionally drops the database after tests (commented out for inspection)
    """
    import os
    from aico.core.config import ConfigurationManager
    from aico.security import AICOKeyManager
    
    # Get database credentials from config (same as connection.py)
    config = ConfigurationManager()
    config.initialize(lightweight=True)
    
    pg_config = config.get("postgres", {})
    host = pg_config.get("host", "localhost")
    port = pg_config.get("port", 5432)
    database = pg_config.get("db_name", "aico")
    user = pg_config.get("user", "postgres")
    
    # Get password from environment or AICOKeyManager (same as connection.py)
    password = os.environ.get("AICO_PG_PASSWORD")
    
    if not password:
        try:
            key_manager = AICOKeyManager(config)
            password = key_manager.get_database_password("postgres", username="postgres")
        except Exception:
            pass
    
    if not password:
        raise RuntimeError("PostgreSQL password not found. Set AICO_PG_PASSWORD environment variable.")
    
    # Connect to postgres (admin database) to create test database
    admin_url = f"postgresql+asyncpg://{user}:{password}@{host}:{port}/postgres"
    admin_engine = create_async_engine(admin_url, isolation_level="AUTOCOMMIT", poolclass=NullPool)
    
    import asyncio
    
    async def _setup():
        try:
            # Drop and recreate test database
            async with admin_engine.connect() as conn:
                # Terminate existing connections to test database
                await conn.execute(text("""
                    SELECT pg_terminate_backend(pg_stat_activity.pid)
                    FROM pg_stat_activity
                    WHERE pg_stat_activity.datname = 'aico_test'
                    AND pid <> pg_backend_pid()
                """))
                
                # Drop and create fresh test database
                await conn.execute(text("DROP DATABASE IF EXISTS aico_test"))
                await conn.execute(text("CREATE DATABASE aico_test"))
            
            # Connect to test database and apply schema
            test_url = f"postgresql+asyncpg://{user}:{password}@{host}:{port}/aico_test"
            test_engine = create_async_engine(test_url, poolclass=NullPool)
            
            # Use raw asyncpg connection to execute multi-statement schema
            import asyncpg
            raw_conn = await asyncpg.connect(
                host=host,
                port=port,
                user=user,
                password=password,
                database='aico_test'
            )
            
            try:
                # Read and execute schema.sql
                schema_path = Path(__file__).parent.parent.parent / "shared" / "aico" / "data" / "postgres" / "schema.sql"
                schema_sql = schema_path.read_text()
                
                # Execute entire schema as one script (asyncpg handles multiple statements)
                await raw_conn.execute(schema_sql)
            finally:
                await raw_conn.close()
            
            await test_engine.dispose()
        finally:
            await admin_engine.dispose()
    
    # Run async setup synchronously
    asyncio.run(_setup())
    
    # CRITICAL: Override database name BEFORE any imports that create session factory
    os.environ["AICO_POSTGRES_DATABASE"] = "aico_test"
    
    # Force reset of global session factory to pick up new database name
    import aico.data.postgres.connection as conn_module
    conn_module._engine = None
    conn_module._session_factory = None
    conn_module._pool = None
    
    yield  # Run all tests
    
    # Cleanup after all tests (optional - comment out to inspect data)
    # async def _cleanup():
    #     admin_engine = create_async_engine(admin_url, isolation_level="AUTOCOMMIT", poolclass=NullPool)
    #     try:
    #         async with admin_engine.connect() as conn:
    #             await conn.execute(text("""
    #                 SELECT pg_terminate_backend(pg_stat_activity.pid)
    #                 FROM pg_stat_activity
    #                 WHERE pg_stat_activity.datname = 'aico_test'
    #                 AND pid <> pg_backend_pid()
    #             """))
    #             await conn.execute(text("DROP DATABASE IF EXISTS aico_test"))
    #     finally:
    #         await admin_engine.dispose()
    # asyncio.run(_cleanup())


@pytest.fixture
async def session_factory():
    """Database session factory."""
    factory = await get_session_factory()
    return factory


@pytest.fixture
async def uow(session_factory):
    """Function-scoped Unit of Work with automatic cleanup."""
    uow = UnitOfWork(session_factory)
    async with uow:
        yield uow
        # Rollback any uncommitted changes
        await uow.rollback()


@pytest.fixture
async def test_user(uow):
    """Create a test user for each test."""
    user_id = f"test_user_{uuid.uuid4().hex[:8]}"
    user = UserProfile(
        uuid=user_id,
        full_name="Test User",
        nickname="tester",
        user_type="parent",
        is_active=True,
        primary_language="en",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    created_user = await uow.users.create(user)
    await uow.commit()
    return created_user


@pytest.fixture
async def test_goal(uow, test_user):
    """Create a test goal for tests that need it."""
    # Create goal directly via SQL to avoid model issues
    from sqlalchemy import text
    
    goal_id = str(uuid.uuid4())
    now = datetime.now(UTC)
    
    query = text("""
        INSERT INTO aico_core.agency_goals 
        (goal_id, user_id, origin, goal_type, title, description, status, priority, created_at, updated_at)
        VALUES (:goal_id, :user_id, :origin, :goal_type, :title, :description, :status, :priority, :created_at, :updated_at)
    """)
    
    await uow._session.execute(query, {
        "goal_id": goal_id,
        "user_id": test_user.uuid,
        "origin": "test",
        "goal_type": "task",
        "title": "Test Goal",
        "description": "Test goal for integration tests",
        "status": "active",
        "priority": "normal",
        "created_at": now,
        "updated_at": now,
    })
    await uow.commit()
    
    # Return a simple object with the goal_id
    class TestGoal:
        def __init__(self, goal_id):
            self.goal_id = goal_id
    
    return TestGoal(goal_id)


@pytest.fixture
async def test_plan(uow, test_user, test_goal):
    """Create a test plan for tests that need it."""
    from sqlalchemy import text
    import json
    
    plan_id = str(uuid.uuid4())
    now = datetime.now(UTC)
    
    query = text("""
        INSERT INTO aico_core.agency_plans 
        (plan_id, goal_id, status, steps_json, created_at, updated_at)
        VALUES (:plan_id, :goal_id, :status, :steps_json, :created_at, :updated_at)
    """)
    
    await uow._session.execute(query, {
        "plan_id": plan_id,
        "goal_id": test_goal.goal_id,
        "status": "draft",
        "steps_json": json.dumps([{"step": 1, "description": "Test step"}]),
        "created_at": now,
        "updated_at": now,
    })
    await uow.commit()
    
    class TestPlan:
        def __init__(self, plan_id):
            self.plan_id = plan_id
    
    return TestPlan(plan_id)


@pytest.fixture
async def test_plan_execution(uow, test_user, test_goal, test_plan):
    """Create a test plan execution for tests that need it."""
    from aico.data.agency.execution_models import AgencyPlanExecution
    
    execution_id = str(uuid.uuid4())
    execution = AgencyPlanExecution(
        execution_id=execution_id,
        plan_id=test_plan.plan_id,
        goal_id=test_goal.goal_id,
        user_id=test_user.uuid,
        status="running",
        steps_total=5,
        steps_completed=0,
        progress_percentage=0.0,
        created_at=datetime.now(UTC).isoformat(),
        updated_at=datetime.now(UTC).isoformat(),
    )
    created_execution = await uow.agency_plan_executions.create(execution)
    await uow.commit()
    return created_execution


@pytest.fixture
async def test_lesson(uow, test_user):
    """Create a test lesson for tests that need it."""
    from sqlalchemy import text
    
    lesson_id = str(uuid.uuid4())
    now = datetime.now(UTC)
    
    # Create lesson directly via SQL matching actual schema
    query = text("""
        INSERT INTO aico_core.agency_lessons 
        (lesson_id, user_id, lesson_type, target_kind, summary_text, proposed_change, 
         confidence, scope, status, created_at, updated_at)
        VALUES (:lesson_id, :user_id, :lesson_type, :target_kind, :summary_text, 
                :proposed_change, :confidence, :scope, :status, :created_at, :updated_at)
    """)
    
    await uow._session.execute(query, {
        "lesson_id": lesson_id,
        "user_id": test_user.uuid,
        "lesson_type": "skill_tuning",
        "target_kind": "skill",
        "target_id": None,
        "summary_text": "Test lesson summary",
        "proposed_change": '{"change_type": "test", "field": "test", "old": "old", "new": "new"}',
        "confidence": 0.85,
        "scope": "this_user",
        "status": "active",
        "created_at": now,
        "updated_at": now,
    })
    await uow.commit()
    
    class TestLesson:
        def __init__(self, lesson_id):
            self.lesson_id = lesson_id
    
    return TestLesson(lesson_id)


@pytest.fixture
async def test_behavioral_skill(uow):
    """Create a test behavioral skill for AMS tests."""
    from sqlalchemy import text
    
    skill_id = f"test_skill_{uuid.uuid4().hex[:8]}"
    now = datetime.now(UTC)
    
    query = text("""
        INSERT INTO aico_core.ams_behavioral_skills 
        (skill_id, skill_name, skill_type, trigger_context, procedure_template, 
         dimension_vector, created_at, updated_at, status)
        VALUES (:skill_id, :skill_name, :skill_type, :trigger_context, :procedure_template,
                :dimension_vector, :created_at, :updated_at, :status)
    """)
    
    await uow._session.execute(query, {
        "skill_id": skill_id,
        "skill_name": "Test Skill",
        "skill_type": "conversational",
        "trigger_context": "test context",
        "procedure_template": "test procedure",
        "dimension_vector": "[0.1, 0.2, 0.3]",
        "created_at": now,
        "updated_at": now,
        "status": "active",
    })
    await uow.commit()
    
    class TestSkill:
        def __init__(self, skill_id):
            self.skill_id = skill_id
    
    return TestSkill(skill_id)


@pytest.fixture
async def test_consent(uow, test_user):
    """Create a test consent for consent_audit_log tests."""
    from sqlalchemy import text
    
    consent_id = str(uuid.uuid4())
    now = datetime.now(UTC).isoformat()
    
    query = text("""
        INSERT INTO aico_core.consent_user_consents 
        (consent_id, user_id, consent_type, scope, granted, granted_at, created_at, updated_at)
        VALUES (:consent_id, :user_id, :consent_type, :scope, :granted, :granted_at, :created_at, :updated_at)
    """)
    
    await uow._session.execute(query, {
        "consent_id": consent_id,
        "user_id": test_user.uuid,
        "consent_type": "data_processing",
        "scope": "global",
        "granted": 1,
        "granted_at": now,
        "created_at": now,
        "updated_at": now,
    })
    await uow.commit()
    
    class TestConsent:
        def __init__(self, consent_id):
            self.consent_id = consent_id
    
    return TestConsent(consent_id)


@pytest.fixture(autouse=True)
async def cleanup_test_data(session_factory):
    """
    Automatically cleanup test data after each test.
    
    This fixture runs after every test to ensure test isolation.
    It removes any test data that might interfere with other tests.
    """
    yield
    
    # Cleanup after test - session_factory is already the factory
    async with session_factory() as session:
        try:
            # Delete test users and cascade will handle related data
            await session.execute(
                text("DELETE FROM aico_core.user_profiles WHERE uuid LIKE 'test_user_%'")
            )
            await session.commit()
        except Exception as e:
            await session.rollback()
            # Silently ignore cleanup errors
