"""
Integration tests for KGEdgesRepository.
"""

import pytest
import uuid
from datetime import datetime, UTC

from aico.data.kg.models import KGEdge, KGNode
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
    user_id = "kg_edges_test_user"
    existing = await uow.users.get_by_id(user_id)
    if not existing:
        user = UserProfile(
            uuid=user_id,
            full_name="KG Edges Test User",
            nickname="kg_edge_tester",
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
    """Create test nodes for edge tests."""
    nodes = []
    for i in range(2):
        node = KGNode(
            id=str(uuid.uuid4()),
            user_id=test_user.uuid,
            label="PERSON",
            properties={"name": f"Person{i}", "test_id": str(uuid.uuid4())},
            confidence=0.9,
            source_text=f"Person{i}",
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        created = await uow.kg_nodes.create(node)
        nodes.append(created)
    await uow.commit()
    return nodes


class TestKGEdgesRepository:
    
    @pytest.mark.asyncio
    async def test_create_edge(self, uow, test_user, test_nodes):
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
        
        created = await uow.kg_edges.create(edge)
        await uow.commit()
        
        assert created.id == edge.id
        assert created.relation_type == "KNOWS"
    
    @pytest.mark.asyncio
    async def test_get_edge_by_id(self, uow, test_user, test_nodes):
        edge = KGEdge(
            id=str(uuid.uuid4()),
            user_id=test_user.uuid,
            source_id=test_nodes[0].id,
            target_id=test_nodes[1].id,
            relation_type="WORKS_WITH",
            confidence=0.95,
            source_text="Person0 works with Person1",
            created_at=datetime.now(UTC),
        )
        
        await uow.kg_edges.create(edge)
        await uow.commit()
        
        found = await uow.kg_edges.get_by_id(edge.id)
        assert found is not None
        assert found.relation_type == "WORKS_WITH"
    
    @pytest.mark.asyncio
    async def test_update_edge(self, uow, test_user, test_nodes):
        edge = KGEdge(
            id=str(uuid.uuid4()),
            user_id=test_user.uuid,
            source_id=test_nodes[0].id,
            target_id=test_nodes[1].id,
            relation_type="KNOWS",
            confidence=0.8,
            source_text="Person0 knows Person1",
            created_at=datetime.now(UTC),
        )
        
        await uow.kg_edges.create(edge)
        await uow.commit()
        
        edge.confidence = 0.95
        edge.updated_at = datetime.now(UTC)
        updated = await uow.kg_edges.update(edge)
        await uow.commit()
        
        assert updated.confidence == 0.95
        
        found = await uow.kg_edges.get_by_id(edge.id)
        assert found.confidence == 0.95
    
    @pytest.mark.asyncio
    async def test_delete_edge(self, uow, test_user, test_nodes):
        edge = KGEdge(
            id=str(uuid.uuid4()),
            user_id=test_user.uuid,
            source_id=test_nodes[0].id,
            target_id=test_nodes[1].id,
            relation_type="KNOWS_3",
            confidence=0.9,
            source_text="Person0 knows Person1",
            created_at=datetime.now(UTC),
        )
        
        await uow.kg_edges.create(edge)
        await uow.commit()
        
        success = await uow.kg_edges.delete(edge.id)
        await uow.commit()
        
        assert success is True
        
        found = await uow.kg_edges.get_by_id(edge.id)
        assert found is None
    
    @pytest.mark.asyncio
    async def test_list_edges(self, uow, test_user, test_nodes):
        # Create multiple edges with unique relation types
        for i in range(3):
            edge = KGEdge(
                id=str(uuid.uuid4()),
                user_id=test_user.uuid,
                source_id=test_nodes[0].id,
                target_id=test_nodes[1].id,
                relation_type=f"KNOWS_{i}" if i < 2 else "WORKS_WITH_4",
                confidence=0.9,
                source_text=f"Edge{i}",
                created_at=datetime.now(UTC),
                is_current=True,
            )
            await uow.kg_edges.create(edge)
        
        await uow.commit()
        
        all_edges = await uow.kg_edges.list(filters={"user_id": test_user.uuid})
        assert len(all_edges) >= 3
        
        knows_edges = await uow.kg_edges.list(filters={"relation_type": "KNOWS_0"})
        assert len(knows_edges) >= 1
    
    @pytest.mark.asyncio
    async def test_count_edges(self, uow, test_user, test_nodes):
        # Create multiple edges with unique relation types
        for i in range(3):
            edge = KGEdge(
                id=str(uuid.uuid4()),
                user_id=test_user.uuid,
                source_id=test_nodes[0].id,
                target_id=test_nodes[1].id,
                relation_type=f"KNOWS_{i}",
                confidence=0.9,
                source_text=f"Edge{i}",
                created_at=datetime.now(UTC),
            )
            await uow.kg_edges.create(edge)
        
        await uow.commit()
        
        count = await uow.kg_edges.count(filters={"user_id": test_user.uuid})
        assert count >= 3
    
    @pytest.mark.asyncio
    async def test_get_node_edges(self, uow, test_user, test_nodes):
        for i in range(2):
            edge = KGEdge(
                id=str(uuid.uuid4()),
                user_id=test_user.uuid,
                source_id=test_nodes[0].id,
                target_id=test_nodes[1].id,
                relation_type=f"KNOWS_NODE_{i}",
                confidence=0.9,
                source_text=f"Edge{i}",
                created_at=datetime.now(UTC),
                is_current=True,
            )
            await uow.kg_edges.create(edge)
        
        await uow.commit()
        
        edges = await uow.kg_edges.get_node_edges(test_nodes[0].id, direction='outgoing')
        assert len(edges) >= 2
        for e in edges:
            assert e.source_id == test_nodes[0].id
