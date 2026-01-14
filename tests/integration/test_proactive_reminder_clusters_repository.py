"""
Integration tests for ProactiveReminderClustersRepository.
"""

import pytest
import uuid
from datetime import datetime, UTC

from aico.data.proactive.models import ProactiveReminderCluster
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
    user_id = f"cluster_test_user_{uuid.uuid4().hex[:8]}"
    user = UserProfile(
        uuid=user_id,
        full_name="Cluster Test User",
        nickname="cluster_tester",
        user_type="parent",
        is_active=True,
        primary_language="en",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    await uow.users.create(user)
    await uow.commit()
    return await uow.users.get_by_id(user_id)


class TestProactiveReminderClustersRepository:
    
    @pytest.mark.asyncio
    async def test_create_cluster(self, uow, test_user):
        cluster = ProactiveReminderCluster(
            cluster_id=str(uuid.uuid4()),
            user_id=test_user.uuid,
            cluster_name="Morning Routine",
            created_at=datetime.now(UTC),
        )
        
        created = await uow.proactive_reminder_clusters.create(cluster)
        await uow.commit()
        
        assert created.cluster_id == cluster.cluster_id
        assert created.cluster_name == "Morning Routine"
    
    @pytest.mark.asyncio
    async def test_get_cluster_by_id(self, uow, test_user):
        cluster = ProactiveReminderCluster(
            cluster_id=str(uuid.uuid4()),
            user_id=test_user.uuid,
            cluster_name="Evening Tasks",
            confidence_score=0.92,
            created_at=datetime.now(UTC),
        )
        
        await uow.proactive_reminder_clusters.create(cluster)
        await uow.commit()
        
        found = await uow.proactive_reminder_clusters.get_by_id(cluster.cluster_id)
        assert found is not None
        assert found.confidence_score == 0.92
    
    @pytest.mark.asyncio
    async def test_update_cluster(self, uow, test_user):
        cluster = ProactiveReminderCluster(
            cluster_id=str(uuid.uuid4()),
            user_id=test_user.uuid,
            cluster_name="Work Tasks",
            created_at=datetime.now(UTC),
        )
        
        await uow.proactive_reminder_clusters.create(cluster)
        await uow.commit()
        
        cluster.pattern_description = "Daily work reminders"
        cluster.confidence_score = 0.88
        updated = await uow.proactive_reminder_clusters.update(cluster)
        await uow.commit()
        
        assert updated.pattern_description == "Daily work reminders"
        
        found = await uow.proactive_reminder_clusters.get_by_id(cluster.cluster_id)
        assert found.confidence_score == 0.88
    
    @pytest.mark.asyncio
    async def test_delete_cluster(self, uow, test_user):
        cluster = ProactiveReminderCluster(
            cluster_id=str(uuid.uuid4()),
            user_id=test_user.uuid,
            cluster_name="Test Cluster",
            created_at=datetime.now(UTC),
        )
        
        await uow.proactive_reminder_clusters.create(cluster)
        await uow.commit()
        
        success = await uow.proactive_reminder_clusters.delete(cluster.cluster_id)
        await uow.commit()
        
        assert success is True
        
        found = await uow.proactive_reminder_clusters.get_by_id(cluster.cluster_id)
        assert found is None
    
    @pytest.mark.asyncio
    async def test_list_clusters(self, uow, test_user):
        for i in range(3):
            cluster = ProactiveReminderCluster(
                cluster_id=str(uuid.uuid4()),
                user_id=test_user.uuid,
                cluster_name=f"Cluster {i}",
                created_at=datetime.now(UTC),
            )
            await uow.proactive_reminder_clusters.create(cluster)
        
        await uow.commit()
        
        all_clusters = await uow.proactive_reminder_clusters.list(filters={"user_id": test_user.uuid})
        assert len(all_clusters) >= 3
    
    @pytest.mark.asyncio
    async def test_count_clusters(self, uow, test_user):
        for i in range(3):
            cluster = ProactiveReminderCluster(
                cluster_id=str(uuid.uuid4()),
                user_id=test_user.uuid,
                cluster_name=f"Count Cluster {i}",
                created_at=datetime.now(UTC),
            )
            await uow.proactive_reminder_clusters.create(cluster)
        
        await uow.commit()
        
        count = await uow.proactive_reminder_clusters.count(filters={"user_id": test_user.uuid})
        assert count >= 3
    
    @pytest.mark.asyncio
    async def test_get_user_clusters(self, uow, test_user):
        for i in range(3):
            cluster = ProactiveReminderCluster(
                cluster_id=str(uuid.uuid4()),
                user_id=test_user.uuid,
                cluster_name=f"User Cluster {i}",
                created_at=datetime.now(UTC),
            )
            await uow.proactive_reminder_clusters.create(cluster)
        
        await uow.commit()
        
        clusters = await uow.proactive_reminder_clusters.get_user_clusters(test_user.uuid)
        assert len(clusters) >= 3
        for c in clusters:
            assert c.user_id == test_user.uuid
