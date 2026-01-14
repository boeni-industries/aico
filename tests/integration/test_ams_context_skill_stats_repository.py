"""
Integration tests for AMSContextSkillStatsRepository.
"""

import pytest
import uuid
from datetime import datetime, UTC

from aico.data.ams.context_models import AMSContextSkillStats
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
    user_id = "context_skill_test_user"
    existing = await uow.users.get_by_id(user_id)
    if not existing:
        user = UserProfile(
            uuid=user_id,
            full_name="Context Skill Test User",
            nickname="skill_tester",
            user_type="parent",
            is_active=True,
            primary_language="en",
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        await uow.users.create(user)
        await uow.commit()
    return await uow.users.get_by_id(user_id)


class TestAMSContextSkillStatsRepository:
    
    @pytest.mark.asyncio
    async def test_create_stat(self, uow, test_user):
        stat = AMSContextSkillStats(
            user_id=test_user.uuid,
            context_bucket=0,
            skill_id="skill_1",
            alpha=2.0,
            beta=1.5,
            last_updated_at=datetime.now(UTC),
        )
        
        created = await uow.ams_context_skill_stats.create(stat)
        await uow.commit()
        
        assert created.user_id == test_user.uuid
        assert created.alpha == 2.0
    
    @pytest.mark.asyncio
    async def test_get_stat_by_id(self, uow, test_user):
        stat = AMSContextSkillStats(
            user_id=test_user.uuid,
            context_bucket=1,
            skill_id="skill_2",
            alpha=1.0,
            beta=1.0,
            last_updated_at=datetime.now(UTC),
        )
        
        await uow.ams_context_skill_stats.create(stat)
        await uow.commit()
        
        found = await uow.ams_context_skill_stats.get_by_id(f"{test_user.uuid}:1:skill_2")
        assert found is not None
        assert found.skill_id == "skill_2"
    
    @pytest.mark.asyncio
    async def test_update_stat(self, uow, test_user):
        stat = AMSContextSkillStats(
            user_id=test_user.uuid,
            context_bucket=2,
            skill_id="skill_3",
            alpha=1.0,
            beta=1.0,
            last_updated_at=datetime.now(UTC),
        )
        
        await uow.ams_context_skill_stats.create(stat)
        await uow.commit()
        
        stat.alpha = 3.0
        stat.beta = 2.0
        updated = await uow.ams_context_skill_stats.update(stat)
        await uow.commit()
        
        assert updated.alpha == 3.0
        
        found = await uow.ams_context_skill_stats.get_by_id(f"{test_user.uuid}:2:skill_3")
        assert found.beta == 2.0
    
    @pytest.mark.asyncio
    async def test_delete_stat(self, uow, test_user):
        stat = AMSContextSkillStats(
            user_id=test_user.uuid,
            context_bucket=3,
            skill_id="skill_4",
            alpha=1.0,
            beta=1.0,
            last_updated_at=datetime.now(UTC),
        )
        
        await uow.ams_context_skill_stats.create(stat)
        await uow.commit()
        
        success = await uow.ams_context_skill_stats.delete(f"{test_user.uuid}:3:skill_4")
        await uow.commit()
        
        assert success is True
        
        found = await uow.ams_context_skill_stats.get_by_id(f"{test_user.uuid}:3:skill_4")
        assert found is None
    
    @pytest.mark.asyncio
    async def test_list_stats(self, uow, test_user):
        for i in range(4, 7):
            stat = AMSContextSkillStats(
                user_id=test_user.uuid,
                context_bucket=4,
                skill_id=f"skill_{i}",
                alpha=1.0,
                beta=1.0,
                last_updated_at=datetime.now(UTC),
            )
            await uow.ams_context_skill_stats.create(stat)
        
        await uow.commit()
        
        all_stats = await uow.ams_context_skill_stats.list(filters={"user_id": test_user.uuid, "context_bucket": 4})
        assert len(all_stats) >= 3
    
    @pytest.mark.asyncio
    async def test_count_stats(self, uow, test_user):
        for i in range(7, 10):
            stat = AMSContextSkillStats(
                user_id=test_user.uuid,
                context_bucket=5,
                skill_id=f"skill_{i}",
                alpha=1.0,
                beta=1.0,
                last_updated_at=datetime.now(UTC),
            )
            await uow.ams_context_skill_stats.create(stat)
        
        await uow.commit()
        
        count = await uow.ams_context_skill_stats.count(filters={"user_id": test_user.uuid})
        assert count >= 3
    
    @pytest.mark.asyncio
    async def test_get_user_context_stats(self, uow, test_user):
        for i in range(10, 13):
            stat = AMSContextSkillStats(
                user_id=test_user.uuid,
                context_bucket=6,
                skill_id=f"skill_{i}",
                alpha=1.0,
                beta=1.0,
                last_updated_at=datetime.now(UTC),
            )
            await uow.ams_context_skill_stats.create(stat)
        
        await uow.commit()
        
        stats = await uow.ams_context_skill_stats.get_user_context_stats(test_user.uuid, 6)
        assert len(stats) >= 3
        for s in stats:
            assert s.user_id == test_user.uuid
            assert s.context_bucket == 6
