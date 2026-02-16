"""
Integration tests for AMSContextPreferenceVectorsRepository.
"""

import pytest
import uuid
from datetime import datetime, UTC
import time

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
        # Cleanup any existing test data
        from sqlalchemy import text
        await uow._session.execute(text("DELETE FROM aico_core.ams_context_preference_vectors WHERE user_id = :user_id"), {"user_id": test_user.uuid})
        await uow.commit()
        
        bucket = int(time.time() * 1000000) % 100
        vector = AMSContextPreferenceVector(
            user_id=test_user.uuid,
            context_bucket=bucket,
            dimensions="[0.1, 0.2, 0.3]",
            last_updated_at=datetime.now(UTC),
        )
        
        created = await uow.ams_context_preference_vectors.create(vector)
        await uow.commit()
        
        assert created.user_id == test_user.uuid
        assert created.context_bucket == bucket
    
    @pytest.mark.asyncio
    async def test_get_vector_by_id(self, uow, test_user):
        from sqlalchemy import text
        await uow._session.execute(text("DELETE FROM aico_core.ams_context_preference_vectors WHERE user_id = :user_id"), {"user_id": test_user.uuid})
        await uow.commit()
        
        bucket = (int(time.time() * 1000000) + 1) % 100
        vector = AMSContextPreferenceVector(
            user_id=test_user.uuid,
            context_bucket=bucket,
            dimensions="[0.4, 0.5, 0.6]",
            last_updated_at=datetime.now(UTC),
        )
        
        await uow.ams_context_preference_vectors.create(vector)
        await uow.commit()
        
        found = await uow.ams_context_preference_vectors.get_by_id(f"{test_user.uuid}:{bucket}")
        assert found is not None
        assert found.context_bucket == bucket
    
    @pytest.mark.asyncio
    async def test_update_vector(self, uow, test_user):
        from sqlalchemy import text
        await uow._session.execute(text("DELETE FROM aico_core.ams_context_preference_vectors WHERE user_id = :user_id"), {"user_id": test_user.uuid})
        await uow.commit()
        
        bucket = (int(time.time() * 1000000) + 2) % 100
        vector = AMSContextPreferenceVector(
            user_id=test_user.uuid,
            context_bucket=bucket,
            dimensions="[0.7, 0.8, 0.9]",
            last_updated_at=datetime.now(UTC),
        )
        
        await uow.ams_context_preference_vectors.create(vector)
        await uow.commit()
        
        vector.dimensions = "[1.0, 1.0, 1.0]"
        updated = await uow.ams_context_preference_vectors.update(vector)
        await uow.commit()
        
        assert updated.dimensions == "[1.0, 1.0, 1.0]"
        
        found = await uow.ams_context_preference_vectors.get_by_id(f"{test_user.uuid}:{bucket}")
        assert found.dimensions == "[1.0, 1.0, 1.0]"
    
    @pytest.mark.asyncio
    async def test_delete_vector(self, uow, test_user):
        from sqlalchemy import text
        await uow._session.execute(text("DELETE FROM aico_core.ams_context_preference_vectors WHERE user_id = :user_id"), {"user_id": test_user.uuid})
        await uow.commit()
        
        bucket = (int(time.time() * 1000000) + 3) % 100
        vector = AMSContextPreferenceVector(
            user_id=test_user.uuid,
            context_bucket=bucket,
            dimensions="[0.1, 0.1, 0.1]",
            last_updated_at=datetime.now(UTC),
        )
        
        created = await uow.ams_context_preference_vectors.create(vector)
        await uow.commit()
        
        success = await uow.ams_context_preference_vectors.delete(f"{test_user.uuid}:{bucket}")
        await uow.commit()
        
        assert success is True
        
        found = await uow.ams_context_preference_vectors.get_by_id(f"{test_user.uuid}:{bucket}")
        assert found is None
    
    @pytest.mark.asyncio
    async def test_list_vectors(self, uow, test_user):
        from sqlalchemy import text
        await uow._session.execute(text("DELETE FROM aico_core.ams_context_preference_vectors WHERE user_id = :user_id"), {"user_id": test_user.uuid})
        await uow.commit()
        
        base = (int(time.time() * 1000000) + 10) % 90
        for i in range(3):
            vector = AMSContextPreferenceVector(
                user_id=test_user.uuid,
                context_bucket=base + i,
                dimensions=f"[{i}, {i}, {i}]",
                last_updated_at=datetime.now(UTC),
            )
            await uow.ams_context_preference_vectors.create(vector)
        
        await uow.commit()
        
        all_vectors = await uow.ams_context_preference_vectors.list(filters={"user_id": test_user.uuid})
        assert len(all_vectors) >= 3
    
    @pytest.mark.asyncio
    async def test_count_vectors(self, uow, test_user):
        from sqlalchemy import text
        await uow._session.execute(text("DELETE FROM aico_core.ams_context_preference_vectors WHERE user_id = :user_id"), {"user_id": test_user.uuid})
        await uow.commit()
        
        base = (int(time.time() * 1000000) + 20) % 90
        for i in range(3):
            vector = AMSContextPreferenceVector(
                user_id=test_user.uuid,
                context_bucket=base + i,
                dimensions=f"[{i}, {i}, {i}]",
                last_updated_at=datetime.now(UTC),
            )
            await uow.ams_context_preference_vectors.create(vector)
        
        await uow.commit()
        
        count = await uow.ams_context_preference_vectors.count(filters={"user_id": test_user.uuid})
        assert count >= 3
    
    @pytest.mark.asyncio
    async def test_get_user_vectors(self, uow, test_user):
        from sqlalchemy import text
        await uow._session.execute(text("DELETE FROM aico_core.ams_context_preference_vectors WHERE user_id = :user_id"), {"user_id": test_user.uuid})
        await uow.commit()
        
        base = (int(time.time() * 1000000) + 30) % 90
        for i in range(3):
            vector = AMSContextPreferenceVector(
                user_id=test_user.uuid,
                context_bucket=base + i,
                dimensions=f"[{i}, {i}, {i}]",
                last_updated_at=datetime.now(UTC),
            )
            await uow.ams_context_preference_vectors.create(vector)
        
        await uow.commit()
        
        vectors = await uow.ams_context_preference_vectors.get_user_vectors(test_user.uuid)
        assert len(vectors) >= 3
        for v in vectors:
            assert v.user_id == test_user.uuid
