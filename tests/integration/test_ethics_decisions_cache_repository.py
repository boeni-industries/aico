"""
Integration tests for EthicsDecisionsCacheRepository.
"""

import pytest
import uuid
from datetime import datetime, UTC

from aico.data.ethics.cache_models import EthicsDecisionsCache
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
    user_id = "ethics_cache_test_user"
    existing = await uow.users.get_by_id(user_id)
    if not existing:
        user = UserProfile(
            uuid=user_id,
            full_name="Ethics Cache Test User",
            nickname="ethics_tester",
            user_type="parent",
            is_active=True,
            primary_language="en",
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        await uow.users.create(user)
        await uow.commit()
    return await uow.users.get_by_id(user_id)


class TestEthicsDecisionsCacheRepository:
    
    @pytest.mark.asyncio
    async def test_create_cache_entry(self, uow, test_user):
        cache = EthicsDecisionsCache(
            cache_id=str(uuid.uuid4()),
            user_id=test_user.uuid,
            target_type="goal",
            target_id=str(uuid.uuid4()),
            decision="approved",
            cached_at=datetime.now(UTC).isoformat(),
        )
        
        created = await uow.ethics_decisions_cache.create(cache)
        await uow.commit()
        
        assert created.cache_id == cache.cache_id
        assert created.decision == "approved"
    
    @pytest.mark.asyncio
    async def test_get_cache_entry_by_id(self, uow, test_user):
        cache = EthicsDecisionsCache(
            cache_id=str(uuid.uuid4()),
            user_id=test_user.uuid,
            target_type="plan",
            target_id=str(uuid.uuid4()),
            decision="blocked",
            cached_at=datetime.now(UTC).isoformat(),
        )
        
        await uow.ethics_decisions_cache.create(cache)
        await uow.commit()
        
        found = await uow.ethics_decisions_cache.get_by_id(cache.cache_id)
        assert found is not None
        assert found.decision == "blocked"
    
    @pytest.mark.asyncio
    async def test_update_cache_entry(self, uow, test_user):
        cache = EthicsDecisionsCache(
            cache_id=str(uuid.uuid4()),
            user_id=test_user.uuid,
            target_type="skill",
            target_id=str(uuid.uuid4()),
            decision="approved",
            cached_at=datetime.now(UTC).isoformat(),
            hit_count=0,
        )
        
        await uow.ethics_decisions_cache.create(cache)
        await uow.commit()
        
        cache.hit_count = 5
        cache.last_hit_at = datetime.now(UTC).isoformat()
        updated = await uow.ethics_decisions_cache.update(cache)
        await uow.commit()
        
        assert updated.hit_count == 5
        
        found = await uow.ethics_decisions_cache.get_by_id(cache.cache_id)
        assert found.hit_count == 5
    
    @pytest.mark.asyncio
    async def test_delete_cache_entry(self, uow, test_user):
        cache = EthicsDecisionsCache(
            cache_id=str(uuid.uuid4()),
            user_id=test_user.uuid,
            target_type="goal",
            target_id=str(uuid.uuid4()),
            decision="needs_review",
            cached_at=datetime.now(UTC).isoformat(),
        )
        
        await uow.ethics_decisions_cache.create(cache)
        await uow.commit()
        
        success = await uow.ethics_decisions_cache.delete(cache.cache_id)
        await uow.commit()
        
        assert success is True
        
        found = await uow.ethics_decisions_cache.get_by_id(cache.cache_id)
        assert found is None
    
    @pytest.mark.asyncio
    async def test_list_cache_entries(self, uow, test_user):
        for i in range(3):
            cache = EthicsDecisionsCache(
                cache_id=str(uuid.uuid4()),
                user_id=test_user.uuid,
                target_type="goal",
                target_id=str(uuid.uuid4()),
                decision="approved" if i < 2 else "blocked",
                cached_at=datetime.now(UTC).isoformat(),
            )
            await uow.ethics_decisions_cache.create(cache)
        
        await uow.commit()
        
        all_cache = await uow.ethics_decisions_cache.list(filters={"user_id": test_user.uuid})
        assert len(all_cache) >= 3
        
        approved = await uow.ethics_decisions_cache.list(filters={"decision": "approved"})
        assert len(approved) >= 2
    
    @pytest.mark.asyncio
    async def test_count_cache_entries(self, uow, test_user):
        for i in range(3):
            cache = EthicsDecisionsCache(
                cache_id=str(uuid.uuid4()),
                user_id=test_user.uuid,
                target_type="plan",
                target_id=str(uuid.uuid4()),
                decision="approved",
                cached_at=datetime.now(UTC).isoformat(),
            )
            await uow.ethics_decisions_cache.create(cache)
        
        await uow.commit()
        
        count = await uow.ethics_decisions_cache.count(filters={"user_id": test_user.uuid})
        assert count >= 3
    
    @pytest.mark.asyncio
    async def test_get_cached_decision(self, uow, test_user):
        target_id = str(uuid.uuid4())
        cache = EthicsDecisionsCache(
            cache_id=str(uuid.uuid4()),
            user_id=test_user.uuid,
            target_type="goal",
            target_id=target_id,
            decision="approved",
            cached_at=datetime.now(UTC).isoformat(),
        )
        
        await uow.ethics_decisions_cache.create(cache)
        await uow.commit()
        
        found = await uow.ethics_decisions_cache.get_cached_decision(test_user.uuid, "goal", target_id)
        assert found is not None
        assert found.target_id == target_id
