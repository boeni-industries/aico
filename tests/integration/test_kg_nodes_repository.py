"""
Integration tests for KGNodesRepository.
"""

import pytest
import uuid
from datetime import datetime, UTC

from aico.data.kg.models import KGNode
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
    user_id = "kg_nodes_test_user"
    existing = await uow.users.get_by_id(user_id)
    if not existing:
        user = UserProfile(
            uuid=user_id,
            full_name="KG Nodes Test User",
            nickname="kg_tester",
            user_type="parent",
            is_active=True,
            primary_language="en",
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        await uow.users.create(user)
        await uow.commit()
    return await uow.users.get_by_id(user_id)


class TestKGNodesRepository:
    
    @pytest.mark.asyncio
    async def test_create_node(self, uow, test_user):
        node = KGNode(
            id=str(uuid.uuid4()),
            user_id=test_user.uuid,
            label="PERSON",
            properties={"name": "John"},
            confidence=0.9,
            source_text="John is a person",
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        
        created = await uow.kg_nodes.create(node)
        await uow.commit()
        
        assert created.id == node.id
        assert created.label == "PERSON"
    
    @pytest.mark.asyncio
    async def test_get_node_by_id(self, uow, test_user):
        node = KGNode(
            id=str(uuid.uuid4()),
            user_id=test_user.uuid,
            label="LOCATION",
            properties={"name": "Paris"},
            confidence=0.95,
            source_text="Paris is a city",
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        
        await uow.kg_nodes.create(node)
        await uow.commit()
        
        found = await uow.kg_nodes.get_by_id(node.id)
        assert found is not None
        assert found.label == "LOCATION"
    
    @pytest.mark.asyncio
    async def test_update_node(self, uow, test_user):
        node = KGNode(
            id=str(uuid.uuid4()),
            user_id=test_user.uuid,
            label="PERSON",
            properties={"name": "Alice"},
            confidence=0.8,
            source_text="Alice is a person",
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        
        await uow.kg_nodes.create(node)
        await uow.commit()
        
        node.confidence = 0.95
        node.updated_at = datetime.now(UTC)
        updated = await uow.kg_nodes.update(node)
        await uow.commit()
        
        assert updated.confidence == 0.95
        
        found = await uow.kg_nodes.get_by_id(node.id)
        assert found.confidence == 0.95
    
    @pytest.mark.asyncio
    async def test_delete_node(self, uow, test_user):
        node = KGNode(
            id=str(uuid.uuid4()),
            user_id=test_user.uuid,
            label="ORGANIZATION",
            properties={"name": "ACME"},
            confidence=0.9,
            source_text="ACME is a company",
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        
        await uow.kg_nodes.create(node)
        await uow.commit()
        
        success = await uow.kg_nodes.delete(node.id)
        await uow.commit()
        
        assert success is True
        
        found = await uow.kg_nodes.get_by_id(node.id)
        assert found is None
    
    @pytest.mark.asyncio
    async def test_list_nodes(self, uow, test_user):
        for i in range(3):
            node = KGNode(
                id=str(uuid.uuid4()),
                user_id=test_user.uuid,
                label="PERSON",
                properties={"name": f"Person{i}"},
                confidence=0.9,
                source_text=f"Person{i} is a person",
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC),
                is_current=True if i < 2 else False,
            )
            await uow.kg_nodes.create(node)
        
        await uow.commit()
        
        all_nodes = await uow.kg_nodes.list(filters={"user_id": test_user.uuid})
        assert len(all_nodes) >= 3
        
        current = await uow.kg_nodes.list(filters={"is_current": True})
        assert len(current) >= 2
    
    @pytest.mark.asyncio
    async def test_count_nodes(self, uow, test_user):
        for i in range(3):
            node = KGNode(
                id=str(uuid.uuid4()),
                user_id=test_user.uuid,
                label="LOCATION",
                properties={"name": f"City{i}"},
                confidence=0.9,
                source_text=f"City{i} is a location",
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC),
            )
            await uow.kg_nodes.create(node)
        
        await uow.commit()
        
        count = await uow.kg_nodes.count(filters={"user_id": test_user.uuid})
        assert count >= 3
    
    @pytest.mark.asyncio
    async def test_get_user_nodes(self, uow, test_user):
        for i in range(3):
            node = KGNode(
                id=str(uuid.uuid4()),
                user_id=test_user.uuid,
                label="PERSON" if i < 2 else "LOCATION",
                properties={"name": f"Entity{i}"},
                confidence=0.9,
                source_text=f"Entity{i}",
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC),
                is_current=True,
            )
            await uow.kg_nodes.create(node)
        
        await uow.commit()
        
        all_user_nodes = await uow.kg_nodes.get_user_nodes(test_user.uuid)
        assert len(all_user_nodes) >= 3
        
        person_nodes = await uow.kg_nodes.get_user_nodes(test_user.uuid, label="PERSON")
        assert len(person_nodes) >= 2
