"""
Phase 1 Integration Tests: Planning

Tests the planning system including:
- Deterministic plan generation with hand-authored shapes
- Plan shape selection based on goal type
- Plan storage and retrieval
- LLM-enhanced planning (with mocked LLM)
"""

import pytest
from unittest.mock import AsyncMock, patch

from aico.core.config import ConfigurationManager
from aico.ai.agency import AgencyEngine
from aico.ai.agency.planner import Planner
from aico.ai.agency.models import PlanStatus


@pytest.mark.asyncio
class TestPlanning:
    """Test suite for planning system."""

    @pytest.fixture
    async def session_factory(self):
        from aico.data.postgres.connection import get_session_factory

        return await get_session_factory()

    @pytest.fixture
    async def uow(self, session_factory):
        from aico.data.uow import UnitOfWork

        async with UnitOfWork(session_factory) as uow:
            yield uow
            await uow.rollback()

    @pytest.fixture
    def agency_service(self, uow):
        from aico.services.agency_service import AgencyService

        return AgencyService(uow)

    @pytest.fixture
    def mock_llm_client(self):
        mock_client = AsyncMock()
        mock_client.model_name = "test-model"

        async def failing_chat(*args, **kwargs):
            raise Exception("LLM unavailable")

        mock_client.get_chat_completions = AsyncMock(side_effect=failing_chat)
        return mock_client
    
    async def test_generate_plan_with_shape_match(self, test_db, sample_goal, mock_llm_client):
        """Test plan generation when goal type matches a template shape."""
        # Arrange
        planner = Planner(mock_llm_client)
        sample_goal.goal_type = "project"  # Should match "research_then_act" or "implement_feature"
        
        # Act
        plan = await planner.generate_initial_plan(sample_goal)
        
        # Assert: Plan generated
        assert plan is not None
        assert plan.goal_id == sample_goal.goal_id
        assert plan.status == PlanStatus.DRAFT
        assert len(plan.steps) > 2  # Template shapes have 3-4 steps
        
        # Assert: Plan uses a shape
        assert "shape_id" in plan.steps[0].metadata
        assert "shape_role" in plan.steps[0].metadata
    
    async def test_generate_plan_fallback(self, test_db, sample_goal, mock_llm_client):
        """Test plan generation falls back to default plan when no shape matches."""
        # Arrange
        planner = Planner(mock_llm_client)
        sample_goal.goal_type = "unknown_type"  # Won't match any shape
        
        # Act
        plan = await planner.generate_initial_plan(sample_goal)
        
        # Assert: Fallback plan generated with default steps
        assert plan is not None
        assert len(plan.steps) >= 2  # At least clarify and act steps
        assert plan.steps[0].description  # Has some description
    
    async def test_plan_storage_and_retrieval(self, test_config, test_db, sample_goal, sample_plan, agency_service, session_factory):
        """Test that plans persist correctly."""
        # Arrange
        engine = AgencyEngine(test_config, agency_service, session_factory=session_factory)

        # Create goal first
        await agency_service.create_goal(sample_goal)

        # Act: Store plan
        stored_plan = await agency_service.create_plan(sample_plan)
        
        # Assert: Plan stored
        assert stored_plan.plan_id == sample_plan.plan_id
        
        # Act: Retrieve plan
        retrieved_plan = await agency_service.get_plan(sample_plan.plan_id)
        
        # Assert: Plan retrieved correctly
        assert retrieved_plan is not None
        assert retrieved_plan.plan_id == sample_plan.plan_id
        assert len(retrieved_plan.steps) == len(sample_plan.steps)
        assert retrieved_plan.steps[0].description == sample_plan.steps[0].description
    
    async def test_plan_shape_selection_by_goal_type(self, test_db, mock_llm_client):
        """Test that different goal types select appropriate plan shapes."""
        # Arrange
        planner = Planner(mock_llm_client)
        from aico.ai.agency.models import Goal, GoalOrigin, GoalPriority, GoalStatus
        
        test_cases = [
            ("project", "research_then_act"),
            ("learning", "research_then_act"),
            ("feature", "implement_feature"),
            ("development", "implement_feature"),
            ("maintenance", "maintenance_cycle"),
            ("cleanup", "maintenance_cycle"),
        ]
        
        for goal_type, expected_shape in test_cases:
            # Arrange
            goal = Goal(
                goal_id=f"test-{goal_type}",
                user_id="test-user",
                origin=GoalOrigin.USER,
                goal_type=goal_type,
                title=f"Test {goal_type} goal",
                status=GoalStatus.PENDING,
                priority=GoalPriority.NORMAL,
            )
            
            # Act
            plan = await planner.generate_initial_plan(goal)
            
            # Assert: Correct shape selected
            if plan.steps[0].metadata.get("shape_id"):
                assert plan.steps[0].metadata["shape_id"] == expected_shape, \
                    f"Goal type '{goal_type}' should use shape '{expected_shape}'"
    
    @patch("backend.services.agency_planner.ModelServiceClient")
    async def test_llm_plan_refinement_success(self, mock_client_class, test_config, test_db, sample_goal, mock_llm_plan_response):
        """Test LLM-enhanced plan refinement when LLM call succeeds."""
        # Arrange
        from aico.data.postgres.connection import get_session_factory
        from aico.data.uow import UnitOfWork
        from aico.services.agency_service import AgencyService

        session_factory = await get_session_factory()
        async with UnitOfWork(session_factory) as uow:
            service = AgencyService(uow)
            engine = AgencyEngine(test_config, service, session_factory=session_factory)
        
        # Mock ModelServiceClient
        mock_client = AsyncMock()
        mock_client.get_chat_completions = AsyncMock(return_value=mock_llm_plan_response)
        mock_client_class.return_value = mock_client
        
        # Generate base plan
        base_plan = await engine.planner.generate_initial_plan(sample_goal)
        
        # Mock LLM refiner (would normally be injected by lifecycle_manager)
        from backend.services.agency_planner import LLMPlanningHelper
        llm_helper = LLMPlanningHelper(test_config, mock_client)
        
        # Act: Refine plan with LLM
        refined_plan = await llm_helper.refine_plan_with_llm(sample_goal, base_plan)
        
        # Assert: Plan refined
        assert refined_plan is not None
        assert refined_plan.metadata.get("llm_refined") is True
        assert "llm_model" in refined_plan.metadata
        
        # Assert: LLM was called
        mock_client.get_chat_completions.assert_called_once()
    
    @patch("backend.services.agency_planner.ModelServiceClient")
    async def test_llm_plan_refinement_failure_fallback(self, mock_client_class, test_config, test_db, sample_goal, mock_llm_plan_response_failure):
        """Test that plan refinement falls back to base plan when LLM fails."""
        # Arrange
        from aico.data.postgres.connection import get_session_factory
        from aico.data.uow import UnitOfWork
        from aico.services.agency_service import AgencyService

        session_factory = await get_session_factory()
        async with UnitOfWork(session_factory) as uow:
            service = AgencyService(uow)
            engine = AgencyEngine(test_config, service, session_factory=session_factory)
        
        # Mock ModelServiceClient with failure
        mock_client = AsyncMock()
        mock_client.get_chat_completions = AsyncMock(return_value=mock_llm_plan_response_failure)
        mock_client_class.return_value = mock_client
        
        # Generate base plan
        base_plan = await engine.planner.generate_initial_plan(sample_goal)
        base_step_count = len(base_plan.steps)
        
        # Mock LLM refiner
        from backend.services.agency_planner import LLMPlanningHelper
        llm_helper = LLMPlanningHelper(test_config, mock_client)
        
        # Act: Attempt refinement (should fail gracefully)
        refined_plan = await llm_helper.refine_plan_with_llm(sample_goal, base_plan)
        
        # Assert: Falls back to base plan
        assert refined_plan is not None
        assert len(refined_plan.steps) == base_step_count
        assert refined_plan.metadata.get("llm_refined") is not True
    
    async def test_plan_steps_have_correct_metadata(self, test_db, sample_plan_with_shape):
        """Test that plan steps generated from shapes have correct metadata."""
        # Assert: Each step has shape metadata
        for step in sample_plan_with_shape.steps:
            assert "shape_id" in step.metadata
            assert "shape_role" in step.metadata
            assert "abstract_step_id" in step.metadata
            
            # Assert: Metadata values are consistent
            assert step.metadata["shape_id"] == "research_then_act"
            assert step.metadata["shape_role"] in ["clarify", "research", "synthesize", "act"]
    
    async def test_goal_with_plan_end_to_end(self, test_config, test_db, test_user, agency_service, session_factory):
        """Test complete flow: create goal → generate plan → store both → retrieve both."""
        # Arrange
        engine = AgencyEngine(test_config, agency_service, session_factory=session_factory)
        
        # Act: Create goal with plan
        goal, plan = await engine.create_goal_with_optional_plan(
            user_id=test_user,
            title="End-to-end Test Goal",
            description="Test the complete goal + plan flow",
            goal_type="project",
            auto_plan=True,
        )
        
        # Assert: Both created
        assert goal is not None
        assert plan is not None
        
        # Act: Retrieve goal
        retrieved_goal = await engine.get_goal(goal.goal_id)
        
        # Assert: Goal retrieved
        assert retrieved_goal is not None
        assert retrieved_goal.goal_id == goal.goal_id
        
        # Act: Retrieve plans for goal
        plans = await agency_service.list_plans(goal.goal_id)
        
        # Assert: Plan retrieved
        assert len(plans) == 1
        assert plans[0].plan_id == plan.plan_id
        assert len(plans[0].steps) == len(plan.steps)
