"""
Integration tests for AMSTrajectoriesRepository.
"""

import pytest
import uuid
from datetime import datetime, UTC

from aico.data.ams.models import Trajectory
from aico.data.user.models import UserProfile
from aico.data.postgres.connection import get_session_factory
from aico.data.uow import UnitOfWork


@pytest.fixture
async def session_factory():
    factory = await get_session_factory()
    return factory


@pytest.fixture
async def uow(session_factory):
    uow = UnitOfWork(session_factory)
    async with uow:
        yield uow


@pytest.fixture
async def test_user(uow):
    user_id = "trajectory_test_user"
    existing = await uow.users.get_by_id(user_id)
    if not existing:
        user = UserProfile(
            uuid=user_id,
            full_name="Trajectory Test User",
            nickname="traj_tester",
            user_type="parent",
            is_active=True,
            primary_language="en",
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        await uow.users.create(user)
        await uow.commit()
    return await uow.users.get_by_id(user_id)


class TestAMSTrajectoriesRepository:
    
    @pytest.mark.asyncio
    async def test_create_trajectory(self, uow, test_user):
        trajectory = Trajectory(
            trajectory_id=str(uuid.uuid4()),
            user_id=test_user.uuid,
            timestamp=datetime.now(UTC),
            archived=False,
        )
        
        created = await uow.ams_trajectories.create(trajectory)
        await uow.commit()
        
        assert created.trajectory_id == trajectory.trajectory_id
        assert created.archived is False
    
    @pytest.mark.asyncio
    async def test_get_trajectory_by_id(self, uow, test_user):
        trajectory = Trajectory(
            trajectory_id=str(uuid.uuid4()),
            user_id=test_user.uuid,
            conversation_id="conv_123",
            timestamp=datetime.now(UTC),
            archived=False,
        )
        
        await uow.ams_trajectories.create(trajectory)
        await uow.commit()
        
        found = await uow.ams_trajectories.get_by_id(trajectory.trajectory_id)
        assert found is not None
        assert found.conversation_id == "conv_123"
    
    @pytest.mark.asyncio
    async def test_update_trajectory(self, uow, test_user):
        trajectory = Trajectory(
            trajectory_id=str(uuid.uuid4()),
            user_id=test_user.uuid,
            timestamp=datetime.now(UTC),
            archived=False,
        )
        
        await uow.ams_trajectories.create(trajectory)
        await uow.commit()
        
        trajectory.archived = True
        trajectory.feedback_reward = 1
        updated = await uow.ams_trajectories.update(trajectory)
        await uow.commit()
        
        assert updated.archived is True
        
        found = await uow.ams_trajectories.get_by_id(trajectory.trajectory_id)
        assert found.feedback_reward == 1
    
    @pytest.mark.asyncio
    async def test_delete_trajectory(self, uow, test_user):
        trajectory = Trajectory(
            trajectory_id=str(uuid.uuid4()),
            user_id=test_user.uuid,
            timestamp=datetime.now(UTC),
            archived=False,
        )
        
        await uow.ams_trajectories.create(trajectory)
        await uow.commit()
        
        success = await uow.ams_trajectories.delete(trajectory.trajectory_id)
        await uow.commit()
        
        assert success is True
        
        found = await uow.ams_trajectories.get_by_id(trajectory.trajectory_id)
        assert found is None
    
    @pytest.mark.asyncio
    async def test_list_trajectories(self, uow, test_user):
        for i in range(3):
            trajectory = Trajectory(
                trajectory_id=str(uuid.uuid4()),
                user_id=test_user.uuid,
                timestamp=datetime.now(UTC),
                archived=False if i < 2 else True,
            )
            await uow.ams_trajectories.create(trajectory)
        
        await uow.commit()
        
        all_trajectories = await uow.ams_trajectories.list(filters={"user_id": test_user.uuid})
        assert len(all_trajectories) >= 3
        
        active = await uow.ams_trajectories.list(filters={"archived": False})
        assert len(active) >= 2
    
    @pytest.mark.asyncio
    async def test_count_trajectories(self, uow, test_user):
        for i in range(3):
            trajectory = Trajectory(
                trajectory_id=str(uuid.uuid4()),
                user_id=test_user.uuid,
                timestamp=datetime.now(UTC),
                archived=False,
            )
            await uow.ams_trajectories.create(trajectory)
        
        await uow.commit()
        
        count = await uow.ams_trajectories.count(filters={"user_id": test_user.uuid})
        assert count >= 3
    
    @pytest.mark.asyncio
    async def test_get_conversation_trajectories(self, uow, test_user):
        conv_id = "conv_test_123"
        for i in range(3):
            trajectory = Trajectory(
                trajectory_id=str(uuid.uuid4()),
                user_id=test_user.uuid,
                conversation_id=conv_id,
                timestamp=datetime.now(UTC),
                archived=False,
            )
            await uow.ams_trajectories.create(trajectory)
        
        await uow.commit()
        
        trajectories = await uow.ams_trajectories.get_conversation_trajectories(conv_id)
        assert len(trajectories) >= 3
        for t in trajectories:
            assert t.conversation_id == conv_id
