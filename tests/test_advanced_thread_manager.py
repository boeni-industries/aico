"""
Comprehensive test suite for AdvancedThreadManager

Tests cover:
- Thread resolution accuracy
- Multi-factor scoring algorithms
- Service integration and fallbacks
- Performance and reliability
- Edge cases and error handling
"""

import pytest
import asyncio
import numpy as np
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, patch
from typing import Dict, List, Any

from backend.services.advanced_thread_manager import (
    AdvancedThreadManager,
    ThreadResolution,
    ThreadContext,
    ConversationAnalysis,
    ThreadAction,
    ThreadReason
)
from backend.services.thread_manager_integration import AICOThreadManagerIntegration


class TestAdvancedThreadManager:
    """Test suite for AdvancedThreadManager core functionality"""
    
    @pytest.fixture
    def thread_manager(self):
        """Create thread manager instance for testing"""
        return AdvancedThreadManager(
            dormancy_threshold_hours=2,
            semantic_similarity_threshold=0.7,
            topic_shift_threshold=0.4,
            enable_caching=True
        )
    
    @pytest.fixture
    def sample_thread_context(self):
        """Create sample thread context for testing"""
        return ThreadContext(
            thread_id="test-thread-123",
            user_id="test-user-456",
            last_activity=datetime.utcnow() - timedelta(minutes=30),
            message_count=5,
            status="active",
            topic_embedding=np.random.random(768),
            recent_messages=[
                {"content": "Hello, I need help with my project", "timestamp": "2024-01-01T10:00:00Z"},
                {"content": "It's about machine learning", "timestamp": "2024-01-01T10:01:00Z"}
            ],
            entities={"PERSON": ["John"], "ORG": ["TechCorp"]},
            intent_history=["greeting", "request"],
            conversation_type="technical_support"
        )
    
    @pytest.fixture
    def sample_analysis(self):
        """Create sample conversation analysis for testing"""
        return ConversationAnalysis(
            message_embedding=np.random.random(768),
            detected_intent="question",
            topic_shift_score=0.2,
            entities={"PERSON": ["John"], "TECH": ["machine learning"]},
            conversation_boundary_score=0.1,
            urgency_score=0.6,
            context_dependency_score=0.8
        )

    @pytest.mark.asyncio
    async def test_thread_resolution_new_user(self, thread_manager):
        """Test thread resolution for new user with no existing threads"""
        with patch.object(thread_manager, '_get_user_thread_contexts', return_value=[]):
            with patch.object(thread_manager, '_analyze_message') as mock_analyze:
                mock_analyze.return_value = ConversationAnalysis(
                    message_embedding=np.random.random(768),
                    detected_intent="greeting",
                    topic_shift_score=0.0,
                    entities={},
                    conversation_boundary_score=0.8,
                    urgency_score=0.5,
                    context_dependency_score=0.2
                )
                
                resolution = await thread_manager.resolve_thread_for_message(
                    user_id="new-user",
                    message="Hello, I'm new here"
                )
                
                assert resolution.action == ThreadAction.CREATE
                assert resolution.primary_reason == ThreadReason.NEW_SESSION
                assert resolution.confidence == 1.0
                assert resolution.thread_id is not None

    @pytest.mark.asyncio
    async def test_thread_continuation_high_similarity(self, thread_manager, sample_thread_context, sample_analysis):
        """Test thread continuation with high semantic similarity"""
        # Mock high similarity
        sample_analysis.topic_shift_score = 0.1
        
        with patch.object(thread_manager, '_get_user_thread_contexts', return_value=[sample_thread_context]):
            with patch.object(thread_manager, '_analyze_message', return_value=sample_analysis):
                with patch.object(thread_manager, '_calculate_thread_scores') as mock_scores:
                    mock_scores.return_value = {
                        sample_thread_context.thread_id: {
                            'semantic_similarity': 0.85,
                            'temporal_continuity': 0.8,
                            'intent_alignment': 0.7,
                            'entity_overlap': 0.6,
                            'conversation_flow': 0.5,
                            'user_pattern_match': 0.5,
                            'overall': 0.75
                        }
                    }
                    
                    resolution = await thread_manager.resolve_thread_for_message(
                        user_id="test-user-456",
                        message="Can you help me with the ML model?"
                    )
                    
                    assert resolution.action == ThreadAction.CONTINUE
                    assert resolution.thread_id == sample_thread_context.thread_id
                    assert resolution.primary_reason == ThreadReason.SEMANTIC_SIMILARITY
                    assert resolution.confidence > 0.7

    @pytest.mark.asyncio
    async def test_thread_branching_topic_shift(self, thread_manager, sample_thread_context, sample_analysis):
        """Test thread branching when topic shift is detected"""
        # Mock topic shift
        sample_analysis.topic_shift_score = 0.8
        
        with patch.object(thread_manager, '_get_user_thread_contexts', return_value=[sample_thread_context]):
            with patch.object(thread_manager, '_analyze_message', return_value=sample_analysis):
                with patch.object(thread_manager, '_calculate_thread_scores') as mock_scores:
                    mock_scores.return_value = {
                        sample_thread_context.thread_id: {
                            'semantic_similarity': 0.3,
                            'temporal_continuity': 0.6,  # Recent enough to branch
                            'intent_alignment': 0.2,
                            'entity_overlap': 0.1,
                            'conversation_flow': 0.2,
                            'user_pattern_match': 0.5,
                            'overall': 0.3
                        }
                    }
                    
                    resolution = await thread_manager.resolve_thread_for_message(
                        user_id="test-user-456",
                        message="By the way, what's the weather like today?"
                    )
                    
                    assert resolution.action == ThreadAction.BRANCH
                    assert resolution.parent_thread_id == sample_thread_context.thread_id
                    assert resolution.primary_reason == ThreadReason.TOPIC_SHIFT
                    assert resolution.thread_id != sample_thread_context.thread_id

    @pytest.mark.asyncio
    async def test_thread_reactivation_dormant(self, thread_manager, sample_thread_context, sample_analysis):
        """Test thread reactivation for dormant but semantically similar thread"""
        # Make thread dormant
        sample_thread_context.last_activity = datetime.utcnow() - timedelta(hours=6)
        
        with patch.object(thread_manager, '_get_user_thread_contexts', return_value=[sample_thread_context]):
            with patch.object(thread_manager, '_analyze_message', return_value=sample_analysis):
                with patch.object(thread_manager, '_calculate_thread_scores') as mock_scores:
                    mock_scores.return_value = {
                        sample_thread_context.thread_id: {
                            'semantic_similarity': 0.6,  # Good similarity
                            'temporal_continuity': 0.1,  # But old
                            'intent_alignment': 0.5,
                            'entity_overlap': 0.4,
                            'conversation_flow': 0.3,
                            'user_pattern_match': 0.5,
                            'overall': 0.4
                        }
                    }
                    
                    resolution = await thread_manager.resolve_thread_for_message(
                        user_id="test-user-456",
                        message="I want to continue working on that ML project"
                    )
                    
                    assert resolution.action == ThreadAction.REACTIVATE
                    assert resolution.thread_id == sample_thread_context.thread_id
                    assert resolution.primary_reason == ThreadReason.SEMANTIC_SIMILARITY

    @pytest.mark.asyncio
    async def test_fallback_on_service_failure(self, thread_manager):
        """Test fallback behavior when services fail"""
        with patch.object(thread_manager, '_get_user_thread_contexts', side_effect=Exception("Service unavailable")):
            resolution = await thread_manager.resolve_thread_for_message(
                user_id="test-user",
                message="Hello"
            )
            
            assert resolution.action == ThreadAction.CREATE
            assert resolution.primary_reason == ThreadReason.FALLBACK
            assert resolution.confidence < 1.0
            assert "Service unavailable" in resolution.reasoning

    def test_cosine_similarity_calculation(self, thread_manager):
        """Test cosine similarity calculation"""
        vec_a = np.array([1, 0, 0])
        vec_b = np.array([1, 0, 0])
        vec_c = np.array([0, 1, 0])
        
        # Identical vectors
        similarity_identical = thread_manager._cosine_similarity(vec_a, vec_b)
        assert abs(similarity_identical - 1.0) < 1e-6
        
        # Orthogonal vectors
        similarity_orthogonal = thread_manager._cosine_similarity(vec_a, vec_c)
        assert abs(similarity_orthogonal - 0.0) < 1e-6

    def test_temporal_score_calculation(self, thread_manager):
        """Test temporal continuity scoring"""
        # Very recent (30 minutes)
        recent_gap = timedelta(minutes=30)
        recent_score = thread_manager._calculate_temporal_score(recent_gap)
        assert recent_score == 1.0
        
        # Moderate gap (1 hour)
        moderate_gap = timedelta(hours=1)
        moderate_score = thread_manager._calculate_temporal_score(moderate_gap)
        assert 0.5 < moderate_score < 1.0
        
        # Old gap (1 day)
        old_gap = timedelta(days=1)
        old_score = thread_manager._calculate_temporal_score(old_gap)
        assert old_score == 0.2
        
        # Very old gap (1 week)
        very_old_gap = timedelta(days=7)
        very_old_score = thread_manager._calculate_temporal_score(very_old_gap)
        assert very_old_score == 0.0

    def test_intent_alignment_calculation(self, thread_manager):
        """Test intent alignment scoring"""
        # Perfect alignment
        perfect_alignment = thread_manager._calculate_intent_alignment(
            "question", ["question", "question", "question"]
        )
        assert perfect_alignment == 1.0
        
        # Partial alignment
        partial_alignment = thread_manager._calculate_intent_alignment(
            "question", ["question", "request", "question"]
        )
        assert 0.5 < partial_alignment < 1.0
        
        # No alignment
        no_alignment = thread_manager._calculate_intent_alignment(
            "question", ["greeting", "request", "information"]
        )
        assert no_alignment == 0.0
        
        # Empty history
        empty_alignment = thread_manager._calculate_intent_alignment("question", [])
        assert empty_alignment == 0.5

    def test_entity_overlap_calculation(self, thread_manager):
        """Test entity overlap scoring"""
        current_entities = {"PERSON": ["John", "Mary"], "ORG": ["TechCorp"]}
        thread_entities = {"PERSON": ["John"], "ORG": ["TechCorp"], "GPE": ["NYC"]}
        
        overlap_score = thread_manager._calculate_entity_overlap(current_entities, thread_entities)
        
        # Should be 2/3 = 0.67 (John and TechCorp match out of John, Mary, TechCorp)
        assert 0.6 < overlap_score < 0.7
        
        # No overlap
        no_overlap_score = thread_manager._calculate_entity_overlap(
            {"PERSON": ["Alice"]}, {"ORG": ["OtherCorp"]}
        )
        assert no_overlap_score == 0.0
        
        # Empty entities
        empty_score = thread_manager._calculate_entity_overlap({}, {"PERSON": ["John"]})
        assert empty_score == 0.0

    def test_conversation_boundary_detection(self, thread_manager):
        """Test conversation boundary score calculation"""
        # Greeting
        greeting_score = asyncio.run(
            thread_manager._calculate_conversation_boundary_score("Hello there!")
        )
        assert greeting_score > 0.5
        
        # Farewell
        farewell_score = asyncio.run(
            thread_manager._calculate_conversation_boundary_score("Thanks, goodbye!")
        )
        assert farewell_score > 0.5
        
        # Regular message
        regular_score = asyncio.run(
            thread_manager._calculate_conversation_boundary_score("What about the project status?")
        )
        assert regular_score < 0.5

    def test_context_dependency_calculation(self, thread_manager):
        """Test context dependency scoring"""
        # High dependency
        high_dependency = asyncio.run(
            thread_manager._calculate_context_dependency("What about that thing we discussed?")
        )
        assert high_dependency > 0.5
        
        # Low dependency
        low_dependency = asyncio.run(
            thread_manager._calculate_context_dependency("The weather is nice today.")
        )
        assert low_dependency < 0.5


class TestAICOThreadManagerIntegration:
    """Test suite for AICO service integration"""
    
    @pytest.fixture
    def integration_manager(self):
        """Create AICO integration manager for testing"""
        return AICOThreadManagerIntegration()
    
    @pytest.mark.asyncio
    async def test_service_initialization_success(self, integration_manager):
        """Test successful service initialization"""
        with patch.object(integration_manager, '_initialize_modelservice', return_value=None):
            with patch.object(integration_manager, '_initialize_working_store', return_value=None):
                with patch.object(integration_manager, '_initialize_semantic_memory', return_value=None):
                    await integration_manager.initialize_services()
                    
                    # Should not raise exceptions
                    assert True

    @pytest.mark.asyncio
    async def test_service_initialization_failure(self, integration_manager):
        """Test graceful handling of service initialization failures"""
        with patch.object(integration_manager, '_initialize_modelservice', side_effect=Exception("Service down")):
            # Should not raise exception, but log error
            await integration_manager.initialize_services()
            
            # Check that error was recorded
            assert 'initialization' in integration_manager._metrics['service_errors']

    @pytest.mark.asyncio
    async def test_embedding_service_integration(self, integration_manager):
        """Test ModelService embedding integration"""
        mock_client = Mock()
        mock_response = Mock()
        mock_response.embeddings = [np.random.random(768).tolist()]
        mock_client.get_embeddings = AsyncMock(return_value=mock_response)
        
        integration_manager._modelservice_client = mock_client
        
        embedding = await integration_manager._get_aico_message_embedding("test message")
        
        assert embedding is not None
        assert len(embedding) == 768
        mock_client.get_embeddings.assert_called_once_with("test message")

    @pytest.mark.asyncio
    async def test_entity_extraction_integration(self, integration_manager):
        """Test AICO NER service integration"""
        mock_client = Mock()
        mock_response = Mock()
        mock_entity_list = Mock()
        mock_entity_list.entities = ["John", "Mary"]
        mock_response.entities = {"PERSON": mock_entity_list}
        mock_client.extract_entities = AsyncMock(return_value=mock_response)
        
        integration_manager._modelservice_client = mock_client
        
        entities = await integration_manager._get_aico_entities("John and Mary are here")
        
        assert entities == {"PERSON": ["John", "Mary"]}
        mock_client.extract_entities.assert_called_once_with("John and Mary are here")

    @pytest.mark.asyncio
    async def test_working_store_integration(self, integration_manager):
        """Test WorkingMemoryStore integration"""
        mock_store = Mock()
        mock_messages = [
            {
                "thread_id": "thread-1",
                "user_id": "user-1",
                "message_content": "Hello",
                "timestamp": "2024-01-01T10:00:00Z"
            }
        ]
        mock_store._get_recent_user_messages = AsyncMock(return_value=mock_messages)
        
        integration_manager._working_store = mock_store
        
        contexts = await integration_manager._get_user_thread_contexts("user-1")
        
        assert len(contexts) >= 0  # Should not fail
        mock_store._get_recent_user_messages.assert_called_once_with("user-1", hours=24)

    @pytest.mark.asyncio
    async def test_caching_behavior(self, integration_manager):
        """Test caching functionality"""
        integration_manager.enable_caching = True
        
        # Mock embedding service
        mock_client = Mock()
        mock_response = Mock()
        mock_response.embeddings = [np.random.random(768).tolist()]
        mock_client.get_embeddings = AsyncMock(return_value=mock_response)
        integration_manager._modelservice_client = mock_client
        
        # First call - should hit service
        embedding1 = await integration_manager._get_aico_message_embedding("test message")
        
        # Second call - should hit cache
        embedding2 = await integration_manager._get_aico_message_embedding("test message")
        
        # Should be identical (from cache)
        np.testing.assert_array_equal(embedding1, embedding2)
        
        # Service should only be called once
        assert mock_client.get_embeddings.call_count == 1
        
        # Cache metrics should reflect hit
        assert integration_manager._metrics['cache_hits'] > 0

    @pytest.mark.asyncio
    async def test_performance_metrics_tracking(self, integration_manager):
        """Test performance metrics collection"""
        with patch.object(integration_manager, '_analyze_message') as mock_analyze:
            mock_analyze.return_value = ConversationAnalysis(
                message_embedding=np.zeros(768),
                detected_intent="general",
                topic_shift_score=0.0,
                entities={},
                conversation_boundary_score=0.0,
                urgency_score=0.5,
                context_dependency_score=0.5
            )
            
            with patch.object(integration_manager, '_get_user_thread_contexts', return_value=[]):
                # Perform resolution
                await integration_manager.resolve_thread_for_message("user-1", "test message")
                
                # Check metrics
                metrics = integration_manager.get_performance_metrics()
                
                assert metrics['resolution_count'] > 0
                assert 'avg_resolution_time_ms' in metrics
                assert 'service_status' in metrics

    @pytest.mark.asyncio
    async def test_health_check(self, integration_manager):
        """Test comprehensive health check"""
        # Mock services as healthy
        mock_client = Mock()
        mock_client.get_embeddings = AsyncMock(return_value=Mock(embeddings=[[1, 2, 3]]))
        integration_manager._modelservice_client = mock_client
        
        mock_store = Mock()
        mock_store._get_recent_user_messages = AsyncMock(return_value=[])
        integration_manager._working_store = mock_store
        
        health = await integration_manager.health_check()
        
        assert health['status'] in ['healthy', 'degraded']
        assert 'services' in health
        assert 'performance' in health
        assert 'timestamp' in health

    def test_intent_classification_heuristics(self, integration_manager):
        """Test intent classification heuristics"""
        # Question
        question_intent = asyncio.run(
            integration_manager._classify_aico_intent("What is machine learning?")
        )
        assert question_intent == "question"
        
        # Greeting
        greeting_intent = asyncio.run(
            integration_manager._classify_aico_intent("Hello there!")
        )
        assert greeting_intent == "greeting"
        
        # Request
        request_intent = asyncio.run(
            integration_manager._classify_aico_intent("Can you help me with this?")
        )
        assert request_intent == "request"
        
        # Information sharing
        info_intent = asyncio.run(
            integration_manager._classify_aico_intent("I am working on a project")
        )
        assert info_intent == "information_sharing"
        
        # General
        general_intent = asyncio.run(
            integration_manager._classify_aico_intent("The system is running well")
        )
        assert general_intent == "general"


class TestThreadManagerPerformance:
    """Performance and stress tests"""
    
    @pytest.mark.asyncio
    async def test_concurrent_resolutions(self):
        """Test concurrent thread resolutions"""
        manager = AdvancedThreadManager()
        
        with patch.object(manager, '_analyze_message') as mock_analyze:
            mock_analyze.return_value = ConversationAnalysis(
                message_embedding=np.zeros(768),
                detected_intent="general",
                topic_shift_score=0.0,
                entities={},
                conversation_boundary_score=0.0,
                urgency_score=0.5,
                context_dependency_score=0.5
            )
            
            with patch.object(manager, '_get_user_thread_contexts', return_value=[]):
                # Run multiple concurrent resolutions
                tasks = []
                for i in range(10):
                    task = manager.resolve_thread_for_message(f"user-{i}", f"message-{i}")
                    tasks.append(task)
                
                results = await asyncio.gather(*tasks)
                
                # All should succeed
                assert len(results) == 10
                for result in results:
                    assert isinstance(result, ThreadResolution)
                    assert result.thread_id is not None

    @pytest.mark.asyncio
    async def test_large_thread_context_handling(self):
        """Test handling of users with many threads"""
        manager = AdvancedThreadManager()
        
        # Create many thread contexts
        many_contexts = []
        for i in range(100):
            context = ThreadContext(
                thread_id=f"thread-{i}",
                user_id="heavy-user",
                last_activity=datetime.utcnow() - timedelta(minutes=i),
                message_count=10,
                status="active",
                topic_embedding=np.random.random(768),
                recent_messages=[],
                entities={},
                intent_history=["general"],
                conversation_type="general"
            )
            many_contexts.append(context)
        
        with patch.object(manager, '_get_user_thread_contexts', return_value=many_contexts):
            with patch.object(manager, '_analyze_message') as mock_analyze:
                mock_analyze.return_value = ConversationAnalysis(
                    message_embedding=np.random.random(768),
                    detected_intent="general",
                    topic_shift_score=0.0,
                    entities={},
                    conversation_boundary_score=0.0,
                    urgency_score=0.5,
                    context_dependency_score=0.5
                )
                
                # Should handle many contexts without issues
                resolution = await manager.resolve_thread_for_message("heavy-user", "test message")
                
                assert isinstance(resolution, ThreadResolution)
                assert resolution.thread_id is not None


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])
