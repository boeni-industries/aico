"""
Integration tests for UserTimePreferencesRepository.
"""

import pytest
import uuid
from datetime import datetime, UTC

from aico.data.user.relationship_models import UserTimePreference
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
    user_id = "time_pref_test_user"
    existing = await uow.users.get_by_id(user_id)
    if not existing:
        user = UserProfile(
            uuid=user_id,
            full_name="Time Pref Test User",
            nickname="time_tester",
            user_type="parent",
            is_active=True,
            primary_language="en",
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        await uow.users.create(user)
        await uow.commit()
    return await uow.users.get_by_id(user_id)


class TestUserTimePreferencesRepository:
    
    @pytest.mark.asyncio
    async def test_create_preference(self, uow, test_user):
        preference = UserTimePreference(
            preference_id=str(uuid.uuid4()),
            user_id=test_user.uuid,
            time_period=f"create_morning_{uuid.uuid4().hex[:8]}",
            productivity_score=1.5,
            active=True,
            created_at=datetime.now(UTC).isoformat(),
            updated_at=datetime.now(UTC).isoformat(),
        )
        
        created = await uow.user_time_preferences.create(preference)
        await uow.commit()
        
        assert created.preference_id == preference.preference_id
        assert "create_morning" in created.time_period
    
    @pytest.mark.asyncio
    async def test_get_preference_by_id(self, uow, test_user):
        preference = UserTimePreference(
            preference_id=str(uuid.uuid4()),
            user_id=test_user.uuid,
            time_period=f"get_afternoon_{uuid.uuid4().hex[:8]}",
            productivity_score=1.2,
            active=True,
            created_at=datetime.now(UTC).isoformat(),
            updated_at=datetime.now(UTC).isoformat(),
        )
        
        await uow.user_time_preferences.create(preference)
        await uow.commit()
        
        found = await uow.user_time_preferences.get_by_id(preference.preference_id)
        assert found is not None
        assert "get_afternoon" in found.time_period
    
    @pytest.mark.asyncio
    async def test_update_preference(self, uow, test_user):
        preference = UserTimePreference(
            preference_id=str(uuid.uuid4()),
            user_id=test_user.uuid,
            time_period=f"update_evening_{uuid.uuid4().hex[:8]}",
            productivity_score=1.0,
            active=True,
            created_at=datetime.now(UTC).isoformat(),
            updated_at=datetime.now(UTC).isoformat(),
        )
        
        await uow.user_time_preferences.create(preference)
        await uow.commit()
        
        preference.productivity_score = 1.8
        preference.active = False
        updated = await uow.user_time_preferences.update(preference)
        await uow.commit()
        
        assert updated.productivity_score == 1.8
        
        found = await uow.user_time_preferences.get_by_id(preference.preference_id)
        assert found.active is False
    
    @pytest.mark.asyncio
    async def test_delete_preference(self, uow, test_user):
        preference = UserTimePreference(
            preference_id=str(uuid.uuid4()),
            user_id=test_user.uuid,
            time_period=f"delete_night_{uuid.uuid4().hex[:8]}",
            productivity_score=0.8,
            active=True,
            created_at=datetime.now(UTC).isoformat(),
            updated_at=datetime.now(UTC).isoformat(),
        )
        
        await uow.user_time_preferences.create(preference)
        await uow.commit()
        
        success = await uow.user_time_preferences.delete(preference.preference_id)
        await uow.commit()
        
        assert success is True
        
        found = await uow.user_time_preferences.get_by_id(preference.preference_id)
        assert found is None
    
    @pytest.mark.asyncio
    async def test_list_preferences(self, uow, test_user):
        test_id = uuid.uuid4().hex[:8]
        periods = [f"list_early_morning_{test_id}", f"list_morning_{test_id}", f"list_afternoon_{test_id}"]
        for i, period in enumerate(periods):
            preference = UserTimePreference(
                preference_id=str(uuid.uuid4()),
                user_id=test_user.uuid,
                time_period=period,
                productivity_score=1.0 + (i * 0.2),
                active=True if i < 2 else False,
                created_at=datetime.now(UTC).isoformat(),
                updated_at=datetime.now(UTC).isoformat(),
            )
            await uow.user_time_preferences.create(preference)
        
        await uow.commit()
        
        all_prefs = await uow.user_time_preferences.list(filters={"user_id": test_user.uuid})
        assert len(all_prefs) >= 3
        
        active = await uow.user_time_preferences.list(filters={"user_id": test_user.uuid, "active": True})
        assert len(active) >= 2
    
    @pytest.mark.asyncio
    async def test_count_preferences(self, uow, test_user):
        test_id = uuid.uuid4().hex[:8]
        for i in range(3):
            preference = UserTimePreference(
                preference_id=str(uuid.uuid4()),
                user_id=test_user.uuid,
                time_period=f"count_period_{i}_{test_id}",
                productivity_score=1.0,
                active=True,
                created_at=datetime.now(UTC).isoformat(),
                updated_at=datetime.now(UTC).isoformat(),
            )
            await uow.user_time_preferences.create(preference)
        
        await uow.commit()
        
        count = await uow.user_time_preferences.count(filters={"user_id": test_user.uuid})
        assert count >= 3
    
    @pytest.mark.asyncio
    async def test_get_user_preferences(self, uow, test_user):
        test_id = uuid.uuid4().hex[:8]
        for i in range(3):
            preference = UserTimePreference(
                preference_id=str(uuid.uuid4()),
                user_id=test_user.uuid,
                time_period=f"user_period_{i}_{test_id}",
                productivity_score=1.0 + (i * 0.3),
                active=True,
                created_at=datetime.now(UTC).isoformat(),
                updated_at=datetime.now(UTC).isoformat(),
            )
            await uow.user_time_preferences.create(preference)
        
        await uow.commit()
        
        prefs = await uow.user_time_preferences.get_user_preferences(test_user.uuid)
        assert len(prefs) >= 3
        for pref in prefs:
            assert pref.user_id == test_user.uuid
