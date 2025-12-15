"""
Store Coverage Tests

Additional tests to improve coverage of agency store modules.
Focuses on error handling, edge cases, and less-used code paths.
"""

import pytest
from datetime import datetime, UTC

from aico.ai.agency import AgencyEngine
from aico.ai.agency.models import (
    Goal,
    GoalOrigin,
    GoalPriority,
    GoalStatus,
    Plan,
    PlanStatus,
    AgencyEvent,
)
from aico.ai.agency.store import GoalStore, PlanStore, AgencyEventStore


@pytest.mark.asyncio
class TestStoreErrorHandling:
    """Test error handling and edge cases in store modules."""
    
    async def test_get_nonexistent_goal(self, test_config, test_db):
        """Test retrieving a goal that doesn't exist."""
        # Arrange
        store = GoalStore(test_db)
        
        # Act
        result = await store.get_goal("nonexistent-goal-id")
        
        # Assert
        assert result is None
    
    async def test_get_nonexistent_plan(self, test_config, test_db):
        """Test retrieving a plan that doesn't exist."""
        # Arrange
        store = PlanStore(test_db)
        
        # Act
        result = await store.get_plan("nonexistent-plan-id")
        
        # Assert
        assert result is None
    
    async def test_update_goal_status(self, test_config, test_db, test_user, sample_goal):
        """Test updating goal status."""
        # Arrange
        store = GoalStore(test_db)
        await store.create_goal(sample_goal)
        
        # Act
        await store.update_goal_status(sample_goal.goal_id, GoalStatus.ACTIVE)
        
        # Assert: Verify status was updated
        updated = await store.get_goal(sample_goal.goal_id)
        assert updated is not None
        assert updated.status == GoalStatus.ACTIVE
    
    async def test_list_goals_empty(self, test_config, test_db, test_user):
        """Test listing goals when none exist."""
        # Arrange
        store = GoalStore(test_db)
        
        # Act
        goals = await store.list_goals(test_user)
        
        # Assert
        assert goals == []
    
    async def test_list_goals_with_status_filter(self, test_config, test_db, test_user, sample_goal):
        """Test listing goals with status filter."""
        # Arrange
        store = GoalStore(test_db)
        await store.create_goal(sample_goal)
        
        # Act: Filter for active goals (should be empty)
        active_goals = await store.list_goals(test_user, status=GoalStatus.ACTIVE)
        
        # Assert
        assert len(active_goals) == 0
        
        # Act: Filter for pending goals (should find our goal)
        pending_goals = await store.list_goals(test_user, status=GoalStatus.PENDING)
        
        # Assert
        assert len(pending_goals) == 1
        assert pending_goals[0].goal_id == sample_goal.goal_id
    
    async def test_create_plan(self, test_config, test_db, test_user, sample_goal, sample_plan):
        """Test creating a plan."""
        # Arrange
        goal_store = GoalStore(test_db)
        plan_store = PlanStore(test_db)
        await goal_store.create_goal(sample_goal)
        
        # Act
        created_plan = await plan_store.create_plan(sample_plan)
        
        # Assert
        assert created_plan is not None
        assert created_plan.plan_id == sample_plan.plan_id
    
    async def test_update_plan_status(self, test_config, test_db, test_user, sample_goal, sample_plan):
        """Test updating plan status."""
        # Arrange
        goal_store = GoalStore(test_db)
        plan_store = PlanStore(test_db)
        await goal_store.create_goal(sample_goal)
        await plan_store.create_plan(sample_plan)
        
        # Act
        await plan_store.update_plan_status(sample_plan.plan_id, PlanStatus.ACTIVE)
        
        # Assert: Verify status was updated
        updated = await plan_store.get_plan(sample_plan.plan_id)
        assert updated is not None
        assert updated.status == PlanStatus.ACTIVE
    
    async def test_list_plans_for_goal(self, test_config, test_db, test_user, sample_goal, sample_plan):
        """Test retrieving all plans for a goal."""
        # Arrange
        goal_store = GoalStore(test_db)
        plan_store = PlanStore(test_db)
        await goal_store.create_goal(sample_goal)
        await plan_store.create_plan(sample_plan)
        
        # Act
        plans = await plan_store.list_plans_for_goal(sample_goal.goal_id)
        
        # Assert
        assert len(plans) == 1
        assert plans[0].plan_id == sample_plan.plan_id
    
    async def test_list_plans_for_nonexistent_goal(self, test_config, test_db):
        """Test retrieving plans for nonexistent goal."""
        # Arrange
        store = PlanStore(test_db)
        
        # Act
        plans = await store.list_plans_for_goal("nonexistent-goal-id")
        
        # Assert
        assert plans == []
    
    async def test_log_event(self, test_config, test_db, test_user, sample_goal):
        # Arrange
        event_store = AgencyEventStore(test_db)
        
        event = AgencyEvent(
            user_id=test_user,
            event_type="goal_created",
            source="test",
            payload={"test": "data"},
        )
        
        # Act
        await event_store.log_event(event)
        
        # Assert - Event should be logged (no exception raised)
        assert event.user_id == test_user
