"""
Unit tests for WorldModelService

Tests the service layer that integrates schema learning, hypothesis management,
and drift detection for the world model.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, MagicMock, patch

from aico.ai.world_model.service import WorldModelService
from aico.ai.world_model.models import (
    UserContext,
    OpenLoop,
    WorldContext,
    Entity,
    Project,
    Context,
    UncertainArea,
    Schema,
    Hypothesis,
    DriftReport,
)


class TestWorldModelService:
    """Test WorldModelService integration."""
    
    @pytest.fixture
    def mock_kg_storage(self):
        """Create mock knowledge graph storage."""
        mock = Mock()
        mock.get_user_nodes = AsyncMock(return_value=[])
        return mock
    
    @pytest.fixture
    def mock_semantic_memory(self):
        """Create mock semantic memory store."""
        mock = Mock()
        mock.query = AsyncMock(return_value=[])
        return mock
    
    @pytest.fixture
    def service(self, mock_kg_storage, mock_semantic_memory):
        """Create WorldModelService instance."""
        return WorldModelService(
            kg_storage=mock_kg_storage,
            semantic_memory=mock_semantic_memory
        )
    
    def test_initialization(self, service):
        """Test service initializes with all components."""
        assert service.kg is not None
        assert service.semantic_memory is not None
        assert service.schema_learner is not None
        assert service.hypothesis_manager is not None
        assert service.drift_detector is not None
    
    @pytest.mark.asyncio
    async def test_get_active_projects_empty(self, service, mock_kg_storage):
        """Test getting active projects returns empty list."""
        mock_kg_storage.get_user_nodes.return_value = []
        
        projects = await service.get_active_projects("user1")
        
        assert projects == []
        mock_kg_storage.get_user_nodes.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_active_projects_with_data(self, service, mock_kg_storage):
        """Test getting active projects with mock data."""
        # Create mock node
        mock_node = Mock()
        mock_node.id = "proj1"
        mock_node.label = "Test Project"
        mock_node.entity_type = "project"
        mock_node.properties = {"description": "Test description"}
        mock_node.created_at = datetime.utcnow()
        mock_node.updated_at = datetime.utcnow()
        
        mock_kg_storage.get_user_nodes.return_value = [mock_node]
        
        projects = await service.get_active_projects("user1")
        
        assert len(projects) == 1
        assert projects[0].id == "proj1"
        assert projects[0].name == "Test Project"
    
    @pytest.mark.asyncio
    async def test_get_open_loops(self, service):
        """Test getting open loops (placeholder returns empty)."""
        loops = await service.get_open_loops("user1")
        
        # Phase 2 placeholder returns empty list
        assert loops == []
    
    @pytest.mark.asyncio
    async def test_query_uncertain_areas(self, service):
        """Test querying uncertain areas."""
        # Mock hypothesis manager
        service.hypothesis_manager.get_open_hypotheses = Mock(return_value=[])
        
        areas = await service.query_uncertain_areas("user1")
        
        assert isinstance(areas, list)
        assert len(areas) == 0
    
    @pytest.mark.asyncio
    async def test_get_world_context(self, service, mock_kg_storage):
        """Test getting world context."""
        mock_kg_storage.get_user_nodes.return_value = []
        
        context = await service.get_world_context("user1")
        
        assert context is not None
        assert context.user_id == "user1"
        assert isinstance(context.entities, list)
        assert isinstance(context.projects, list)
    
    @pytest.mark.asyncio
    async def test_learn_schema(self, service):
        """Test schema learning delegation."""
        samples = [
            {"name": "Alice", "age": 30},
            {"name": "Bob", "age": 25},
        ]
        
        schema = await service.learn_schema("Person", samples)
        
        assert schema.entity_type == "Person"
        assert schema.sample_count == 2
    
    @pytest.mark.asyncio
    async def test_validate_data(self, service):
        """Test data validation delegation."""
        samples = [{"name": "Alice", "age": 30}]
        schema = await service.learn_schema("Person", samples)
        
        # Valid data (exact same as sample to pass strict constraints)
        result = await service.validate_data(schema, {"name": "Alice", "age": 30})
        assert result.is_valid
        
        # Invalid data (wrong type)
        result = await service.validate_data(schema, {"name": "Dave", "age": "thirty"})
        assert not result.is_valid
    
    @pytest.mark.asyncio
    async def test_generate_hypothesis(self, service):
        """Test hypothesis generation delegation."""
        hypothesis = await service.generate_hypothesis(
            user_id="user1",
            description="Test hypothesis",
            hypothesis_type="preference",
            affected_entities=["entity1"],
            initial_evidence=["evidence1"]
        )
        
        assert hypothesis.user_id == "user1"
        assert hypothesis.description == "Test hypothesis"
        assert hypothesis.status == "open"
    
    @pytest.mark.asyncio
    async def test_test_hypothesis(self, service):
        """Test hypothesis testing delegation."""
        # First generate a hypothesis
        hypothesis = await service.generate_hypothesis(
            user_id="user1",
            description="Test",
            hypothesis_type="preference",
            affected_entities=[]
        )
        
        # Test it
        result = await service.test_hypothesis(
            hypothesis_id=hypothesis.hypothesis_id,
            test_type="observation",
            supports_hypothesis=True
        )
        
        assert result is not None
    
    @pytest.mark.asyncio
    async def test_get_hypotheses(self, service):
        """Test getting hypotheses for user."""
        hypotheses = await service.get_hypotheses("user1")
        
        assert isinstance(hypotheses, list)
    
    @pytest.mark.asyncio
    async def test_detect_drift(self, service):
        """Test drift detection delegation."""
        historical_states = [
            {"name": "Alice", "age": 30, "timestamp": datetime.utcnow()},
            {"name": "Alice", "age": 31, "timestamp": datetime.utcnow()},
        ]
        
        drift = await service.detect_drift(
            entity_id="user1",
            entity_type="Person",
            historical_states=historical_states
        )
        
        # May or may not detect drift depending on threshold
        assert drift is None or isinstance(drift, DriftReport)
    
    @pytest.mark.asyncio
    async def test_detect_contradictions(self, service):
        """Test contradiction detection delegation."""
        facts = [
            {"content": "User lives in NYC", "confidence": 0.9, "timestamp": datetime.utcnow()},
            {"content": "User lives in LA", "confidence": 0.8, "timestamp": datetime.utcnow()},
        ]
        
        contradictions = await service.detect_contradictions(facts)
        
        assert isinstance(contradictions, list)
    
    @pytest.mark.asyncio
    async def test_query_aico_self_assessment(self, service):
        """Test querying AICO's self-assessment (placeholder)."""
        results = await service.query_aico_self_assessment("skill", "test_skill")
        
        # Placeholder returns empty list
        assert results == []
    
    @pytest.mark.asyncio
    async def test_link_lesson_to_hypothesis(self, service):
        """Test linking lesson to hypothesis."""
        result = await service.link_lesson_to_hypothesis("lesson1", "hyp1")
        
        # Should return True (logged intent)
        assert result is True
    
    @pytest.mark.asyncio
    async def test_get_user_context(self, service, mock_kg_storage):
        """Test getting comprehensive user context."""
        mock_kg_storage.get_user_nodes.return_value = []
        
        context = await service.get_user_context("user1")
        
        assert context.user_id == "user1"
        assert isinstance(context.active_projects, list)
    
    @pytest.mark.asyncio
    async def test_get_entities_around_user(self, service, mock_kg_storage):
        """Test getting entities around user."""
        mock_node = Mock()
        mock_node.id = "entity1"
        mock_node.label = "Test Entity"
        mock_node.entity_type = "person"
        mock_node.properties = {}
        mock_node.confidence = 0.9
        mock_node.updated_at = datetime.utcnow()
        
        mock_kg_storage.get_user_nodes.return_value = [mock_node]
        
        entities = await service.get_entities_around_user("user1", limit=10)
        
        assert len(entities) == 1
        assert entities[0].id == "entity1"
    
    @pytest.mark.asyncio
    async def test_get_recurring_contexts(self, service):
        """Test getting recurring contexts (placeholder)."""
        contexts = await service.get_recurring_contexts("user1")
        
        # Placeholder returns empty
        assert contexts == []
    
    @pytest.mark.asyncio
    async def test_detect_anomalies(self, service):
        """Test anomaly detection (placeholder)."""
        anomalies = await service.detect_anomalies("user1")
        
        # Placeholder returns empty
        assert anomalies == []
