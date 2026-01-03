"""
Executor Coverage Tests

Tests for PlanExecutor to improve coverage of executor.py.
Follows patterns from existing agency tests.
"""

import pytest
from datetime import datetime, UTC
from unittest.mock import AsyncMock, patch, MagicMock
import uuid

from aico.ai.agency import AgencyEngine
from aico.ai.agency.executor import PlanExecutor, ExecutionStatus, StepExecutionStatus
from aico.ai.agency.store import PlanStore
from aico.ai.agency.models import (
    Plan,
    PlanStep,
    PlanStatus,
    StepStatus,
    Goal,
    GoalOrigin,
    GoalPriority,
    GoalStatus
)


@pytest.mark.asyncio
class TestPlanExecutor:
    """Test suite for PlanExecutor."""
    
    async def test_start_execution_creates_execution_record(self, test_config, test_db, test_user):
        """Test that starting execution creates proper execution record."""
        # Arrange
        engine = AgencyEngine(test_config, test_db)
        
        # Create goal and plan
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
        
        await engine.goal_store.create_goal(goal)
        await engine.plan_store.create_plan(plan)
        
        # Act
        executor = PlanExecutor(
            db=test_db,
            plan_store=engine.plan_store,
            goal_store=engine.goal_store,
            skill_invoker=None
        )
        
        execution = await executor.start_execution(
            plan_id=plan.plan_id,
            goal_id=goal.goal_id,
            user_id=test_user
        )
        
        # Assert
        assert execution is not None
        assert execution.plan_id == plan.plan_id
        assert execution.goal_id == goal.goal_id
        assert execution.user_id == test_user
        assert execution.status == ExecutionStatus.PENDING
        assert execution.steps_total == len(plan.steps)
    
    async def test_start_execution_with_context(self, test_config, test_db, test_user):
        """Test starting execution with execution context."""
        # Arrange
        engine = AgencyEngine(test_config, test_db)
        
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
        
        await engine.goal_store.create_goal(goal)
        await engine.plan_store.create_plan(plan)
        
        executor = PlanExecutor(
            db=test_db,
            plan_store=engine.plan_store,
            goal_store=engine.goal_store,
            skill_invoker=None
        )
        
        context = {"personality": "helpful", "emotion": "neutral"}
        
        # Act
        execution = await executor.start_execution(
            plan_id=plan.plan_id,
            goal_id=goal.goal_id,
            user_id=test_user,
            context=context
        )
        
        # Assert
        assert execution.execution_context == context
    
    async def test_start_execution_nonexistent_plan_raises_error(self, test_config, test_db, test_user):
        """Test that starting execution for non-existent plan raises error."""
        # Arrange
        engine = AgencyEngine(test_config, test_db)
        executor = PlanExecutor(
            db=test_db,
            plan_store=engine.plan_store,
            goal_store=engine.goal_store,
            skill_invoker=None
        )
        
        # Act & Assert
        with pytest.raises(ValueError, match="not found"):
            await executor.start_execution(
                plan_id=str(uuid.uuid4()),
                goal_id=str(uuid.uuid4()),
                user_id=test_user
            )
    
    async def test_pause_execution_changes_status(self, test_config, test_db, test_user):
        """Test pausing execution changes status to PAUSED."""
        # Arrange
        engine = AgencyEngine(test_config, test_db)
        
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
        
        await engine.goal_store.create_goal(goal)
        await engine.plan_store.create_plan(plan)
        
        executor = PlanExecutor(
            db=test_db,
            plan_store=engine.plan_store,
            goal_store=engine.goal_store,
            skill_invoker=None
        )
        
        execution = await executor.start_execution(
            plan_id=plan.plan_id,
            goal_id=goal.goal_id,
            user_id=test_user
        )
        
        # Update to running state first
        execution.status = ExecutionStatus.RUNNING
        await executor._save_execution(execution)
        
        # Act
        paused = await executor.pause_execution(execution.execution_id)
        
        # Assert
        assert paused.status == ExecutionStatus.PAUSED
        assert paused.paused_at is not None
    
    async def test_resume_execution_changes_status(self, test_config, test_db, test_user):
        """Test resuming execution changes status to RUNNING."""
        # Arrange
        engine = AgencyEngine(test_config, test_db)
        
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
        
        await engine.goal_store.create_goal(goal)
        await engine.plan_store.create_plan(plan)
        
        executor = PlanExecutor(
            db=test_db,
            plan_store=engine.plan_store,
            goal_store=engine.goal_store,
            skill_invoker=None
        )
        
        execution = await executor.start_execution(
            plan_id=plan.plan_id,
            goal_id=goal.goal_id,
            user_id=test_user
        )
        
        # Pause it first
        execution.status = ExecutionStatus.RUNNING
        await executor._save_execution(execution)
        paused = await executor.pause_execution(execution.execution_id)
        
        # Act
        resumed = await executor.resume_execution(paused.execution_id)
        
        # Assert
        assert resumed.status == ExecutionStatus.RUNNING
        assert resumed.paused_at is None
    
    async def test_cancel_execution_sets_cancellation_reason(self, test_config, test_db, test_user):
        """Test cancelling execution sets cancellation reason."""
        # Arrange
        engine = AgencyEngine(test_config, test_db)
        
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
        
        await engine.goal_store.create_goal(goal)
        await engine.plan_store.create_plan(plan)
        
        executor = PlanExecutor(
            db=test_db,
            plan_store=engine.plan_store,
            goal_store=engine.goal_store,
            skill_invoker=None
        )
        
        execution = await executor.start_execution(
            plan_id=plan.plan_id,
            goal_id=goal.goal_id,
            user_id=test_user
        )
        
        # Act
        cancelled = await executor.cancel_execution(
            execution.execution_id,
            reason="User requested cancellation"
        )
        
        # Assert
        assert cancelled.status == ExecutionStatus.CANCELLED
        assert cancelled.cancelled_at is not None
        assert cancelled.cancellation_reason == "User requested cancellation"
    
    async def test_get_execution_status_returns_details(self, test_config, test_db, test_user):
        """Test getting execution status returns detailed information."""
        # Arrange
        engine = AgencyEngine(test_config, test_db)
        
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
        
        await engine.goal_store.create_goal(goal)
        await engine.plan_store.create_plan(plan)
        
        executor = PlanExecutor(
            db=test_db,
            plan_store=engine.plan_store,
            goal_store=engine.goal_store,
            skill_invoker=None
        )
        
        execution = await executor.start_execution(
            plan_id=plan.plan_id,
            goal_id=goal.goal_id,
            user_id=test_user
        )
        
        # Act
        status = await executor.get_execution_status(execution.execution_id)
        
        # Assert
        assert status is not None
        assert status["execution_id"] == execution.execution_id
        assert status["plan_id"] == plan.plan_id
        assert status["goal_id"] == goal.goal_id
        assert status["status"] == ExecutionStatus.PENDING.value
        assert "steps" in status
    
    async def test_get_execution_status_nonexistent_returns_none(self, test_config, test_db):
        """Test getting status for non-existent execution returns None."""
        # Arrange
        engine = AgencyEngine(test_config, test_db)
        executor = PlanExecutor(
            db=test_db,
            plan_store=engine.plan_store,
            goal_store=engine.goal_store,
            skill_invoker=None
        )
        
        # Act
        status = await executor.get_execution_status(str(uuid.uuid4()))
        
        # Assert
        assert status is None
    
    async def test_execute_next_step_completes_step(self, test_config, test_db, test_user):
        """Test executing next step completes it successfully."""
        engine = AgencyEngine(test_config, test_db)
        
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
        
        await engine.goal_store.create_goal(goal)
        await engine.plan_store.create_plan(plan)
        
        executor = PlanExecutor(
            db=test_db,
            plan_store=engine.plan_store,
            goal_store=engine.goal_store,
            skill_invoker=None
        )
        
        execution = await executor.start_execution(
            plan_id=plan.plan_id,
            goal_id=goal.goal_id,
            user_id=test_user
        )
        
        # Act
        has_more, step_exec = await executor.execute_next_step(execution.execution_id)
        
        # Assert
        assert has_more is False  # No more steps
        assert step_exec is not None
        assert step_exec.status == StepExecutionStatus.COMPLETED
    
    async def test_execute_next_step_with_invalid_status(self, test_config, test_db, test_user):
        """Test executing step with invalid execution status returns False."""
        engine = AgencyEngine(test_config, test_db)
        
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
        
        plan = Plan(
            plan_id=str(uuid.uuid4()),
            goal_id=goal.goal_id,
            user_id=test_user,
            title="Test Plan",
            description="Test",
            status=PlanStatus.ACTIVE,
            steps=[],
            metadata={},
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC)
        )
        
        await engine.goal_store.create_goal(goal)
        await engine.plan_store.create_plan(plan)
        
        executor = PlanExecutor(
            db=test_db,
            plan_store=engine.plan_store,
            goal_store=engine.goal_store,
            skill_invoker=None
        )
        
        execution = await executor.start_execution(
            plan_id=plan.plan_id,
            goal_id=goal.goal_id,
            user_id=test_user
        )
        
        # Cancel execution to make it invalid
        await executor.cancel_execution(execution.execution_id, "test")
        
        # Act
        has_more, step_exec = await executor.execute_next_step(execution.execution_id)
        
        # Assert
        assert has_more is False
        assert step_exec is None
    
    async def test_execute_next_step_nonexistent_execution_raises_error(self, test_config, test_db):
        """Test executing step for non-existent execution raises error."""
        engine = AgencyEngine(test_config, test_db)
        executor = PlanExecutor(
            db=test_db,
            plan_store=engine.plan_store,
            goal_store=engine.goal_store,
            skill_invoker=None
        )
        
        # Act & Assert
        with pytest.raises(ValueError, match="not found"):
            await executor.execute_next_step(str(uuid.uuid4()))
    
    async def test_execute_next_step_updates_progress(self, test_config, test_db, test_user):
        """Test executing step updates execution progress."""
        engine = AgencyEngine(test_config, test_db)
        
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
                ),
                PlanStep(
                    step_id=str(uuid.uuid4()),
                    order=2,
                    description="Step 2",
                    skill_name="test_skill",
                    parameters={},
                    status=StepStatus.PENDING
                )
            ],
            metadata={},
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC)
        )
        
        await engine.goal_store.create_goal(goal)
        await engine.plan_store.create_plan(plan)
        
        executor = PlanExecutor(
            db=test_db,
            plan_store=engine.plan_store,
            goal_store=engine.goal_store,
            skill_invoker=None
        )
        
        execution = await executor.start_execution(
            plan_id=plan.plan_id,
            goal_id=goal.goal_id,
            user_id=test_user
        )
        
        # Act - execute first step
        has_more, step_exec = await executor.execute_next_step(execution.execution_id)
        
        # Assert
        assert step_exec is not None
        assert step_exec.status == StepExecutionStatus.COMPLETED
        updated_exec = await executor._get_execution(execution.execution_id)
        assert updated_exec.steps_completed == 1
        assert updated_exec.progress_percentage == 50.0
        assert updated_exec.status == ExecutionStatus.RUNNING
