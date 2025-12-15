"""
Skills Communication Coverage Tests

Tests for communication skills to improve coverage.
Follows patterns from existing agency tests.
"""

import pytest
from datetime import datetime, UTC
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

from aico.ai.agency.skills.communication.ask_user import AskUserSkill
from aico.ai.agency.skills.communication.initiate import InitiateConversationSkill


@pytest.mark.asyncio
class TestAskUserSkill:
    """Test suite for AskUserSkill."""
    
    async def test_skill_properties(self, test_db):
        """Test skill has correct properties."""
        skill = AskUserSkill(db=test_db)
        
        assert skill.skill_id == "ask_user"
        assert skill.name == "Ask User"
        assert "question" in skill.description.lower()
        assert skill.category == "communication"
        assert len(skill.parameters) == 4
        
        param_names = [p.name for p in skill.parameters]
        assert "question" in param_names
        assert "context" in param_names
        assert "urgency" in param_names
        assert "expected_answer_type" in param_names
    
    async def test_ask_user_basic_question(self, test_db, test_user):
        """Test asking user a basic question."""
        skill = AskUserSkill(db=test_db)
        
        with patch('aico.core.bus.MessageBusClient') as mock_bus:
            mock_instance = AsyncMock()
            mock_bus.return_value = mock_instance
            
            result = await skill.execute(
                user_id=test_user,
                input_data={"question": "What is your favorite color?"},
                context={}
            )
            
            assert result.success is True
            assert result.output["question"] == "What is your favorite color?"
            assert result.output["status"] == "pending"
            assert "initiation_id" in result.output
            assert "conversation_id" in result.output
    
    async def test_ask_user_with_context(self, test_db, test_user):
        """Test asking user with context."""
        skill = AskUserSkill(db=test_db)
        
        with patch('aico.core.bus.MessageBusClient') as mock_bus:
            mock_instance = AsyncMock()
            mock_bus.return_value = mock_instance
            
            result = await skill.execute(
                user_id=test_user,
                input_data={
                    "question": "What time works best?",
                    "context": "I need to schedule a reminder for you"
                },
                context={}
            )
            
            assert result.success is True
            assert result.output["context"] == "I need to schedule a reminder for you"
    
    async def test_ask_user_with_urgency(self, test_db, test_user):
        """Test asking user with urgency level."""
        skill = AskUserSkill(db=test_db)
        
        with patch('aico.core.bus.MessageBusClient') as mock_bus:
            mock_instance = AsyncMock()
            mock_bus.return_value = mock_instance
            
            result = await skill.execute(
                user_id=test_user,
                input_data={
                    "question": "Urgent question?",
                    "urgency": "high"
                },
                context={}
            )
            
            assert result.success is True
            assert result.output["urgency"] == "high"
    
    async def test_ask_user_with_answer_type(self, test_db, test_user):
        """Test asking user with expected answer type."""
        skill = AskUserSkill(db=test_db)
        
        with patch('aico.core.bus.MessageBusClient') as mock_bus:
            mock_instance = AsyncMock()
            mock_bus.return_value = mock_instance
            
            result = await skill.execute(
                user_id=test_user,
                input_data={
                    "question": "Do you agree?",
                    "expected_answer_type": "yes_no"
                },
                context={}
            )
            
            assert result.success is True
            assert result.output["expected_answer_type"] == "yes_no"
    
    async def test_ask_user_without_question(self, test_db, test_user):
        """Test asking user without question fails."""
        skill = AskUserSkill(db=test_db)
        
        result = await skill.execute(
            user_id=test_user,
            input_data={},
            context={}
        )
        
        assert result.success is False
        assert "required" in result.error.lower()
    
    async def test_ask_user_without_database(self, test_user):
        """Test asking user without database fails."""
        skill = AskUserSkill(db=None)
        
        result = await skill.execute(
            user_id=test_user,
            input_data={"question": "Test?"},
            context={}
        )
        
        assert result.success is False
        assert "database" in result.error.lower()
    
    async def test_ask_user_stores_in_database(self, test_db, test_user):
        """Test that question is stored in database."""
        skill = AskUserSkill(db=test_db)
        
        with patch('aico.core.bus.MessageBusClient') as mock_bus:
            mock_instance = AsyncMock()
            mock_bus.return_value = mock_instance
            
            result = await skill.execute(
                user_id=test_user,
                input_data={"question": "Test question?"},
                context={}
            )
            
            assert result.success is True
            
            # Verify stored in database
            row = test_db.execute(
                "SELECT * FROM aico_conversation_initiations WHERE initiation_id = ?",
                (result.output["initiation_id"],)
            ).fetchone()
            
            assert row is not None
            assert row["question"] == "Test question?"
            assert row["resolution_status"] == "pending"
    
    async def test_ask_user_defaults(self, test_db, test_user):
        """Test that default values are used."""
        skill = AskUserSkill(db=test_db)
        
        with patch('aico.core.bus.MessageBusClient') as mock_bus:
            mock_instance = AsyncMock()
            mock_bus.return_value = mock_instance
            
            result = await skill.execute(
                user_id=test_user,
                input_data={"question": "Test?"},
                context={}
            )
            
            assert result.success is True
            assert result.output["urgency"] == "medium"
            assert result.output["expected_answer_type"] == "text"
            assert result.output["context"] == ""


@pytest.mark.asyncio
class TestInitiateConversationSkill:
    """Test suite for InitiateConversationSkill."""
    
    async def test_skill_properties(self, test_db):
        """Test skill has correct properties."""
        skill = InitiateConversationSkill(db=test_db)
        
        assert skill.skill_id == "initiate_conversation"
        assert skill.name == "Initiate Conversation"
        assert "conversation" in skill.description.lower()
        assert skill.category == "communication"
        assert len(skill.parameters) >= 2
        
        param_names = [p.name for p in skill.parameters]
        assert "topic" in param_names
        assert "message" in param_names
    
    async def test_initiate_basic_conversation(self, test_db, test_user):
        """Test initiating a basic conversation."""
        skill = InitiateConversationSkill(db=test_db)
        
        with patch('aico.core.bus.MessageBusClient') as mock_bus:
            mock_instance = AsyncMock()
            mock_bus.return_value = mock_instance
            
            result = await skill.execute(
                user_id=test_user,
                input_data={
                    "topic": "greeting",
                    "message": "Hello! How are you today?"
                },
                context={}
            )
            
            assert result.success is True
            assert "initiation_id" in result.output
    
    async def test_initiate_without_topic(self, test_db, test_user):
        """Test initiating conversation without topic fails."""
        skill = InitiateConversationSkill(db=test_db)
        
        result = await skill.execute(
            user_id=test_user,
            input_data={"message": "Hello"},
            context={}
        )
        
        assert result.success is False
    
    async def test_initiate_without_database(self, test_user):
        """Test initiating conversation without database fails."""
        skill = InitiateConversationSkill(db=None)
        
        result = await skill.execute(
            user_id=test_user,
            input_data={"topic": "test", "message": "Hello"},
            context={}
        )
        
        assert result.success is False
        assert "database" in result.error.lower()
