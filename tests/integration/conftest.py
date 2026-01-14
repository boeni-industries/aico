"""
Shared test fixtures for integration tests.

Provides:
- Database session management
- Test data cleanup
- Common fixtures for users, goals, plans, etc.
"""

import pytest
import uuid
from datetime import datetime, UTC
from sqlalchemy import text

from aico.data.postgres.connection import get_session_factory
from aico.data.uow import UnitOfWork
from aico.ai.user.models import UserProfile


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
