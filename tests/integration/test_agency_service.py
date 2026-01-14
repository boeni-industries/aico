"""
Integration tests for AgencyService.

Tests the service layer using actual repositories and database.
"""

import pytest
import uuid
from datetime import datetime, UTC

from aico.services.agency_service import AgencyService
from aico.ai.agency.models import Goal, GoalOrigin, GoalStatus, GoalPriority, Plan, PlanStatus


@pytest.fixture
async def agency_service(uow):
    """Create AgencyService with UnitOfWork."""
    return AgencyService(uow)


@pytest.fixture
async def test_goal(agency_service, test_user):
    """Create a test goal."""
    goal = Goal(
        goal_id=str(uuid.uuid4()),
        user_id=test_user.uuid,
        origin=GoalOrigin.USER,
        goal_type="personal",
        title="Test Goal",
        description="Test goal description",
        status=GoalStatus.ACTIVE,
        priority=GoalPriority.NORMAL,
        metadata={},
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    return await agency_service.create_goal(goal)


class TestAgencyService:
    """Test suite for AgencyService."""

    @pytest.mark.asyncio
    async def test_create_goal(self, agency_service, test_user):
        """Test creating a goal through the service."""
        goal = Goal(
            goal_id=str(uuid.uuid4()),
            user_id=test_user.uuid,
            origin=GoalOrigin.USER,
            goal_type="personal",
            title="Service Test Goal",
            description="Created via service",
            status=GoalStatus.ACTIVE,
            priority=GoalPriority.HIGH,
            metadata={"source": "test"},
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        
        created = await agency_service.create_goal(goal)
        
        assert created.goal_id == goal.goal_id
        assert created.user_id == test_user.uuid
        assert created.title == "Service Test Goal"
        assert created.status == GoalStatus.ACTIVE

    @pytest.mark.asyncio
    async def test_get_goal(self, agency_service, test_goal):
        """Test retrieving a goal."""
        retrieved = await agency_service.get_goal(test_goal.goal_id)
        
        assert retrieved is not None
        assert retrieved.goal_id == test_goal.goal_id
        assert retrieved.title == test_goal.title

    @pytest.mark.asyncio
    async def test_list_goals(self, agency_service, test_user, test_goal):
        """Test listing goals for a user."""
        goals = await agency_service.list_goals(test_user.uuid)
        
        assert len(goals) >= 1
        assert any(g.goal_id == test_goal.goal_id for g in goals)

    @pytest.mark.asyncio
    async def test_update_goal(self, agency_service, test_goal):
        """Test updating a goal."""
        test_goal.title = "Updated Title"
        test_goal.status = GoalStatus.COMPLETED
        
        updated = await agency_service.update_goal(test_goal)
        
        assert updated.title == "Updated Title"
        assert updated.status == GoalStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_get_active_goals(self, agency_service, test_user, test_goal):
        """Test getting active goals."""
        active_goals = await agency_service.get_active_goals(test_user.uuid)
        
        assert len(active_goals) >= 1
        assert all(g.status == GoalStatus.ACTIVE for g in active_goals)

    @pytest.mark.asyncio
    async def test_create_plan(self, agency_service, test_goal):
        """Test creating a plan."""
        plan = Plan(
            plan_id=str(uuid.uuid4()),
            goal_id=test_goal.goal_id,
            title="Test Plan",
            description="Plan description",
            status=PlanStatus.ACTIVE,
            steps=[],
            metadata={},
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        
        created = await agency_service.create_plan(plan)
        
        assert created.plan_id == plan.plan_id
        assert created.goal_id == test_goal.goal_id
        assert created.status == PlanStatus.ACTIVE

    @pytest.mark.asyncio
    async def test_get_active_plan(self, agency_service, test_goal):
        """Test getting active plan for a goal."""
        # Create a plan first
        plan = Plan(
            plan_id=str(uuid.uuid4()),
            goal_id=test_goal.goal_id,
            title="Active Plan",
            description="Active plan description",
            status=PlanStatus.ACTIVE,
            steps=[],
            metadata={},
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        await agency_service.create_plan(plan)
        
        active_plan = await agency_service.get_active_plan(test_goal.goal_id)
        
        assert active_plan is not None
        assert active_plan.status == PlanStatus.ACTIVE
        assert active_plan.goal_id == test_goal.goal_id

    @pytest.mark.asyncio
    async def test_delete_goal(self, agency_service, test_user):
        """Test deleting a goal."""
        goal = Goal(
            goal_id=str(uuid.uuid4()),
            user_id=test_user.uuid,
            origin=GoalOrigin.USER,
            goal_type="temporary",
            title="Goal to Delete",
            status=GoalStatus.ACTIVE,
            priority=GoalPriority.NORMAL,
            metadata={},
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        created = await agency_service.create_goal(goal)
        
        success = await agency_service.delete_goal(created.goal_id)
        assert success is True
        
        deleted = await agency_service.get_goal(created.goal_id)
        assert deleted is None

    @pytest.mark.asyncio
    async def test_get_plan(self, agency_service, test_goal):
        """Test retrieving a plan by ID."""
        plan = Plan(
            plan_id=str(uuid.uuid4()),
            goal_id=test_goal.goal_id,
            title="Test Plan",
            status=PlanStatus.DRAFT,
            steps=[],
            metadata={},
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        created = await agency_service.create_plan(plan)
        
        retrieved = await agency_service.get_plan(created.plan_id)
        assert retrieved is not None
        assert retrieved.plan_id == created.plan_id
        assert retrieved.title == "Test Plan"

    @pytest.mark.asyncio
    async def test_update_plan(self, agency_service, test_goal):
        """Test updating a plan."""
        plan = Plan(
            plan_id=str(uuid.uuid4()),
            goal_id=test_goal.goal_id,
            title="Original Plan",
            status=PlanStatus.DRAFT,
            steps=[],
            metadata={},
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        created = await agency_service.create_plan(plan)
        
        created.title = "Updated Plan"
        created.status = PlanStatus.ACTIVE
        updated = await agency_service.update_plan(created)
        
        assert updated.title == "Updated Plan"
        assert updated.status == PlanStatus.ACTIVE

    @pytest.mark.asyncio
    async def test_delete_plan(self, agency_service, test_goal):
        """Test deleting a plan."""
        plan = Plan(
            plan_id=str(uuid.uuid4()),
            goal_id=test_goal.goal_id,
            title="Plan to Delete",
            status=PlanStatus.DRAFT,
            steps=[],
            metadata={},
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        created = await agency_service.create_plan(plan)
        
        success = await agency_service.delete_plan(created.plan_id)
        assert success is True
        
        deleted = await agency_service.get_plan(created.plan_id)
        assert deleted is None
