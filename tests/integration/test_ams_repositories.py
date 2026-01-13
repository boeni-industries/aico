"""
Integration tests for AMS repositories (Trajectory, Feedback).

Tests the TrajectoryRepository and FeedbackRepository with real PostgreSQL database.
"""

import pytest
import uuid
from datetime import datetime, UTC, timedelta

from aico.data.ams.models import Trajectory, Feedback
from aico.data.user.models import UserProfile
from aico.data.agency.models import Goal
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
    """Create a test user for AMS tests."""
    user = UserProfile(
        uuid=str(uuid.uuid4()),
        full_name="AMS Test User",
        nickname="ams_tester",
        user_type="parent",
        is_active=True,
        primary_language="en",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    await uow.users.create(user)
    await uow.commit()
    return user


@pytest.fixture
async def test_goal(uow, test_user):
    """Create a test goal for trajectory tests."""
    goal = Goal(
        goal_id=str(uuid.uuid4()),
        user_id=test_user.uuid,
        origin="user_initiated",
        goal_type="project",
        title="Test Goal for Trajectory",
        status="active",
        priority="high",
    )
    await uow.goals.create(goal)
    await uow.commit()
    return goal


class TestTrajectoryRepository:
    """Test TrajectoryRepository CRUD operations."""
    
    @pytest.mark.asyncio
    async def test_create_trajectory(self, uow, test_user, test_goal):
        """Test creating a new trajectory."""
        trajectory = Trajectory(
            trajectory_id=str(uuid.uuid4()),
            user_id=test_user.uuid,
            goal_id=test_goal.goal_id,
            start_time=datetime.now(UTC),
            status="active",
            metadata_json={"context": "test"},
        )
        
        created = await uow.trajectories.create(trajectory)
        await uow.commit()
        
        assert created.trajectory_id == trajectory.trajectory_id
        assert created.status == "active"
    
    @pytest.mark.asyncio
    async def test_get_trajectory_by_id(self, uow, test_user):
        """Test retrieving trajectory by ID."""
        trajectory = Trajectory(
            trajectory_id=str(uuid.uuid4()),
            user_id=test_user.uuid,
            goal_id=None,
            start_time=datetime.now(UTC),
            status="active",
        )
        
        await uow.trajectories.create(trajectory)
        await uow.commit()
        
        found = await uow.trajectories.get_by_id(trajectory.trajectory_id)
        assert found is not None
        assert found.user_id == test_user.uuid
    
    @pytest.mark.asyncio
    async def test_update_trajectory(self, uow, test_user):
        """Test updating a trajectory."""
        trajectory = Trajectory(
            trajectory_id=str(uuid.uuid4()),
            user_id=test_user.uuid,
            goal_id=None,
            start_time=datetime.now(UTC),
            status="active",
        )
        
        await uow.trajectories.create(trajectory)
        await uow.commit()
        
        # Update the trajectory
        trajectory.status = "paused"
        trajectory.outcome = "interrupted"
        updated = await uow.trajectories.update(trajectory)
        await uow.commit()
        
        assert updated.status == "paused"
        
        # Verify update persisted
        found = await uow.trajectories.get_by_id(trajectory.trajectory_id)
        assert found.outcome == "interrupted"
    
    @pytest.mark.asyncio
    async def test_delete_trajectory(self, uow, test_user):
        """Test deleting a trajectory."""
        trajectory = Trajectory(
            trajectory_id=str(uuid.uuid4()),
            user_id=test_user.uuid,
            goal_id=None,
            start_time=datetime.now(UTC),
            status="active",
        )
        
        await uow.trajectories.create(trajectory)
        await uow.commit()
        
        # Delete the trajectory
        success = await uow.trajectories.delete(trajectory.trajectory_id)
        await uow.commit()
        
        assert success is True
        
        # Verify it's gone
        found = await uow.trajectories.get_by_id(trajectory.trajectory_id)
        assert found is None
    
    @pytest.mark.asyncio
    async def test_list_trajectories(self, uow, test_user):
        """Test listing trajectories with filters."""
        for i in range(3):
            trajectory = Trajectory(
                trajectory_id=str(uuid.uuid4()),
                user_id=test_user.uuid,
                goal_id=None,
                start_time=datetime.now(UTC) - timedelta(hours=i),
                status="active" if i < 2 else "completed",
            )
            await uow.trajectories.create(trajectory)
        
        await uow.commit()
        
        # List all trajectories for user
        all_trajectories = await uow.trajectories.list(filters={"user_id": test_user.uuid})
        assert len(all_trajectories) >= 3
        
        # List only active trajectories
        active_trajectories = await uow.trajectories.list(filters={"user_id": test_user.uuid, "status": "active"})
        assert len(active_trajectories) >= 2
    
    @pytest.mark.asyncio
    async def test_count_trajectories(self, uow, test_user):
        """Test counting trajectories."""
        for i in range(3):
            trajectory = Trajectory(
                trajectory_id=str(uuid.uuid4()),
                user_id=test_user.uuid,
                goal_id=None,
                start_time=datetime.now(UTC),
                status="active",
            )
            await uow.trajectories.create(trajectory)
        
        await uow.commit()
        
        count = await uow.trajectories.count(filters={"user_id": test_user.uuid, "status": "active"})
        assert count >= 3
    
    @pytest.mark.asyncio
    async def test_get_active_trajectories_for_user(self, uow, test_user):
        """Test getting active trajectories for a user."""
        for i in range(3):
            trajectory = Trajectory(
                trajectory_id=str(uuid.uuid4()),
                user_id=test_user.uuid,
                goal_id=None,
                start_time=datetime.now(UTC) - timedelta(hours=i),
                status="active" if i < 2 else "completed",
            )
            await uow.trajectories.create(trajectory)
        
        await uow.commit()
        
        active_trajectories = await uow.trajectories.get_active_trajectories_for_user(test_user.uuid)
        assert len(active_trajectories) >= 2
        # Should only include active trajectories
        for traj in active_trajectories:
            assert traj.status == "active"
    
    @pytest.mark.asyncio
    async def test_complete_trajectory(self, uow, test_user):
        """Test completing a trajectory."""
        trajectory = Trajectory(
            trajectory_id=str(uuid.uuid4()),
            user_id=test_user.uuid,
            goal_id=None,
            start_time=datetime.now(UTC),
            status="active",
        )
        
        await uow.trajectories.create(trajectory)
        await uow.commit()
        
        # Complete the trajectory
        success = await uow.trajectories.complete_trajectory(trajectory.trajectory_id, "success")
        await uow.commit()
        
        assert success is True
        
        # Verify completion
        found = await uow.trajectories.get_by_id(trajectory.trajectory_id)
        assert found.status == "completed"
        assert found.outcome == "success"
        assert found.end_time is not None


class TestFeedbackRepository:
    """Test FeedbackRepository CRUD operations."""
    
    @pytest.mark.asyncio
    async def test_create_feedback(self, uow, test_user):
        """Test creating a new feedback entry."""
        feedback = Feedback(
            feedback_id=str(uuid.uuid4()),
            user_id=test_user.uuid,
            trajectory_id=None,
            feedback_type="positive",
            content="Great experience!",
            rating=5.0,
        )
        
        created = await uow.feedback.create(feedback)
        await uow.commit()
        
        assert created.feedback_id == feedback.feedback_id
        assert created.content == "Great experience!"
    
    @pytest.mark.asyncio
    async def test_get_feedback_by_id(self, uow, test_user):
        """Test retrieving feedback by ID."""
        feedback = Feedback(
            feedback_id=str(uuid.uuid4()),
            user_id=test_user.uuid,
            trajectory_id=None,
            feedback_type="negative",
            content="Needs improvement",
            rating=2.0,
        )
        
        await uow.feedback.create(feedback)
        await uow.commit()
        
        found = await uow.feedback.get_by_id(feedback.feedback_id)
        assert found is not None
        assert found.content == "Needs improvement"
    
    @pytest.mark.asyncio
    async def test_update_feedback(self, uow, test_user):
        """Test updating feedback."""
        feedback = Feedback(
            feedback_id=str(uuid.uuid4()),
            user_id=test_user.uuid,
            trajectory_id=None,
            feedback_type="neutral",
            content="Original content",
            rating=3.0,
        )
        
        await uow.feedback.create(feedback)
        await uow.commit()
        
        # Update the feedback
        feedback.content = "Updated content"
        feedback.rating = 4.0
        updated = await uow.feedback.update(feedback)
        await uow.commit()
        
        assert updated.content == "Updated content"
        
        # Verify update persisted
        found = await uow.feedback.get_by_id(feedback.feedback_id)
        assert found.rating == 4.0
    
    @pytest.mark.asyncio
    async def test_delete_feedback(self, uow, test_user):
        """Test deleting feedback."""
        feedback = Feedback(
            feedback_id=str(uuid.uuid4()),
            user_id=test_user.uuid,
            trajectory_id=None,
            feedback_type="positive",
            content="To be deleted",
        )
        
        await uow.feedback.create(feedback)
        await uow.commit()
        
        # Delete the feedback
        success = await uow.feedback.delete(feedback.feedback_id)
        await uow.commit()
        
        assert success is True
        
        # Verify it's gone
        found = await uow.feedback.get_by_id(feedback.feedback_id)
        assert found is None
    
    @pytest.mark.asyncio
    async def test_list_feedback(self, uow, test_user):
        """Test listing feedback with filters."""
        for i in range(3):
            feedback = Feedback(
                feedback_id=str(uuid.uuid4()),
                user_id=test_user.uuid,
                trajectory_id=None,
                feedback_type="positive" if i < 2 else "negative",
                content=f"Feedback {i}",
            )
            await uow.feedback.create(feedback)
        
        await uow.commit()
        
        # List all feedback for user
        all_feedback = await uow.feedback.list(filters={"user_id": test_user.uuid})
        assert len(all_feedback) >= 3
        
        # List only positive feedback
        positive_feedback = await uow.feedback.list(filters={"user_id": test_user.uuid, "feedback_type": "positive"})
        assert len(positive_feedback) >= 2
    
    @pytest.mark.asyncio
    async def test_count_feedback(self, uow, test_user):
        """Test counting feedback."""
        for i in range(3):
            feedback = Feedback(
                feedback_id=str(uuid.uuid4()),
                user_id=test_user.uuid,
                trajectory_id=None,
                feedback_type="positive",
                content=f"Count feedback {i}",
            )
            await uow.feedback.create(feedback)
        
        await uow.commit()
        
        count = await uow.feedback.count(filters={"user_id": test_user.uuid, "feedback_type": "positive"})
        assert count >= 3
    
    @pytest.mark.asyncio
    async def test_get_unprocessed_feedback(self, uow, test_user):
        """Test getting unprocessed feedback."""
        for i in range(3):
            feedback = Feedback(
                feedback_id=str(uuid.uuid4()),
                user_id=test_user.uuid,
                trajectory_id=None,
                feedback_type="positive",
                content=f"Unprocessed {i}",
                processed_at=datetime.now(UTC) if i == 2 else None,
            )
            await uow.feedback.create(feedback)
        
        await uow.commit()
        
        unprocessed = await uow.feedback.get_unprocessed_feedback(test_user.uuid)
        assert len(unprocessed) >= 2
        # Should only include unprocessed feedback
        for fb in unprocessed:
            assert fb.processed_at is None
    
    @pytest.mark.asyncio
    async def test_mark_as_processed(self, uow, test_user):
        """Test marking feedback as processed."""
        feedback = Feedback(
            feedback_id=str(uuid.uuid4()),
            user_id=test_user.uuid,
            trajectory_id=None,
            feedback_type="positive",
            content="To be processed",
        )
        
        await uow.feedback.create(feedback)
        await uow.commit()
        
        # Mark as processed
        success = await uow.feedback.mark_as_processed(feedback.feedback_id)
        await uow.commit()
        
        assert success is True
        
        # Verify processed_at is set
        found = await uow.feedback.get_by_id(feedback.feedback_id)
        assert found.processed_at is not None
