"""
Integration tests for KGEdgePropertiesRepository.
"""

import pytest
import uuid
from datetime import datetime, UTC

from aico.data.kg.models import KGNode, KGEdge
from aico.data.kg.property_models import KGEdgeProperty
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
    user_id = f"kg_edge_prop_test_{uuid.uuid4().hex[:8]}"
    user = UserProfile(
        uuid=user_id,
        full_name="KG Edge Props Test User",
        nickname="kg_edge_prop_tester",
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
async def test_nodes(uow, test_user):
    nodes = []
    for i in range(2):
        node = KGNode(
            id=str(uuid.uuid4()),
            user_id=test_user.uuid,
            label="PERSON",
            properties={"name": f"EdgePropPerson{i}"},
            confidence=0.9,
            source_text=f"Person{i}",
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        await uow.kg_nodes.create(node)
        nodes.append(node)
    await uow.commit()
    return nodes


@pytest.fixture
async def test_edge(uow, test_user, test_nodes):
    edge = KGEdge(
        id=str(uuid.uuid4()),
        user_id=test_user.uuid,
        source_id=test_nodes[0].id,
        target_id=test_nodes[1].id,
        relation_type="KNOWS",
        confidence=0.9,
        source_text="Person0 knows Person1",
        created_at=datetime.now(UTC),
    )
    await uow.kg_edges.create(edge)
    await uow.commit()
    return edge


class TestKGEdgePropertiesRepository:
    
    @pytest.mark.asyncio
    async def test_create_property(self, uow, test_edge):
        prop = KGEdgeProperty(
            edge_id=test_edge.id,
            key="since",
            value="2020",
        )
        
        created = await uow.kg_edge_properties.create(prop)
        await uow.commit()
        
        assert created.edge_id == test_edge.id
        assert created.key == "since"
    
    @pytest.mark.asyncio
    async def test_delete_property(self, uow, test_edge):
        prop = KGEdgeProperty(
            edge_id=test_edge.id,
            key="strength",
            value="strong",
        )
        
        await uow.kg_edge_properties.create(prop)
        await uow.commit()
        
        success = await uow.kg_edge_properties.delete_property(test_edge.id, "strength", "strong")
        await uow.commit()
        
        assert success is True
        
        props = await uow.kg_edge_properties.get_edge_properties(test_edge.id)
        assert len([p for p in props if p.key == "strength"]) == 0
    
    @pytest.mark.asyncio
    async def test_list_properties(self, uow, test_edge):
        for i in range(3):
            prop = KGEdgeProperty(
                edge_id=test_edge.id,
                key=f"prop{i}",
                value=f"value{i}",
            )
            await uow.kg_edge_properties.create(prop)
        
        await uow.commit()
        
        all_props = await uow.kg_edge_properties.list(filters={"edge_id": test_edge.id})
        assert len(all_props) >= 3
    
    @pytest.mark.asyncio
    async def test_count_properties(self, uow, test_edge):
        for i in range(3):
            prop = KGEdgeProperty(
                edge_id=test_edge.id,
                key=f"count_prop{i}",
                value=f"value{i}",
            )
            await uow.kg_edge_properties.create(prop)
        
        await uow.commit()
        
        count = await uow.kg_edge_properties.count(filters={"edge_id": test_edge.id})
        assert count >= 3
    
    @pytest.mark.asyncio
    async def test_get_edge_properties(self, uow, test_edge):
        for i in range(3):
            prop = KGEdgeProperty(
                edge_id=test_edge.id,
                key=f"get_prop{i}",
                value=f"value{i}",
            )
            await uow.kg_edge_properties.create(prop)
        
        await uow.commit()
        
        props = await uow.kg_edge_properties.get_edge_properties(test_edge.id)
        assert len(props) >= 3
        for p in props:
            assert p.edge_id == test_edge.id
    
    @pytest.mark.asyncio
    async def test_find_by_property(self, uow, test_edge):
        prop = KGEdgeProperty(
            edge_id=test_edge.id,
            key="type",
            value="professional",
        )
        await uow.kg_edge_properties.create(prop)
        await uow.commit()
        
        found = await uow.kg_edge_properties.find_by_property("type", "professional")
        assert len(found) >= 1
        assert any(p.edge_id == test_edge.id for p in found)
