"""
Integration tests for Knowledge Graph repositories (Node, Edge).

Tests the KGNodeRepository and KGEdgeRepository with real PostgreSQL database.
"""

import pytest
import uuid
from datetime import datetime, UTC

from aico.ai.knowledge_graph.models import Node, Edge
from aico.data.user.models import UserProfile
from aico.data.postgres.connection import get_session_factory
from aico.data.uow import UnitOfWork


@pytest.fixture
async def session_factory():
    """Create async session factory for tests."""
    factory = await get_session_factory()
    return factory


@pytest.fixture
async def uow(session_factory):
    """Create Unit of Work for tests."""
    uow = UnitOfWork(session_factory)
    async with uow:
        yield uow


@pytest.fixture
async def test_user(uow):
    """Create a test user for KG tests."""
    user = UserProfile(
        uuid=str(uuid.uuid4()),
        full_name="KG Test User",
        nickname="kg_tester",
        user_type="parent",
        is_active=True,
        primary_language="en",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    await uow.users.create(user)
    await uow.commit()
    return user


class TestKGNodeRepository:
    """Test KGNodeRepository CRUD operations."""
    
    @pytest.mark.asyncio
    async def test_create_node(self, uow, test_user):
        """Test creating a new KG node."""
        node = Node(
            id=str(uuid.uuid4()),
            user_id=test_user.uuid,
            label="PERSON",
            properties={"name": "John Doe", "age": 30},
            confidence=0.95,
            source_text="John Doe is 30 years old",
            language="en",
            is_current=True,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        
        created = await uow.kg_nodes.create(node)
        await uow.commit()
        
        assert created.id == node.id
        assert created.label == "PERSON"
        assert created.properties.get("name") == "John Doe"
    
    @pytest.mark.asyncio
    async def test_get_node_by_id(self, uow, test_user):
        """Test retrieving node by ID."""
        node = Node(
            id=str(uuid.uuid4()),
            user_id=test_user.uuid,
            label="LOCATION",
            properties={"name": "Paris", "country": "France"},
            confidence=0.9,
            source_text="Paris is in France",
            is_current=True,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        
        await uow.kg_nodes.create(node)
        await uow.commit()
        
        found = await uow.kg_nodes.get_by_id(node.id)
        assert found is not None
        assert found.label == "LOCATION"
        assert found.properties.get("name") == "Paris"
    
    @pytest.mark.asyncio
    async def test_update_node(self, uow, test_user):
        """Test updating a node."""
        node = Node(
            id=str(uuid.uuid4()),
            user_id=test_user.uuid,
            label="ORGANIZATION",
            properties={"name": "ACME Corp"},
            confidence=0.8,
            source_text="ACME Corp is an organization",
            is_current=True,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        
        await uow.kg_nodes.create(node)
        await uow.commit()
        
        # Update the node
        node.properties["name"] = "ACME Corporation"
        node.confidence = 0.95
        updated = await uow.kg_nodes.update(node)
        await uow.commit()
        
        assert updated.properties.get("name") == "ACME Corporation"
        
        # Verify update persisted
        found = await uow.kg_nodes.get_by_id(node.id)
        assert found.confidence == 0.95
    
    @pytest.mark.asyncio
    async def test_delete_node(self, uow, test_user):
        """Test deleting a node."""
        node = Node(
            id=str(uuid.uuid4()),
            user_id=test_user.uuid,
            label="EVENT",
            properties={"name": "Test Event"},
            confidence=0.7,
            source_text="Test Event occurred",
            is_current=True,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        
        await uow.kg_nodes.create(node)
        await uow.commit()
        
        # Delete the node
        success = await uow.kg_nodes.delete(node.id)
        await uow.commit()
        
        assert success is True
        
        # Verify it's gone
        found = await uow.kg_nodes.get_by_id(node.id)
        assert found is None
    
    @pytest.mark.asyncio
    async def test_list_nodes(self, uow, test_user):
        """Test listing nodes with filters."""
        for i in range(3):
            node = Node(
                id=str(uuid.uuid4()),
                user_id=test_user.uuid,
                label="PERSON" if i < 2 else "LOCATION",
                properties={"name": f"Entity {i}"},
                confidence=0.8,
                source_text=f"Entity {i} exists",
                is_current=True,
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC),
            )
            await uow.kg_nodes.create(node)
        
        await uow.commit()
        
        # List all nodes for user
        all_nodes = await uow.kg_nodes.list(filters={"user_id": test_user.uuid})
        assert len(all_nodes) >= 3
        
        # List only PERSON nodes
        person_nodes = await uow.kg_nodes.list(filters={"user_id": test_user.uuid, "label": "PERSON"})
        assert len(person_nodes) >= 2
    
    @pytest.mark.asyncio
    async def test_count_nodes(self, uow, test_user):
        """Test counting nodes."""
        for i in range(3):
            node = Node(
                id=str(uuid.uuid4()),
                user_id=test_user.uuid,
                label="CONCEPT",
                properties={"name": f"Concept {i}"},
                confidence=0.85,
                source_text=f"Concept {i} is important",
                is_current=True,
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC),
            )
            await uow.kg_nodes.create(node)
        
        await uow.commit()
        
        count = await uow.kg_nodes.count(filters={"user_id": test_user.uuid, "label": "CONCEPT"})
        assert count >= 3
    
    @pytest.mark.asyncio
    async def test_get_by_label_for_user(self, uow, test_user):
        """Test getting nodes by label for a user."""
        for i in range(3):
            node = Node(
                id=str(uuid.uuid4()),
                user_id=test_user.uuid,
                label="HOBBY",
                properties={"name": f"Hobby {i}"},
                confidence=0.9 - (i * 0.1),  # Decreasing confidence
                source_text=f"Hobby {i} is enjoyable",
                is_current=True,
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC),
            )
            await uow.kg_nodes.create(node)
        
        await uow.commit()
        
        hobby_nodes = await uow.kg_nodes.get_by_label_for_user(test_user.uuid, "HOBBY")
        assert len(hobby_nodes) >= 3
        # Should be ordered by confidence desc
        if len(hobby_nodes) >= 2:
            assert hobby_nodes[0].confidence >= hobby_nodes[1].confidence
    
    @pytest.mark.asyncio
    async def test_mark_as_superseded(self, uow, test_user):
        """Test marking a node as superseded."""
        node = KGNode(
            id=str(uuid.uuid4()),
            user_id=test_user.uuid,
            label="PREFERENCE",
            properties={"name": "Old Preference"},
            confidence=0.8,
            source_text="User prefers this",
            is_current=True,
        )
        
        await uow.kg_nodes.create(node)
        await uow.commit()
        
        # Mark as superseded by new node
        new_node_id = str(uuid.uuid4())
        success = await uow.kg_nodes.mark_as_superseded(node.id, new_node_id)
        await uow.commit()
        
        assert success is True
        
        # Verify is_current is False
        found = await uow.kg_nodes.get_by_id(node.id)
        assert found.is_current is False


class TestKGEdgeRepository:
    """Test KGEdgeRepository CRUD operations."""
    
    @pytest.mark.asyncio
    async def test_create_edge(self, uow, test_user):
        """Test creating a new KG edge."""
        # Create source and target nodes first
        source = KGNode(
            id=str(uuid.uuid4()),
            user_id=test_user.uuid,
            label="PERSON",
            properties={"name": "Alice"},
            confidence=0.95,
            source_text="Alice is a person",
            is_current=True,
        )
        target = KGNode(
            id=str(uuid.uuid4()),
            user_id=test_user.uuid,
            label="PERSON",
            properties={"name": "Bob"},
            confidence=0.95,
            source_text="Bob is a person",
            is_current=True,
        )
        
        await uow.kg_nodes.create(source)
        await uow.kg_nodes.create(target)
        await uow.commit()
        
        # Create edge
        edge = KGEdge(
            id=str(uuid.uuid4()),
            user_id=test_user.uuid,
            source_id=source.id,
            target_id=target.id,
            relation_type="KNOWS",
            source_text="Alice knows Bob",
            properties={"since": "2020"},
            confidence=0.9,
            is_current=True,
        )
        
        created = await uow.kg_edges.create(edge)
        await uow.commit()
        
        assert created.id == edge.id
        assert created.relation_type == "KNOWS"
    
    @pytest.mark.asyncio
    async def test_get_edge_by_id(self, uow, test_user):
        """Test retrieving edge by ID."""
        # Create nodes
        source = KGNode(
            id=str(uuid.uuid4()),
            user_id=test_user.uuid,
            label="PERSON",
            properties={"name": "Charlie"},
            confidence=0.95,
            source_text="Charlie is a person",
            is_current=True,
        )
        target = KGNode(
            id=str(uuid.uuid4()),
            user_id=test_user.uuid,
            label="ORGANIZATION",
            properties={"name": "TechCorp"},
            confidence=0.95,
            source_text="TechCorp is an organization",
            is_current=True,
        )
        
        await uow.kg_nodes.create(source)
        await uow.kg_nodes.create(target)
        
        # Create edge
        edge = KGEdge(
            id=str(uuid.uuid4()),
            user_id=test_user.uuid,
            source_id=source.id,
            target_id=target.id,
            relation_type="WORKS_AT",
            source_text="Charlie works at TechCorp",
            confidence=0.85,
            is_current=True,
        )
        
        await uow.kg_edges.create(edge)
        await uow.commit()
        
        found = await uow.kg_edges.get_by_id(edge.id)
        assert found is not None
        assert found.relation_type == "WORKS_AT"
    
    @pytest.mark.asyncio
    async def test_get_edges_for_node(self, uow, test_user):
        """Test getting edges connected to a node."""
        # Create central node
        central = KGNode(
            id=str(uuid.uuid4()),
            user_id=test_user.uuid,
            label="PERSON",
            properties={"name": "David"},
            confidence=0.95,
            source_text="David is a person",
            is_current=True,
        )
        await uow.kg_nodes.create(central)
        
        # Create connected nodes and edges
        for i in range(2):
            other = KGNode(
                id=str(uuid.uuid4()),
                user_id=test_user.uuid,
                label="PERSON",
                properties={"name": f"Person {i}"},
                confidence=0.9,
                source_text=f"Person {i} exists",
                is_current=True,
            )
            await uow.kg_nodes.create(other)
            
            edge = KGEdge(
                id=str(uuid.uuid4()),
                user_id=test_user.uuid,
                source_id=central.id,
                target_id=other.id,
                relation_type="KNOWS",
                source_text=f"David knows Person {i}",
                confidence=0.85,
                is_current=True,
            )
            await uow.kg_edges.create(edge)
        
        await uow.commit()
        
        # Get outgoing edges
        outgoing = await uow.kg_edges.get_edges_for_node(central.id, direction='outgoing')
        assert len(outgoing) >= 2
    
    @pytest.mark.asyncio
    async def test_get_edges_by_relation_type(self, uow, test_user):
        """Test getting edges by relation type."""
        # Create nodes and edges
        for i in range(2):
            source = KGNode(
                id=str(uuid.uuid4()),
                user_id=test_user.uuid,
                label="PERSON",
                properties={"name": f"Person {i}"},
                confidence=0.9,
                source_text=f"Person {i} exists",
                is_current=True,
            )
            target = KGNode(
                id=str(uuid.uuid4()),
                user_id=test_user.uuid,
                label="LOCATION",
                properties={"name": f"City {i}"},
                confidence=0.9,
                source_text=f"City {i} is a location",
                is_current=True,
            )
            
            await uow.kg_nodes.create(source)
            await uow.kg_nodes.create(target)
            
            edge = KGEdge(
                id=str(uuid.uuid4()),
                user_id=test_user.uuid,
                source_id=source.id,
                target_id=target.id,
                relation_type="LIVES_IN",
                source_text=f"Person {i} lives in City {i}",
                confidence=0.8,
                is_current=True,
            )
            await uow.kg_edges.create(edge)
        
        await uow.commit()
        
        lives_in_edges = await uow.kg_edges.get_edges_by_relation_type(test_user.uuid, "LIVES_IN")
        assert len(lives_in_edges) >= 2
    
    @pytest.mark.asyncio
    async def test_mark_edge_as_superseded(self, uow, test_user):
        """Test marking an edge as superseded."""
        # Create nodes
        source = KGNode(
            id=str(uuid.uuid4()),
            user_id=test_user.uuid,
            label="PERSON",
            properties={"name": "Eve"},
            confidence=0.95,
            source_text="Eve is a person",
            is_current=True,
        )
        target = KGNode(
            id=str(uuid.uuid4()),
            user_id=test_user.uuid,
            label="SKILL",
            properties={"name": "Python"},
            confidence=0.9,
            source_text="Python is a skill",
            is_current=True,
        )
        
        await uow.kg_nodes.create(source)
        await uow.kg_nodes.create(target)
        
        edge = KGEdge(
            id=str(uuid.uuid4()),
            user_id=test_user.uuid,
            source_id=source.id,
            target_id=target.id,
            relation_type="HAS_SKILL",
            source_text="Eve has Python skill",
            confidence=0.85,
            is_current=True,
        )
        
        await uow.kg_edges.create(edge)
        await uow.commit()
        
        # Mark as superseded by new edge
        new_edge_id = str(uuid.uuid4())
        success = await uow.kg_edges.mark_as_superseded(edge.id, new_edge_id)
        await uow.commit()
        
        assert success is True
        
        # Verify is_current is False
        found = await uow.kg_edges.get_by_id(edge.id)
        assert found.is_current is False
    
    @pytest.mark.asyncio
    async def test_update_edge(self, uow, test_user):
        """Test updating an edge."""
        # Create nodes
        source = KGNode(
            id=str(uuid.uuid4()),
            user_id=test_user.uuid,
            label="PERSON",
            properties={"name": "Frank"},
            confidence=0.95,
            source_text="Frank is a person",
            is_current=True,
        )
        target = KGNode(
            id=str(uuid.uuid4()),
            user_id=test_user.uuid,
            label="COMPANY",
            properties={"name": "StartupCo"},
            confidence=0.9,
            source_text="StartupCo is a company",
            is_current=True,
        )
        
        await uow.kg_nodes.create(source)
        await uow.kg_nodes.create(target)
        
        edge = KGEdge(
            id=str(uuid.uuid4()),
            user_id=test_user.uuid,
            source_id=source.id,
            target_id=target.id,
            relation_type="WORKS_AT",
            source_text="Frank works at StartupCo",
            confidence=0.8,
            is_current=True,
        )
        
        await uow.kg_edges.create(edge)
        await uow.commit()
        
        # Update the edge
        edge.confidence = 0.95
        edge.source_text = "Frank works at StartupCo since 2024"
        updated = await uow.kg_edges.update(edge)
        await uow.commit()
        
        assert updated.confidence == 0.95
        
        # Verify update persisted
        found = await uow.kg_edges.get_by_id(edge.id)
        assert found.confidence == 0.95
        assert "2024" in found.source_text
    
    @pytest.mark.asyncio
    async def test_delete_edge(self, uow, test_user):
        """Test deleting an edge."""
        # Create nodes
        source = KGNode(
            id=str(uuid.uuid4()),
            user_id=test_user.uuid,
            label="PERSON",
            properties={"name": "Grace"},
            confidence=0.95,
            source_text="Grace is a person",
            is_current=True,
        )
        target = KGNode(
            id=str(uuid.uuid4()),
            user_id=test_user.uuid,
            label="HOBBY",
            properties={"name": "Photography"},
            confidence=0.9,
            source_text="Photography is a hobby",
            is_current=True,
        )
        
        await uow.kg_nodes.create(source)
        await uow.kg_nodes.create(target)
        
        edge = KGEdge(
            id=str(uuid.uuid4()),
            user_id=test_user.uuid,
            source_id=source.id,
            target_id=target.id,
            relation_type="ENJOYS",
            source_text="Grace enjoys photography",
            confidence=0.85,
            is_current=True,
        )
        
        await uow.kg_edges.create(edge)
        await uow.commit()
        
        # Delete the edge
        success = await uow.kg_edges.delete(edge.id)
        await uow.commit()
        
        assert success is True
        
        # Verify it's gone
        found = await uow.kg_edges.get_by_id(edge.id)
        assert found is None
    
    @pytest.mark.asyncio
    async def test_list_edges(self, uow, test_user):
        """Test listing edges with filters."""
        # Create nodes
        person = KGNode(
            id=str(uuid.uuid4()),
            user_id=test_user.uuid,
            label="PERSON",
            properties={"name": "Henry"},
            confidence=0.95,
            source_text="Henry is a person",
            is_current=True,
        )
        await uow.kg_nodes.create(person)
        
        # Create multiple target nodes and edges
        for i in range(3):
            target = KGNode(
                id=str(uuid.uuid4()),
                user_id=test_user.uuid,
                label="INTEREST",
                properties={"name": f"Interest {i}"},
                confidence=0.9,
                source_text=f"Interest {i} exists",
                is_current=True,
            )
            await uow.kg_nodes.create(target)
            
            edge = KGEdge(
                id=str(uuid.uuid4()),
                user_id=test_user.uuid,
                source_id=person.id,
                target_id=target.id,
                relation_type="INTERESTED_IN" if i < 2 else "LOVES",
                source_text=f"Henry is interested in Interest {i}",
                confidence=0.85,
                is_current=True,
            )
            await uow.kg_edges.create(edge)
        
        await uow.commit()
        
        # List all edges for user
        all_edges = await uow.kg_edges.list(filters={"user_uuid": test_user.uuid})
        assert len(all_edges) >= 3
        
        # List only INTERESTED_IN edges
        interested_edges = await uow.kg_edges.list(filters={"user_uuid": test_user.uuid, "relation_type": "INTERESTED_IN"})
        assert len(interested_edges) >= 2
    
    @pytest.mark.asyncio
    async def test_count_edges(self, uow, test_user):
        """Test counting edges."""
        # Create nodes
        person = KGNode(
            id=str(uuid.uuid4()),
            user_id=test_user.uuid,
            label="PERSON",
            properties={"name": "Iris"},
            confidence=0.95,
            source_text="Iris is a person",
            is_current=True,
        )
        await uow.kg_nodes.create(person)
        
        # Create multiple edges
        for i in range(3):
            target = KGNode(
                id=str(uuid.uuid4()),
                user_id=test_user.uuid,
                label="SKILL",
                properties={"name": f"Skill {i}"},
                confidence=0.9,
                source_text=f"Skill {i} exists",
                is_current=True,
            )
            await uow.kg_nodes.create(target)
            
            edge = KGEdge(
                id=str(uuid.uuid4()),
                user_id=test_user.uuid,
                source_id=person.id,
                target_id=target.id,
                relation_type="HAS_SKILL",
                source_text=f"Iris has Skill {i}",
                confidence=0.85,
                is_current=True,
            )
            await uow.kg_edges.create(edge)
        
        await uow.commit()
        
        # Count all edges for user
        count = await uow.kg_edges.count(filters={"user_uuid": test_user.uuid})
        assert count >= 3
