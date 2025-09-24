"""
Thread Manager Integration Layer

Provides seamless integration between AdvancedThreadManager and existing AICO services:
- ModelService for embeddings and NER
- WorkingMemoryStore for thread persistence
- Semantic memory for context retrieval
- Performance monitoring and fallbacks
"""

import asyncio
import json
import time
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
import numpy as np
from dataclasses import asdict

from aico.core.logging import get_logger
from .advanced_thread_manager import (
    AdvancedThreadManager, 
    ThreadContext, 
    ConversationAnalysis,
    ThreadResolution,
    ThreadAction,
    ThreadReason
)

logger = get_logger("backend", "services.thread_manager_integration")


class AICOThreadManagerIntegration(AdvancedThreadManager):
    """
    AICO-integrated thread manager that connects with existing services.
    
    Integrates with:
    - ModelService for embeddings and NER
    - WorkingMemoryStore for thread data
    - Semantic memory for context retrieval
    - Existing conversation processing pipeline
    """
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        
        # AICO service connections
        self._modelservice_client = None
        self._working_store = None
        self._semantic_memory = None
        
        # Performance tracking
        self._metrics = {
            'resolution_times': [],
            'cache_hits': 0,
            'cache_misses': 0,
            'fallback_activations': 0,
            'service_errors': {}
        }
        
        logger.info("[AICO_THREAD_MANAGER] Initialized with AICO service integration")

    async def initialize_services(self):
        """Initialize AICO services with robust error handling"""
        logger.info("[AICO_THREAD_MANAGER] 🔧 Initializing AICO services...")
        
        try:
            # Initialize ModelService client
            await self._initialize_modelservice()
            logger.info("[AICO_THREAD_MANAGER] ✅ ModelService initialized")
            
            # Initialize WorkingMemoryStore
            await self._initialize_working_store()
            logger.info("[AICO_THREAD_MANAGER] ✅ WorkingMemoryStore initialized")
            
            # Initialize Semantic Memory
            await self._initialize_semantic_memory()
            logger.info("[AICO_THREAD_MANAGER] ✅ Semantic Memory initialized")
            
            logger.info("[AICO_THREAD_MANAGER] 🎉 All AICO services initialized successfully")
            
        except Exception as e:
            logger.error(f"[AICO_THREAD_MANAGER] ⚠️ Service initialization failed: {e}")
            logger.warning("[AICO_THREAD_MANAGER] Operating in degraded mode with fallbacks")
            self._metrics['service_errors']['initialization'] = str(e)

    async def _initialize_modelservice(self):
        """Initialize ModelService client for embeddings and NER"""
        try:
            # Import and initialize ModelService client
            from backend.services.modelservice_client import ModelServiceClient
            
            self._modelservice_client = ModelServiceClient()
            
            # Test connection with a simple request
            test_response = await self._modelservice_client.get_embeddings("test")
            if test_response:
                logger.debug("[AICO_THREAD_MANAGER] ModelService connection verified")
            
        except Exception as e:
            logger.error(f"[AICO_THREAD_MANAGER] ModelService initialization failed: {e}")
            self._modelservice_client = None
            raise

    async def _initialize_working_store(self):
        """Initialize WorkingMemoryStore for thread persistence"""
        try:
            # Get shared working memory store from ai_registry
            import sys
            import os
            
            project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            if project_root not in sys.path:
                sys.path.insert(0, project_root)
            
            from aico.ai import ai_registry
            
            memory_processor = ai_registry.get("memory")
            if not memory_processor:
                raise RuntimeError("Memory processor not found in ai_registry")
            
            # Ensure memory processor is initialized
            if not memory_processor._initialized:
                logger.info("[AICO_THREAD_MANAGER] Initializing memory processor...")
                dummy_request = {
                    "thread_id": "dummy",
                    "user_id": "dummy", 
                    "message": "dummy",
                    "message_type": "user_input"
                }
                await memory_processor.process(dummy_request)
            
            self._working_store = memory_processor._working_store
            if not self._working_store:
                raise RuntimeError("WorkingMemoryStore not available")
                
            logger.debug("[AICO_THREAD_MANAGER] WorkingMemoryStore connection verified")
            
        except Exception as e:
            logger.error(f"[AICO_THREAD_MANAGER] WorkingMemoryStore initialization failed: {e}")
            self._working_store = None
            raise

    async def _initialize_semantic_memory(self):
        """Initialize Semantic Memory for context retrieval"""
        try:
            # Get semantic memory from ai_registry
            from aico.ai import ai_registry
            
            self._semantic_memory = ai_registry.get("semantic_memory")
            if self._semantic_memory:
                logger.debug("[AICO_THREAD_MANAGER] Semantic Memory connection verified")
            else:
                logger.warning("[AICO_THREAD_MANAGER] Semantic Memory not available")
                
        except Exception as e:
            logger.error(f"[AICO_THREAD_MANAGER] Semantic Memory initialization failed: {e}")
            self._semantic_memory = None

    async def resolve_thread_for_message(
        self, 
        user_id: str, 
        message: str, 
        context: Optional[Dict[str, Any]] = None
    ) -> ThreadResolution:
        """
        Enhanced thread resolution with AICO service integration and performance tracking
        """
        start_time = time.time()
        
        try:
            logger.info(f"[AICO_THREAD_MANAGER] 🧠 Resolving thread for user {user_id}")
            
            # Use parent class resolution with AICO services
            resolution = await super().resolve_thread_for_message(user_id, message, context)
            
            # Track performance
            resolution_time = (time.time() - start_time) * 1000  # ms
            self._metrics['resolution_times'].append(resolution_time)
            
            # Log detailed resolution info
            logger.info(f"[AICO_THREAD_MANAGER] ✅ Resolution: {resolution.action.value} "
                       f"(confidence={resolution.confidence:.2f}, "
                       f"reason={resolution.primary_reason.value}, "
                       f"time={resolution_time:.1f}ms)")
            
            # Add AICO-specific context to resolution
            resolution.context_factors['resolution_time_ms'] = resolution_time
            resolution.context_factors['service_status'] = self._get_service_status()
            
            return resolution
            
        except Exception as e:
            logger.error(f"[AICO_THREAD_MANAGER] ❌ Resolution failed: {e}")
            self._metrics['fallback_activations'] += 1
            
            # Enhanced fallback with AICO context
            return await self._aico_fallback_resolution(user_id, message, str(e))

    async def _analyze_message(
        self, 
        message: str, 
        context: Optional[Dict[str, Any]] = None
    ) -> ConversationAnalysis:
        """Enhanced message analysis using AICO services"""
        try:
            logger.debug(f"[AICO_THREAD_MANAGER] 🔍 Analyzing message: '{message[:50]}...'")
            
            # Get message embedding from ModelService
            embedding = await self._get_aico_message_embedding(message)
            
            # Extract entities using AICO NER
            entities = await self._get_aico_entities(message)
            
            # Classify intent (using simple heuristics for now)
            intent = await self._classify_aico_intent(message)
            
            # Calculate conversation indicators
            topic_shift_score = await self._calculate_aico_topic_shift(message, embedding)
            boundary_score = await self._calculate_conversation_boundary_score(message)
            urgency_score = await self._calculate_urgency_score(message)
            context_dependency = await self._calculate_context_dependency(message)
            
            analysis = ConversationAnalysis(
                message_embedding=embedding,
                detected_intent=intent,
                topic_shift_score=topic_shift_score,
                entities=entities,
                conversation_boundary_score=boundary_score,
                urgency_score=urgency_score,
                context_dependency_score=context_dependency
            )
            
            logger.debug(f"[AICO_THREAD_MANAGER] Analysis complete: intent={intent}, "
                        f"entities={len(entities)}, topic_shift={topic_shift_score:.2f}")
            
            return analysis
            
        except Exception as e:
            logger.warning(f"[AICO_THREAD_MANAGER] Message analysis failed: {e}")
            self._metrics['service_errors']['message_analysis'] = str(e)
            
            # Return minimal analysis as fallback
            return ConversationAnalysis(
                message_embedding=np.zeros(768),
                detected_intent="general",
                topic_shift_score=0.0,
                entities={},
                conversation_boundary_score=0.0,
                urgency_score=0.5,
                context_dependency_score=0.5
            )

    async def _get_aico_message_embedding(self, message: str) -> np.ndarray:
        """Get message embedding using AICO ModelService"""
        try:
            # Check cache first
            cache_key = f"embedding:{hash(message)}"
            if self.enable_caching and cache_key in self._embedding_cache:
                self._metrics['cache_hits'] += 1
                return self._embedding_cache[cache_key]
            
            self._metrics['cache_misses'] += 1
            
            if self._modelservice_client:
                # Use AICO ModelService
                response = await self._modelservice_client.get_embeddings(message)
                if response and hasattr(response, 'embeddings') and response.embeddings:
                    embedding = np.array(response.embeddings[0])
                    
                    # Cache result
                    if self.enable_caching:
                        self._embedding_cache[cache_key] = embedding
                    
                    return embedding
            
            # Fallback: return zero vector
            logger.warning("[AICO_THREAD_MANAGER] Using zero embedding fallback")
            return np.zeros(768)
            
        except Exception as e:
            logger.error(f"[AICO_THREAD_MANAGER] Embedding generation failed: {e}")
            self._metrics['service_errors']['embeddings'] = str(e)
            return np.zeros(768)

    async def _get_aico_entities(self, message: str) -> Dict[str, List[str]]:
        """Extract entities using AICO NER service"""
        try:
            if self._modelservice_client:
                # Use AICO NER service
                response = await self._modelservice_client.extract_entities(message)
                if response and hasattr(response, 'entities'):
                    # Convert protobuf response to dict
                    entities = {}
                    for entity_type, entity_list in response.entities.items():
                        entities[entity_type] = list(entity_list.entities)
                    
                    logger.debug(f"[AICO_THREAD_MANAGER] Extracted entities: {entities}")
                    return entities
            
            # Fallback: return empty dict
            return {}
            
        except Exception as e:
            logger.error(f"[AICO_THREAD_MANAGER] Entity extraction failed: {e}")
            self._metrics['service_errors']['entities'] = str(e)
            return {}

    async def _classify_aico_intent(self, message: str) -> str:
        """Classify message intent using AICO services or heuristics"""
        try:
            # Simple intent classification based on message patterns
            message_lower = message.lower().strip()
            
            # Question intents
            if any(word in message_lower for word in ['what', 'how', 'why', 'when', 'where', 'who']):
                return "question"
            
            # Greeting intents
            if any(word in message_lower for word in ['hi', 'hello', 'hey', 'good morning', 'good afternoon']):
                return "greeting"
            
            # Request intents
            if any(word in message_lower for word in ['please', 'can you', 'could you', 'help me']):
                return "request"
            
            # Information sharing
            if any(word in message_lower for word in ['i am', 'i have', 'my', 'just', 'today']):
                return "information_sharing"
            
            # Default
            return "general"
            
        except Exception as e:
            logger.error(f"[AICO_THREAD_MANAGER] Intent classification failed: {e}")
            return "general"

    async def _calculate_aico_topic_shift(self, message: str, embedding: np.ndarray) -> float:
        """Calculate topic shift using AICO semantic memory"""
        try:
            if self._semantic_memory and embedding is not None:
                # Query recent conversation segments for topic comparison
                # This would use AICO's semantic memory to find similar topics
                # For now, return a simple heuristic
                pass
            
            # Simple topic shift detection based on keywords
            topic_shift_indicators = [
                'by the way', 'speaking of', 'anyway', 'also', 'another thing',
                'changing topics', 'different subject', 'new topic'
            ]
            
            message_lower = message.lower()
            for indicator in topic_shift_indicators:
                if indicator in message_lower:
                    return 0.8
            
            return 0.0
            
        except Exception as e:
            logger.error(f"[AICO_THREAD_MANAGER] Topic shift calculation failed: {e}")
            return 0.0

    async def _get_user_thread_contexts(self, user_id: str) -> List[ThreadContext]:
        """Get enriched thread contexts using AICO WorkingMemoryStore"""
        try:
            logger.debug(f"[AICO_THREAD_MANAGER] Getting thread contexts for user {user_id}")
            
            # Check cache first
            cache_key = f"contexts:{user_id}"
            if self.enable_caching and cache_key in self._user_pattern_cache:
                cached_data = self._user_pattern_cache[cache_key]
                cache_age = (datetime.utcnow() - cached_data.get('timestamp', datetime.min)).seconds
                if cache_age < 300:  # 5 minute cache
                    self._metrics['cache_hits'] += 1
                    return cached_data.get('contexts', [])
            
            self._metrics['cache_misses'] += 1
            
            if not self._working_store:
                logger.warning("[AICO_THREAD_MANAGER] WorkingMemoryStore not available")
                return []
            
            # Get recent messages from AICO WorkingMemoryStore
            recent_messages = await self._working_store._get_recent_user_messages(user_id, hours=24)
            logger.debug(f"[AICO_THREAD_MANAGER] Retrieved {len(recent_messages)} recent messages")
            
            # Build thread contexts
            thread_contexts = await self._build_aico_thread_contexts(recent_messages)
            
            # Cache results
            if self.enable_caching:
                self._user_pattern_cache[cache_key] = {
                    'contexts': thread_contexts,
                    'timestamp': datetime.utcnow()
                }
            
            logger.debug(f"[AICO_THREAD_MANAGER] Built {len(thread_contexts)} thread contexts")
            return thread_contexts
            
        except Exception as e:
            logger.error(f"[AICO_THREAD_MANAGER] Failed to get thread contexts: {e}")
            self._metrics['service_errors']['thread_contexts'] = str(e)
            return []

    async def _build_aico_thread_contexts(self, messages: List[Dict[str, Any]]) -> List[ThreadContext]:
        """Build enriched thread contexts from AICO message data"""
        try:
            # Group messages by thread_id
            thread_groups = {}
            for msg in messages:
                thread_id = msg.get('thread_id')
                if thread_id:
                    if thread_id not in thread_groups:
                        thread_groups[thread_id] = []
                    thread_groups[thread_id].append(msg)
            
            # Build ThreadContext objects
            thread_contexts = []
            for thread_id, thread_messages in thread_groups.items():
                try:
                    context = await self._build_single_thread_context(thread_id, thread_messages)
                    if context:
                        thread_contexts.append(context)
                except Exception as e:
                    logger.warning(f"[AICO_THREAD_MANAGER] Failed to build context for thread {thread_id}: {e}")
            
            return thread_contexts
            
        except Exception as e:
            logger.error(f"[AICO_THREAD_MANAGER] Failed to build thread contexts: {e}")
            return []

    async def _build_single_thread_context(self, thread_id: str, messages: List[Dict[str, Any]]) -> Optional[ThreadContext]:
        """Build a single ThreadContext from message data"""
        try:
            if not messages:
                return None
            
            # Sort messages by timestamp
            sorted_messages = sorted(messages, key=lambda m: m.get('timestamp', ''))
            
            # Get basic info
            user_id = messages[0].get('user_id', '')
            last_message = sorted_messages[-1]
            last_activity = datetime.fromisoformat(last_message.get('timestamp', '').replace('Z', '+00:00'))
            
            # Collect recent messages (last 10)
            recent_messages = sorted_messages[-10:]
            
            # Extract entities from recent messages
            all_entities = {}
            intent_history = []
            
            for msg in recent_messages:
                content = msg.get('message_content', '')
                if content:
                    # Extract entities
                    msg_entities = await self._get_aico_entities(content)
                    for entity_type, entity_list in msg_entities.items():
                        if entity_type not in all_entities:
                            all_entities[entity_type] = []
                        all_entities[entity_type].extend(entity_list)
                    
                    # Classify intent
                    intent = await self._classify_aico_intent(content)
                    intent_history.append(intent)
            
            # Remove duplicate entities
            for entity_type in all_entities:
                all_entities[entity_type] = list(set(all_entities[entity_type]))
            
            # Calculate topic embedding (average of recent message embeddings)
            topic_embedding = None
            if recent_messages:
                embeddings = []
                for msg in recent_messages[-3:]:  # Last 3 messages
                    content = msg.get('message_content', '')
                    if content:
                        embedding = await self._get_aico_message_embedding(content)
                        if embedding is not None and embedding.any():
                            embeddings.append(embedding)
                
                if embeddings:
                    topic_embedding = np.mean(embeddings, axis=0)
            
            # Create ThreadContext
            context = ThreadContext(
                thread_id=thread_id,
                user_id=user_id,
                last_activity=last_activity,
                message_count=len(messages),
                status="active",
                topic_embedding=topic_embedding,
                recent_messages=recent_messages,
                entities=all_entities,
                intent_history=intent_history,
                semantic_summary=None,  # Could be generated later
                conversation_type="general",
                user_engagement_score=0.5  # Could be calculated based on message patterns
            )
            
            return context
            
        except Exception as e:
            logger.error(f"[AICO_THREAD_MANAGER] Failed to build thread context: {e}")
            return None

    async def _aico_fallback_resolution(
        self, 
        user_id: str, 
        message: str, 
        error: str
    ) -> ThreadResolution:
        """Enhanced fallback resolution with AICO context"""
        logger.warning(f"[AICO_THREAD_MANAGER] Using AICO fallback resolution: {error}")
        
        thread_id = str(uuid.uuid4())
        
        return ThreadResolution(
            thread_id=thread_id,
            action=ThreadAction.CREATE,
            confidence=0.3,  # Lower confidence for fallback
            primary_reason=ThreadReason.FALLBACK,
            reasoning=f"AICO fallback thread creation: {error[:100]}",
            created_at=datetime.utcnow(),
            context_factors={
                'fallback_reason': error,
                'service_status': self._get_service_status(),
                'user_id': user_id
            }
        )

    def _get_service_status(self) -> Dict[str, str]:
        """Get current status of AICO services"""
        return {
            'modelservice': 'available' if self._modelservice_client else 'unavailable',
            'working_store': 'available' if self._working_store else 'unavailable',
            'semantic_memory': 'available' if self._semantic_memory else 'unavailable'
        }

    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get performance metrics for monitoring"""
        resolution_times = self._metrics['resolution_times']
        
        return {
            'resolution_count': len(resolution_times),
            'avg_resolution_time_ms': np.mean(resolution_times) if resolution_times else 0,
            'p95_resolution_time_ms': np.percentile(resolution_times, 95) if resolution_times else 0,
            'cache_hit_rate': self._metrics['cache_hits'] / max(1, self._metrics['cache_hits'] + self._metrics['cache_misses']),
            'fallback_activations': self._metrics['fallback_activations'],
            'service_errors': self._metrics['service_errors'],
            'service_status': self._get_service_status()
        }

    async def health_check(self) -> Dict[str, Any]:
        """Comprehensive health check for monitoring"""
        try:
            health = {
                'status': 'healthy',
                'timestamp': datetime.utcnow().isoformat(),
                'services': {},
                'performance': self.get_performance_metrics()
            }
            
            # Check ModelService
            try:
                if self._modelservice_client:
                    test_response = await asyncio.wait_for(
                        self._modelservice_client.get_embeddings("health check"), 
                        timeout=5.0
                    )
                    health['services']['modelservice'] = 'healthy' if test_response else 'degraded'
                else:
                    health['services']['modelservice'] = 'unavailable'
            except Exception as e:
                health['services']['modelservice'] = f'unhealthy: {str(e)[:50]}'
            
            # Check WorkingMemoryStore
            try:
                if self._working_store:
                    # Simple test query
                    await asyncio.wait_for(
                        self._working_store._get_recent_user_messages("health_check", hours=1),
                        timeout=5.0
                    )
                    health['services']['working_store'] = 'healthy'
                else:
                    health['services']['working_store'] = 'unavailable'
            except Exception as e:
                health['services']['working_store'] = f'unhealthy: {str(e)[:50]}'
            
            # Check Semantic Memory
            health['services']['semantic_memory'] = 'available' if self._semantic_memory else 'unavailable'
            
            # Overall status
            unhealthy_services = [k for k, v in health['services'].items() if 'unhealthy' in str(v)]
            if unhealthy_services:
                health['status'] = 'degraded'
            
            return health
            
        except Exception as e:
            return {
                'status': 'unhealthy',
                'error': str(e),
                'timestamp': datetime.utcnow().isoformat()
            }


# FastAPI dependency
async def get_aico_thread_manager() -> AICOThreadManagerIntegration:
    """FastAPI dependency for AICO-integrated thread manager"""
    manager = AICOThreadManagerIntegration()
    await manager.initialize_services()
    return manager
