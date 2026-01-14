"""
Integration tests for KG Service.

Tests the KGService with real PostgreSQL database.
"""

import pytest
import uuid
import json
from datetime import datetime, UTC

from aico.services.kg_service import KGService
from aico.ai.knowledge_graph.models import Node, Edge


@pytest.fixture
async def kg_service(uow):
    """Create KGService with UnitOfWork."""
    return KGService(uow)


@pytest.fixture
async def test_node(kg_service, test_user):
    """Create a test node."""
    node = Node.create(
        user_id=test_user.uuid,
        label="PERSON",
        properties={"name": "Test Entity", "age": 30, "location": "Test City"},
        confidence=0.95,
        source_text="Test entity from integration test",
        language="en"
    )
    return await kg_service.create_node(node)


class TestKGService:
    """Test suite for KGService."""

    @pytest.mark.asyncio
    async def test_create_node(self, kg_service, test_user):
        """Test creating a node through the service."""
        node = Node.create(
            user_id=test_user.uuid,
            label="ORGANIZATION",
            properties={"name": "Test Company", "industry": "tech"},
            confidence=0.9,
            source_text="Test company from integration test",
            language="en"
        )
        
        created = await kg_service.create_node(node)
        
        assert created.id == node.id
        assert created.properties["name"] == "Test Company"
        assert created.label == "ORGANIZATION"

    @pytest.mark.asyncio
    async def test_get_node(self, kg_service, test_node):
        """Test retrieving a node."""
        retrieved = await kg_service.get_node(test_node.id)
        
        assert retrieved is not None
        assert retrieved.id == test_node.id
        assert retrieved.label == test_node.label

    @pytest.mark.asyncio
    async def test_create_edge(self, kg_service, test_user):
        """Test creating an edge between nodes."""
        # Create two nodes
        node1 = Node.create(
            user_id=test_user.uuid,
            label="PERSON",
            properties={"name": "Alice"},
            confidence=0.95,
            source_text="Alice from test",
            language="en"
        )
        node2 = Node.create(
            user_id=test_user.uuid,
            label="PERSON",
            properties={"name": "Bob"},
            confidence=0.95,
            source_text="Bob from test",
            language="en"
        )
        
        await kg_service.create_node(node1)
        await kg_service.create_node(node2)
        
        # Create edge
        edge = Edge.create(
            user_id=test_user.uuid,
            source_id=node1.id,
            target_id=node2.id,
            relation_type="KNOWS",
            properties={"since": "2020"},
            confidence=0.9,
            source_text="Alice knows Bob from test"
        )
        
        created_edge = await kg_service.create_edge(edge)
        
        assert created_edge.id == edge.id
        assert created_edge.relation_type == "KNOWS"

    @pytest.mark.asyncio
    async def test_list_nodes_by_user(self, kg_service, test_user, test_node):
        """Test listing nodes for a user."""
        nodes = await kg_service.list_nodes(test_user.uuid)
        
        assert len(nodes) >= 1
        assert any(n.id == test_node.id for n in nodes)

    @pytest.mark.asyncio
    async def test_update_node(self, kg_service, test_node):
        """Test updating a node."""
        test_node.properties["name"] = "Updated Company"
        test_node.confidence = 0.95
        
        updated = await kg_service.update_node(test_node)
        
        assert updated.properties["name"] == "Updated Company"
        assert updated.confidence == 0.95

    @pytest.mark.asyncio
    async def test_delete_node(self, kg_service, test_user):
        """Test deleting a node."""
        node = Node.create(
            user_id=test_user.uuid,
            label="TEMP",
            properties={"name": "Temporary Node"},
            confidence=0.8,
            source_text="temp"
        )
        created = await kg_service.create_node(node)
        
        success = await kg_service.delete_node(created.id)
        assert success is True
        
        deleted = await kg_service.get_node(created.id)
        assert deleted is None

    @pytest.mark.asyncio
    async def test_update_edge(self, kg_service, test_user):
        """Test updating an edge."""
        node1 = Node.create(
            user_id=test_user.uuid,
            label="PERSON",
            properties={"name": "Alice"},
            confidence=0.9,
            source_text="Alice"
        )
        node2 = Node.create(
            user_id=test_user.uuid,
            label="PERSON",
            properties={"name": "Bob"},
            confidence=0.9,
            source_text="Bob"
        )
        created_node1 = await kg_service.create_node(node1)
        created_node2 = await kg_service.create_node(node2)
        
        edge = Edge.create(
            user_id=test_user.uuid,
            source_id=created_node1.id,
            target_id=created_node2.id,
            relation_type="KNOWS",
            properties={"since": "2020"},
            confidence=0.8,
            source_text="Alice knows Bob"
        )
        created_edge = await kg_service.create_edge(edge)
        
        created_edge.confidence = 0.95
        created_edge.properties["since"] = "2021"
        updated = await kg_service.update_edge(created_edge)
        
        assert updated.confidence == 0.95
        assert updated.properties["since"] == "2021"

    @pytest.mark.asyncio
    async def test_delete_edge(self, kg_service, test_user):
        """Test deleting an edge."""
        node1 = Node.create(
            user_id=test_user.uuid,
            label="PERSON",
            properties={"name": "Charlie"},
            confidence=0.9,
            source_text="Charlie"
        )
        node2 = Node.create(
            user_id=test_user.uuid,
            label="PERSON",
            properties={"name": "David"},
            confidence=0.9,
            source_text="David"
        )
        created_node1 = await kg_service.create_node(node1)
        created_node2 = await kg_service.create_node(node2)
        
        edge = Edge.create(
            user_id=test_user.uuid,
            source_id=created_node1.id,
            target_id=created_node2.id,
            relation_type="TEMP",
            properties={},
            confidence=0.8,
            source_text="temp"
        )
        created_edge = await kg_service.create_edge(edge)
        
        success = await kg_service.delete_edge(created_edge.id)
        assert success is True
