"""
Agency Test Fixtures

Provides reusable test data and fixtures for agency system testing.
"""

import pytest
from datetime import datetime, timedelta, UTC
from typing import Dict, Any

from aico.ai.agency.models import (
    Goal,
    GoalOrigin,
    GoalPriority,
    GoalStatus,
    Plan,
    PlanStatus,
    PlanStep,
    StepStatus,
    AgencyEvent,
)


@pytest.fixture
def sample_goal(test_user) -> Goal:
    """Provide a basic test goal with real test user."""
    return Goal(
        goal_id="test-goal-1",
        user_id=test_user,
        origin=GoalOrigin.USER,
        goal_type="project",
        title="Learn Python Testing",
        description="Master pytest and write comprehensive tests for AICO",
        status=GoalStatus.PENDING,
        priority=GoalPriority.NORMAL,
        metadata={"source": "test_fixture"},
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )


@pytest.fixture
def sample_hobby_goal(test_user) -> Goal:
    """Provide a hobby/agent-self goal with real test user."""
    return Goal(
        goal_id="test-goal-hobby-1",
        user_id=test_user,
        origin=GoalOrigin.HOBBY,
        goal_type="learning",
        title="Study quantum computing",
        description="Explore quantum algorithms during idle time",
        status=GoalStatus.PENDING,
        priority=GoalPriority.LOW,
        metadata={"hobby_category": "science"},
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )


@pytest.fixture
def sample_goals(test_user) -> list[Goal]:
    """Provide multiple test goals with different states."""
    now = datetime.now(UTC)
    return [
        Goal(
            goal_id="g1",
            user_id=test_user,
            origin=GoalOrigin.USER,
            goal_type="project",
            title="Build AICO",
            status=GoalStatus.ACTIVE,
            priority=GoalPriority.HIGH,
            created_at=now - timedelta(days=7),
            updated_at=now - timedelta(days=1),
        ),
        Goal(
            goal_id="g2",
            user_id=test_user,
            origin=GoalOrigin.USER,
            goal_type="learning",
            title="Learn Rust",
            status=GoalStatus.PENDING,
            priority=GoalPriority.NORMAL,
            created_at=now - timedelta(days=3),
            updated_at=now - timedelta(days=3),
        ),
        Goal(
            goal_id="g3",
            user_id=test_user,
            origin=GoalOrigin.HOBBY,
            goal_type="hobby",
            title="Read philosophy",
            status=GoalStatus.PAUSED,
            priority=GoalPriority.LOW,
            created_at=now - timedelta(days=30),
            updated_at=now - timedelta(days=15),
        ),
    ]


@pytest.fixture
def sample_plan() -> Plan:
    """Provide a basic test plan."""
    return Plan(
        plan_id="test-plan-1",
        goal_id="test-goal-1",
        status=PlanStatus.DRAFT,
        steps=[
            PlanStep(
                step_id="step-1",
                order=1,
                description="Set up testing environment",
                status=StepStatus.PENDING,
                metadata={"phase": "setup"},
            ),
            PlanStep(
                step_id="step-2",
                order=2,
                description="Write first unit test",
                status=StepStatus.PENDING,
                metadata={"phase": "implementation"},
            ),
            PlanStep(
                step_id="step-3",
                order=3,
                description="Run tests and verify coverage",
                status=StepStatus.PENDING,
                metadata={"phase": "verification"},
            ),
        ],
        metadata={"generated_at": datetime.now(UTC).isoformat()},
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )


@pytest.fixture
def sample_plan_with_shape() -> Plan:
    """Provide a plan generated from a template shape."""
    return Plan(
        plan_id="test-plan-shaped-1",
        goal_id="test-goal-1",
        status=PlanStatus.DRAFT,
        steps=[
            PlanStep(
                step_id="step-1",
                order=1,
                description="Clarify the specific question or outcome for this goal.",
                status=StepStatus.PENDING,
                metadata={
                    "shape_id": "research_then_act",
                    "shape_role": "clarify",
                    "abstract_step_id": "clarify_goal",
                },
            ),
            PlanStep(
                step_id="step-2",
                order=2,
                description="Gather key information, examples, or constraints relevant to the goal.",
                status=StepStatus.PENDING,
                metadata={
                    "shape_id": "research_then_act",
                    "shape_role": "research",
                    "abstract_step_id": "gather_information",
                },
            ),
            PlanStep(
                step_id="step-3",
                order=3,
                description="Summarise options or approaches and choose a direction.",
                status=StepStatus.PENDING,
                metadata={
                    "shape_id": "research_then_act",
                    "shape_role": "synthesize",
                    "abstract_step_id": "synthesize_options",
                },
            ),
            PlanStep(
                step_id="step-4",
                order=4,
                description="Take the first concrete action towards the chosen direction.",
                status=StepStatus.PENDING,
                metadata={
                    "shape_id": "research_then_act",
                    "shape_role": "act",
                    "abstract_step_id": "take_first_action",
                },
            ),
        ],
        metadata={
            "generated_at": datetime.now(UTC).isoformat(),
            "shape_id": "research_then_act",
        },
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )


@pytest.fixture
def sample_agency_event(test_user) -> AgencyEvent:
    """Provide a sample agency event."""
    return AgencyEvent(
        user_id=test_user,
        goal_id="test-goal-1",
        plan_id="test-plan-1",
        event_type="goal_created",
        source="test_fixture",
        payload={"title": "Test Goal", "goal_type": "project"},
        created_at=datetime.now(UTC),
    )


@pytest.fixture
def mock_llm_plan_response() -> Dict[str, Any]:
    """Provide a mock LLM response for plan refinement."""
    return {
        "success": True,
        "data": {
            "content": """1. Set up a comprehensive testing environment with pytest and coverage tools
2. Write your first unit test for the Goal model validation
3. Run the test suite and verify you achieve 80%+ code coverage
4. Review test output and refine your testing approach"""
        },
    }


@pytest.fixture
def mock_llm_plan_response_failure() -> Dict[str, Any]:
    """Provide a mock LLM failure response."""
    return {
        "success": False,
        "error": "Model timeout",
    }


@pytest.fixture
async def seeded_goals(test_db, sample_goals):
    """Seed database with sample goals."""
    from aico.ai.agency.store import GoalStore
    
    # Clean up any existing goals with these IDs first
    test_db.execute("PRAGMA foreign_keys = OFF")
    for goal in sample_goals:
        test_db.execute("DELETE FROM agency_goals WHERE goal_id = ?", (goal.goal_id,))
    test_db.commit()
    test_db.execute("PRAGMA foreign_keys = ON")
    
    store = GoalStore(test_db)
    for goal in sample_goals:
        await store.create_goal(goal)
    
    return sample_goals


@pytest.fixture
async def seeded_goal_with_plan(test_db, sample_goal, sample_plan):
    """Seed database with a goal and its plan."""
    from aico.ai.agency.store import GoalStore, PlanStore
    
    # Clean up any existing goal/plan with these IDs first
    test_db.execute("PRAGMA foreign_keys = OFF")
    test_db.execute("DELETE FROM agency_plans WHERE plan_id = ?", (sample_plan.plan_id,))
    test_db.execute("DELETE FROM agency_goals WHERE goal_id = ?", (sample_goal.goal_id,))
    test_db.commit()
    test_db.execute("PRAGMA foreign_keys = ON")
    
    goal_store = GoalStore(test_db)
    plan_store = PlanStore(test_db)
    
    await goal_store.create_goal(sample_goal)
    await plan_store.create_plan(sample_plan)
    
    return sample_goal, sample_plan


@pytest.fixture
def permissive_value_profile(test_user, test_db):
    """Create a permissive value profile for testing that allows all curiosity signals."""
    from aico.ai.agency.values_ethics import ValuesEthicsService, ProactiveBehaviorLevel
    
    service = ValuesEthicsService(test_db)
    
    # Get or create profile
    profile = service._get_or_create_profile(test_user)
    
    # Make it permissive - no sensitive areas, high curiosity intensity
    profile.sensitive_life_areas = []  # No sensitive areas
    profile.curiosity_intensity = 1.0  # Allow all curiosity signals
    profile.proactive_behavior_level = ProactiveBehaviorLevel.PROACTIVE
    
    # Update in database
    test_db.execute(
        """
        UPDATE ethics_value_profiles 
        SET sensitive_life_areas = ?, curiosity_intensity = ?, proactive_behavior_level = ?
        WHERE profile_id = ?
        """,
        ("[]", 1.0, "proactive", profile.profile_id)
    )
    test_db.commit()
    
    return profile


@pytest.fixture
def mock_message_bus():
    """Provide a mock message bus for testing."""
    from unittest.mock import MagicMock
    
    mock = MagicMock()
    mock.publish_called = False
    mock.published_topics = []
    
    async def mock_publish(topic, message):
        mock.publish_called = True
        mock.published_topics.append(topic)
    
    mock.publish = mock_publish
    mock.connect = MagicMock()
    mock.disconnect = MagicMock()
    
    return mock


@pytest.fixture
def agency_engine(test_db, test_config, mock_message_bus):
    """Provide an initialized AgencyEngine for testing."""
    from aico.ai.agency.engine import AgencyEngine
    
    engine = AgencyEngine(
        config=test_config,
        db_connection=test_db,
        message_bus=mock_message_bus,
    )
    
    return engine
