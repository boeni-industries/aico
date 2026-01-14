"""
Integration tests for UserProfilesRepository.
"""

import pytest
import uuid
from datetime import datetime, UTC

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


class TestUserProfilesRepository:
    
    @pytest.mark.asyncio
    async def test_create_profile(self, uow):
        profile = UserProfile(
            uuid=str(uuid.uuid4()),
            full_name="Test User",
            nickname="tester",
            user_type="person",
            is_active=True,
            primary_language="en",
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        
        created = await uow.user_profiles.create(profile)
        await uow.commit()
        
        assert created.uuid == profile.uuid
        assert created.full_name == "Test User"
    
    @pytest.mark.asyncio
    async def test_get_profile_by_id(self, uow):
        profile = UserProfile(
            uuid=str(uuid.uuid4()),
            full_name="Get Test User",
            nickname="getter",
            user_type="person",
            is_active=True,
            primary_language="en",
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        
        await uow.user_profiles.create(profile)
        await uow.commit()
        
        found = await uow.user_profiles.get_by_id(profile.uuid)
        assert found is not None
        assert found.nickname == "getter"
    
    @pytest.mark.asyncio
    async def test_update_profile(self, uow):
        profile = UserProfile(
            uuid=str(uuid.uuid4()),
            full_name="Update Test",
            nickname="updater",
            user_type="person",
            is_active=True,
            primary_language="en",
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        
        await uow.user_profiles.create(profile)
        await uow.commit()
        
        profile.full_name = "Updated Name"
        profile.is_active = False
        updated = await uow.user_profiles.update(profile)
        await uow.commit()
        
        assert updated.full_name == "Updated Name"
        
        found = await uow.user_profiles.get_by_id(profile.uuid)
        assert found.is_active is False
    
    @pytest.mark.asyncio
    async def test_delete_profile(self, uow):
        profile = UserProfile(
            uuid=str(uuid.uuid4()),
            full_name="Delete Test",
            nickname="deleter",
            user_type="person",
            is_active=True,
            primary_language="en",
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        
        await uow.user_profiles.create(profile)
        await uow.commit()
        
        success = await uow.user_profiles.delete(profile.uuid)
        await uow.commit()
        
        assert success is True
        
        found = await uow.user_profiles.get_by_id(profile.uuid)
        assert found is None
    
    @pytest.mark.asyncio
    async def test_list_profiles(self, uow):
        for i in range(3):
            profile = UserProfile(
                uuid=str(uuid.uuid4()),
                full_name=f"List User {i}",
                nickname=f"lister{i}",
                user_type="person",
                is_active=True if i < 2 else False,
                primary_language="en",
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC),
            )
            await uow.user_profiles.create(profile)
        
        await uow.commit()
        
        all_profiles = await uow.user_profiles.list()
        assert len(all_profiles) >= 3
        
        active = await uow.user_profiles.list(filters={"is_active": True})
        assert len(active) >= 2
    
    @pytest.mark.asyncio
    async def test_count_profiles(self, uow):
        for i in range(3):
            profile = UserProfile(
                uuid=str(uuid.uuid4()),
                full_name=f"Count User {i}",
                nickname=f"counter{i}",
                user_type="person",
                is_active=True,
                primary_language="en",
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC),
            )
            await uow.user_profiles.create(profile)
        
        await uow.commit()
        
        count = await uow.user_profiles.count()
        assert count >= 3
    
    @pytest.mark.asyncio
    async def test_get_active_users(self, uow):
        for i in range(3):
            profile = UserProfile(
                uuid=str(uuid.uuid4()),
                full_name=f"Active User {i}",
                nickname=f"active{i}",
                user_type="person",
                is_active=True if i < 2 else False,
                primary_language="en",
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC),
            )
            await uow.user_profiles.create(profile)
        
        await uow.commit()
        
        active = await uow.user_profiles.get_active_users()
        assert len(active) >= 2
        for p in active:
            assert p.is_active is True
