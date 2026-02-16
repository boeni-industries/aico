"""
Integration tests for Agency repositories (Goal, Plan).

Tests the GoalRepository and PlanRepository with real PostgreSQL database.
Note: LessonRepository tests are skipped as the schema needs proper modeling.
"""

import pytest
import uuid
from datetime import datetime, UTC

from aico.data.agency.models import Goal, Plan
from aico.data.user.models import UserProfile
from aico.data.postgres.connection import get_session_factory
from aico.data.uow import UnitOfWork


@pytest.fixture
async def session_factory():
    """Create async session factory for tests."""
    factory = await get_session_factory()
    return factory


@pytest.fixture
async def uow(session_factory):
    """Create Unit of Work for tests."""
    uow = UnitOfWork(session_factory)
    async with uow:
        yield uow


@pytest.fixture
async def test_user(uow):
    """Create a test user for agency tests."""
    user = UserProfile(
        uuid=str(uuid.uuid4()),
        full_name="Agency Test User",
        nickname="agency_tester",
        user_type="parent",
        is_active=True,
        primary_language="en",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    await uow.users.create(user)
    await uow.commit()
    return user


class TestGoalRepository:
    """Test GoalRepository CRUD operations."""
    
    @pytest.mark.asyncio
    async def test_create_goal(self, uow, test_user):
        """Test creating a new goal."""
        goal = Goal(
            goal_id=str(uuid.uuid4()),
            user_id=test_user.uuid,
            origin="user_initiated",
            goal_type="learning",
            title="Learn Python",
            description="Master Python programming",
            status="active",
            priority="high",
            metadata_json={"tags": ["programming", "education"]},
        )
        
        created = await uow.goals.create(goal)
        await uow.commit()
        
        assert created.goal_id == goal.goal_id
        assert created.title == "Learn Python"
    
    @pytest.mark.asyncio
    async def test_get_goal_by_id(self, uow, test_user):
        """Test retrieving goal by ID."""
        goal = Goal(
            goal_id=str(uuid.uuid4()),
            user_id=test_user.uuid,
            origin="system_suggested",
            goal_type="habit",
            title="Exercise Daily",
            status="active",
            priority="medium",
        )
        
        await uow.goals.create(goal)
        await uow.commit()
        
        found = await uow.goals.get_by_id(goal.goal_id)
        assert found is not None
        assert found.title == "Exercise Daily"
    
    @pytest.mark.asyncio
    async def test_update_goal_status(self, uow, test_user):
        """Test updating goal status."""
        goal = Goal(
            goal_id=str(uuid.uuid4()),
            user_id=test_user.uuid,
            origin="user_initiated",
            goal_type="project",
            title="Test Goal",
            status="active",
            priority="low",
        )
        
        await uow.goals.create(goal)
        await uow.commit()
        
        success = await uow.goals.update_status(goal.goal_id, "completed")
        await uow.commit()
        
        assert success is True
        
        found = await uow.goals.get_by_id(goal.goal_id)
        assert found.status == "completed"
    
    @pytest.mark.asyncio
    async def test_list_goals(self, uow, test_user):
        """Test listing goals with filters."""
        for i in range(3):
            goal = Goal(
                goal_id=str(uuid.uuid4()),
                user_id=test_user.uuid,
                origin="user_initiated",
                goal_type="project",
                title=f"Goal {i}",
                status="active" if i < 2 else "completed",
                priority="high",
            )
            await uow.goals.create(goal)
        
        await uow.commit()
        
        # List all goals
        all_goals = await uow.goals.list(filters={"user_id": test_user.uuid})
        assert len(all_goals) >= 3
        
        # List only active goals
        active_goals = await uow.goals.list(filters={"user_id": test_user.uuid, "status": "active"})
        assert len(active_goals) >= 2
    
    @pytest.mark.asyncio
    async def test_count_goals(self, uow, test_user):
        """Test counting goals."""
        for i in range(3):
            goal = Goal(
                goal_id=str(uuid.uuid4()),
                user_id=test_user.uuid,
                origin="user_initiated",
                goal_type="habit",
                title=f"Count Goal {i}",
                status="active",
                priority="medium",
            )
            await uow.goals.create(goal)
        
        await uow.commit()
        
        count = await uow.goals.count(filters={"user_id": test_user.uuid})
        assert count >= 3
    
    @pytest.mark.asyncio
    async def test_get_active_goals_for_user(self, uow, test_user):
        """Test getting active goals for a user."""
        for i in range(3):
            goal = Goal(
                goal_id=str(uuid.uuid4()),
                user_id=test_user.uuid,
                origin="user_initiated",
                goal_type="project",
                title=f"Active Goal {i}",
                status="active" if i < 2 else "paused",
                priority="high",
            )
            await uow.goals.create(goal)
        
        await uow.commit()
        
        active_goals = await uow.goals.get_active_goals_for_user(test_user.uuid)
        assert len(active_goals) >= 2
        # Should only include active/in_progress goals
        for goal in active_goals:
            assert goal.status in ["active", "in_progress"]
    
    @pytest.mark.asyncio
    async def test_update_goal(self, uow, test_user):
        """Test updating a goal."""
        goal = Goal(
            goal_id=str(uuid.uuid4()),
            user_id=test_user.uuid,
            origin="user_initiated",
            goal_type="project",
            title="Original Title",
            description="Original description",
            status="active",
            priority="low",
        )
        
        await uow.goals.create(goal)
        await uow.commit()
        
        # Update the goal
        goal.title = "Updated Title"
        goal.priority = "high"
        updated = await uow.goals.update(goal)
        await uow.commit()
        
        assert updated.title == "Updated Title"
        
        # Verify update persisted
        found = await uow.goals.get_by_id(goal.goal_id)
        assert found.title == "Updated Title"
        assert found.priority == "high"
    
    @pytest.mark.asyncio
    async def test_delete_goal(self, uow, test_user):
        """Test deleting a goal."""
        goal = Goal(
            goal_id=str(uuid.uuid4()),
            user_id=test_user.uuid,
            origin="user_initiated",
            goal_type="project",
            title="Goal to Delete",
            status="active",
            priority="low",
        )
        
        await uow.goals.create(goal)
        await uow.commit()
        
        # Delete the goal
        success = await uow.goals.delete(goal.goal_id)
        await uow.commit()
        
        assert success is True
        
        # Verify it's gone
        found = await uow.goals.get_by_id(goal.goal_id)
        assert found is None


class TestPlanRepository:
    """Test PlanRepository CRUD operations."""
    
    @pytest.mark.asyncio
    async def test_create_plan(self, uow, test_user):
        """Test creating a new plan."""
        goal = Goal(
            goal_id=str(uuid.uuid4()),
            user_id=test_user.uuid,
            origin="user_initiated",
            goal_type="project",
            title="Test Goal for Plan",
            status="active",
            priority="high",
        )
        await uow.goals.create(goal)
        await uow.commit()
        
        plan = Plan(
            plan_id=str(uuid.uuid4()),
            goal_id=goal.goal_id,
            status="active",
            steps_json=[
                {"step": 1, "description": "First step"},
                {"step": 2, "description": "Second step"},
            ],
            metadata_json={"estimated_duration": "2 weeks"},
        )
        
        created = await uow.plans.create(plan)
        await uow.commit()
        
        assert created.plan_id == plan.plan_id
        assert len(created.steps_json) == 2
    
    @pytest.mark.asyncio
    async def test_get_active_plan_for_goal(self, uow, test_user):
        """Test getting the active plan for a goal."""
        goal = Goal(
            goal_id=str(uuid.uuid4()),
            user_id=test_user.uuid,
            origin="user_initiated",
            goal_type="project",
            title="Goal with Active Plan",
            status="active",
            priority="high",
        )
        await uow.goals.create(goal)
        await uow.commit()
        
        plan = Plan(
            plan_id=str(uuid.uuid4()),
            goal_id=goal.goal_id,
            status="active",
            steps_json=[{"step": 1, "description": "Active plan"}],
        )
        await uow.plans.create(plan)
        await uow.commit()
        
        active_plan = await uow.plans.get_active_plan_for_goal(goal.goal_id)
        assert active_plan is not None
        assert active_plan.status == "active"
    
    @pytest.mark.asyncio
    async def test_get_plan_by_id(self, uow, test_user):
        """Test retrieving plan by ID."""
        goal = Goal(
            goal_id=str(uuid.uuid4()),
            user_id=test_user.uuid,
            origin="user_initiated",
            goal_type="project",
            title="Goal for Plan Retrieval",
            status="active",
            priority="medium",
        )
        await uow.goals.create(goal)
        await uow.commit()
        
        plan = Plan(
            plan_id=str(uuid.uuid4()),
            goal_id=goal.goal_id,
            status="active",
            steps_json=[{"step": 1, "description": "Test step"}],
        )
        await uow.plans.create(plan)
        await uow.commit()
        
        found = await uow.plans.get_by_id(plan.plan_id)
        assert found is not None
        assert found.plan_id == plan.plan_id
    
    @pytest.mark.asyncio
    async def test_get_plans_for_goal(self, uow, test_user):
        """Test getting all plans for a goal."""
        goal = Goal(
            goal_id=str(uuid.uuid4()),
            user_id=test_user.uuid,
            origin="user_initiated",
            goal_type="project",
            title="Goal with Multiple Plans",
            status="active",
            priority="medium",
        )
        await uow.goals.create(goal)
        await uow.commit()
        
        # Create multiple plans
        for i in range(3):
            plan = Plan(
                plan_id=str(uuid.uuid4()),
                goal_id=goal.goal_id,
                status="active" if i == 0 else "draft",
                steps_json=[{"step": 1, "description": f"Plan {i}"}],
            )
            await uow.plans.create(plan)
        
        await uow.commit()
        
        plans = await uow.plans.get_plans_for_goal(goal.goal_id)
        assert len(plans) >= 3
    
    @pytest.mark.asyncio
    async def test_list_plans(self, uow, test_user):
        """Test listing plans with filters."""
        goal = Goal(
            goal_id=str(uuid.uuid4()),
            user_id=test_user.uuid,
            origin="user_initiated",
            goal_type="project",
            title="Goal for Plan Listing",
            status="active",
            priority="high",
        )
        await uow.goals.create(goal)
        await uow.commit()
        
        for i in range(2):
            plan = Plan(
                plan_id=str(uuid.uuid4()),
                goal_id=goal.goal_id,
                status="active" if i == 0 else "completed",
                steps_json=[{"step": 1}],
            )
            await uow.plans.create(plan)
        
        await uow.commit()
        
        # List all plans for goal
        all_plans = await uow.plans.list(filters={"goal_id": goal.goal_id})
        assert len(all_plans) >= 2
        
        # List only active plans
        active_plans = await uow.plans.list(filters={"goal_id": goal.goal_id, "status": "active"})
        assert len(active_plans) >= 1
    
    @pytest.mark.asyncio
    async def test_count_plans(self, uow, test_user):
        """Test counting plans."""
        goal = Goal(
            goal_id=str(uuid.uuid4()),
            user_id=test_user.uuid,
            origin="user_initiated",
            goal_type="project",
            title="Goal for Plan Counting",
            status="active",
            priority="medium",
        )
        await uow.goals.create(goal)
        await uow.commit()
        
        for i in range(3):
            plan = Plan(
                plan_id=str(uuid.uuid4()),
                goal_id=goal.goal_id,
                status="active",
                steps_json=[{"step": 1}],
            )
            await uow.plans.create(plan)
        
        await uow.commit()
        
        count = await uow.plans.count(filters={"goal_id": goal.goal_id})
        assert count >= 3
    
    @pytest.mark.asyncio
    async def test_update_plan(self, uow, test_user):
        """Test updating a plan."""
        goal = Goal(
            goal_id=str(uuid.uuid4()),
            user_id=test_user.uuid,
            origin="user_initiated",
            goal_type="project",
            title="Goal for Plan Update",
            status="active",
            priority="high",
        )
        await uow.goals.create(goal)
        await uow.commit()
        
        plan = Plan(
            plan_id=str(uuid.uuid4()),
            goal_id=goal.goal_id,
            status="draft",
            steps_json=[{"step": 1, "description": "Original"}],
        )
        await uow.plans.create(plan)
        await uow.commit()
        
        # Update the plan
        plan.status = "active"
        plan.steps_json = [{"step": 1, "description": "Updated"}]
        updated = await uow.plans.update(plan)
        await uow.commit()
        
        assert updated.status == "active"
        
        # Verify update persisted
        found = await uow.plans.get_by_id(plan.plan_id)
        assert found.status == "active"
        assert found.steps_json[0]["description"] == "Updated"
    
    @pytest.mark.asyncio
    async def test_update_plan_status(self, uow, test_user):
        """Test updating plan status."""
        goal = Goal(
            goal_id=str(uuid.uuid4()),
            user_id=test_user.uuid,
            origin="user_initiated",
            goal_type="project",
            title="Goal for Status Update",
            status="active",
            priority="medium",
        )
        await uow.goals.create(goal)
        await uow.commit()
        
        plan = Plan(
            plan_id=str(uuid.uuid4()),
            goal_id=goal.goal_id,
            status="active",
            steps_json=[{"step": 1}],
        )
        await uow.plans.create(plan)
        await uow.commit()
        
        success = await uow.plans.update_status(plan.plan_id, "completed")
        await uow.commit()
        
        assert success is True
        
        found = await uow.plans.get_by_id(plan.plan_id)
        assert found.status == "completed"
    
    @pytest.mark.asyncio
    async def test_delete_plan(self, uow, test_user):
        """Test deleting a plan."""
        goal = Goal(
            goal_id=str(uuid.uuid4()),
            user_id=test_user.uuid,
            origin="user_initiated",
            goal_type="project",
            title="Goal for Plan Deletion",
            status="active",
            priority="low",
        )
        await uow.goals.create(goal)
        await uow.commit()
        
        plan = Plan(
            plan_id=str(uuid.uuid4()),
            goal_id=goal.goal_id,
            status="draft",
            steps_json=[{"step": 1}],
        )
        await uow.plans.create(plan)
        await uow.commit()
        
        success = await uow.plans.delete(plan.plan_id)
        await uow.commit()
        
        assert success is True
        
        found = await uow.plans.get_by_id(plan.plan_id)
        assert found is None
