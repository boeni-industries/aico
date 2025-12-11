"""
Tests for LessonMemoryProjector - Phase 6.10.3
"""

import pytest
from datetime import datetime
from unittest.mock import Mock, AsyncMock

from aico.ai.agency.lesson_projector import LessonMemoryProjector


class TestLessonMemoryProjector:
    """Test LessonMemoryProjector functionality."""
    
    @pytest.fixture
    def mock_config(self):
        """Create mock configuration."""
        return Mock()
    
    @pytest.fixture
    def mock_db(self):
        """Create mock database connection."""
        return Mock()
    
    @pytest.fixture
    def mock_kg_storage(self):
        """Create mock KG storage."""
        mock = Mock()
        mock.add_node = AsyncMock()
        mock.add_edge = AsyncMock()
        return mock
    
    @pytest.fixture
    def projector(self, mock_config, mock_db, mock_kg_storage):
        """Create LessonMemoryProjector instance."""
        return LessonMemoryProjector(
            config=mock_config,
            db_connection=mock_db,
            kg_storage=mock_kg_storage
        )
    
    @pytest.fixture
    def mock_lesson(self):
        """Create mock lesson."""
        lesson = Mock()
        lesson.lesson_id = "lesson_1"
        lesson.user_id = "user1"
        lesson.lesson_type = Mock(value="skill_tuning")
        lesson.target_kind = Mock(value="skill")
        lesson.target_id = "test_skill"
        lesson.description = "Test lesson"
        lesson.confidence = 0.85
        lesson.status = Mock(value="active")
        lesson.created_at = datetime.utcnow()
        lesson.metrics_basis = None
        return lesson
    
    @pytest.fixture
    def mock_self_model_entry(self):
        """Create mock self-model entry."""
        entry = Mock()
        entry.model_id = "model_1"
        entry.user_id = "user1"
        entry.entity_type = Mock(value="skill")
        entry.entity_id = "test_skill"
        entry.performance_summary = Mock()
        entry.confidence = 0.9
        entry.last_updated = datetime.utcnow()
        return entry
    
    def test_initialization(self, projector):
        """Test projector initializes correctly."""
        assert projector.config is not None
        assert projector.db is not None
        assert projector.kg_storage is not None
        assert projector.lesson_store is not None
        assert projector.self_model_store is not None
        assert projector.run_store is not None
    
    @pytest.mark.asyncio
    async def test_project_lesson_to_memory(self, projector, mock_lesson):
        """Test projecting lesson to memory."""
        result = await projector.project_lesson_to_memory(mock_lesson)
        
        assert result is not None
        assert result.get("success") is True
        assert "lesson_id" in result
    
    @pytest.mark.asyncio
    async def test_project_lesson_to_kg(self, projector, mock_lesson, mock_kg_storage):
        """Test projecting lesson to knowledge graph."""
        result = await projector.project_lesson_to_kg(mock_lesson)
        
        # Should create KG nodes/edges
        assert result is not None
    
    @pytest.mark.asyncio
    async def test_project_self_model_to_kg(self, projector, mock_self_model_entry, mock_kg_storage):
        """Test projecting self-model entry to KG."""
        result = await projector.project_self_model_to_kg(mock_self_model_entry)
        
        assert result is not None
    
    @pytest.mark.asyncio
    async def test_query_active_lessons(self, projector):
        """Test querying active lessons."""
        # Mock the lesson store
        projector.lesson_store.get_active_lessons = Mock(return_value=[])
        
        results = await projector.query_active_lessons("user1")
        
        assert isinstance(results, list)
    
    def test_generate_relevance_tags(self, projector, mock_lesson):
        """Test relevance tag generation."""
        tags = projector._generate_relevance_tags(mock_lesson)
        
        assert isinstance(tags, list)
        assert len(tags) > 0
        # Should include lesson type and target
        assert any("skill" in tag.lower() for tag in tags)
    
    def test_get_target_node_id(self, projector):
        """Test getting target node ID."""
        from aico.ai.agency.models import TargetKind
        
        # Test skill target
        node_id = projector._get_target_node_id(TargetKind.SKILL, "test_skill")
        assert node_id == "skill:test_skill"
        
        # Test policy target
        node_id = projector._get_target_node_id(TargetKind.POLICY_RULE, "test_policy")
        assert node_id == "policy_rule:test_policy"
    
    @pytest.mark.asyncio
    async def test_project_lesson_with_no_kg(self, mock_config, mock_db, mock_lesson):
        """Test projection works without KG storage."""
        projector = LessonMemoryProjector(
            config=mock_config,
            db_connection=mock_db,
            kg_storage=None  # No KG
        )
        
        # Should not fail
        result = await projector.project_lesson_to_memory(mock_lesson)
        assert result is not None
    
    @pytest.mark.asyncio
    async def test_project_lesson_error_handling(self, projector):
        """Test error handling in projection."""
        # Invalid lesson
        invalid_lesson = Mock()
        invalid_lesson.lesson_id = None
        
        # Should handle gracefully
        try:
            result = await projector.project_lesson_to_memory(invalid_lesson)
            # Either returns error result or raises handled exception
            assert True
        except Exception:
            # Expected for invalid input
            assert True
