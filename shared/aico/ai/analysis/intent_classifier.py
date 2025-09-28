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

logger = get_logger("shared", "ai.analysis.intent_classifier")


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
        self.model_name = "intent_classification"  # Model name in TransformersManager
        self.embedding_dim = 768  # XLM-RoBERTa embedding dimension
        self.supported_languages = [
            'en', 'es', 'fr', 'de', 'it', 'pt', 'ru', 'zh', 'ja', 'ko',
            'ar', 'hi', 'th', 'vi', 'tr', 'pl', 'nl', 'sv', 'da', 'no'
            # XLM-RoBERTa supports 100 languages
        ]
        
        # Intent prototypes (semantic embeddings)
        self.intent_embeddings = {}  # Intent name -> embedding
        
        # Caching and performance
        self.embedding_cache = {}
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
            logger.info("[INTENT_CLASSIFIER] Initializing processor (models managed by ModelService)")
            
            # Initialize intent categories
            await self._load_default_intents()
            
            # Create semantic prototypes using ModelService
            await self._create_semantic_prototypes()
            
            self.is_healthy = True
            logger.info("[INTENT_CLASSIFIER] ✅ Processor initialized successfully")
            
        except Exception as e:
            logger.error(f"[INTENT_CLASSIFIER] Failed to initialize processor: {e}")
            self.is_healthy = False
            raise

    async def _get_modelservice_client(self):
        """Get ModelService client (lazy initialization)"""
        if self._modelservice_client is None:
            try:
                from backend.services.modelservice_client import ModelServiceClient
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
            # Check if we have intent embeddings
            if not self.intent_embeddings:
                logger.warning("[INTENT_CLASSIFIER] No intent embeddings available")
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
            "add_training_example",
            "get_intent_confidence",
            "detect_language",
            "analyze_conversation_context"
        ]

    async def _load_default_intents(self):
        """Initialize intent categories - no hardcoded examples needed with transformer models"""
        # Define intent categories only - the transformer model handles the semantic understanding
        self.intent_categories = [intent.value for intent in IntentType]
        
        # Create semantic prototypes using the model's understanding
        await self._create_semantic_prototypes()
        
        logger.info(f"[INTENT_CLASSIFIER] Initialized {len(self.intent_categories)} intent categories "
                   f"using transformer semantic understanding")

    async def _create_semantic_prototypes(self):
        """Create semantic prototypes for intent categories using the transformer model"""
        logger.info("[INTENT_CLASSIFIER] Creating semantic prototypes for intent categories...")
        
        # Use the model's semantic understanding to create intent prototypes
        intent_descriptions = {
            IntentType.GREETING.value: "greeting hello hi welcome",
            IntentType.QUESTION.value: "question what how why when where",
            IntentType.REQUEST.value: "request help please can you assist",
            IntentType.INFORMATION_SHARING.value: "information sharing telling explaining describing",
            IntentType.CONFIRMATION.value: "confirmation yes correct agree right",
            IntentType.NEGATION.value: "negation no wrong disagree incorrect",
            IntentType.COMPLAINT.value: "complaint problem issue frustrated broken",
            IntentType.FAREWELL.value: "farewell goodbye bye see you later",
            IntentType.GENERAL.value: "general conversation discussion talk"
        }
        
        # Create embeddings for intent prototypes
        for intent_name, description in intent_descriptions.items():
            embedding = await self._get_text_embedding(description)
            if embedding is not None:
                self.intent_embeddings[intent_name] = embedding
        
        logger.info(f"[INTENT_CLASSIFIER] Created semantic prototypes for {len(self.intent_embeddings)} intents")

    async def _get_text_embedding(self, text: str) -> Optional[np.ndarray]:
        """Get embedding for text using ModelService"""
        # Check cache first
        cache_key = hash(text)
        if cache_key in self.embedding_cache:
            cached_entry = self.embedding_cache[cache_key]
            if datetime.now() - cached_entry['timestamp'] < self.cache_ttl:
                return cached_entry['embedding']
        
        try:
            # Get ModelService client
            client = await self._get_modelservice_client()
            
            # Request embedding from ModelService
            response = await client.get_embeddings(
                model=self.model_name,
                prompt=text
            )
            
            if response.get('success') and response.get('data', {}).get('embedding'):
                embedding = np.array(response['data']['embedding'])
                
                # Cache the result
                self.embedding_cache[cache_key] = {
                    'embedding': embedding,
                    'timestamp': datetime.now()
                }
                
                # Limit cache size
                if len(self.embedding_cache) > self.config["cache_size"]:
                    # Remove oldest entries
                    oldest_keys = sorted(
                        self.embedding_cache.keys(),
                        key=lambda k: self.embedding_cache[k]['timestamp']
                    )[:100]
                    for key in oldest_keys:
                        del self.embedding_cache[key]
                
                return embedding
            else:
                logger.warning(f"[INTENT_CLASSIFIER] Failed to get embedding from ModelService: {response.get('error')}")
                return None
            
        except Exception as e:
            logger.error(f"[INTENT_CLASSIFIER] Failed to get embedding via ModelService: {e}")
            return None

    async def _classify_intent(
        self,
        text: str,
        user_id: Optional[str] = None,
        conversation_context: Optional[List[str]] = None
    ) -> IntentPrediction:
        """Classify intent of input text"""
        start_time = time.time()
        
        try:
            # Get text embedding
            text_embedding = await self._get_text_embedding(text)
            if text_embedding is None:
                return IntentPrediction(
                    intent=IntentType.GENERAL.value,
                    confidence=0.0,
                    inference_time_ms=(time.time() - start_time) * 1000
                )
            
            # Calculate similarities with all intent embeddings
            similarities = {}
            for intent_name, intent_embedding in self.intent_embeddings.items():
                similarity = self._cosine_similarity(text_embedding, intent_embedding)
                similarities[intent_name] = float(similarity)
            
            # Find best match
            best_intent = max(similarities, key=similarities.get)
            best_confidence = similarities[best_intent]
            
            # Apply conversation context boost
            if user_id and conversation_context:
                best_intent, best_confidence = await self._apply_context_boost(
                    best_intent, best_confidence, similarities, user_id, conversation_context
                )
            
            # Detect language (simple heuristic)
            detected_language = self._detect_language(text)
            
            # Get alternatives (top 3)
            sorted_intents = sorted(similarities.items(), key=lambda x: x[1], reverse=True)
            alternatives = [(intent, conf) for intent, conf in sorted_intents[1:4]]
            
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
            return IntentPrediction(
                intent=IntentType.GENERAL.value,
                confidence=0.0,
                inference_time_ms=(time.time() - start_time) * 1000
            )

    async def _apply_context_boost(
        self,
        predicted_intent: str,
        confidence: float,
        all_similarities: Dict[str, float],
        user_id: str,
        conversation_context: List[str]
    ) -> Tuple[str, float]:
        """Apply conversation context to boost related intents"""
        
        # Context patterns that boost certain intents
        context_boosts = {
            IntentType.QUESTION.value: {
                "follows": [IntentType.GREETING.value, IntentType.INFORMATION_SHARING.value],
                "boost": 0.1
            },
            IntentType.CONFIRMATION.value: {
                "follows": [IntentType.QUESTION.value, IntentType.REQUEST.value],
                "boost": 0.15
            },
            IntentType.NEGATION.value: {
                "follows": [IntentType.QUESTION.value, IntentType.REQUEST.value],
                "boost": 0.15
            },
            IntentType.FAREWELL.value: {
                "follows": [IntentType.CONFIRMATION.value, IntentType.INFORMATION_SHARING.value],
                "boost": 0.1
            }
        }
        
        # Apply context boosts
        boosted_similarities = all_similarities.copy()
        
        for intent, boost_config in context_boosts.items():
            if any(prev_intent in boost_config["follows"] for prev_intent in conversation_context[-3:]):
                if intent in boosted_similarities:
                    boosted_similarities[intent] += boost_config["boost"]
        
        # Find new best match
        best_intent = max(boosted_similarities, key=boosted_similarities.get)
        best_confidence = boosted_similarities[best_intent]
        
        return best_intent, min(best_confidence, 1.0)  # Cap at 1.0

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

    def _cosine_similarity(self, a: np.ndarray, b: np.ndarray) -> float:
        """Calculate cosine similarity between two vectors"""
        try:
            dot_product = np.dot(a, b)
            norm_a = np.linalg.norm(a)
            norm_b = np.linalg.norm(b)
            
            if norm_a == 0 or norm_b == 0:
                return 0.0
            
            return float(dot_product / (norm_a * norm_b))
        except Exception as e:
            logger.error(f"[INTENT_CLASSIFIER] Cosine similarity calculation failed: {e}")
            return 0.0

    async def add_training_example(self, text: str, intent: str, language: Optional[str] = None):
        """Add a new training example and update intent embeddings"""
        try:
            # Get embedding for the new example
            embedding = await self._get_text_embedding(text)
            if embedding is None:
                logger.warning(f"[INTENT_CLASSIFIER] Failed to get embedding for training example: {text}")
                return
            
            # Update or create intent embedding
            if intent in self.intent_embeddings:
                # Average with existing embedding (simple approach)
                existing_embedding = self.intent_embeddings[intent]
                self.intent_embeddings[intent] = (existing_embedding + embedding) / 2
            else:
                # New intent
                self.intent_embeddings[intent] = embedding
            
            logger.info(f"[INTENT_CLASSIFIER] Added training example for intent '{intent}'")
            
        except Exception as e:
            logger.error(f"[INTENT_CLASSIFIER] Failed to add training example: {e}")


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
