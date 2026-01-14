"""
Integration tests for KGNodePropertiesRepository.
"""

import pytest
import uuid
from datetime import datetime, UTC

from aico.data.kg.models import KGNode
from aico.data.kg.property_models import KGNodeProperty
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
    user_id = f"kg_prop_test_user_{uuid.uuid4().hex[:8]}"
    user = UserProfile(
        uuid=user_id,
        full_name="KG Props Test User",
        nickname="kg_prop_tester",
        user_type="parent",
        is_active=True,
        primary_language="en",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    await uow.users.create(user)
    await uow.commit()
    return await uow.users.get_by_id(user_id)


@pytest.fixture
async def test_node(uow, test_user):
    node = KGNode(
        id=str(uuid.uuid4()),
        user_id=test_user.uuid,
        label="PERSON",
        properties={"name": "TestPerson"},
        confidence=0.9,
        source_text="Test person",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    await uow.kg_nodes.create(node)
    await uow.commit()
    return node


class TestKGNodePropertiesRepository:
    
    @pytest.mark.asyncio
    async def test_create_property(self, uow, test_node):
        prop = KGNodeProperty(
            node_id=test_node.id,
            key="age",
            value="30",
        )
        
        created = await uow.kg_node_properties.create(prop)
        await uow.commit()
        
        assert created.node_id == test_node.id
        assert created.key == "age"
    
    @pytest.mark.asyncio
    async def test_delete_property(self, uow, test_node):
        prop = KGNodeProperty(
            node_id=test_node.id,
            key="city",
            value="Paris",
        )
        
        await uow.kg_node_properties.create(prop)
        await uow.commit()
        
        success = await uow.kg_node_properties.delete_property(test_node.id, "city", "Paris")
        await uow.commit()
        
        assert success is True
        
        props = await uow.kg_node_properties.get_node_properties(test_node.id)
        assert len([p for p in props if p.key == "city"]) == 0
    
    @pytest.mark.asyncio
    async def test_list_properties(self, uow, test_node):
        for i in range(3):
            prop = KGNodeProperty(
                node_id=test_node.id,
                key=f"prop{i}",
                value=f"value{i}",
            )
            await uow.kg_node_properties.create(prop)
        
        await uow.commit()
        
        all_props = await uow.kg_node_properties.list(filters={"node_id": test_node.id})
        assert len(all_props) >= 3
    
    @pytest.mark.asyncio
    async def test_count_properties(self, uow, test_node):
        for i in range(3):
            prop = KGNodeProperty(
                node_id=test_node.id,
                key=f"count_prop{i}",
                value=f"value{i}",
            )
            await uow.kg_node_properties.create(prop)
        
        await uow.commit()
        
        count = await uow.kg_node_properties.count(filters={"node_id": test_node.id})
        assert count >= 3
    
    @pytest.mark.asyncio
    async def test_get_node_properties(self, uow, test_node):
        for i in range(3):
            prop = KGNodeProperty(
                node_id=test_node.id,
                key=f"get_prop{i}",
                value=f"value{i}",
            )
            await uow.kg_node_properties.create(prop)
        
        await uow.commit()
        
        props = await uow.kg_node_properties.get_node_properties(test_node.id)
        assert len(props) >= 3
        for p in props:
            assert p.node_id == test_node.id
    
    @pytest.mark.asyncio
    async def test_find_by_property(self, uow, test_node):
        prop = KGNodeProperty(
            node_id=test_node.id,
            key="occupation",
            value="engineer",
        )
        await uow.kg_node_properties.create(prop)
        await uow.commit()
        
        found = await uow.kg_node_properties.find_by_property("occupation", "engineer")
        assert len(found) >= 1
        assert any(p.node_id == test_node.id for p in found)
