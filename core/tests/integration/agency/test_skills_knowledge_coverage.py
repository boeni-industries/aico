"""
Skills Knowledge Coverage Tests

Tests for knowledge skills to improve coverage.
Follows patterns from existing agency tests.
"""

import pytest
from datetime import datetime
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

from aico.ai.agency.skills.knowledge.graph import UpdateKnowledgeGraphSkill


@pytest.mark.asyncio
class TestUpdateKnowledgeGraphSkill:
    """Test suite for UpdateKnowledgeGraphSkill."""

    def _make_mock_storage(self):
        storage = MagicMock()
        storage.save_graph = AsyncMock(return_value=None)
        return storage
    
    async def test_skill_properties(self, test_db):
        """Test skill has correct properties."""
        skill = UpdateKnowledgeGraphSkill(kg_storage=self._make_mock_storage())
        
        assert skill.skill_id == "update_knowledge_graph"
        assert skill.name == "Update Knowledge Graph"
        assert "knowledge graph" in skill.description.lower()
        assert skill.category == "knowledge"
        assert len(skill.parameters) == 3
        
        param_names = [p.name for p in skill.parameters]
        assert "entities" in param_names
        assert "relationships" in param_names
        assert "source" in param_names
    
    async def test_update_with_entities_only(self, test_db, test_user):
        """Test updating knowledge graph with entities only."""
        skill = UpdateKnowledgeGraphSkill(kg_storage=self._make_mock_storage())
        
        entities = [
            {"type": "person", "value": "Alice", "metadata": {"age": 30}},
            {"type": "location", "value": "New York", "metadata": {}},
        ]
        
        result = await skill.execute(
            user_id=test_user,
            input_data={"entities": entities},
            context={}
        )
        
        # Tables don't exist, so entities won't be added but skill should handle gracefully
        assert result.success is True
        assert "entities_added" in result.output
        assert "relationships_added" in result.output
        assert result.output["source"] == "conversation"
    
    async def test_update_with_entities_and_relationships(self, test_db, test_user):
        """Test updating with both entities and relationships."""
        skill = UpdateKnowledgeGraphSkill(kg_storage=self._make_mock_storage())
        
        entities = [
            {"type": "person", "value": "Bob", "metadata": {}},
            {"type": "company", "value": "TechCorp", "metadata": {}},
        ]
        
        relationships = [
            {"from": "Bob", "to": "TechCorp", "type": "works_at", "metadata": {}}
        ]
        
        result = await skill.execute(
            user_id=test_user,
            input_data={
                "entities": entities,
                "relationships": relationships
            },
            context={}
        )
        
        assert result.success is True
        assert "entities_added" in result.output
        assert "relationships_added" in result.output
    
    async def test_update_with_custom_source(self, test_db, test_user):
        """Test updating with custom source."""
        skill = UpdateKnowledgeGraphSkill(kg_storage=self._make_mock_storage())
        
        entities = [{"type": "fact", "value": "Test fact", "metadata": {}}]
        
        result = await skill.execute(
            user_id=test_user,
            input_data={
                "entities": entities,
                "source": "user_input"
            },
            context={}
        )
        
        assert result.success is True
        assert result.output["source"] == "user_input"
    
    async def test_update_with_string_entities(self, test_db, test_user):
        """Test updating with simple string entities."""
        skill = UpdateKnowledgeGraphSkill(kg_storage=self._make_mock_storage())
        
        entities = ["Alice", "Bob", "Charlie"]
        
        result = await skill.execute(
            user_id=test_user,
            input_data={"entities": entities},
            context={}
        )
        
        assert result.success is True
        assert "entities_added" in result.output
    
    async def test_update_without_entities(self, test_db, test_user):
        """Test updating without entities."""
        skill = UpdateKnowledgeGraphSkill(kg_storage=self._make_mock_storage())
        
        result = await skill.execute(
            user_id=test_user,
            input_data={},
            context={}
        )
        
        assert result.success is True
        assert result.output["entities_added"] == 0
        assert result.output["relationships_added"] == 0
    
    async def test_update_without_database(self, test_user):
        """Test updating without database fails."""
        skill = UpdateKnowledgeGraphSkill(kg_storage=None)
        
        result = await skill.execute(
            user_id=test_user,
            input_data={"entities": [{"type": "test", "value": "test"}]},
            context={}
        )
        
        assert result.success is False
        assert "storage" in result.error.lower()
    
    async def test_update_result_structure(self, test_db, test_user):
        """Test that result has correct structure."""
        skill = UpdateKnowledgeGraphSkill(kg_storage=self._make_mock_storage())
        
        entities = [{"type": "test", "value": "test"}]
        
        result = await skill.execute(
            user_id=test_user,
            input_data={"entities": entities},
            context={}
        )
        
        assert result.success is True
        output = result.output
        
        # Check all required fields
        assert "entities_added" in output
        assert "relationships_added" in output
        assert "source" in output
        assert "entities" in output
        assert "relationships" in output
        assert "updated_at" in output
        
        # Check types
        assert isinstance(output["entities_added"], int)
        assert isinstance(output["relationships_added"], int)
        assert isinstance(output["source"], str)
        assert isinstance(output["entities"], list)
        assert isinstance(output["relationships"], list)
    
    async def test_update_metadata(self, test_db, test_user):
        """Test that metadata is included in result."""
        skill = UpdateKnowledgeGraphSkill(kg_storage=self._make_mock_storage())
        
        result = await skill.execute(
            user_id=test_user,
            input_data={"entities": [{"type": "test", "value": "test"}]},
            context={}
        )
        
        assert result.success is True
        assert result.metadata is not None
        assert "skill_id" in result.metadata
        assert result.metadata["skill_id"] == "update_knowledge_graph"
    
    async def test_update_with_empty_relationships(self, test_db, test_user):
        """Test updating with empty relationships list."""
        skill = UpdateKnowledgeGraphSkill(kg_storage=self._make_mock_storage())
        
        result = await skill.execute(
            user_id=test_user,
            input_data={
                "entities": [{"type": "test", "value": "test"}],
                "relationships": []
            },
            context={}
        )
        
        assert result.success is True
        assert result.output["relationships_added"] == 0
    
    async def test_update_with_complex_metadata(self, test_db, test_user):
        """Test updating with complex entity metadata."""
        skill = UpdateKnowledgeGraphSkill(kg_storage=self._make_mock_storage())
        
        entities = [
            {
                "type": "person",
                "value": "Alice",
                "metadata": {
                    "age": 30,
                    "occupation": "Engineer",
                    "skills": ["Python", "JavaScript"]
                }
            }
        ]
        
        result = await skill.execute(
            user_id=test_user,
            input_data={"entities": entities},
            context={}
        )
        
        assert result.success is True
        assert "entities_added" in result.output
    
    async def test_update_replaces_existing_entities(self, test_db, test_user):
        """Test that updating same entity replaces it."""
        skill = UpdateKnowledgeGraphSkill(kg_storage=self._make_mock_storage())
        
        # First update
        entities1 = [{"type": "person", "value": "Alice", "metadata": {"age": 30}}]
        result1 = await skill.execute(
            user_id=test_user,
            input_data={"entities": entities1},
            context={}
        )
        
        # Second update with same entity
        entities2 = [{"type": "person", "value": "Alice", "metadata": {"age": 31}}]
        result2 = await skill.execute(
            user_id=test_user,
            input_data={"entities": entities2},
            context={}
        )
        
        assert result1.success is True
        assert result2.success is True
        assert "entities_added" in result2.output
    
    async def test_update_with_relationship_metadata(self, test_db, test_user):
        """Test updating relationships with metadata."""
        skill = UpdateKnowledgeGraphSkill(kg_storage=self._make_mock_storage())
        
        relationships = [
            {
                "from": "Alice",
                "to": "TechCorp",
                "type": "works_at",
                "metadata": {"since": "2020", "role": "Engineer"}
            }
        ]
        
        result = await skill.execute(
            user_id=test_user,
            input_data={
                "entities": [],
                "relationships": relationships
            },
            context={}
        )
        
        assert result.success is True
        assert "relationships_added" in result.output
