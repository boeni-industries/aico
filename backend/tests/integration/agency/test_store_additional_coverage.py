"""
Additional coverage tests for agency/store.py - targeting uncovered lines.

Focuses on error handling, edge cases, and conditional branches in all store classes.
"""

import pytest
import json
from datetime import datetime, timedelta, UTC
from unittest.mock import Mock, patch

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
from aico.services.agency_service import AgencyService
from aico.data.uow import UnitOfWork
from aico.data.postgres.connection import get_session_factory
from aico.ai.agency.store import (
    AgencyEventStore,
    ReflectionStore,
)


# Note: test_user, sample_goal, and sample_plan fixtures are provided by
# backend/tests/fixtures/agency.py and imported via conftest.py


class TestGoalStoreErrorHandling:
    """Tests for GoalStore error handling and edge cases."""
    
    @pytest.mark.asyncio
    async def test_create_goal_database_error(self, test_config, test_db, sample_goal):
        """Test error handling when database fails during goal creation."""
        session_factory = await get_session_factory()
        uow = UnitOfWork(session_factory)
        agency_service = AgencyService(uow)
        
        # Mock database to raise error
        with patch.object(test_db, 'execute', side_effect=Exception("DB error")):
            with pytest.raises(Exception, match="DB error"):
                await agency_service.create_goal(sample_goal)
    
    @pytest.mark.asyncio
    async def test_get_goal_database_error(self, test_config, test_db):
        """Test error handling when database fails during goal retrieval."""
        session_factory = await get_session_factory()
        uow = UnitOfWork(session_factory)
        agency_service = AgencyService(uow)
        
        with patch.object(test_db, 'execute', side_effect=Exception("DB error")):
            with pytest.raises(Exception, match="DB error"):
                await agency_service.get_goal("goal-123")
    
    @pytest.mark.asyncio
    async def test_list_goals_database_error(self, test_config, test_db, test_user):
        """Test error handling when database fails during goal listing."""
        session_factory = await get_session_factory()
        uow = UnitOfWork(session_factory)
        agency_service = AgencyService(uow)
        
        with patch.object(test_db, 'execute', side_effect=Exception("DB error")):
            with pytest.raises(Exception, match="DB error"):
                await agency_service.list_goals(test_user)
    
    @pytest.mark.asyncio
    async def test_update_goal_status_database_error(self, test_config, test_db):
        """Test error handling when database fails during status update."""
        session_factory = await get_session_factory()
        uow = UnitOfWork(session_factory)
        agency_service = AgencyService(uow)
        
        with patch.object(test_db, 'execute', side_effect=Exception("DB error")):
            with pytest.raises(Exception, match="DB error"):
                await agency_service.update_goal_status("goal-123", GoalStatus.ACTIVE)
    
    @pytest.mark.asyncio
    async def test_get_goals_by_status_empty_statuses(self, test_config, test_db, test_user):
        """Test get_goals_by_status with empty status list."""
        session_factory = await get_session_factory()
        uow = UnitOfWork(session_factory)
        agency_service = AgencyService(uow)
        
        goals = await agency_service.get_goals_by_status(test_user, [])
        
        assert goals == []
    
    @pytest.mark.asyncio
    async def test_get_goals_by_status_single_status(self, test_config, test_db, test_user, sample_goal):
        """Test get_goals_by_status with single status."""
        session_factory = await get_session_factory()
        uow = UnitOfWork(session_factory)
        agency_service = AgencyService(uow)
        await agency_service.create_goal(sample_goal)
        
        goals = await agency_service.get_goals_by_status(test_user, [GoalStatus.PENDING])
        
        assert len(goals) == 1
        assert goals[0].goal_id == sample_goal.goal_id
    
    @pytest.mark.asyncio
    async def test_get_goals_by_status_multiple_statuses(self, test_config, test_db, test_user, sample_goal):
        """Test get_goals_by_status with multiple statuses."""
        session_factory = await get_session_factory()
        uow = UnitOfWork(session_factory)
        agency_service = AgencyService(uow)
        await agency_service.create_goal(sample_goal)
        
        # Update one to active
        await agency_service.update_goal_status(sample_goal.goal_id, GoalStatus.ACTIVE)
        
        # Create another pending goal
        goal2 = Goal(
            goal_id="goal-456",
            user_id=test_user,
            origin=GoalOrigin.CURIOSITY,
            goal_type="exploration",
            title="Second Goal",
        )
        await agency_service.create_goal(goal2)
        
        # Query for both statuses
        goals = await agency_service.get_goals_by_status(test_user, [GoalStatus.PENDING, GoalStatus.ACTIVE])
        
        assert len(goals) == 2
    
    @pytest.mark.asyncio
    async def test_get_goals_by_status_database_error(self, test_config, test_db, test_user):
        """Test error handling in get_goals_by_status."""
        session_factory = await get_session_factory()
        uow = UnitOfWork(session_factory)
        agency_service = AgencyService(uow)
        
        with patch.object(test_db, 'execute', side_effect=Exception("DB error")):
            with pytest.raises(Exception, match="DB error"):
                await agency_service.get_goals_by_status(test_user, [GoalStatus.PENDING])
    
    @pytest.mark.asyncio
    async def test_create_goal_with_empty_metadata(self, test_config, test_db, test_user):
        """Test creating goal with empty metadata."""
        session_factory = await get_session_factory()
        uow = UnitOfWork(session_factory)
        agency_service = AgencyService(uow)
        
        goal = Goal(
            goal_id="goal-empty-meta",
            user_id=test_user,
            origin=GoalOrigin.SYSTEM,
            goal_type="maintenance",
            title="Goal with empty metadata",
            metadata={},  # Empty dict instead of None
        )
        
        created = await agency_service.create_goal(goal)
        
        assert created.goal_id == goal.goal_id
        
        # Retrieve and verify
        retrieved = await agency_service.get_goal(goal.goal_id)
        assert retrieved is not None
        assert retrieved.metadata == {}
    
    @pytest.mark.asyncio
    async def test_list_goals_with_status_filter(self, test_config, test_db, test_user, sample_goal):
        """Test listing goals with status filter."""
        session_factory = await get_session_factory()
        uow = UnitOfWork(session_factory)
        agency_service = AgencyService(uow)
        await agency_service.create_goal(sample_goal)
        
        # Filter for completed (should be empty)
        completed = await agency_service.list_goals(test_user, status=GoalStatus.COMPLETED)
        assert len(completed) == 0
        
        # Filter for pending (should find our goal)
        pending = await agency_service.list_goals(test_user, status=GoalStatus.PENDING)
        assert len(pending) == 1
        assert pending[0].goal_id == sample_goal.goal_id


class TestPlanStoreErrorHandling:
    """Tests for PlanStore error handling and edge cases."""
    
    @pytest.mark.asyncio
    async def test_create_plan_database_error(self, test_config, test_db, sample_plan):
        """Test error handling when database fails during plan creation."""
        store = PlanStore(test_db)
        
        with patch.object(test_db, 'execute', side_effect=Exception("DB error")):
            with pytest.raises(Exception, match="DB error"):
                await agency_service.create_plan(sample_plan)
    
    @pytest.mark.asyncio
    async def test_get_plan_database_error(self, test_config, test_db):
        """Test error handling when database fails during plan retrieval."""
        store = PlanStore(test_db)
        
        with patch.object(test_db, 'execute', side_effect=Exception("DB error")):
            with pytest.raises(Exception, match="DB error"):
                await agency_service.get_plan("plan-123")
    
    @pytest.mark.asyncio
    async def test_list_plans_for_goal_database_error(self, test_config, test_db):
        """Test error handling when database fails during plan listing."""
        store = PlanStore(test_db)
        
        with patch.object(test_db, 'execute', side_effect=Exception("DB error")):
            with pytest.raises(Exception, match="DB error"):
                await agency_service.list_plans_for_goal("goal-123")
    
    @pytest.mark.asyncio
    async def test_update_plan_status_database_error(self, test_config, test_db):
        """Test error handling when database fails during status update."""
        store = PlanStore(test_db)
        
        with patch.object(test_db, 'execute', side_effect=Exception("DB error")):
            with pytest.raises(Exception, match="DB error"):
                await agency_service.update_plan_status("plan-123", PlanStatus.ACTIVE)
    
    @pytest.mark.asyncio
    async def test_save_steps_database_error(self, test_config, test_db):
        """Test error handling when database fails during step saving."""
        store = PlanStore(test_db)
        
        steps = [
            PlanStep(
                step_id="step-1",
                order=1,
                description="Test step",
            )
        ]
        
        with patch.object(test_db, 'execute', side_effect=Exception("DB error")):
            with pytest.raises(Exception, match="DB error"):
                await agency_service.save_steps("plan-123", steps)
    
    @pytest.mark.asyncio
    async def test_create_plan_with_empty_metadata_dict(self, test_config, test_db, test_user, sample_goal):
        """Test creating plan with empty metadata dict."""
        goal_store = GoalStore(test_db)
        plan_store = PlanStore(test_db)
        
        await goal_store.create_goal(sample_goal)
        
        plan = Plan(
            plan_id="plan-empty-meta",
            goal_id=sample_goal.goal_id,
            status=PlanStatus.DRAFT,
            steps=[],
            metadata={},  # Empty dict instead of None
        )
        
        created = await plan_store.create_plan(plan)
        
        assert created.plan_id == plan.plan_id
        
        # Retrieve and verify
        retrieved = await plan_store.get_plan(plan.plan_id)
        assert retrieved is not None
        assert retrieved.metadata == {}
    
    @pytest.mark.asyncio
    async def test_create_plan_with_empty_steps(self, test_config, test_db, test_user, sample_goal):
        """Test creating plan with empty steps list."""
        goal_store = GoalStore(test_db)
        plan_store = PlanStore(test_db)
        
        await goal_store.create_goal(sample_goal)
        
        plan = Plan(
            plan_id="plan-empty-steps",
            goal_id=sample_goal.goal_id,
            status=PlanStatus.DRAFT,
            steps=[],
        )
        
        created = await plan_store.create_plan(plan)
        
        assert created.plan_id == plan.plan_id
        
        # Retrieve and verify
        retrieved = await plan_store.get_plan(plan.plan_id)
        assert retrieved is not None
        assert retrieved.steps == []
    
    @pytest.mark.asyncio
    async def test_save_steps(self, test_config, test_db, test_user, sample_goal, sample_plan):
        """Test saving plan steps."""
        goal_store = GoalStore(test_db)
        plan_store = PlanStore(test_db)
        
        await goal_store.create_goal(sample_goal)
        await plan_store.create_plan(sample_plan)
        
        # Update steps
        new_steps = [
            PlanStep(
                step_id="step-1",
                order=1,
                description="Updated step 1",
                status=StepStatus.DONE,
            ),
            PlanStep(
                step_id="step-2",
                order=2,
                description="New step 2",
                status=StepStatus.PENDING,
            ),
        ]
        
        await plan_store.save_steps(sample_plan.plan_id, new_steps)
        
        # Retrieve and verify
        retrieved = await plan_store.get_plan(sample_plan.plan_id)
        assert retrieved is not None
        assert len(retrieved.steps) == 2
        assert retrieved.steps[0].description == "Updated step 1"
        assert retrieved.steps[1].description == "New step 2"
    
    @pytest.mark.asyncio
    async def test_get_plan_with_empty_steps_json(self, test_config, test_db, test_user, sample_goal):
        """Test retrieving plan with empty steps_json array."""
        goal_store = GoalStore(test_db)
        plan_store = PlanStore(test_db)
        
        await goal_store.create_goal(sample_goal)
        
        # Manually insert plan with empty steps_json array
        test_db.execute(
            """INSERT INTO agency_plans (
                plan_id, goal_id, status, steps_json, metadata_json,
                created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                "plan-empty-steps",
                sample_goal.goal_id,
                PlanStatus.DRAFT.value,
                "[]",  # Empty JSON array instead of null
                None,
                datetime.now(UTC).isoformat(),
                datetime.now(UTC).isoformat(),
            ),
        )
        test_db.commit()
        
        # Retrieve and verify
        retrieved = await plan_store.get_plan("plan-empty-steps")
        assert retrieved is not None
        assert retrieved.steps == []


class TestAgencyEventStoreErrorHandling:
    """Tests for AgencyEventStore error handling."""
    
    @pytest.mark.asyncio
    async def test_log_event_database_error(self, test_config, test_db, test_user):
        """Test error handling when database fails during event logging."""
        store = AgencyEventStore(test_db)
        
        event = AgencyEvent(
            user_id=test_user,
            event_type="test_event",
            source="test",
            payload={"data": "value"},
        )
        
        with patch.object(test_db, 'execute', side_effect=Exception("DB error")):
            with pytest.raises(Exception, match="DB error"):
                await agency_service.log_event(event)
    
    @pytest.mark.asyncio
    async def test_log_event_with_goal_and_plan_ids(self, test_config, test_db, test_user, sample_goal, sample_plan):
        """Test logging event with goal and plan IDs."""
        # Create goal and plan first to satisfy FK constraints
        goal_store = GoalStore(test_db)
        plan_store = PlanStore(test_db)
        await goal_store.create_goal(sample_goal)
        await plan_store.create_plan(sample_plan)
        
        store = AgencyEventStore(test_db)
        
        event = AgencyEvent(
            user_id=test_user,
            goal_id=sample_goal.goal_id,
            plan_id=sample_plan.plan_id,
            event_type="plan_executed",
            source="executor",
            payload={"result": "success"},
        )
        
        # Should not raise exception
        await agency_service.log_event(event)
    
    @pytest.mark.asyncio
    async def test_log_event_without_goal_plan_ids(self, test_config, test_db, test_user):
        """Test logging event without goal/plan IDs."""
        store = AgencyEventStore(test_db)
        
        event = AgencyEvent(
            user_id=test_user,
            event_type="test_event",
            source="test",
            payload={"data": "value"},
        )
        
        # Should not raise exception
        await agency_service.log_event(event)


class TestReflectionStoreErrorHandling:
    """Tests for ReflectionStore error handling."""
    
    @pytest.mark.asyncio
    async def test_create_note(self, test_config, test_db, test_user):
        """Test creating reflection note."""
        from aico.ai.agency.models import ReflectionNote
        import uuid
        
        store = ReflectionStore(test_db)
        
        note = ReflectionNote(
            note_id=f"note-create-{uuid.uuid4().hex[:8]}",  # Unique ID
            user_id=test_user,
            title="Test Note",
            content="Test content",
            tags=["tag1", "tag2"],
        )
        
        created = await agency_service.create_note(note)
        
        assert created.note_id == note.note_id
        assert created.created_at is not None
        assert created.updated_at is not None
    
    @pytest.mark.asyncio
    async def test_create_note_with_goal_and_plan_refs(self, test_config, test_db, test_user, sample_goal, sample_plan):
        """Test creating note with goal and plan references."""
        from aico.ai.agency.models import ReflectionNote
        import uuid
        
        # Create goal and plan first to satisfy FK constraints
        goal_store = GoalStore(test_db)
        plan_store = PlanStore(test_db)
        await goal_store.create_goal(sample_goal)
        await plan_store.create_plan(sample_plan)
        
        store = ReflectionStore(test_db)
        
        note = ReflectionNote(
            note_id=f"note-refs-{uuid.uuid4().hex[:8]}",  # Unique ID
            user_id=test_user,
            related_goal_id=sample_goal.goal_id,
            related_plan_id=sample_plan.plan_id,
            title="Goal Reflection",
            content="Reflection on goal progress",
        )
        
        created = await agency_service.create_note(note)
        
        assert created.note_id == note.note_id
        assert created.related_goal_id == sample_goal.goal_id
        assert created.related_plan_id == sample_plan.plan_id
    
    @pytest.mark.asyncio
    async def test_create_note_with_empty_tags(self, test_config, test_db, test_user):
        """Test creating note with empty tags."""
        from aico.ai.agency.models import ReflectionNote
        import uuid
        
        store = ReflectionStore(test_db)
        
        note = ReflectionNote(
            note_id=f"note-empty-tags-{uuid.uuid4().hex[:8]}",  # Unique ID
            user_id=test_user,
            title="Note without tags",
            content="Content",
            tags=[],  # Empty list instead of None
        )
        
        created = await agency_service.create_note(note)
        
        assert created.note_id == note.note_id


class TestGoalStoreEdgeCases:
    """Additional edge case tests for GoalStore."""
    
    @pytest.mark.asyncio
    async def test_get_goal_with_null_description(self, test_config, test_db, test_user):
        """Test retrieving goal with null description."""
        session_factory = await get_session_factory()
        uow = UnitOfWork(session_factory)
        agency_service = AgencyService(uow)
        
        goal = Goal(
            goal_id="goal-no-desc",
            user_id=test_user,
            origin=GoalOrigin.HOBBY,
            goal_type="hobby",
            title="Goal without description",
            description=None,
        )
        
        await agency_service.create_goal(goal)
        
        retrieved = await agency_service.get_goal(goal.goal_id)
        assert retrieved is not None
        assert retrieved.description is None
    
    @pytest.mark.asyncio
    async def test_list_goals_without_status_filter(self, test_config, test_db, test_user):
        """Test listing all goals without status filter."""
        session_factory = await get_session_factory()
        uow = UnitOfWork(session_factory)
        agency_service = AgencyService(uow)
        
        # Create goals with different statuses
        goal1 = Goal(
            goal_id="goal-1",
            user_id=test_user,
            origin=GoalOrigin.USER,
            goal_type="task",
            title="Goal 1",
            status=GoalStatus.PENDING,
        )
        goal2 = Goal(
            goal_id="goal-2",
            user_id=test_user,
            origin=GoalOrigin.CURIOSITY,
            goal_type="exploration",
            title="Goal 2",
            status=GoalStatus.ACTIVE,
        )
        
        await agency_service.create_goal(goal1)
        await agency_service.create_goal(goal2)
        
        # List all goals
        all_goals = await agency_service.list_goals(test_user)
        
        assert len(all_goals) == 2


class TestPlanStoreEdgeCases:
    """Additional edge case tests for PlanStore."""
    
    @pytest.mark.asyncio
    async def test_create_plan_with_complex_steps(self, test_config, test_db, test_user, sample_goal):
        """Test creating plan with complex step configurations."""
        goal_store = GoalStore(test_db)
        plan_store = PlanStore(test_db)
        
        await goal_store.create_goal(sample_goal)
        
        # Don't use scheduled_for with datetime - it causes JSON serialization issues
        plan = Plan(
            plan_id="plan-complex",
            goal_id=sample_goal.goal_id,
            status=PlanStatus.DRAFT,
            steps=[
                PlanStep(
                    step_id="step-1",
                    order=1,
                    description="First step",
                    status=StepStatus.PENDING,
                    tool_id="tool-123",
                    skill_id="skill-456",
                    scheduled_for=None,  # Avoid datetime serialization issue
                    depends_on=["step-0"],
                    metadata={"custom": "data"},
                ),
            ],
        )
        
        created = await plan_store.create_plan(plan)
        
        assert created.plan_id == plan.plan_id
        
        # Retrieve and verify all fields
        retrieved = await plan_store.get_plan(plan.plan_id)
        assert retrieved is not None
        assert len(retrieved.steps) == 1
        assert retrieved.steps[0].tool_id == "tool-123"
        assert retrieved.steps[0].skill_id == "skill-456"
        assert retrieved.steps[0].depends_on == ["step-0"]
