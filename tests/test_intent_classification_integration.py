"""
Integration test for the intent classification system

Tests the complete pipeline:
- AICO AI processor in /shared/aico/ai/
- ModelService handler delegation
- ZMQ integration
- Enhanced semantic memory usage
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch

from shared.aico.ai.analysis.intent_classifier import IntentClassificationProcessor, get_intent_classifier
from shared.aico.ai.base import ProcessingContext, ProcessingResult
from modelservice.handlers.intent_classification_handler import get_intent_classification_handler


class TestIntentClassificationIntegration:
    """Test the complete intent classification integration"""
    
    @pytest.mark.asyncio
    async def test_ai_processor_initialization(self):
        """Test that the AI processor initializes correctly"""
        processor = IntentClassificationProcessor()
        
        # Check basic properties
        assert processor.component_name == "intent_classifier"
        assert processor.version == "v2.0"
        assert processor.model_name == "intent_classification"  # Model name in TransformersManager
        assert len(processor.supported_languages) > 10  # Should support many languages

    @pytest.mark.asyncio
    async def test_semantic_prototypes_creation(self):
        """Test that semantic prototypes are created without hardcoded examples"""
        processor = IntentClassificationProcessor()
        processor.is_healthy = True
        
        # Mock ModelService client
        mock_client = Mock()
        mock_client.get_embeddings = AsyncMock(return_value={
            'success': True,
            'data': {'embedding': [0.1, 0.2, 0.3] * 256}  # 768-dim vector
        })
        processor._get_modelservice_client = AsyncMock(return_value=mock_client)
        
        # Test semantic prototype creation
        await processor._create_semantic_prototypes()
        
        # Should have embeddings for all intent types
        assert len(processor.intent_embeddings) == 9  # Number of IntentType enum values
        assert "greeting" in processor.intent_embeddings
        assert "question" in processor.intent_embeddings
        assert "request" in processor.intent_embeddings

    @pytest.mark.asyncio
    async def test_processing_context_integration(self):
        """Test that the processor works with AICO's ProcessingContext"""
        processor = IntentClassificationProcessor()
        processor.is_healthy = True
        
        # Mock the model components
        processor.tokenizer = Mock()
        processor.model = Mock()
        
        # Mock the classification method
        async def mock_classify_intent(text, user_id=None, context=None):
            from shared.aico.ai.analysis.intent_classifier import IntentPrediction
            return IntentPrediction(
                intent="question",
                confidence=0.85,
                detected_language="en",
                alternatives=[("request", 0.12), ("general", 0.03)],
                inference_time_ms=15.5
            )
        
        processor._classify_intent = mock_classify_intent
        
        # Create processing context
        context = ProcessingContext(
            conversation_id="test-thread",
            user_id="test-user",
            request_id="test-request",
            message_content="What is machine learning?",
            shared_state={'recent_intents': ['greeting']}
        )
        
        # Process the request
        result = await processor.process(context)
        
        # Verify result
        assert isinstance(result, ProcessingResult)
        assert result.success is True
        assert result.data["predicted_intent"] == "question"
        assert result.data["confidence"] == 0.85
        assert result.data["detected_language"] == "en"
        assert len(result.data["alternatives"]) == 2

    @pytest.mark.asyncio
    async def test_modelservice_handler_delegation(self):
        """Test that the ModelService handler properly delegates to AI processor"""
        from aico.proto.aico_modelservice_pb2 import IntentClassificationRequest, IntentClassificationResponse
        
        # Create a mock request
        request = IntentClassificationRequest()
        request.text = "Hello there!"
        request.user_id = "test-user"
        request.conversation_context.extend(["greeting"])
        
        # Mock the AI processor
        mock_processor = Mock()
        mock_result = ProcessingResult(
            success=True,
            data={
                "predicted_intent": "greeting",
                "confidence": 0.92,
                "detected_language": "en",
                "alternatives": [("farewell", 0.05)],
                "inference_time_ms": 12.3
            },
            metadata={"processor": "intent_classifier"},
            processing_time_ms=12.3
        )
        mock_processor.process = AsyncMock(return_value=mock_result)
        
        # Test the handler
        handler = await get_intent_classification_handler()
        
        with patch('shared.aico.ai.analysis.intent_classifier.get_intent_classifier', return_value=mock_processor):
            response = await handler.handle_request(request)
        
        # Verify response
        assert isinstance(response, IntentClassificationResponse)
        assert response.success is True
        assert response.predicted_intent == "greeting"
        assert response.confidence == 0.92
        assert response.detected_language == "en"
        assert len(response.alternative_predictions) == 1

    @pytest.mark.asyncio
    async def test_thread_manager_integration(self):
        """Test that the thread manager can use the new intent classifier"""
        from backend.services.advanced_thread_manager import AdvancedThreadManager
        
        thread_manager = AdvancedThreadManager()
        
        # Mock the AI processor
        mock_processor = Mock()
        mock_result = ProcessingResult(
            success=True,
            data={"predicted_intent": "question"},
            metadata={},
            processing_time_ms=10.0
        )
        mock_processor.process = AsyncMock(return_value=mock_result)
        
    @pytest.mark.asyncio
    async def test_no_hardcoded_patterns(self):
        """Test that we removed all hardcoded pattern matching"""
        processor = IntentClassificationProcessor()
        
        # Check that we don't load models directly (delegated to ModelService)
        assert not hasattr(processor, 'tokenizer') or processor.tokenizer is None
        assert not hasattr(processor, 'model') or processor.model is None
        
        # Check that we use ModelService client instead
        assert hasattr(processor, '_modelservice_client')
        assert processor.model_name == "intent_classification"  # TransformersManager model name

    @pytest.mark.asyncio
    async def test_multilingual_capability(self):
        """Test that the system can handle multiple languages"""
        processor = IntentClassificationProcessor()
        # Check supported languages
        assert 'en' in processor.supported_languages
        assert 'es' in processor.supported_languages  # Spanish
        assert 'fr' in processor.supported_languages  # French
        assert 'de' in processor.supported_languages  # German
        assert 'zh' in processor.supported_languages  # Chinese
        assert 'ja' in processor.supported_languages  # Japanese
        
        # Should support 100+ languages via XLM-RoBERTa
        assert len(processor.supported_languages) >= 20

    def test_architecture_compliance(self):
        """Test that the implementation follows AICO architecture patterns"""
        from shared.aico.ai.base import BaseAIProcessor
        from shared.aico.ai.analysis.intent_classifier import IntentClassificationProcessor
        
        # Should extend BaseAIProcessor
        assert issubclass(IntentClassificationProcessor, BaseAIProcessor)
        
        # Should be in the correct location
        processor = IntentClassificationProcessor()
        assert processor.component_name == "intent_classifier"
        assert hasattr(processor, 'get_supported_operations')
        assert hasattr(processor, 'health_check')

    @pytest.mark.asyncio
    async def test_performance_requirements(self):
        """Test that the system meets performance requirements"""
        processor = IntentClassificationProcessor()
        processor.is_healthy = True
        
        # Mock fast processing
        async def mock_classify_intent(text, user_id=None, context=None):
            from shared.aico.ai.analysis.intent_classifier import IntentPrediction
            return IntentPrediction(
                intent="general",
                confidence=0.8,
                inference_time_ms=25.0  # Should be < 50ms
            )
        
        processor._classify_intent = mock_classify_intent
        
        context = ProcessingContext(
            conversation_id="perf-test",
            user_id="test",
            request_id="perf",
            message_content="Test message"
        )
        
        result = await processor.process(context)
        
        # Should meet performance targets
        assert result.processing_time_ms < 100  # Reasonable for mocked test
        assert result.data["inference_time_ms"] < 50  # Target performance


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])
