"""
Skills Reflection Coverage Tests

Tests for reflection skills to improve coverage.
Follows patterns from existing agency tests.
"""

import pytest
from datetime import datetime, timedelta, UTC
import uuid

from aico.ai.agency.skills.reflection.goal import ReflectOnGoalSkill
from aico.ai.agency.models import (
    Goal,
    GoalOrigin,
    GoalPriority,
    GoalStatus,
    Plan,
    PlanStatus,
    PlanStep,
    StepStatus,
)


@pytest.mark.asyncio
class TestReflectOnGoalSkill:
    """Test suite for ReflectOnGoalSkill."""
    
    async def test_skill_properties(self, agency_engine):
        """Test skill has correct properties."""
        skill = ReflectOnGoalSkill(agency_service=agency_engine.agency_service)
        
        assert skill.skill_id == "reflect_on_goal"
        assert skill.name == "Reflect on Goal"
        assert "progress" in skill.description.lower()
        assert skill.category == "reflection"
        assert len(skill.parameters) == 2
        
        # Check parameters
        param_names = [p.name for p in skill.parameters]
        assert "goal_id" in param_names
        assert "include_history" in param_names
    
    async def test_reflect_on_pending_goal(self, agency_engine, test_user):
        """Test reflection on a pending goal with no plans."""
        # Arrange
        skill = ReflectOnGoalSkill(agency_service=agency_engine.agency_service)
        
        goal = Goal(
            goal_id=str(uuid.uuid4()),
            user_id=test_user,
            origin=GoalOrigin.USER,
            goal_type="project",
            title="Test Goal",
            description="Test",
            status=GoalStatus.PENDING,
            priority=GoalPriority.NORMAL,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC)
        )
        
        await agency_engine.agency_service.create_goal(goal)
        
        # Act
        result = await skill.execute(
            user_id=test_user,
            input_data={"goal_id": goal.goal_id, "include_history": True},
            context={}
        )
        
        # Assert
        assert result.success is True
        assert result.output["goal_id"] == goal.goal_id
        assert result.output["goal_status"] == "pending"
        assert "No plans created" in str(result.output["blockers"])
        assert len(result.output["insights"]) > 0
        assert len(result.output["recommendations"]) > 0
    
    async def test_reflect_on_active_goal_with_plan(self, agency_engine, test_user):
        """Test reflection on active goal with a plan."""
        # Arrange
        # Using agency_engine fixture instead
        skill = ReflectOnGoalSkill(agency_service=agency_engine.agency_service)
        
        goal = Goal(
            goal_id=str(uuid.uuid4()),
            user_id=test_user,
            origin=GoalOrigin.USER,
            goal_type="project",
            title="Active Goal",
            description="Test",
            status=GoalStatus.ACTIVE,
            priority=GoalPriority.NORMAL,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC)
        )
        
        plan = Plan(
            plan_id=str(uuid.uuid4()),
            goal_id=goal.goal_id,
            user_id=test_user,
            title="Test Plan",
            description="Test",
            status=PlanStatus.ACTIVE,
            steps=[
                PlanStep(
                    step_id=str(uuid.uuid4()),
                    order=1,
                    description="Step 1",
                    skill_name="test_skill",
                    parameters={},
                    status=StepStatus.PENDING
                )
            ],
            metadata={},
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC)
        )
        
        await agency_engine.agency_service.create_goal(goal)
        await agency_engine.agency_service.create_plan(plan)
        
        # Act
        result = await skill.execute(
            user_id=test_user,
            input_data={"goal_id": goal.goal_id, "include_history": True},
            context={}
        )
        
        # Assert
        assert result.success is True
        assert result.output["goal_status"] == "active"
        assert result.output["plans_count"] == 1
        assert "active plan" in str(result.output["insights"]).lower()
    
    async def test_reflect_on_paused_goal(self, agency_engine, test_user):
        """Test reflection on paused goal."""
        # Arrange
        # Using agency_engine fixture instead
        skill = ReflectOnGoalSkill(agency_service=agency_engine.agency_service)
        
        goal = Goal(
            goal_id=str(uuid.uuid4()),
            user_id=test_user,
            origin=GoalOrigin.USER,
            goal_type="project",
            title="Paused Goal",
            description="Test",
            status=GoalStatus.PAUSED,
            priority=GoalPriority.NORMAL,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC)
        )
        
        await agency_engine.agency_service.create_goal(goal)
        
        # Act
        result = await skill.execute(
            user_id=test_user,
            input_data={"goal_id": goal.goal_id},
            context={}
        )
        
        # Assert
        assert result.success is True
        assert "paused" in str(result.output["blockers"]).lower()
        assert any("resuming" in r.lower() for r in result.output["recommendations"])
    
    async def test_reflect_without_history(self, agency_engine, test_user):
        """Test reflection without including execution history."""
        # Arrange
        # Using agency_engine fixture instead
        skill = ReflectOnGoalSkill(agency_service=agency_engine.agency_service)
        
        goal = Goal(
            goal_id=str(uuid.uuid4()),
            user_id=test_user,
            origin=GoalOrigin.USER,
            goal_type="project",
            title="Test Goal",
            description="Test",
            status=GoalStatus.ACTIVE,
            priority=GoalPriority.NORMAL,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC)
        )
        
        await agency_engine.agency_service.create_goal(goal)
        
        # Act
        result = await skill.execute(
            user_id=test_user,
            input_data={"goal_id": goal.goal_id, "include_history": False},
            context={}
        )
        
        # Assert
        assert result.success is True
        assert result.output["executions_analyzed"] == 0
    
    async def test_reflect_on_nonexistent_goal(self, agency_engine, test_user):
        """Test reflection on non-existent goal."""
        # Arrange
        skill = ReflectOnGoalSkill(agency_service=agency_engine.agency_service)
        
        # Act
        result = await skill.execute(
            user_id=test_user,
            input_data={"goal_id": str(uuid.uuid4())},
            context={}
        )
        
        # Assert
        assert result.success is False
        assert "not found" in result.error.lower()
    
    async def test_reflect_with_draft_plans(self, agency_engine, test_user):
        """Test reflection on goal with draft plans."""
        # Arrange
        # Using agency_engine fixture instead
        skill = ReflectOnGoalSkill(agency_service=agency_engine.agency_service)
        
        goal = Goal(
            goal_id=str(uuid.uuid4()),
            user_id=test_user,
            origin=GoalOrigin.USER,
            goal_type="project",
            title="Goal with Drafts",
            description="Test",
            status=GoalStatus.ACTIVE,
            priority=GoalPriority.NORMAL,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC)
        )
        
        plan1 = Plan(
            plan_id=str(uuid.uuid4()),
            goal_id=goal.goal_id,
            user_id=test_user,
            title="Draft Plan 1",
            description="Test",
            status=PlanStatus.DRAFT,
            steps=[],
            metadata={},
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC)
        )
        
        plan2 = Plan(
            plan_id=str(uuid.uuid4()),
            goal_id=goal.goal_id,
            user_id=test_user,
            title="Draft Plan 2",
            description="Test",
            status=PlanStatus.DRAFT,
            steps=[],
            metadata={},
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC)
        )
        
        await agency_engine.agency_service.create_goal(goal)
        await agency_engine.agency_service.create_plan(plan1)
        await agency_engine.agency_service.create_plan(plan2)
        
        # Act
        result = await skill.execute(
            user_id=test_user,
            input_data={"goal_id": goal.goal_id},
            context={}
        )
        
        # Assert
        assert result.success is True
        assert result.output["plans_count"] == 2
        assert any("2 draft plan" in str(i) for i in result.output["insights"])
    
    async def test_reflect_result_structure(self, agency_engine, test_user):
        """Test that reflection result has correct structure."""
        # Arrange
        # Using agency_engine fixture instead
        skill = ReflectOnGoalSkill(agency_service=agency_engine.agency_service)
        
        goal = Goal(
            goal_id=str(uuid.uuid4()),
            user_id=test_user,
            origin=GoalOrigin.USER,
            goal_type="project",
            title="Test Goal",
            description="Test",
            status=GoalStatus.ACTIVE,
            priority=GoalPriority.NORMAL,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC)
        )
        
        await agency_engine.agency_service.create_goal(goal)
        
        # Act
        result = await skill.execute(
            user_id=test_user,
            input_data={"goal_id": goal.goal_id},
            context={}
        )
        
        # Assert
        assert result.success is True
        output = result.output
        
        # Check all required fields
        assert "goal_id" in output
        assert "goal_title" in output
        assert "goal_status" in output
        assert "progress_assessment" in output
        assert "blockers" in output
        assert "insights" in output
        assert "recommendations" in output
        assert "plans_count" in output
        assert "executions_analyzed" in output
        assert "reflected_at" in output
        
        # Check types
        assert isinstance(output["blockers"], list)
        assert isinstance(output["insights"], list)
        assert isinstance(output["recommendations"], list)
        assert isinstance(output["plans_count"], int)
        assert isinstance(output["executions_analyzed"], int)
