"""
Integration tests for EthicsValueProfilesRepository.
"""

import pytest
import uuid
from datetime import datetime, UTC

from aico.data.ethics.value_models import EthicsValueProfile
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
    user_id = f"ethics_value_test_user_{uuid.uuid4().hex[:8]}"
    user = UserProfile(
        uuid=user_id,
        full_name="Ethics Value Test User",
        nickname="value_tester",
        user_type="parent",
        is_active=True,
        primary_language="en",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    await uow.users.create(user)
    await uow.commit()
    return await uow.users.get_by_id(user_id)


class TestEthicsValueProfilesRepository:
    
    @pytest.mark.asyncio
    async def test_create_profile(self, uow, test_user):
        profile = EthicsValueProfile(
            profile_id=str(uuid.uuid4()),
            user_id=test_user.uuid,
            curiosity_intensity=0.7,
            autonomy_level='proactive',
        )
        
        created = await uow.ethics_value_profiles.create(profile)
        await uow.commit()
        
        assert created.profile_id == profile.profile_id
        assert created.curiosity_intensity == 0.7
    
    @pytest.mark.asyncio
    async def test_get_profile_by_id(self, uow, test_user):
        profile = EthicsValueProfile(
            profile_id=str(uuid.uuid4()),
            user_id=test_user.uuid,
            autonomy_level='quiet',
        )
        
        await uow.ethics_value_profiles.create(profile)
        await uow.commit()
        
        found = await uow.ethics_value_profiles.get_by_id(profile.profile_id)
        assert found is not None
        assert found.autonomy_level == 'quiet'
    
    @pytest.mark.asyncio
    async def test_update_profile(self, uow, test_user):
        profile = EthicsValueProfile(
            profile_id=str(uuid.uuid4()),
            user_id=test_user.uuid,
            curiosity_intensity=0.5,
        )
        
        await uow.ethics_value_profiles.create(profile)
        await uow.commit()
        
        profile.curiosity_intensity = 0.8
        profile.autonomy_level = 'proactive'
        updated = await uow.ethics_value_profiles.update(profile)
        await uow.commit()
        
        assert updated.curiosity_intensity == 0.8
        
        found = await uow.ethics_value_profiles.get_by_id(profile.profile_id)
        assert found.autonomy_level == 'proactive'
    
    @pytest.mark.asyncio
    async def test_delete_profile(self, uow, test_user):
        profile = EthicsValueProfile(
            profile_id=str(uuid.uuid4()),
            user_id=test_user.uuid,
        )
        
        await uow.ethics_value_profiles.create(profile)
        await uow.commit()
        
        success = await uow.ethics_value_profiles.delete(profile.profile_id)
        await uow.commit()
        
        assert success is True
        
        found = await uow.ethics_value_profiles.get_by_id(profile.profile_id)
        assert found is None
    
    @pytest.mark.asyncio
    async def test_list_profiles(self, uow):
        user_ids = []
        for i in range(3):
            user_id = f"list_user_{uuid.uuid4().hex[:8]}"
            user = UserProfile(
                uuid=user_id,
                full_name=f"List User {i}",
                nickname=f"list_{i}",
                user_type="parent",
                is_active=True,
                primary_language="en",
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC),
            )
            await uow.users.create(user)
            user_ids.append(user_id)
            
            profile = EthicsValueProfile(
                profile_id=str(uuid.uuid4()),
                user_id=user_id,
            )
            await uow.ethics_value_profiles.create(profile)
        
        await uow.commit()
        
        all_profiles = await uow.ethics_value_profiles.list()
        assert len(all_profiles) >= 3
    
    @pytest.mark.asyncio
    async def test_count_profiles(self, uow):
        user_ids = []
        for i in range(3):
            user_id = f"count_user_{uuid.uuid4().hex[:8]}"
            user = UserProfile(
                uuid=user_id,
                full_name=f"Count User {i}",
                nickname=f"count_{i}",
                user_type="parent",
                is_active=True,
                primary_language="en",
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC),
            )
            await uow.users.create(user)
            user_ids.append(user_id)
            
            profile = EthicsValueProfile(
                profile_id=str(uuid.uuid4()),
                user_id=user_id,
            )
            await uow.ethics_value_profiles.create(profile)
        
        await uow.commit()
        
        count = await uow.ethics_value_profiles.count()
        assert count >= 3
    
    @pytest.mark.asyncio
    async def test_get_by_user_id(self, uow, test_user):
        profile = EthicsValueProfile(
            profile_id=str(uuid.uuid4()),
            user_id=test_user.uuid,
            curiosity_intensity=0.6,
        )
        
        await uow.ethics_value_profiles.create(profile)
        await uow.commit()
        
        found = await uow.ethics_value_profiles.get_by_user_id(test_user.uuid)
        assert found is not None
        assert found.user_id == test_user.uuid
