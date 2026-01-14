"""
Integration tests for AMS repositories (Trajectory and BehavioralFeedback).

Tests with correct models matching actual PostgreSQL schema.
"""

import pytest
import uuid
from datetime import datetime, UTC

from aico.data.ams.models import Trajectory, BehavioralFeedback
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


class TestTrajectoryRepository:
    """Test TrajectoryRepository CRUD operations."""
    
    @pytest.mark.asyncio
    async def test_create_trajectory(self, uow, test_user):
        """Test creating a new trajectory."""
        trajectory = Trajectory(
            trajectory_id=str(uuid.uuid4()),
            user_id=test_user.uuid,
            timestamp=datetime.now(UTC),
            conversation_id=str(uuid.uuid4()),
            selected_skill_id="test_skill",
            context_bucket="bucket_1",
            archived=False,
        )
        
        created = await uow.trajectories.create(trajectory)
        await uow.commit()
        
        assert created.trajectory_id == trajectory.trajectory_id
        assert created.user_id == test_user.uuid
    
    @pytest.mark.asyncio
    async def test_get_trajectory_by_id(self, uow, test_user):
        """Test retrieving trajectory by ID."""
        trajectory = Trajectory(
            trajectory_id=str(uuid.uuid4()),
            user_id=test_user.uuid,
            timestamp=datetime.now(UTC),
            conversation_id=str(uuid.uuid4()),
        )
        
        await uow.trajectories.create(trajectory)
        await uow.commit()
        
        found = await uow.trajectories.get_by_id(trajectory.trajectory_id)
        assert found is not None
        assert found.trajectory_id == trajectory.trajectory_id
    
    @pytest.mark.asyncio
    async def test_update_trajectory(self, uow, test_user):
        """Test updating a trajectory."""
        trajectory = Trajectory(
            trajectory_id=str(uuid.uuid4()),
            user_id=test_user.uuid,
            timestamp=datetime.now(UTC),
            feedback_reward=0,
        )
        
        await uow.trajectories.create(trajectory)
        await uow.commit()
        
        # Update the trajectory
        trajectory.feedback_reward = 5
        trajectory.archived = True
        updated = await uow.trajectories.update(trajectory)
        await uow.commit()
        
        assert updated.feedback_reward == 5
        
        # Verify update persisted
        found = await uow.trajectories.get_by_id(trajectory.trajectory_id)
        assert found.archived is True
    
    @pytest.mark.asyncio
    async def test_delete_trajectory(self, uow, test_user):
        """Test deleting a trajectory."""
        trajectory = Trajectory(
            trajectory_id=str(uuid.uuid4()),
            user_id=test_user.uuid,
            timestamp=datetime.now(UTC),
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
                timestamp=datetime.now(UTC),
                archived=i == 2,
            )
            await uow.trajectories.create(trajectory)
        
        await uow.commit()
        
        # List all trajectories for user
        all_trajectories = await uow.trajectories.list(filters={"user_id": test_user.uuid})
        assert len(all_trajectories) >= 3
        
        # List only non-archived
        active = await uow.trajectories.list(filters={"user_id": test_user.uuid, "archived": False})
        assert len(active) >= 2
    
    @pytest.mark.asyncio
    async def test_count_trajectories(self, uow, test_user):
        """Test counting trajectories."""
        for i in range(3):
            trajectory = Trajectory(
                trajectory_id=str(uuid.uuid4()),
                user_id=test_user.uuid,
                timestamp=datetime.now(UTC),
            )
            await uow.trajectories.create(trajectory)
        
        await uow.commit()
        
        count = await uow.trajectories.count(filters={"user_id": test_user.uuid})
        assert count >= 3
    
    @pytest.mark.asyncio
    async def test_get_active_trajectories_for_user(self, uow, test_user):
        """Test getting active trajectories for user."""
        # Create active and archived trajectories
        for i in range(3):
            trajectory = Trajectory(
                trajectory_id=str(uuid.uuid4()),
                user_id=test_user.uuid,
                timestamp=datetime.now(UTC),
                archived=i == 2,
            )
            await uow.trajectories.create(trajectory)
        
        await uow.commit()
        
        # Get active trajectories
        active = await uow.trajectories.get_active_trajectories_for_user(test_user.uuid)
        assert len(active) >= 2
        for traj in active:
            assert traj.archived is False
    
    @pytest.mark.asyncio
    async def test_archive_trajectory(self, uow, test_user):
        """Test archiving a trajectory."""
        trajectory = Trajectory(
            trajectory_id=str(uuid.uuid4()),
            user_id=test_user.uuid,
            timestamp=datetime.now(UTC),
            archived=False,
        )
        
        await uow.trajectories.create(trajectory)
        await uow.commit()
        
        # Archive it
        success = await uow.trajectories.archive_trajectory(trajectory.trajectory_id)
        await uow.commit()
        
        assert success is True
        
        # Verify it's archived
        found = await uow.trajectories.get_by_id(trajectory.trajectory_id)
        assert found.archived is True


class TestBehavioralFeedbackRepository:
    """Test BehavioralFeedbackRepository CRUD operations."""
    
    @pytest.mark.asyncio
    async def test_create_feedback(self, uow, test_user):
        """Test creating feedback."""
        feedback = BehavioralFeedback(
            feedback_id=str(uuid.uuid4()),
            user_id=test_user.uuid,
            timestamp=datetime.now(UTC).isoformat(),
            skill_id="test_skill",
            reward=5,
            processed=0,
        )
        
        created = await uow.feedback.create(feedback)
        await uow.commit()
        
        assert created.feedback_id == feedback.feedback_id
        assert created.user_id == test_user.uuid
    
    @pytest.mark.asyncio
    async def test_get_feedback_by_id(self, uow, test_user):
        """Test retrieving feedback by ID."""
        feedback = BehavioralFeedback(
            feedback_id=str(uuid.uuid4()),
            user_id=test_user.uuid,
            timestamp=datetime.now(UTC).isoformat(),
            processed=0,
        )
        
        await uow.feedback.create(feedback)
        await uow.commit()
        
        found = await uow.feedback.get_by_id(feedback.feedback_id)
        assert found is not None
        assert found.feedback_id == feedback.feedback_id
    
    @pytest.mark.asyncio
    async def test_update_feedback(self, uow, test_user):
        """Test updating feedback."""
        feedback = BehavioralFeedback(
            feedback_id=str(uuid.uuid4()),
            user_id=test_user.uuid,
            timestamp=datetime.now(UTC).isoformat(),
            reward=0,
            processed=0,
        )
        
        await uow.feedback.create(feedback)
        await uow.commit()
        
        # Update the feedback
        feedback.reward = 10
        feedback.user_satisfaction = 0.9
        updated = await uow.feedback.update(feedback)
        await uow.commit()
        
        assert updated.reward == 10
        
        # Verify update persisted
        found = await uow.feedback.get_by_id(feedback.feedback_id)
        assert found.user_satisfaction == 0.9
    
    @pytest.mark.asyncio
    async def test_delete_feedback(self, uow, test_user):
        """Test deleting feedback."""
        feedback = BehavioralFeedback(
            feedback_id=str(uuid.uuid4()),
            user_id=test_user.uuid,
            timestamp=datetime.now(UTC).isoformat(),
            processed=0,
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
            feedback = BehavioralFeedback(
                feedback_id=str(uuid.uuid4()),
                user_id=test_user.uuid,
                timestamp=datetime.now(UTC).isoformat(),
                processed=i % 2,
            )
            await uow.feedback.create(feedback)
        
        await uow.commit()
        
        # List all feedback for user
        all_feedback = await uow.feedback.list(filters={"user_id": test_user.uuid})
        assert len(all_feedback) >= 3
        
        # List only unprocessed
        unprocessed = await uow.feedback.list(filters={"user_id": test_user.uuid, "processed": 0})
        assert len(unprocessed) >= 1
    
    @pytest.mark.asyncio
    async def test_count_feedback(self, uow, test_user):
        """Test counting feedback."""
        for i in range(3):
            feedback = BehavioralFeedback(
                feedback_id=str(uuid.uuid4()),
                user_id=test_user.uuid,
                timestamp=datetime.now(UTC).isoformat(),
                processed=0,
            )
            await uow.feedback.create(feedback)
        
        await uow.commit()
        
        count = await uow.feedback.count(filters={"user_id": test_user.uuid})
        assert count >= 3
    
    @pytest.mark.asyncio
    async def test_get_unprocessed_feedback(self, uow, test_user):
        """Test getting unprocessed feedback."""
        # Create processed and unprocessed feedback
        for i in range(3):
            feedback = BehavioralFeedback(
                feedback_id=str(uuid.uuid4()),
                user_id=test_user.uuid,
                timestamp=datetime.now(UTC).isoformat(),
                processed=i % 2,
            )
            await uow.feedback.create(feedback)
        
        await uow.commit()
        
        # Get unprocessed feedback
        unprocessed = await uow.feedback.get_unprocessed_feedback(test_user.uuid)
        assert len(unprocessed) >= 1
        for fb in unprocessed:
            assert fb.processed == 0
    
    @pytest.mark.asyncio
    async def test_mark_as_processed(self, uow, test_user):
        """Test marking feedback as processed."""
        feedback = BehavioralFeedback(
            feedback_id=str(uuid.uuid4()),
            user_id=test_user.uuid,
            timestamp=datetime.now(UTC).isoformat(),
            processed=0,
        )
        
        await uow.feedback.create(feedback)
        await uow.commit()
        
        # Mark as processed
        success = await uow.feedback.mark_as_processed(feedback.feedback_id)
        await uow.commit()
        
        assert success is True
        
        # Verify it's processed
        found = await uow.feedback.get_by_id(feedback.feedback_id)
        assert found.processed == 1
