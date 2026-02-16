"""
Integration tests for AuthSessionsRepository.
"""

import pytest
import uuid
from datetime import datetime, UTC, timedelta

from aico.data.auth.session_models import AuthSession
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
    user_id = "auth_session_test_user"
    existing = await uow.users.get_by_id(user_id)
    if not existing:
        user = UserProfile(
            uuid=user_id,
            full_name="Auth Session Test User",
            nickname="auth_tester",
            user_type="parent",
            is_active=True,
            primary_language="en",
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        await uow.users.create(user)
        await uow.commit()
    return await uow.users.get_by_id(user_id)


class TestAuthSessionsRepository:
    
    @pytest.mark.asyncio
    async def test_create_session(self, uow, test_user):
        session = AuthSession(
            uuid=str(uuid.uuid4()),
            user_uuid=test_user.uuid,
            device_uuid=str(uuid.uuid4()),
            jwt_token_hash="test_hash_123",
            expires_at=datetime.now(UTC) + timedelta(hours=1),
            is_active=True,
        )
        
        created = await uow.auth_sessions.create(session)
        await uow.commit()
        
        assert created.uuid == session.uuid
        assert created.user_uuid == test_user.uuid
    
    @pytest.mark.asyncio
    async def test_get_session_by_id(self, uow, test_user):
        session = AuthSession(
            uuid=str(uuid.uuid4()),
            user_uuid=test_user.uuid,
            device_uuid=str(uuid.uuid4()),
            jwt_token_hash="test_hash_456",
            expires_at=datetime.now(UTC) + timedelta(hours=2),
            is_active=True,
        )
        
        await uow.auth_sessions.create(session)
        await uow.commit()
        
        found = await uow.auth_sessions.get_by_id(session.uuid)
        assert found is not None
        assert found.jwt_token_hash == "test_hash_456"
    
    @pytest.mark.asyncio
    async def test_update_session(self, uow, test_user):
        session = AuthSession(
            uuid=str(uuid.uuid4()),
            user_uuid=test_user.uuid,
            device_uuid=str(uuid.uuid4()),
            jwt_token_hash="test_hash_789",
            expires_at=datetime.now(UTC) + timedelta(hours=1),
            is_active=True,
        )
        
        await uow.auth_sessions.create(session)
        await uow.commit()
        
        session.is_active = False
        updated = await uow.auth_sessions.update(session)
        await uow.commit()
        
        assert updated.is_active is False
        
        found = await uow.auth_sessions.get_by_id(session.uuid)
        assert found.is_active is False
    
    @pytest.mark.asyncio
    async def test_delete_session(self, uow, test_user):
        session = AuthSession(
            uuid=str(uuid.uuid4()),
            user_uuid=test_user.uuid,
            device_uuid=str(uuid.uuid4()),
            jwt_token_hash="test_hash_del",
            expires_at=datetime.now(UTC) + timedelta(hours=1),
            is_active=True,
        )
        
        await uow.auth_sessions.create(session)
        await uow.commit()
        
        success = await uow.auth_sessions.delete(session.uuid)
        await uow.commit()
        
        assert success is True
        
        found = await uow.auth_sessions.get_by_id(session.uuid)
        assert found is None
    
    @pytest.mark.asyncio
    async def test_list_sessions(self, uow, test_user):
        for i in range(3):
            session = AuthSession(
                uuid=str(uuid.uuid4()),
                user_uuid=test_user.uuid,
                device_uuid=str(uuid.uuid4()),
                jwt_token_hash=f"test_hash_list_{i}",
                expires_at=datetime.now(UTC) + timedelta(hours=1),
                is_active=True if i < 2 else False,
            )
            await uow.auth_sessions.create(session)
        
        await uow.commit()
        
        all_sessions = await uow.auth_sessions.list(filters={"user_uuid": test_user.uuid})
        assert len(all_sessions) >= 3
        
        active = await uow.auth_sessions.list(filters={"is_active": True})
        assert len(active) >= 2
    
    @pytest.mark.asyncio
    async def test_count_sessions(self, uow, test_user):
        for i in range(3):
            session = AuthSession(
                uuid=str(uuid.uuid4()),
                user_uuid=test_user.uuid,
                device_uuid=str(uuid.uuid4()),
                jwt_token_hash=f"test_hash_count_{i}",
                expires_at=datetime.now(UTC) + timedelta(hours=1),
                is_active=True,
            )
            await uow.auth_sessions.create(session)
        
        await uow.commit()
        
        count = await uow.auth_sessions.count(filters={"user_uuid": test_user.uuid})
        assert count >= 3
    
    @pytest.mark.asyncio
    async def test_get_active_sessions(self, uow, test_user):
        for i in range(3):
            session = AuthSession(
                uuid=str(uuid.uuid4()),
                user_uuid=test_user.uuid,
                device_uuid=str(uuid.uuid4()),
                jwt_token_hash=f"test_hash_active_{i}",
                expires_at=datetime.now(UTC) + timedelta(hours=1) if i < 2 else datetime.now(UTC) - timedelta(hours=1),
                is_active=True if i < 2 else False,
            )
            await uow.auth_sessions.create(session)
        
        await uow.commit()
        
        active = await uow.auth_sessions.get_active_sessions(test_user.uuid)
        assert len(active) >= 2
        for s in active:
            assert s.is_active is True
            assert s.expires_at > datetime.now(UTC)
