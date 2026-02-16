"""
Integration tests for AuthAccessPoliciesRepository.
"""

import pytest
import uuid
from datetime import datetime, UTC

from aico.data.auth.access_models import AuthAccessPolicy
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
    user_id = "auth_policy_test_user"
    existing = await uow.users.get_by_id(user_id)
    if not existing:
        from aico.data.user.models import UserProfile
        from datetime import datetime, UTC
        user = UserProfile(
            uuid=user_id,
            full_name="Auth Policy Test User",
            nickname="policy_tester",
            user_type="parent",
            is_active=True,
            primary_language="en",
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        await uow.users.create(user)
        await uow.commit()
    return await uow.users.get_by_id(user_id)


class TestAuthAccessPoliciesRepository:
    
    @pytest.mark.asyncio
    async def test_create_policy(self, uow, test_user):
        policy = AuthAccessPolicy(
            uuid=str(uuid.uuid4()),
            user_uuid=test_user.uuid,
            resource_type="conversation",
            permission="read",
        )
        
        created = await uow.auth_access_policies.create(policy)
        await uow.commit()
        
        assert created.uuid == policy.uuid
        assert created.permission == "read"
    
    @pytest.mark.asyncio
    async def test_get_policy_by_id(self, uow, test_user):
        policy = AuthAccessPolicy(
            uuid=str(uuid.uuid4()),
            user_uuid=test_user.uuid,
            resource_type="goal",
            permission="write",
        )
        
        await uow.auth_access_policies.create(policy)
        await uow.commit()
        
        found = await uow.auth_access_policies.get_by_id(policy.uuid)
        assert found is not None
        assert found.permission == "write"
    
    @pytest.mark.asyncio
    async def test_update_policy(self, uow, test_user):
        policy = AuthAccessPolicy(
            uuid=str(uuid.uuid4()),
            user_uuid=test_user.uuid,
            resource_type="skill",
            permission="execute",
        )
        
        await uow.auth_access_policies.create(policy)
        await uow.commit()
        
        policy.permission = "deny"
        policy.is_active = False
        updated = await uow.auth_access_policies.update(policy)
        await uow.commit()
        
        assert updated.permission == "deny"
        
        found = await uow.auth_access_policies.get_by_id(policy.uuid)
        assert found.is_active is False
    
    @pytest.mark.asyncio
    async def test_delete_policy(self, uow, test_user):
        policy = AuthAccessPolicy(
            uuid=str(uuid.uuid4()),
            user_uuid=test_user.uuid,
            resource_type="test",
            permission="delete",
        )
        
        await uow.auth_access_policies.create(policy)
        await uow.commit()
        
        success = await uow.auth_access_policies.delete(policy.uuid)
        await uow.commit()
        
        assert success is True
        
        found = await uow.auth_access_policies.get_by_id(policy.uuid)
        assert found is None
    
    @pytest.mark.asyncio
    async def test_list_policies(self, uow, test_user):
        for i in range(3):
            policy = AuthAccessPolicy(
                uuid=str(uuid.uuid4()),
                user_uuid=test_user.uuid,
                resource_type="conversation",
                permission="read" if i < 2 else "write",
                is_active=True if i < 2 else False,
            )
            await uow.auth_access_policies.create(policy)
        
        await uow.commit()
        
        all_policies = await uow.auth_access_policies.list(filters={"user_uuid": test_user.uuid})
        assert len(all_policies) >= 3
        
        active = await uow.auth_access_policies.list(filters={"user_uuid": test_user.uuid, "is_active": True})
        assert len(active) >= 2
    
    @pytest.mark.asyncio
    async def test_count_policies(self, uow, test_user):
        for i in range(3):
            policy = AuthAccessPolicy(
                uuid=str(uuid.uuid4()),
                user_uuid=test_user.uuid,
                resource_type="goal",
                permission="read",
            )
            await uow.auth_access_policies.create(policy)
        
        await uow.commit()
        
        count = await uow.auth_access_policies.count(filters={"user_uuid": test_user.uuid})
        assert count >= 3
    
    @pytest.mark.asyncio
    async def test_get_active_policies(self, uow, test_user):
        for i in range(3):
            policy = AuthAccessPolicy(
                uuid=str(uuid.uuid4()),
                user_uuid=test_user.uuid,
                resource_type="conversation",
                permission="read",
                is_active=True if i < 2 else False,
            )
            await uow.auth_access_policies.create(policy)
        
        await uow.commit()
        
        active = await uow.auth_access_policies.list(filters={"user_uuid": test_user.uuid, "is_active": True, "resource_type": "conversation"})
        assert len(active) >= 2
        for p in active:
            assert p.is_active is True
            assert p.resource_type == "conversation"
            assert p.permission == "read"
