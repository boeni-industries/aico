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
from aico.data.postgres.connection import get_session_factory
from aico.data.uow import UnitOfWork

@pytest.fixture
async def session_factory():
    return await get_session_factory()


@pytest.mark.asyncio
class TestAskUserSkill:
    """Test suite for AskUserSkill."""
    
    async def test_skill_properties(self, session_factory):
        """Test skill has correct properties."""
        skill = AskUserSkill(session_factory=session_factory)
        
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
    
    async def test_ask_user_basic_question(self, session_factory, test_user):
        """Test asking user a basic question."""
        skill = AskUserSkill(session_factory=session_factory)
        
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
            assert "interaction_id" in result.output
            assert "correlation_id" in result.output
    
    async def test_ask_user_with_context(self, session_factory, test_user):
        """Test asking user with context."""
        skill = AskUserSkill(session_factory=session_factory)
        
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
    
    async def test_ask_user_with_urgency(self, session_factory, test_user):
        """Test asking user with urgency level."""
        skill = AskUserSkill(session_factory=session_factory)
        
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
    
    async def test_ask_user_with_answer_type(self, session_factory, test_user):
        """Test asking user with expected answer type."""
        skill = AskUserSkill(session_factory=session_factory)
        
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
    
    async def test_ask_user_without_question(self, session_factory, test_user):
        """Test asking user without question fails."""
        skill = AskUserSkill(session_factory=session_factory)
        
        result = await skill.execute(
            user_id=test_user,
            input_data={},
            context={}
        )
        
        assert result.success is False
        assert "required" in result.error.lower()
    
    async def test_ask_user_without_database(self, test_user):
        """Test asking user without database fails."""
        skill = AskUserSkill(session_factory=None)
        
        result = await skill.execute(
            user_id=test_user,
            input_data={"question": "Test?"},
            context={}
        )
        
        assert result.success is False
        assert "session_factory" in result.error.lower()
    
    async def test_ask_user_stores_in_database(self, session_factory, test_user):
        """Test that question is stored in database."""
        skill = AskUserSkill(session_factory=session_factory)
        
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
            async with UnitOfWork(session_factory) as uow:
                row = await uow.interaction_requests.get_by_id(result.output["interaction_id"])
            
            assert row is not None
            assert row.prompt == "Test question?"
            assert row.status == "pending"
    
    async def test_ask_user_defaults(self, session_factory, test_user):
        """Test that default values are used."""
        skill = AskUserSkill(session_factory=session_factory)
        
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
    
    async def test_skill_properties(self, session_factory):
        """Test skill has correct properties."""
        skill = InitiateConversationSkill(session_factory=session_factory)
        
        assert skill.skill_id == "initiate_conversation"
        assert skill.name == "Initiate Conversation"
        assert "conversation" in skill.description.lower()
        assert skill.category == "communication"
        assert len(skill.parameters) >= 2
        
        param_names = [p.name for p in skill.parameters]
        assert "topic" in param_names
        assert "message" in param_names
    
    async def test_initiate_basic_conversation(self, session_factory, test_user):
        """Test initiating a basic conversation."""
        skill = InitiateConversationSkill(session_factory=session_factory)
        
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
            assert "interaction_id" in result.output
    
    async def test_initiate_without_topic(self, session_factory, test_user):
        """Test initiating conversation without topic fails."""
        skill = InitiateConversationSkill(session_factory=session_factory)
        
        result = await skill.execute(
            user_id=test_user,
            input_data={"message": "Hello"},
            context={}
        )
        
        assert result.success is False
    
    async def test_initiate_without_database(self, test_user):
        """Test initiating conversation without database fails."""
        skill = InitiateConversationSkill(session_factory=None)
        
        result = await skill.execute(
            user_id=test_user,
            input_data={"topic": "test", "message": "Hello"},
            context={}
        )
        
        assert result.success is False
        assert "session_factory" in result.error.lower()
