"""
Integration tests for EthicsPolicyRulesRepository.
"""

import pytest
import uuid
from datetime import datetime, UTC

from aico.data.ethics.policy_models import EthicsPolicyRule
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


class TestEthicsPolicyRulesRepository:
    
    @pytest.mark.asyncio
    async def test_create_rule(self, uow):
        rule = EthicsPolicyRule(
            rule_id=str(uuid.uuid4()),
            rule_name="Test Rule",
            target_type="goal",
            conditions_json={"type": "test"},
            effect="allow",
            priority=100,
        )
        
        created = await uow.ethics_policy_rules.create(rule)
        await uow.commit()
        
        assert created.rule_id == rule.rule_id
        assert created.effect == "allow"
    
    @pytest.mark.asyncio
    async def test_get_rule_by_id(self, uow):
        rule = EthicsPolicyRule(
            rule_id=str(uuid.uuid4()),
            rule_name="Get Test Rule",
            target_type="plan",
            conditions_json={"type": "test"},
            effect="block",
            priority=50,
        )
        
        await uow.ethics_policy_rules.create(rule)
        await uow.commit()
        
        found = await uow.ethics_policy_rules.get_by_id(rule.rule_id)
        assert found is not None
        assert found.effect == "block"
    
    @pytest.mark.asyncio
    async def test_update_rule(self, uow):
        rule = EthicsPolicyRule(
            rule_id=str(uuid.uuid4()),
            rule_name="Update Test",
            target_type="skill",
            conditions_json={"type": "test"},
            effect="allow",
            priority=100,
        )
        
        await uow.ethics_policy_rules.create(rule)
        await uow.commit()
        
        rule.effect = "allow_with_warning"
        rule.priority = 75
        updated = await uow.ethics_policy_rules.update(rule)
        await uow.commit()
        
        assert updated.effect == "allow_with_warning"
        
        found = await uow.ethics_policy_rules.get_by_id(rule.rule_id)
        assert found.priority == 75
    
    @pytest.mark.asyncio
    async def test_delete_rule(self, uow):
        rule = EthicsPolicyRule(
            rule_id=str(uuid.uuid4()),
            rule_name="Delete Test",
            target_type="goal",
            conditions_json={"type": "test"},
            effect="block",
            priority=100,
        )
        
        await uow.ethics_policy_rules.create(rule)
        await uow.commit()
        
        success = await uow.ethics_policy_rules.delete(rule.rule_id)
        await uow.commit()
        
        assert success is True
        
        found = await uow.ethics_policy_rules.get_by_id(rule.rule_id)
        assert found is None
    
    @pytest.mark.asyncio
    async def test_list_rules(self, uow):
        for i in range(3):
            rule = EthicsPolicyRule(
                rule_id=str(uuid.uuid4()),
                rule_name=f"List Rule {i}",
                target_type="goal",
                conditions_json={"type": "test"},
                effect="allow",
                priority=100 + i,
                enabled=True if i < 2 else False,
            )
            await uow.ethics_policy_rules.create(rule)
        
        await uow.commit()
        
        all_rules = await uow.ethics_policy_rules.list()
        assert len(all_rules) >= 3
        
        enabled = await uow.ethics_policy_rules.list(filters={"enabled": True})
        assert len(enabled) >= 2
    
    @pytest.mark.asyncio
    async def test_count_rules(self, uow):
        for i in range(3):
            rule = EthicsPolicyRule(
                rule_id=str(uuid.uuid4()),
                rule_name=f"Count Rule {i}",
                target_type="plan",
                conditions_json={"type": "test"},
                effect="allow",
                priority=100,
            )
            await uow.ethics_policy_rules.create(rule)
        
        await uow.commit()
        
        count = await uow.ethics_policy_rules.count(filters={"enabled": True})
        assert count >= 3
    
    @pytest.mark.asyncio
    async def test_get_active_rules(self, uow):
        for i in range(3):
            rule = EthicsPolicyRule(
                rule_id=str(uuid.uuid4()),
                rule_name=f"Active Rule {i}",
                target_type="goal",
                conditions_json={"type": "test"},
                effect="allow",
                priority=100 + i,
                enabled=True if i < 2 else False,
            )
            await uow.ethics_policy_rules.create(rule)
        
        await uow.commit()
        
        active = await uow.ethics_policy_rules.get_active_rules("goal")
        assert len(active) >= 2
        for r in active:
            assert r.enabled is True
            assert r.target_type == "goal"
