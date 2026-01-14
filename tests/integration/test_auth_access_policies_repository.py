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


class TestAuthAccessPoliciesRepository:
    
    @pytest.mark.asyncio
    async def test_create_policy(self, uow):
        policy = AuthAccessPolicy(
            policy_id=str(uuid.uuid4()),
            resource_type="conversation",
            action="read",
            effect="allow",
        )
        
        created = await uow.auth_access_policies.create(policy)
        await uow.commit()
        
        assert created.policy_id == policy.policy_id
        assert created.effect == "allow"
    
    @pytest.mark.asyncio
    async def test_get_policy_by_id(self, uow):
        policy = AuthAccessPolicy(
            policy_id=str(uuid.uuid4()),
            resource_type="goal",
            action="write",
            effect="deny",
            priority=50,
        )
        
        await uow.auth_access_policies.create(policy)
        await uow.commit()
        
        found = await uow.auth_access_policies.get_by_id(policy.policy_id)
        assert found is not None
        assert found.priority == 50
    
    @pytest.mark.asyncio
    async def test_update_policy(self, uow):
        policy = AuthAccessPolicy(
            policy_id=str(uuid.uuid4()),
            resource_type="skill",
            action="execute",
            effect="allow",
        )
        
        await uow.auth_access_policies.create(policy)
        await uow.commit()
        
        policy.effect = "deny"
        policy.priority = 75
        updated = await uow.auth_access_policies.update(policy)
        await uow.commit()
        
        assert updated.effect == "deny"
        
        found = await uow.auth_access_policies.get_by_id(policy.policy_id)
        assert found.priority == 75
    
    @pytest.mark.asyncio
    async def test_delete_policy(self, uow):
        policy = AuthAccessPolicy(
            policy_id=str(uuid.uuid4()),
            resource_type="test",
            action="delete",
            effect="allow",
        )
        
        await uow.auth_access_policies.create(policy)
        await uow.commit()
        
        success = await uow.auth_access_policies.delete(policy.policy_id)
        await uow.commit()
        
        assert success is True
        
        found = await uow.auth_access_policies.get_by_id(policy.policy_id)
        assert found is None
    
    @pytest.mark.asyncio
    async def test_list_policies(self, uow):
        for i in range(3):
            policy = AuthAccessPolicy(
                policy_id=str(uuid.uuid4()),
                resource_type="conversation",
                action="read" if i < 2 else "write",
                effect="allow",
                enabled=True if i < 2 else False,
            )
            await uow.auth_access_policies.create(policy)
        
        await uow.commit()
        
        all_policies = await uow.auth_access_policies.list()
        assert len(all_policies) >= 3
        
        enabled = await uow.auth_access_policies.list(filters={"enabled": True})
        assert len(enabled) >= 2
    
    @pytest.mark.asyncio
    async def test_count_policies(self, uow):
        for i in range(3):
            policy = AuthAccessPolicy(
                policy_id=str(uuid.uuid4()),
                resource_type="goal",
                action="read",
                effect="allow",
            )
            await uow.auth_access_policies.create(policy)
        
        await uow.commit()
        
        count = await uow.auth_access_policies.count(filters={"enabled": True})
        assert count >= 3
    
    @pytest.mark.asyncio
    async def test_get_active_policies(self, uow):
        for i in range(3):
            policy = AuthAccessPolicy(
                policy_id=str(uuid.uuid4()),
                resource_type="conversation",
                action="read",
                effect="allow",
                priority=100 + i,
                enabled=True if i < 2 else False,
            )
            await uow.auth_access_policies.create(policy)
        
        await uow.commit()
        
        active = await uow.auth_access_policies.get_active_policies("conversation", "read")
        assert len(active) >= 2
        for p in active:
            assert p.enabled is True
            assert p.resource_type == "conversation"
            assert p.action == "read"
