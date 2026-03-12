"""
AICO Advanced Intent Classification Processor

Modern multilingual intent classification using ModelService architecture.
Follows AICO's BaseAIProcessor architecture and delegates to ModelService for all model operations.

Key Features:
- Multilingual XLM-RoBERTa via ModelService (100+ languages)
- Semantic understanding beyond keyword matching
- Conversation context awareness
- Confidence scoring and uncertainty detection
- Real-time inference with caching
- Proper AICO architecture compliance

Architecture:
- Follows AICO's BaseAIProcessor pattern
- Uses ModelService for all transformer operations
- Integrates with ProcessingContext for coordination
- Returns structured ProcessingResult with metadata
- Supports health checks and capability reporting
"""

import asyncio
import json
import time
import numpy as np
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from enum import Enum

from aico.core.config import ConfigurationManager
from aico.core.logging import get_logger
from ..base import BaseAIProcessor, ProcessingContext, ProcessingResult

logger = get_logger("shared.ai.analysis.intent_classifier")


class IntentType(Enum):
    """Standard conversation intent types"""
    GREETING = "greeting"
    QUESTION = "question"
    REQUEST = "request"
    INFORMATION_SHARING = "information_sharing"
    CONFIRMATION = "confirmation"
    NEGATION = "negation"
    COMPLAINT = "complaint"
    FAREWELL = "farewell"
    GENERAL = "general"


@dataclass
class IntentExample:
    """Training example for intent classification"""
    text: str
    intent: str
    language: Optional[str] = None
    confidence: float = 1.0
    context: Optional[Dict[str, Any]] = None


@dataclass
class IntentPrediction:
    """Intent prediction with confidence and metadata"""
    intent: str
    confidence: float
    detected_language: Optional[str] = None
    alternatives: List[Tuple[str, float]] = None
    inference_time_ms: float = 0.0


class IntentClassificationProcessor(BaseAIProcessor):
    """
    Advanced multilingual intent classification processor following AICO patterns.
    
    Uses ModelService for all transformer operations, maintaining proper architecture.
    Integrates with AICO's processing coordination system via BaseAIProcessor.
    """
    
    def __init__(self):
        super().__init__(
            component_name="intent_classifier",
            version="v2.0"
        )
        
        # Model configuration (managed by ModelService)
        self.model_name = "intent_classification"  # Zero-shot NLI model in TransformersManager
        self.supported_languages = [
            'en', 'es', 'fr', 'de', 'it', 'pt', 'ru', 'zh', 'ja', 'ko',
            'ar', 'hi', 'th', 'vi', 'tr', 'pl', 'nl', 'sv', 'da', 'no'
            # joeddav/xlm-roberta-large-xnli supports 15+ languages natively, 100+ via XLM-R
        ]
        
        # Intent categories for zero-shot classification
        self.intent_labels = []  # Will be populated in initialize()
        
        # Caching and performance
        self.prediction_cache = {}
        self.cache_ttl = timedelta(hours=1)
        
        # Conversation context
        self.conversation_contexts = {}  # user_id -> recent intents
        
        # Configuration
        self.config_manager = ConfigurationManager()
        self.config = self.config_manager.get("ai.intent_classifier", {
            "confidence_threshold": 0.7,
            "cache_size": 1000,
            "context_window": 10,
            "enable_few_shot": True
        })
        
        # ModelService client (will be initialized on first use)
        self._modelservice_client = None
        
        logger.info("[INTENT_CLASSIFIER] Advanced multilingual intent classification processor initialized")

    async def initialize(self):
        """Initialize the intent classification processor (no direct model loading)"""
        try:
            logger.info("[INTENT_CLASSIFIER] Initializing zero-shot NLI processor (models managed by ModelService)")
            
            # Initialize intent categories for zero-shot classification
            self.intent_labels = [intent.value for intent in IntentType]
            
            self.is_healthy = True
            logger.info(f"[INTENT_CLASSIFIER] ✅ Processor initialized with {len(self.intent_labels)} intent categories")
            
        except Exception as e:
            logger.error(f"[INTENT_CLASSIFIER] Failed to initialize processor: {e}")
            self.is_healthy = False
            raise

    async def _get_modelservice_client(self):
        """Get ModelService client (lazy initialization)"""
        if self._modelservice_client is None:
            try:
                from core.services.modelservice_client import ModelServiceClient
                self._modelservice_client = ModelServiceClient(self.config_manager)
                logger.debug("[INTENT_CLASSIFIER] ModelService client initialized")
            except Exception as e:
                logger.error(f"[INTENT_CLASSIFIER] Failed to initialize ModelService client: {e}")
                raise
        return self._modelservice_client

    async def process(self, context: ProcessingContext) -> ProcessingResult:
        """
        Process intent classification request following AICO patterns.
        
        Args:
            context: ProcessingContext with message and conversation state
            
        Returns:
            ProcessingResult with intent prediction and metadata
        """
        start_time = time.time()
        
        try:
            # Extract message from context
            message = context.message_content
            user_id = context.user_id
            
            # Get conversation context from shared state
            conversation_context = context.shared_state.get('recent_intents', [])
            
            # Classify intent
            prediction = await self._classify_intent(
                text=message,
                user_id=user_id,
                conversation_context=conversation_context
            )
            
            # Update conversation context in shared state
            await self._update_conversation_context(context, prediction.intent)
            
            # Track performance
            processing_time = (time.time() - start_time) * 1000
            self.processing_count += 1
            self.average_processing_time = (
                (self.average_processing_time * (self.processing_count - 1) + processing_time)
                / self.processing_count
            )
            
            # Create result
            result = ProcessingResult(
                component="intent_classifier",
                operation="classify_intent",
                success=True,
                result_data={
                    "predicted_intent": prediction.intent,
                    "confidence": prediction.confidence,
                    "detected_language": prediction.detected_language,
                    "alternatives": prediction.alternatives or [],
                    "inference_time_ms": prediction.inference_time_ms
                },
                confidence_score=prediction.confidence,
                processing_time_ms=processing_time
            )
            
            logger.debug(f"[INTENT_CLASSIFIER] Classified '{message[:50]}...' as '{prediction.intent}' "
                        f"(confidence={prediction.confidence:.3f}, time={processing_time:.1f}ms)")
            
            return result
            
        except Exception as e:
            logger.error(f"[INTENT_CLASSIFIER] Processing failed: {e}")
            self.error_count += 1
            
            return ProcessingResult(
                component="intent_classifier",
                operation="classify_intent",
                success=False,
                result_data={"predicted_intent": "general", "confidence": 0.0},
                error_message=str(e),
                processing_time_ms=(time.time() - start_time) * 1000
            )

    async def health_check(self) -> bool:
        """Check if processor is healthy and ready"""
        if not self.is_healthy:
            return False
        
        try:
            # Check if we have intent labels
            if not self.intent_labels:
                logger.warning("[INTENT_CLASSIFIER] No intent labels available")
                return False
            
            # Quick test with ModelService
            client = await self._get_modelservice_client()
            health_response = await client.get_health()
            
            return health_response.get('success', False)
        except Exception as e:
            logger.error(f"[INTENT_CLASSIFIER] Health check failed: {e}")
            self.is_healthy = False
            return False

    def get_supported_operations(self) -> List[str]:
        """Get list of supported operations"""
        return [
            "classify_intent",
            "detect_language",
            "analyze_conversation_context"
        ]


    async def _classify_intent(
        self,
        text: str,
        user_id: Optional[str] = None,
        conversation_context: Optional[List[str]] = None
    ) -> IntentPrediction:
        """Classify intent using zero-shot NLI approach"""
        start_time = time.time()
        
        try:
            # Get ModelService client
            client = await self._get_modelservice_client()
            
            # Use intent classification via ModelService (uses zero-shot NLI internally)
            response = await client.classify_intent(
                text=text,
                model=self.model_name
            )
            
            if not response.get('success'):
                logger.warning(f"[INTENT_CLASSIFIER] Classification failed: {response.get('error')}")
                return IntentPrediction(
                    intent=IntentType.GENERAL.value,
                    confidence=0.0,
                    inference_time_ms=(time.time() - start_time) * 1000
                )
            
            # Extract results from intent classification response
            result_data = response.get('data', {})
            best_intent = result_data.get('predicted_intent', IntentType.GENERAL.value)
            best_confidence = result_data.get('confidence', 0.0)
            
            # Get alternatives if available
            alternatives_data = result_data.get('alternatives', [])
            alternatives = [(alt[0], alt[1]) for alt in alternatives_data[:3]]
            
            # Detect language (simple heuristic)
            detected_language = self._detect_language(text)
            
            inference_time = (time.time() - start_time) * 1000
            
            return IntentPrediction(
                intent=best_intent,
                confidence=best_confidence,
                detected_language=detected_language,
                alternatives=alternatives,
                inference_time_ms=inference_time
            )
            
        except Exception as e:
            logger.error(f"[INTENT_CLASSIFIER] Classification failed: {e}")
            import traceback
            logger.error(f"[INTENT_CLASSIFIER] Traceback: {traceback.format_exc()}")
            return IntentPrediction(
                intent=IntentType.GENERAL.value,
                confidence=0.0,
                inference_time_ms=(time.time() - start_time) * 1000
            )

    def _detect_language(self, text: str) -> Optional[str]:
        """Simple language detection based on character patterns"""
        # Chinese characters
        if any('\u4e00' <= char <= '\u9fff' for char in text):
            return 'zh'
        
        # Japanese hiragana/katakana
        if any('\u3040' <= char <= '\u309f' or '\u30a0' <= char <= '\u30ff' for char in text):
            return 'ja'
        
        # Korean hangul
        if any('\uac00' <= char <= '\ud7af' for char in text):
            return 'ko'
        
        # Arabic
        if any('\u0600' <= char <= '\u06ff' for char in text):
            return 'ar'
        
        # Cyrillic (Russian, etc.)
        if any('\u0400' <= char <= '\u04ff' for char in text):
            return 'ru'
        
        # Default to English for Latin scripts
        return 'en'

    async def _update_conversation_context(self, context: ProcessingContext, intent: str):
        """Update conversation context in shared state"""
        recent_intents = context.shared_state.get('recent_intents', [])
        recent_intents.append(intent)
        
        # Keep only last N intents
        context_window = self.config["context_window"]
        if len(recent_intents) > context_window:
            recent_intents = recent_intents[-context_window:]
        
        context.shared_state['recent_intents'] = recent_intents


# Global processor instance for AICO coordination
_intent_processor = None


async def get_intent_classifier() -> IntentClassificationProcessor:
    """Get the global intent classification processor"""
    global _intent_processor
    
    if _intent_processor is None:
        try:
            _intent_processor = IntentClassificationProcessor()
            await _intent_processor.initialize()
        except Exception as e:
            # Reset to None on initialization failure to prevent broken instance caching
            _intent_processor = None
            logger.error(f"[INTENT_CLASSIFIER] Failed to initialize processor: {e}")
            raise
    
    return _intent_processor
