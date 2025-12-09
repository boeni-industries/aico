"""
Phase 1 Integration Tests: Goal Lifecycle

Tests the complete lifecycle of goals from creation through various state transitions.
Validates:
- Goal creation with optional plan generation
- Goal lifecycle operations (activate, pause, complete, retire)
- Telemetry and event logging
- Database persistence
"""

import pytest
from datetime import datetime

from aico.core.config import ConfigurationManager
from aico.ai.agency import AgencyEngine
from aico.ai.agency.models import GoalStatus, GoalOrigin, GoalPriority


@pytest.mark.asyncio
class TestGoalLifecycle:
    """Test suite for goal lifecycle operations."""
    
    async def test_create_goal_without_plan(self, test_config, test_db, test_user):
        """Test creating a goal without an automatic plan."""
        # Arrange
        engine = AgencyEngine(test_config, test_db)
        
        # Act - Use test user (will be cleaned up automatically)
        goal, plan = await engine.create_goal_with_optional_plan(
            user_id=test_user,
            title="Learn Python",
            description="Master Python programming",
            goal_type="project",
            auto_plan=False,
        )
        
        # Assert: Goal created
        assert goal is not None
        assert goal.goal_id is not None
        assert goal.title == "Learn Python"
        assert goal.status == GoalStatus.PENDING
        assert goal.origin == GoalOrigin.USER
        
        # Assert: No plan generated
        assert plan is None
        
        # Assert: Telemetry logged
        events = test_db.execute(
            "SELECT * FROM agency_events WHERE goal_id = ?",
            (goal.goal_id,)
        ).fetchall()
        assert len(events) == 1
        assert events[0][4] == "goal_created"  # event_type column
    
    async def test_create_goal_with_plan(self, test_config, test_db, test_user):
        """Test creating a goal with automatic plan generation."""
        # Arrange
        engine = AgencyEngine(test_config, test_db)
        
        # Act
        goal, plan = await engine.create_goal_with_optional_plan(
            user_id=test_user,
            title="Learn Testing",
            description="Master pytest and integration testing",
            goal_type="learning",
            auto_plan=True,
        )
        
        # Assert: Goal created
        assert goal is not None
        assert goal.status == GoalStatus.PENDING
        
        # Assert: Plan generated
        assert plan is not None
        assert plan.goal_id == goal.goal_id
        assert len(plan.steps) > 0
        
        # Assert: Plan uses appropriate shape
        # "learning" goal_type should match "research_then_act" shape
        if plan.metadata.get("shape_id"):
            assert plan.metadata["shape_id"] == "research_then_act"
        
        # Assert: Telemetry logged
        events = test_db.execute(
            "SELECT * FROM agency_events WHERE goal_id = ?",
            (goal.goal_id,)
        ).fetchall()
        assert len(events) == 2  # goal_created + plan_generated
        event_types = [e[4] for e in events]
        assert "goal_created" in event_types
        assert "plan_generated" in event_types
    
    async def test_create_hobby_goal(self, test_config, test_db, test_user):
        """Test creating an agent-self hobby goal."""
        # Arrange
        engine = AgencyEngine(test_config, test_db)
        
        # Act
        goal, plan = await engine.create_hobby_goal_with_optional_plan(
            user_id=test_user,
            title="Study quantum physics",
            description="Explore quantum mechanics during idle time",
            goal_type="hobby",
            priority=GoalPriority.LOW,
            auto_plan=True,
        )
        
        # Assert: Goal has correct origin
        assert goal.origin == GoalOrigin.HOBBY
        assert goal.priority == GoalPriority.LOW
        
        # Assert: Plan generated
        assert plan is not None
    
    async def test_activate_goal(self, test_config, test_db, sample_goal):
        """Test activating a pending goal."""
        # Arrange
        engine = AgencyEngine(test_config, test_db)
        
        # Create goal first
        await engine.goal_store.create_goal(sample_goal)
        
        # Act
        activated_goal = await engine.activate_goal(sample_goal.goal_id)
        
        # Assert: Goal activated
        assert activated_goal is not None
        assert activated_goal.status == GoalStatus.ACTIVE
        
        # Assert: Telemetry logged
        events = test_db.execute(
            "SELECT * FROM agency_events WHERE goal_id = ? AND event_type = ?",
            (sample_goal.goal_id, "goal_activated")
        ).fetchall()
        assert len(events) == 1
    
    async def test_pause_goal(self, test_config, test_db, sample_goal):
        """Test pausing an active goal."""
        # Arrange
        engine = AgencyEngine(test_config, test_db)
        
        # Create and activate goal
        sample_goal.status = GoalStatus.ACTIVE
        await engine.goal_store.create_goal(sample_goal)
        
        # Act
        paused_goal = await engine.pause_goal(sample_goal.goal_id)
        
        # Assert: Goal paused
        assert paused_goal is not None
        assert paused_goal.status == GoalStatus.PAUSED
        
        # Assert: Telemetry logged
        events = test_db.execute(
            "SELECT * FROM agency_events WHERE goal_id = ? AND event_type = ?",
            (sample_goal.goal_id, "goal_paused")
        ).fetchall()
        assert len(events) == 1
    
    async def test_complete_goal(self, test_config, test_db, sample_goal):
        """Test completing a goal."""
        # Arrange
        engine = AgencyEngine(test_config, test_db)
        
        # Create goal
        await engine.goal_store.create_goal(sample_goal)
        
        # Act
        completed_goal = await engine.complete_goal(sample_goal.goal_id)
        
        # Assert: Goal completed
        assert completed_goal is not None
        assert completed_goal.status == GoalStatus.COMPLETED
        
        # Assert: Telemetry logged
        events = test_db.execute(
            "SELECT * FROM agency_events WHERE goal_id = ? AND event_type = ?",
            (sample_goal.goal_id, "goal_completed")
        ).fetchall()
        assert len(events) == 1
    
    async def test_retire_goal(self, test_config, test_db, sample_goal):
        """Test retiring a goal (abandoned/no longer relevant)."""
        # Arrange
        engine = AgencyEngine(test_config, test_db)
        
        # Create goal
        await engine.goal_store.create_goal(sample_goal)
        
        # Act
        retired_goal = await engine.retire_goal(sample_goal.goal_id)
        
        # Assert: Goal retired
        assert retired_goal is not None
        assert retired_goal.status == GoalStatus.RETIRED
        
        # Assert: Telemetry logged
        events = test_db.execute(
            "SELECT * FROM agency_events WHERE goal_id = ? AND event_type = ?",
            (sample_goal.goal_id, "goal_retired")
        ).fetchall()
        assert len(events) == 1
    
    async def test_lifecycle_state_transitions(self, test_config, test_db, test_user):
        """Test a complete lifecycle: pending → active → paused → active → completed."""
        # Arrange
        engine = AgencyEngine(test_config, test_db)
        
        # Act: Create goal
        goal, _ = await engine.create_goal_with_optional_plan(
            user_id=test_user,
            title="Multi-state Goal",
            auto_plan=False,
        )
        
        # Assert: Starts as pending
        assert goal.status == GoalStatus.PENDING
        
        # Act: Activate
        goal = await engine.activate_goal(goal.goal_id)
        assert goal.status == GoalStatus.ACTIVE
        
        # Act: Pause
        goal = await engine.pause_goal(goal.goal_id)
        assert goal.status == GoalStatus.PAUSED
        
        # Act: Re-activate
        goal = await engine.activate_goal(goal.goal_id)
        assert goal.status == GoalStatus.ACTIVE
        
        # Act: Complete
        goal = await engine.complete_goal(goal.goal_id)
        assert goal.status == GoalStatus.COMPLETED
        
        # Assert: All transitions logged
        events = test_db.execute(
            "SELECT event_type FROM agency_events WHERE goal_id = ? ORDER BY created_at",
            (goal.goal_id,)
        ).fetchall()
        event_types = [e[0] for e in events]
        assert event_types == [
            "goal_created",
            "goal_activated",
            "goal_paused",
            "goal_activated",
            "goal_completed",
        ]
    
    async def test_list_goals_for_user(self, test_config, test_db, test_user, seeded_goals):
        """Test listing goals for a user with optional status filter."""
        # Arrange
        engine = AgencyEngine(test_config, test_db)
        
        # Act: List all goals
        all_goals = await engine.list_goals_for_user(test_user)
        
        # Assert: All goals returned
        assert len(all_goals) == 3
        
        # Act: List only active goals
        active_goals = await engine.list_goals_for_user(test_user, status=GoalStatus.ACTIVE)
        
        # Assert: Only active goals returned
        assert len(active_goals) == 1
        assert active_goals[0].status == GoalStatus.ACTIVE
    
    async def test_goal_persistence(self, test_config, test_db, test_user):
        """Test that goals persist correctly across engine instances."""
        # Arrange
        engine1 = AgencyEngine(test_config, test_db)
        
        # Act: Create goal with first engine
        goal, _ = await engine1.create_goal_with_optional_plan(
            user_id=test_user,
            title="Persistent Goal",
            auto_plan=False,
        )
        goal_id = goal.goal_id
        
        # Create new engine instance
        engine2 = AgencyEngine(test_config, test_db)
        
        # Act: Retrieve goal with second engine
        retrieved_goal = await engine2.get_goal(goal_id)
        
        # Assert: Goal retrieved successfully
        assert retrieved_goal is not None
        assert retrieved_goal.goal_id == goal_id
        assert retrieved_goal.title == "Persistent Goal"
