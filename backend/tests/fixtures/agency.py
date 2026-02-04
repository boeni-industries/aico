"""
Agency Test Fixtures

Provides reusable test data and fixtures for agency system testing.
"""

import pytest
import pytest_asyncio
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
    from aico.services.agency_service import AgencyService
    from aico.data.uow import UnitOfWork
    from aico.data.postgres.connection import get_session_factory

    session_factory = await get_session_factory()
    async with UnitOfWork(session_factory) as uow:
        agency_service = AgencyService(uow)

        # Clean up any existing goals with these IDs first
        for goal in sample_goals:
            await uow.goals.delete(goal.goal_id)

        # Seed goals
        for goal in sample_goals:
            await agency_service.create_goal(goal)

    return sample_goals


@pytest.fixture
async def seeded_goal_with_plan(test_db, sample_goal, sample_plan):
    """Seed database with a goal and its plan."""
    from aico.services.agency_service import AgencyService
    from aico.data.uow import UnitOfWork
    from aico.data.postgres.connection import get_session_factory

    session_factory = await get_session_factory()
    async with UnitOfWork(session_factory) as uow:
        agency_service = AgencyService(uow)

        # Clean up any existing goal/plan with these IDs first
        await uow.plans.delete(sample_plan.plan_id)
        await uow.goals.delete(sample_goal.goal_id)
        await uow.commit()

        await agency_service.create_goal(sample_goal)
        await agency_service.create_plan(sample_plan)

    return sample_goal, sample_plan


@pytest.fixture
async def permissive_value_profile(test_user):
    """Create a permissive value profile for testing that allows all curiosity signals."""
    from aico.ai.agency.values_ethics import ValuesEthicsService, ProactiveBehaviorLevel
    from aico.data.postgres.connection import get_session_factory
    from aico.data.uow import UnitOfWork
    
    service = ValuesEthicsService()
    session_factory = await get_session_factory()
    
    async with UnitOfWork(session_factory) as uow:
        # Get or create profile
        profile = await service._get_or_create_profile(test_user, uow)
    
        # Make it permissive - no sensitive areas, high curiosity intensity
        profile.sensitive_life_areas = []  # No sensitive areas
        profile.curiosity_intensity = 1.0  # Allow all curiosity signals
        profile.proactive_behavior_level = ProactiveBehaviorLevel.PROACTIVE

        entity = await uow.ethics_value_profiles.get_by_user_id(test_user)
        if entity is not None:
            entity.sensitive_life_areas = "[]"
            entity.allowed_curiosity_domains = "[]"
            entity.curiosity_intensity = 1.0
            entity.proactive_behavior_level = ProactiveBehaviorLevel.PROACTIVE.value
            entity.storage_preferences = "{}"
            await uow.ethics_value_profiles.update(entity)
        await uow.commit()
    
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


@pytest_asyncio.fixture
async def agency_engine(test_config, mock_message_bus):
    """Provide an initialized AgencyEngine for testing."""
    from aico.ai.agency.engine import AgencyEngine
    from aico.data.postgres.connection import get_session_factory
    from aico.data.uow import UnitOfWork
    from aico.services.agency_service import AgencyService

    session_factory = await get_session_factory()
    uow = UnitOfWork(session_factory)
    async with uow:
        service = AgencyService(uow)
        engine = AgencyEngine(
            config=test_config,
            agency_service=service,
            message_bus=mock_message_bus,
            session_factory=session_factory,
        )
        yield engine

        await uow.rollback()
