"""
Skills Analysis Coverage Tests

Tests for analysis skills to improve coverage.
Follows patterns from existing agency tests.
"""

import pytest
from datetime import datetime, timedelta, UTC
import uuid
from unittest.mock import AsyncMock, MagicMock

from aico.ai.agency.skills.analysis.conversation import AnalyzeConversationSkill


@pytest.mark.asyncio
class TestAnalyzeConversationSkill:
    """Test suite for AnalyzeConversationSkill."""
    
    async def test_skill_properties(self, test_db):
        """Test skill has correct properties."""
        skill = AnalyzeConversationSkill(db=test_db, memory_manager=None)
        
        assert skill.skill_id == "analyze_conversation"
        assert skill.name == "Analyze Conversation"
        assert "insights" in skill.description.lower()
        assert skill.category == "analysis"
        assert len(skill.parameters) == 2
        
        param_names = [p.name for p in skill.parameters]
        assert "conversation_limit" in param_names
        assert "focus_areas" in param_names
    
    async def test_analyze_with_memory_manager(self, test_db, test_user):
        """Test analysis with memory manager."""
        mock_memory = MagicMock()
        skill = AnalyzeConversationSkill(db=test_db, memory_manager=mock_memory)
        
        result = await skill.execute(
            user_id=test_user,
            input_data={"conversation_limit": 10},
            context={}
        )
        
        assert result.success is True
        assert result.output["conversation_count"] == 0
        assert "implementation" in result.output["note"].lower()
        assert len(result.output["insights"]) > 0
    
    async def test_analyze_without_memory_manager(self, test_db, test_user):
        """Test analysis without memory manager raises error."""
        skill = AnalyzeConversationSkill(db=test_db, memory_manager=None)
        
        result = await skill.execute(
            user_id=test_user,
            input_data={"conversation_limit": 10},
            context={}
        )
        
        assert result.success is False
        assert "memory manager" in result.error.lower()
    
    async def test_analyze_with_custom_limit(self, test_db, test_user):
        """Test analysis with custom conversation limit."""
        mock_memory = MagicMock()
        skill = AnalyzeConversationSkill(db=test_db, memory_manager=mock_memory)
        
        result = await skill.execute(
            user_id=test_user,
            input_data={"conversation_limit": 5},
            context={}
        )
        
        assert result.success is True
        assert result.output["focus_areas_analyzed"] == ["preferences", "patterns"]
    
    async def test_analyze_with_custom_focus_areas(self, test_db, test_user):
        """Test analysis with custom focus areas."""
        mock_memory = MagicMock()
        skill = AnalyzeConversationSkill(db=test_db, memory_manager=mock_memory)
        
        result = await skill.execute(
            user_id=test_user,
            input_data={"focus_areas": ["topics", "sentiment"]},
            context={}
        )
        
        assert result.success is True
        assert result.output["focus_areas_analyzed"] == ["topics", "sentiment"]
    
    async def test_analyze_result_structure(self, test_db, test_user):
        """Test that analysis result has correct structure."""
        mock_memory = MagicMock()
        skill = AnalyzeConversationSkill(db=test_db, memory_manager=mock_memory)
        
        result = await skill.execute(
            user_id=test_user,
            input_data={},
            context={}
        )
        
        assert result.success is True
        output = result.output
        
        # Check all required fields
        assert "conversation_count" in output
        assert "total_messages_analyzed" in output
        assert "focus_areas_analyzed" in output
        assert "insights" in output
        assert "patterns" in output
        assert "topics" in output
        assert "analyzed_at" in output
        
        # Check types
        assert isinstance(output["conversation_count"], int)
        assert isinstance(output["total_messages_analyzed"], int)
        assert isinstance(output["insights"], list)
        assert isinstance(output["patterns"], list)
        assert isinstance(output["topics"], list)
    
    async def test_analyze_metadata(self, test_db, test_user):
        """Test that metadata is included in result."""
        mock_memory = MagicMock()
        skill = AnalyzeConversationSkill(db=test_db, memory_manager=mock_memory)
        
        result = await skill.execute(
            user_id=test_user,
            input_data={},
            context={}
        )
        
        assert result.success is True
        assert result.metadata is not None
        assert "skill_id" in result.metadata
        assert result.metadata["skill_id"] == "analyze_conversation"
    
    async def test_analyze_initialization(self, test_db):
        """Test skill initialization with both parameters."""
        mock_memory = MagicMock()
        skill = AnalyzeConversationSkill(db=test_db, memory_manager=mock_memory)
        
        assert skill.db == test_db
        assert skill.memory_manager == mock_memory
    
    async def test_analyze_parameters_defaults(self, test_db, test_user):
        """Test that default parameters are used when not provided."""
        mock_memory = MagicMock()
        skill = AnalyzeConversationSkill(db=test_db, memory_manager=mock_memory)
        
        result = await skill.execute(
            user_id=test_user,
            input_data={},  # No parameters provided
            context={}
        )
        
        assert result.success is True
        # Default focus areas should be used
        assert result.output["focus_areas_analyzed"] == ["preferences", "patterns"]
    
    
