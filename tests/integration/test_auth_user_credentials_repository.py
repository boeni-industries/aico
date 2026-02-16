"""
Integration tests for AuthUserCredentialsRepository.
"""

import pytest
import uuid
from datetime import datetime, UTC, timedelta

from aico.data.auth.credentials_models import AuthUserCredentials
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
    user_id = "auth_creds_test_user"
    existing = await uow.users.get_by_id(user_id)
    if not existing:
        user = UserProfile(
            uuid=user_id,
            full_name="Auth Creds Test User",
            nickname="creds_tester",
            user_type="parent",
            is_active=True,
            primary_language="en",
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        await uow.users.create(user)
        await uow.commit()
    return await uow.users.get_by_id(user_id)


class TestAuthUserCredentialsRepository:
    
    @pytest.mark.asyncio
    async def test_create_credentials(self, uow, test_user):
        creds = AuthUserCredentials(
            uuid=str(uuid.uuid4()),
            user_uuid=test_user.uuid,
            pin_hash="hashed_pin_123",
            failed_attempts=0,
        )
        
        created = await uow.auth_user_credentials.create(creds)
        await uow.commit()
        
        assert created.uuid == creds.uuid
        assert created.user_uuid == test_user.uuid
    
    @pytest.mark.asyncio
    async def test_get_credentials_by_id(self, uow, test_user):
        creds = AuthUserCredentials(
            uuid=str(uuid.uuid4()),
            user_uuid=test_user.uuid,
            pin_hash="hashed_pin_456",
            failed_attempts=0,
        )
        
        await uow.auth_user_credentials.create(creds)
        await uow.commit()
        
        found = await uow.auth_user_credentials.get_by_id(creds.uuid)
        assert found is not None
        assert found.pin_hash == "hashed_pin_456"
    
    @pytest.mark.asyncio
    async def test_update_credentials(self, uow, test_user):
        creds = AuthUserCredentials(
            uuid=str(uuid.uuid4()),
            user_uuid=test_user.uuid,
            pin_hash="hashed_pin_789",
            failed_attempts=0,
        )
        
        await uow.auth_user_credentials.create(creds)
        await uow.commit()
        
        creds.failed_attempts = 3
        creds.locked_until = datetime.now(UTC) + timedelta(minutes=30)
        updated = await uow.auth_user_credentials.update(creds)
        await uow.commit()
        
        assert updated.failed_attempts == 3
        
        found = await uow.auth_user_credentials.get_by_id(creds.uuid)
        assert found.failed_attempts == 3
        assert found.locked_until is not None
    
    @pytest.mark.asyncio
    async def test_delete_credentials(self, uow, test_user):
        creds = AuthUserCredentials(
            uuid=str(uuid.uuid4()),
            user_uuid=test_user.uuid,
            pin_hash="hashed_pin_del",
            failed_attempts=0,
        )
        
        await uow.auth_user_credentials.create(creds)
        await uow.commit()
        
        success = await uow.auth_user_credentials.delete(creds.uuid)
        await uow.commit()
        
        assert success is True
        
        found = await uow.auth_user_credentials.get_by_id(creds.uuid)
        assert found is None
    
    @pytest.mark.asyncio
    async def test_list_credentials(self, uow, test_user):
        for i in range(3):
            creds = AuthUserCredentials(
                uuid=str(uuid.uuid4()),
                user_uuid=test_user.uuid,
                pin_hash=f"hashed_pin_list_{i}",
                failed_attempts=i,
            )
            await uow.auth_user_credentials.create(creds)
        
        await uow.commit()
        
        all_creds = await uow.auth_user_credentials.list(filters={"user_uuid": test_user.uuid})
        assert len(all_creds) >= 3
    
    @pytest.mark.asyncio
    async def test_count_credentials(self, uow, test_user):
        for i in range(3):
            creds = AuthUserCredentials(
                uuid=str(uuid.uuid4()),
                user_uuid=test_user.uuid,
                pin_hash=f"hashed_pin_count_{i}",
                failed_attempts=0,
            )
            await uow.auth_user_credentials.create(creds)
        
        await uow.commit()
        
        count = await uow.auth_user_credentials.count(filters={"user_uuid": test_user.uuid})
        assert count >= 3
    
    @pytest.mark.asyncio
    async def test_get_by_user_uuid(self, uow, test_user):
        creds = AuthUserCredentials(
            uuid=str(uuid.uuid4()),
            user_uuid=test_user.uuid,
            pin_hash="hashed_pin_user",
            failed_attempts=0,
        )
        
        await uow.auth_user_credentials.create(creds)
        await uow.commit()
        
        found = await uow.auth_user_credentials.get_by_user_uuid(test_user.uuid)
        assert found is not None
        assert found.user_uuid == test_user.uuid
