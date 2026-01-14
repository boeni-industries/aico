"""
Integration tests for AMSContextPreferenceVectorsRepository.
"""

import pytest
import uuid
from datetime import datetime, UTC

from aico.data.ams.context_models import AMSContextPreferenceVector
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
    user_id = "context_pref_test_user"
    existing = await uow.users.get_by_id(user_id)
    if not existing:
        user = UserProfile(
            uuid=user_id,
            full_name="Context Pref Test User",
            nickname="context_tester",
            user_type="parent",
            is_active=True,
            primary_language="en",
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        await uow.users.create(user)
        await uow.commit()
    return await uow.users.get_by_id(user_id)


class TestAMSContextPreferenceVectorsRepository:
    
    @pytest.mark.asyncio
    async def test_create_vector(self, uow, test_user):
        vector = AMSContextPreferenceVector(
            user_id=test_user.uuid,
            context_bucket=0,
            dimensions="[0.1, 0.2, 0.3]",
            last_updated_at=datetime.now(UTC),
        )
        
        created = await uow.ams_context_preference_vectors.create(vector)
        await uow.commit()
        
        assert created.user_id == test_user.uuid
        assert created.context_bucket == 0
    
    @pytest.mark.asyncio
    async def test_get_vector_by_id(self, uow, test_user):
        vector = AMSContextPreferenceVector(
            user_id=test_user.uuid,
            context_bucket=1,
            dimensions="[0.4, 0.5, 0.6]",
            last_updated_at=datetime.now(UTC),
        )
        
        await uow.ams_context_preference_vectors.create(vector)
        await uow.commit()
        
        found = await uow.ams_context_preference_vectors.get_by_id(f"{test_user.uuid}:1")
        assert found is not None
        assert found.context_bucket == 1
    
    @pytest.mark.asyncio
    async def test_update_vector(self, uow, test_user):
        vector = AMSContextPreferenceVector(
            user_id=test_user.uuid,
            context_bucket=2,
            dimensions="[0.7, 0.8, 0.9]",
            last_updated_at=datetime.now(UTC),
        )
        
        await uow.ams_context_preference_vectors.create(vector)
        await uow.commit()
        
        vector.dimensions = "[0.9, 0.8, 0.7]"
        updated = await uow.ams_context_preference_vectors.update(vector)
        await uow.commit()
        
        assert updated.dimensions == "[0.9, 0.8, 0.7]"
        
        found = await uow.ams_context_preference_vectors.get_by_id(f"{test_user.uuid}:2")
        assert found.dimensions == "[0.9, 0.8, 0.7]"
    
    @pytest.mark.asyncio
    async def test_delete_vector(self, uow, test_user):
        vector = AMSContextPreferenceVector(
            user_id=test_user.uuid,
            context_bucket=3,
            dimensions="[0.1, 0.1, 0.1]",
            last_updated_at=datetime.now(UTC),
        )
        
        await uow.ams_context_preference_vectors.create(vector)
        await uow.commit()
        
        success = await uow.ams_context_preference_vectors.delete(f"{test_user.uuid}:3")
        await uow.commit()
        
        assert success is True
        
        found = await uow.ams_context_preference_vectors.get_by_id(f"{test_user.uuid}:3")
        assert found is None
    
    @pytest.mark.asyncio
    async def test_list_vectors(self, uow, test_user):
        for i in range(4, 7):
            vector = AMSContextPreferenceVector(
                user_id=test_user.uuid,
                context_bucket=i,
                dimensions=f"[{i}, {i}, {i}]",
                last_updated_at=datetime.now(UTC),
            )
            await uow.ams_context_preference_vectors.create(vector)
        
        await uow.commit()
        
        all_vectors = await uow.ams_context_preference_vectors.list(filters={"user_id": test_user.uuid})
        assert len(all_vectors) >= 3
    
    @pytest.mark.asyncio
    async def test_count_vectors(self, uow, test_user):
        for i in range(7, 10):
            vector = AMSContextPreferenceVector(
                user_id=test_user.uuid,
                context_bucket=i,
                dimensions=f"[{i}, {i}, {i}]",
                last_updated_at=datetime.now(UTC),
            )
            await uow.ams_context_preference_vectors.create(vector)
        
        await uow.commit()
        
        count = await uow.ams_context_preference_vectors.count(filters={"user_id": test_user.uuid})
        assert count >= 3
    
    @pytest.mark.asyncio
    async def test_get_user_vectors(self, uow, test_user):
        for i in range(10, 13):
            vector = AMSContextPreferenceVector(
                user_id=test_user.uuid,
                context_bucket=i,
                dimensions=f"[{i}, {i}, {i}]",
                last_updated_at=datetime.now(UTC),
            )
            await uow.ams_context_preference_vectors.create(vector)
        
        await uow.commit()
        
        vectors = await uow.ams_context_preference_vectors.get_user_vectors(test_user.uuid)
        assert len(vectors) >= 3
        for v in vectors:
            assert v.user_id == test_user.uuid
