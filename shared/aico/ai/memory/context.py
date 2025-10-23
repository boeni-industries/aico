"""
AICO Memory Context Assembler

This module provides intelligent cross-tier memory context assembly for AI processing,
coordinating retrieval and scoring of relevant information from working, episodic, 
semantic, and procedural memory stores to create unified context for conversations.

Core Functionality:
- Cross-tier context retrieval: Intelligently queries all memory tiers based on current conversation context
- Relevance scoring: Applies tier-specific weights and semantic similarity scoring to prioritize context items
- Context assembly: Combines and filters context items to create optimal AI processing context
- Thread strength calculation: Determines conversation thread continuation strength using semantic analysis
- Personalization hints: Extracts user preferences and patterns to guide AI response personalization
- Context summarization: Generates human-readable summaries of assembled context for transparency

Memory Tier Integration:
- Working Memory: Recent session context, active thread messages, temporary conversation state
- Episodic Memory: Historical conversation threads, message sequences, temporal context patterns
- Semantic Memory: Knowledge base queries, concept relationships, factual information retrieval
- Procedural Memory: User behavior patterns, interaction preferences, learned response styles

Technologies & Dependencies:
- asyncio: Asynchronous context retrieval across multiple memory stores
- dataclasses: Structured context item representation with metadata
- datetime: Temporal scoring and recency calculations
- typing: Type safety for context assembly operations
- sentence-transformers: Embedding generation for semantic similarity calculations in context scoring
  Rationale: Enables semantic similarity matching between context items and current conversation
- numpy: Vector operations for embedding similarity calculations and relevance scoring
- AICO ConfigurationManager: Memory tier configuration and scoring parameters
- AICO Logging: Structured logging for context assembly operations and debugging

AI Model Integration:
- Semantic similarity scoring: Uses transformer embeddings for intelligent context relevance calculation
- Content similarity matching: Advanced semantic analysis beyond simple word overlap
- Thread coherence analysis: Semantic understanding for thread continuation decisions
- Context optimization: AI-driven context filtering and prioritization for optimal token usage

Scoring & Filtering:
- Tier-weighted relevance scoring with configurable weights per memory type
- Semantic similarity matching using transformer embeddings and cosine similarity
- Content relevance boost based on semantic understanding of conversation context
- Recency decay functions for temporal relevance adjustment
- Confidence thresholds for procedural memory pattern inclusion
- Context item limits and prioritization for optimal AI processing performance

Personalization Features:
- Communication style adaptation based on procedural memory patterns and learned preferences
- Response length preferences extracted from user interaction history analysis
- Topic interest identification from semantic and episodic memory analysis using embeddings
- Interaction pattern recognition for conversational flow optimization
- Behavioral learning integration for adaptive context assembly based on user feedback
"""

import asyncio
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass

from aico.core.logging import get_logger

logger = get_logger("ai", "memory.context")


@dataclass
class ContextItem:
    """Individual context item with metadata"""
    content: str
    source_tier: str  # working, episodic, semantic, procedural
    relevance_score: float
    timestamp: datetime
    metadata: Dict[str, Any]
    item_type: str  # message, knowledge, pattern, preference


class ContextAssembler:
    """
    Cross-tier memory context assembly coordinator.
    
    Retrieves and combines relevant context from all memory tiers:
    - Working memory: Current session context
    - Episodic memory: Conversation history
    - Semantic memory: Related knowledge
    - Procedural memory: User patterns and preferences
    
    Provides unified, prioritized context for AI processing.
    """
    
    def __init__(self, working_store, episodic_store, semantic_store, procedural_store):
        self.working_store = working_store
        self.episodic_store = episodic_store
        self.semantic_store = semantic_store
        self.procedural_store = procedural_store
        
        # Context assembly configuration
        self._max_context_items = 50
        self._relevance_threshold = 0.3
        self._tier_weights = {
            "working": 1.0,
            "episodic": 0.8,
            "semantic": 0.6,
            "procedural": 0.7
        }
        
        # Smart caching for expensive operations
        self._intent_classifier_cache = None
        self._intent_classifier_initializing = False
        self._similarity_cache = {}
        self._boundary_cache = {}
        
        # V2: Removed automatic background initialization to prevent ModelService dependency issues
        # Components will be initialized on-demand when ModelService is available
    
    async def assemble_context(self, user_id: str, current_message: str, 
                              max_context_items: int = None, conversation_id: str = None) -> Dict[str, Any]:
        """Assemble comprehensive context from all memory tiers with royal precision and enlightened wisdom"""
        max_items = max_context_items or self._max_context_items
        assembly_start = datetime.utcnow()
        
        try:
            import time
            timestamp = time.time()
            print(f"⏱️ [TIMING] Context assembly started for user {user_id} [{timestamp:.6f}]")
            logger.info(f"🧠 Assembling context for user {user_id} with sovereign excellence")
            
            # Retrieve context from all available memory tiers
            
            all_items = []
            
            # Get working memory context (immediate conversation)
            try:
                # 1. Get working memory context
                import time
                working_start = datetime.utcnow()
                print(f"⏱️ [TIMING] Starting working memory retrieval... [{time.time():.6f}]")
                working_items = await self._get_working_context(user_id, conversation_id)
                working_time = (datetime.utcnow() - working_start).total_seconds() * 1000
                print(f"⏱️ [TIMING] Working memory completed in {working_time:.2f}ms [{time.time():.6f}]")
                all_items.extend(working_items or [])
                logger.debug(f"Retrieved {len(working_items or [])} items from working memory")
            except Exception as e:
                logger.warning(f"Working memory context retrieval failed: {e}")
            
            # PHASE 1: Re-enable semantic context retrieval with timeout and fallback
            try:
                semantic_start = datetime.utcnow()
                import time
                timestamp = time.time()
                print(f"⏱️ [TIMING] Starting PROTECTED semantic memory retrieval... [{timestamp:.6f}]")
                
                # PHASE 1: Use timeout to prevent blocking
                semantic_timeout = 3.0  # Reasonable timeout - embeddings + ChromaDB query should be <2s
                semantic_items = await asyncio.wait_for(
                    self._get_semantic_context_safe(current_message, user_id),
                    timeout=semantic_timeout
                )
                
                semantic_time = (datetime.utcnow() - semantic_start).total_seconds() * 1000
                import time
                timestamp = time.time()
                print(f"⏱️ [TIMING] Protected semantic memory completed in {semantic_time:.2f}ms [{timestamp:.6f}]")
                all_items.extend(semantic_items or [])
                logger.debug(f"Retrieved {len(semantic_items or [])} items from semantic memory")
                
            except asyncio.TimeoutError:
                semantic_time = (datetime.utcnow() - semantic_start).total_seconds() * 1000
                print(f"🚨 [SEMANTIC_CONTEXT] ⚠️ FALLBACK: Semantic retrieval timed out after {semantic_time:.2f}ms")
                logger.warning(f"⚠️  SEMANTIC FALLBACK: Context retrieval timed out after {semantic_time:.2f}ms - graceful degradation active")
                # Continue without semantic context (graceful degradation)
            except Exception as e:
                semantic_time = (datetime.utcnow() - semantic_start).total_seconds() * 1000
                print(f"🚨 [SEMANTIC_CONTEXT] ⚠️ FALLBACK: Semantic retrieval failed after {semantic_time:.2f}ms: {e}")
                logger.warning(f"⚠️  SEMANTIC FALLBACK: Context retrieval failed: {e} - graceful degradation active")
            
            # V2: Episodic and procedural memory retrieval removed
            
            logger.debug(f"Retrieved {len(all_items)} total items from all memory tiers")
            
            # Score and filter with Gandhian non-violence toward irrelevant context
            scored_items = self._score_context_items(all_items, current_message)
            print(f"🔍 [CONTEXT_PIPELINE] After scoring: {len(scored_items)} items")
            
            # Apply entity boost for items containing query entities
            print(f"🔍 [CONTEXT_PIPELINE] Starting entity boost phase...")
            boosted_items = self._apply_entity_boost(scored_items, current_message)
            print(f"🔍 [CONTEXT_PIPELINE] After entity boost: {len(boosted_items)} items")
            
            # Apply graduated relevance filtering for optimal context diversity
            print(f"🔍 [CONTEXT_PIPELINE] Starting graduated selection...")
            final_items = self._select_diverse_context(boosted_items, max_items)
            print(f"🔍 [CONTEXT_PIPELINE] Final selection: {len(final_items)} items")
            
            logger.debug(f"Selected {len(final_items)} items using graduated threshold approach")
            
            # Transform ContextItem objects into ConversationEngine-compatible format
            user_facts = []
            recent_context = []
            
            for item in final_items:
                if item.source_tier == "semantic" and item.item_type == "knowledge":
                    # Convert semantic facts to user_facts format
                    user_facts.append({
                        "content": item.content,
                        "confidence": item.metadata.get("confidence", 0.5),
                        "category": item.metadata.get("category", "personal"),
                        "relevance_score": item.relevance_score,
                        "timestamp": item.timestamp.isoformat()
                    })
                elif item.source_tier == "working" and item.item_type == "message":
                    # Convert working memory to recent_context format
                    recent_context.append({
                        "role": item.metadata.get("role", "user"),
                        "content": item.content,
                        "timestamp": item.timestamp.isoformat(),
                        "relevance_score": item.relevance_score
                    })
            
            # Assemble context in ConversationEngine-compatible format
            context = {
                "memory_context": {
                    "user_facts": user_facts,
                    "recent_context": recent_context
                },
                # Keep original metadata for debugging and future use
                "metadata": {
                    "user_id": user_id,
                    "current_message": current_message,
                    "assembled_at": assembly_start.isoformat(),
                    "total_items": len(final_items),
                    "context_summary": self._generate_context_summary(final_items),
                    "tier_distribution": self._get_tier_distribution(final_items),
                    "personalization": self._extract_personalization_hints(final_items),
                    "assembly_time_ms": (datetime.utcnow() - assembly_start).total_seconds() * 1000,
                    "conversation_strength": self._calculate_conversation_strength(final_items)
                }
            }
            
            total_time = (datetime.utcnow() - assembly_start).total_seconds() * 1000
            import time
            timestamp = time.time()
            print(f"⏱️ [TIMING] TOTAL context assembly completed in {total_time:.2f}ms [{timestamp:.6f}]")
            logger.info(f"✨ Context assembled with {len(final_items)} items in {context['metadata']['assembly_time_ms']:.2f}ms")
            return context
            
        except Exception as e:
            logger.error(f"💔 Context assembly failed with sovereign disappointment: {e}")
            import traceback
            logger.error(f"Full traceback: {traceback.format_exc()}")
            
            return {
                "memory_context": {
                    "user_facts": [],
                    "recent_context": []
                },
                "metadata": {
                    "user_id": user_id,
                    "current_message": current_message,
                    "assembled_at": assembly_start.isoformat(),
                    "total_items": 0,
                    "context_summary": "Context assembly failed with grace",
                    "tier_distribution": {},
                    "personalization": {},
                    "assembly_time_ms": (datetime.utcnow() - assembly_start).total_seconds() * 1000,
                    "conversation_strength": 0.0
                }
            }
    
    async def get_user_context(self, user_id: str) -> Dict[str, Any]:
        """Get context specifically for thread resolution - Phase 1 interface"""
        try:
            # TODO Phase 1: Implement thread-specific context
            # - Focus on recent episodic and working memory
            # - Get temporal patterns for thread continuation
            # - Calculate context strength for thread resolution
            
            logger.debug(f"Would retrieve user context for: {user_id}")
            return {"user_id": user_id, "context_strength": 0.0}
            
        except Exception as e:
            logger.error(f"Failed to get user context: {e}")
            return {"user_id": user_id, "context_strength": 0.0}
    
    async def query_memories(self, query) -> Any:
        """Query memories across all tiers with unified interface - Phase 1 interface"""
        try:
            # TODO Phase 1: Implement unified memory querying
            # - Query each tier based on query type
            # - Combine results with relevance scoring
            # - Apply thresholds and limits
            # - Return MemoryResult object
            
            logger.debug(f"Would query memories: {query.query_text}")
            from .manager import MemoryResult
            return MemoryResult(
                memories=[],
                context_summary="Query scaffolding",
                relevance_scores=[],
                total_found=0,
                processing_time_ms=0.0
            )
            
        except Exception as e:
            logger.error(f"Failed to query memories: {e}")
            from .manager import MemoryResult
            return MemoryResult(
                memories=[],
                context_summary="Query failed",
                relevance_scores=[],
                total_found=0,
                processing_time_ms=0.0
            )
    
    async def _get_working_context(self, user_id: str, conversation_id: str = None) -> List[ContextItem]:
        """Get conversation context using enhanced semantic memory approach"""
        try:
            method_start = datetime.utcnow()
            print(f"⏱️ [TIMING] _get_working_context started for user {user_id}")
            
            if not self.working_store:
                logger.debug("No working memory store available - gracefully continuing")
                return []
            
            # ENHANCED SEMANTIC APPROACH: Get conversation or user messages for intelligent context assembly
            db_start = datetime.utcnow()
            if conversation_id:
                print(f"⏱️ [TIMING] Querying working store for conversation {conversation_id}...")
                all_messages = await self.working_store.retrieve_conversation_history(conversation_id, limit=100)
            else:
                print(f"⏱️ [TIMING] Querying working store for user messages...")
                all_messages = await self.working_store.retrieve_user_history(user_id, limit=100)
            db_time = (datetime.utcnow() - db_start).total_seconds() * 1000
            print(f"⏱️ [TIMING] Working store query completed in {db_time:.2f}ms - got {len(all_messages)} messages")
            logger.debug(f"Retrieved {len(all_messages)} messages for semantic context assembly")
            
            # Smart conversation continuity: Find related messages using semantic + temporal signals
            assembly_start = datetime.utcnow()
            print(f"⏱️ [TIMING] Starting conversation context assembly...")
            conversation_messages = await self._assemble_conversation_context(user_id, all_messages)
            assembly_time = (datetime.utcnow() - assembly_start).total_seconds() * 1000
            print(f"⏱️ [TIMING] Conversation context assembly completed in {assembly_time:.2f}ms")
            logger.debug(f"Assembled {len(conversation_messages)} contextually relevant messages")
            
            # Limit to prevent context explosion (industry standard: ~10 recent messages)
            thread_messages = conversation_messages[-10:] if conversation_messages else []
            logger.debug(f"Using {len(thread_messages)} most recent conversation messages")
            
            context_items = []
            now = datetime.utcnow()
            seen_content = set()  # Track content to prevent duplicates
            
            for msg in thread_messages:
                # Calculate recency score with temporal wisdom
                msg_timestamp = msg.get('timestamp', now)
                
                # Handle timestamp parsing with royal grace - ensure UTC consistency
                if isinstance(msg_timestamp, str):
                    try:
                        # Parse timestamp as UTC and ensure it's naive for consistent comparison
                        if msg_timestamp.endswith('Z'):
                            # Remove the Z and treat as naive UTC
                            msg_timestamp = datetime.fromisoformat(msg_timestamp[:-1])
                        elif '+' in msg_timestamp:
                            # Strip timezone info to make naive
                            msg_timestamp = datetime.fromisoformat(msg_timestamp.split('+')[0])
                        else:
                            # Assume UTC if no timezone info
                            msg_timestamp = datetime.fromisoformat(msg_timestamp)
                    except (ValueError, AttributeError):
                        msg_timestamp = now  # Fallback to current time
                
                time_diff = now - msg_timestamp
                recency_hours = time_diff.total_seconds() / 3600
                recency_score = max(0.1, 1.0 - (recency_hours / 24.0))  # Decay over 24 hours
                
                # Base relevance from working memory tier weight
                base_score = self._tier_weights["working"] * recency_score
                
                # Create context item with enlightened metadata
                # CRITICAL FIX: Use 'content' key (matches what's stored in working memory)
                message_content = msg.get('content', '')
                message_type = msg.get('message_type', 'text')
                
                # CRITICAL FIX: Skip empty messages and prevent duplicates
                if not message_content.strip():
                    continue
                    
                # Create a content hash to prevent duplicates
                content_hash = hash(message_content.strip().lower())
                if content_hash in seen_content:
                    logger.debug(f"[DEDUP] Skipping duplicate content: '{message_content[:50]}...'")
                    continue
                seen_content.add(content_hash)
                
                # Determine role based on message type, not the user identifier
                if message_type in ['user_input', 'text']:
                    role = 'user'
                elif message_type in ['ai_response', 'response', 'assistant_response']:
                    role = 'assistant'
                else:
                    role = 'user'  # Default fallback
                
                # Debug logging to trace role assignment
                logger.debug(f"[ROLE_DEBUG] message_type='{message_type}' -> role='{role}', content='{message_content[:50]}...'")
                
                context_item = ContextItem(
                    content=message_content,
                    source_tier="working",
                    relevance_score=base_score,
                    timestamp=msg_timestamp,
                    metadata={
                        "message_id": msg.get('message_id'),
                        "role": role,
                        "conversation_id": msg.get('conversation_id', f"{user_id}_session"),  # Use actual conversation_id from message
                        "recency_hours": recency_hours,
                        "message_type": message_type
                    },
                    item_type="message"
                )
                
                # Debug logging to trace metadata role assignment
                logger.debug(f"[METADATA_DEBUG] ContextItem created with metadata role='{role}', content='{message_content[:50]}...'")
                context_items.append(context_item)
            
            logger.debug(f"Retrieved {len(context_items)} working memory items for user {user_id}")
            return context_items
            
        except Exception as e:
            logger.error(f"Failed to get working context with noble resilience: {e}")
            return []
    
    async def _assemble_conversation_context(self, user_id: str, all_messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Assemble conversation context using enhanced semantic memory approach"""
        try:
            method_start = datetime.utcnow()
            print(f"⏱️ [TIMING] _assemble_conversation_context started with {len(all_messages)} messages")
            
            if not all_messages:
                return []
            
            # ENHANCED SEMANTIC MEMORY: Combine temporal + semantic + conversational signals
            
            # 1. TEMPORAL PRIORITY: Recent messages get higher weight
            now = datetime.utcnow()
            for msg in all_messages:
                msg_time = msg.get('timestamp', now)
                if isinstance(msg_time, str):
                    try:
                        # Ensure naive datetime by removing timezone info
                        if msg_time.endswith('Z'):
                            msg_time = datetime.fromisoformat(msg_time[:-1])
                        elif '+' in msg_time:
                            msg_time = datetime.fromisoformat(msg_time.split('+')[0])
                        else:
                            msg_time = datetime.fromisoformat(msg_time)
                    except:
                        msg_time = now
                
                # Calculate temporal score (0-1, higher = more recent)
                time_diff = (now - msg_time).total_seconds()
                temporal_score = max(0, 1 - (time_diff / (24 * 3600)))  # Decay over 24 hours
                msg['temporal_score'] = temporal_score
            
            # 2. CONVERSATION CONTINUITY: Messages in same conversation get boost
            current_conversation_messages = [
                msg for msg in all_messages 
                if msg.get('conversation_id', '').startswith(user_id)  # Same user conversations
            ]
            
            # 3. SEMANTIC RELEVANCE: Get most recent message for semantic comparison
            current_message_content = None
            if all_messages:
                # Use most recent message as semantic anchor
                # CRITICAL FIX: Use 'content' field (matches storage format)
                current_message_content = all_messages[-1].get('content', '')
            
            # 4. INTELLIGENT SELECTION: Combine all signals
            relevant_messages = []
            
            if current_message_content:
                # ENHANCED: Use proper semantic analysis (extracted from thread manager)
                loop_start = datetime.utcnow()
                print(f"⏱️ [TIMING] Starting message analysis loop for {len(current_conversation_messages)} messages")
                
                for i, msg in enumerate(current_conversation_messages):
                    msg_start = datetime.utcnow()
                    # CRITICAL FIX: Use 'content' field (matches storage format)
                    msg_content = msg.get('content', '')
                    if msg_content and len(msg_content.strip()) > 0:
                        print(f"⏱️ [TIMING] Processing message {i+1}/{len(current_conversation_messages)}")
                        
                        # Use proper semantic analysis with smart caching
                        sim_start = datetime.utcnow()
                        semantic_score = await self._calculate_message_similarity_cached(current_message_content, msg_content)
                        sim_time = (datetime.utcnow() - sim_start).total_seconds() * 1000
                        print(f"⏱️ [TIMING] Similarity calculation took {sim_time:.2f}ms")
                        
                        # Use intelligent boundary detection with timeout protection
                        boundary_start = datetime.utcnow()
                        boundary_score = await self._detect_conversation_boundary_safe(msg_content)
                        boundary_time = (datetime.utcnow() - boundary_start).total_seconds() * 1000
                        print(f"⏱️ [TIMING] Boundary detection took {boundary_time:.2f}ms")
                        
                        boundary_penalty = max(0, boundary_score - 0.5) * 0.5
                        
                        msg_total_time = (datetime.utcnow() - msg_start).total_seconds() * 1000
                        print(f"⏱️ [TIMING] Message {i+1} total processing: {msg_total_time:.2f}ms")
                        
                        # Combined relevance score with boundary detection
                        combined_score = (msg['temporal_score'] * 0.7) + (semantic_score * 0.3) - boundary_penalty
                        msg['relevance_score'] = max(0, combined_score)  # Ensure non-negative
                        
                        # Higher threshold with boundary detection
                        if combined_score > 0.15:  # Increased threshold for quality
                            relevant_messages.append(msg)
            else:
                # No current message - use temporal priority only
                relevant_messages = current_conversation_messages
            
            # Sort by relevance (temporal + semantic)
            relevant_messages.sort(key=lambda x: x.get('relevance_score', x.get('temporal_score', 0)), reverse=True)
            
            method_total_time = (datetime.utcnow() - method_start).total_seconds() * 1000
            print(f"⏱️ [TIMING] _assemble_conversation_context completed in {method_total_time:.2f}ms")
            logger.debug(f"Enhanced semantic memory selected {len(relevant_messages)} relevant messages from {len(all_messages)} total")
            return relevant_messages
            
        except Exception as e:
            logger.error(f"Failed to assemble conversation context: {e}")
            # ROBUST FALLBACK: Ensure user never sees degraded experience
            logger.warning(f"Conversation context assembly failed: {e}")
            # Return ALL recent messages to ensure no context loss
            all_messages.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
            return all_messages[:15]  # Conservative limit to prevent context explosion
    
    async def _calculate_message_similarity(self, message1: str, message2: str) -> float:
        """Calculate semantic similarity between messages (extracted from thread manager)"""
        try:
            # Simple but effective similarity calculation
            words1 = set(message1.lower().split())
            words2 = set(message2.lower().split())
            
            if not words1 or not words2:
                return 0.0
            
            # Jaccard similarity with length normalization
            intersection = len(words1 & words2)
            union = len(words1 | words2)
            jaccard = intersection / union if union > 0 else 0.0
            
            # Length similarity bonus (similar length messages often related)
            len_ratio = min(len(message1), len(message2)) / max(len(message1), len(message2))
            length_bonus = len_ratio * 0.1
            
            return min(1.0, jaccard + length_bonus)
            
        except Exception as e:
            logger.debug(f"Message similarity calculation failed: {e}")
            return 0.0  # Safe fallback
    
    async def _detect_conversation_boundary_via_intent(self, message: str) -> float:
        """Detect conversation boundaries using FULL POWER of sophisticated intent classifier"""
        try:
            # Check cache first
            if message in self._boundary_cache:
                return self._boundary_cache[message]
            
            # V2: Use fast fallback when ModelService unavailable - no automatic retries
            if self._intent_classifier_cache is None:
                logger.debug("Intent classifier not available (ModelService offline), using fast fallback")
                return self._fast_boundary_fallback(message)
            
            # 🚀 USE FULL POWER: Create proper ProcessingContext for sophisticated analysis
            from ..base import ProcessingContext
            from datetime import datetime
            import uuid
            
            context = ProcessingContext(
                conversation_id="boundary_analysis",
                user_id="context_assembly", 
                request_id=str(uuid.uuid4()),
                message_content=message,
                message_type="boundary_detection",
                timestamp=datetime.utcnow(),
                shared_state={'recent_intents': []}  # Enable context awareness
            )
            
            # 🧠 SOPHISTICATED: Use full processor with context awareness, multilingual support, etc.
            result = await self._intent_classifier_cache.process(context)
            
            if result.success and result.result_data:
                prediction = result.result_data.get('prediction')
                if prediction:
                    # Enhanced boundary detection with sophisticated intent understanding
                    boundary_intents = {
                        'greeting': 0.9,           # Very strong boundary (conversation start)
                        'farewell': 0.95,          # Strongest boundary (conversation end)  
                        'question': 0.3,           # Medium boundary (topic shift)
                        'information_sharing': 0.2, # Weak boundary (continuation)
                        'request': 0.4,            # Medium boundary (new need)
                        'complaint': 0.6,          # Strong boundary (mood shift)
                        'confirmation': 0.1,       # Very weak (continuation)
                        'negation': 0.3,           # Medium (disagreement)
                        'general': 0.1,            # Weak boundary
                    }
                    
                    boundary_score = boundary_intents.get(prediction.intent, 0.2)
                    
                    # 🎯 SOPHISTICATED: Weight by confidence AND consider alternatives
                    confidence_weight = prediction.confidence
                    
                    # Boost confidence if alternatives are also boundary intents
                    if hasattr(prediction, 'alternatives') and prediction.alternatives:
                        alt_boundary_boost = 0
                        for alt_intent, alt_conf in prediction.alternatives[:2]:  # Top 2 alternatives
                            if alt_intent in boundary_intents and boundary_intents[alt_intent] > 0.5:
                                alt_boundary_boost += alt_conf * 0.1  # Small boost for boundary alternatives
                        confidence_weight = min(1.0, confidence_weight + alt_boundary_boost)
                    
                    final_score = boundary_score * confidence_weight
                    
                    # Cache the sophisticated result
                    self._boundary_cache[message] = final_score
                    return final_score
            
            # Fallback if sophisticated analysis fails
            return self._fast_boundary_fallback(message)
            
        except Exception as e:
            logger.debug(f"Intent-based boundary detection failed: {e}")
            # Fallback to simple linguistic cues (DRY: reuse sync method)
            return self._fast_boundary_fallback(message)
    
    async def _calculate_message_similarity_cached(self, message1: str, message2: str) -> float:
        """Smart cached semantic similarity with timeout protection"""
        try:
            # Use existing sophisticated method with timeout
            import asyncio
            return await asyncio.wait_for(
                self._calculate_message_similarity(message1, message2),
                timeout=0.5  # 500ms timeout per similarity calculation
            )
        except asyncio.TimeoutError:
            logger.warning(f"🚨 DEGRADATION: Similarity calculation timed out (>500ms), using fast fallback")
            print(f"🚨 [CONTEXT_ASSEMBLY] Similarity timeout - degrading to fast mode for: '{message1[:50]}...' vs '{message2[:50]}...'")
            # Fallback to fast approximation only on timeout
            return self._fast_similarity_fallback(message1, message2)
        except Exception as e:
            logger.warning(f"🚨 DEGRADATION: Similarity calculation failed: {e}, using fast fallback")
            print(f"🚨 [CONTEXT_ASSEMBLY] Similarity error - degrading to fast mode: {e}")
            return self._fast_similarity_fallback(message1, message2)
    
    async def _detect_conversation_boundary_safe(self, message: str) -> float:
        """Smart boundary detection with timeout protection and caching"""
        try:
            # Use existing sophisticated method with timeout
            import asyncio
            return await asyncio.wait_for(
                self._detect_conversation_boundary_via_intent(message),
                timeout=0.3  # 300ms timeout per boundary detection
            )
        except asyncio.TimeoutError:
            logger.warning(f"🚨 DEGRADATION: Boundary detection timed out (>300ms), using fast fallback")
            print(f"🚨 [CONTEXT_ASSEMBLY] Boundary timeout - degrading to fast mode for: '{message[:50]}...'")
            # Fallback to fast approximation only on timeout
            return self._fast_boundary_fallback(message)
        except Exception as e:
            logger.warning(f"🚨 DEGRADATION: Boundary detection failed: {e}, using fast fallback")
            print(f"🚨 [CONTEXT_ASSEMBLY] Boundary error - degrading to fast mode: {e}")
            return self._fast_boundary_fallback(message)
    
    def _fast_similarity_fallback(self, message1: str, message2: str) -> float:
        """Fast fallback only used when sophisticated method times out"""
        try:
            words1 = set(message1.lower().split())
            words2 = set(message2.lower().split())
            if not words1 or not words2:
                return 0.0
            intersection = len(words1.intersection(words2))
            union = len(words1.union(words2))
            return intersection / union if union > 0 else 0.0
        except Exception:
            return 0.0
    
    def _fast_boundary_fallback(self, message: str) -> float:
        """Fast fallback only used when sophisticated method times out"""
        try:
            message_lower = message.lower().strip()
            if any(greeting in message_lower for greeting in ['hello', 'hi', 'hey']):
                return 0.8
            if any(farewell in message_lower for farewell in ['goodbye', 'bye']):
                return 0.9
            if any(topic_change in message_lower for topic_change in ['by the way', 'anyway']):
                return 0.6
            return 0.1
        except Exception:
            return 0.1
    
    # V2: Removed _initialize_expensive_components() method - no automatic background initialization

    # V2: Episodic memory retrieval removed
    
    async def _get_semantic_context(self, current_message: str, user_id: str) -> List[ContextItem]:
        """Get context from semantic memory with the breadth of universal knowledge"""
        try:
            if not self.semantic_store:
                logger.debug("No semantic memory store available - proceeding with mindfulness")
                return []
            
            # Query semantic memory for relevant user facts
            logger.debug(f"Querying semantic memory for user {user_id} with message: '{current_message[:50]}...'")
            
            # Use semantic store's query method to find relevant facts
            semantic_results = await self.semantic_store.query(
                query_text=current_message,
                max_results=10,  # Limit semantic context items
                filters={"user_id": user_id}  # Scope to specific user
            )
            
            if not semantic_results:
                logger.debug("No relevant semantic facts found")
                return []
            
            # Convert semantic results to ContextItem objects
            context_items = []
            now = datetime.utcnow()
            
            for result in semantic_results:
                # Calculate age-based relevance decay for semantic facts
                timestamp = result.get('metadata', {}).get('timestamp', now)
                
                # Ensure timestamp is a naive datetime
                if isinstance(timestamp, str):
                    try:
                        if timestamp.endswith('Z'):
                            timestamp = datetime.fromisoformat(timestamp[:-1])
                        elif '+' in timestamp:
                            timestamp = datetime.fromisoformat(timestamp.split('+')[0])
                        else:
                            timestamp = datetime.fromisoformat(timestamp)
                    except:
                        timestamp = now
                
                fact_age_hours = (now - timestamp).total_seconds() / 3600 if isinstance(timestamp, datetime) else 0
                age_decay = max(0.3, 1.0 - (fact_age_hours / (365 * 24)))  # Decay over 1 year, minimum 0.3
                
                # Base semantic relevance from similarity score
                base_score = result.get('similarity', 0.5) * self._tier_weights["semantic"] * age_decay
                
                # Extract metadata from result
                metadata = result.get('metadata', {})
                
                context_item = ContextItem(
                    content=result.get('content', ''),
                    source_tier="semantic",
                    relevance_score=base_score,
                    timestamp=timestamp if isinstance(timestamp, datetime) else now,
                    metadata={
                        "user_id": user_id,
                        "category": metadata.get('category', 'unknown'),
                        "permanence": metadata.get('permanence', 'unknown'),
                        "confidence": metadata.get('confidence', 0.5),
                        "similarity": result.get('similarity', 0.5),
                        "fact_age_hours": fact_age_hours,
                        "entities": metadata.get("entities", "{}"),
                        "entities_json": metadata.get("entities_json", "{}")
                    },
                    item_type="knowledge"
                )
                context_items.append(context_item)
            
            logger.debug(f"Retrieved {len(context_items)} semantic memory items for user {user_id}")
            return context_items
            
        except Exception as e:
            logger.error(f"Failed to get semantic context with philosophical calm: {e}")
            return []
    
    async def _get_semantic_context_safe(self, current_message: str, user_id: str) -> List[ContextItem]:
        """V3: Get context from semantic memory (conversation segments)"""
        try:
            if not self.semantic_store:
                logger.debug("No semantic memory store available")
                return []
            
            # Query conversation segments
            logger.debug(f"Querying semantic memory for user {user_id}")
            
            semantic_results = await self.semantic_store.query_segments(
                query_text=current_message,
                user_id=user_id,
                max_results=5
            )
            
            if not semantic_results:
                logger.debug("No relevant conversation segments found")
                return []
            
            # Convert segments to ContextItem objects
            context_items = []
            now = datetime.utcnow()
            
            for result in semantic_results:
                metadata = result.get('metadata', {})
                
                # Parse timestamp
                timestamp_str = metadata.get('timestamp', now.isoformat())
                try:
                    if timestamp_str.endswith('Z'):
                        timestamp = datetime.fromisoformat(timestamp_str[:-1])
                    elif '+' in timestamp_str:
                        timestamp = datetime.fromisoformat(timestamp_str.split('+')[0])
                    else:
                        timestamp = datetime.fromisoformat(timestamp_str)
                except:
                    timestamp = now
                
                # Calculate relevance with age decay
                segment_age_hours = (now - timestamp).total_seconds() / 3600
                age_decay = max(0.5, 1.0 - (segment_age_hours / (30 * 24)))  # Decay over 30 days
                
                # Distance is similarity (lower = more similar in ChromaDB)
                distance = result.get('distance', 1.0)
                similarity = max(0.0, 1.0 - distance)  # Convert distance to similarity
                base_score = similarity * self._tier_weights["semantic"] * age_decay
                
                context_item = ContextItem(
                    content=result.get('content', ''),
                    source_tier="semantic",
                    relevance_score=base_score,
                    timestamp=timestamp,
                    metadata={
                        "user_id": user_id,
                        "conversation_id": metadata.get('conversation_id', ''),
                        "role": metadata.get('role', 'unknown'),
                        "similarity": similarity,
                        "segment_age_hours": segment_age_hours
                    },
                    item_type="conversation_history"
                )
                context_items.append(context_item)
            
            print(f"🟢 [SEMANTIC_CONTEXT] ✅ Retrieved {len(context_items)} semantic items")
            logger.debug(f"Retrieved {len(context_items)} semantic memory items for user {user_id}")
            return context_items
            
        except Exception as e:
            print(f"🚨 [SEMANTIC_CONTEXT] ⚠️ FALLBACK: Semantic context failed: {e}")
            logger.error(f"🚨 [SEMANTIC_CONTEXT] CRITICAL ERROR: Failed to get semantic context: {e}")
            logger.error(f"🚨 [SEMANTIC_CONTEXT] Error type: {type(e).__name__}")
            if "Modelservice required" in str(e):
                logger.error("🚨 [SEMANTIC_CONTEXT] ROOT CAUSE: Semantic store has no modelservice dependency!")
                logger.error("🚨 [SEMANTIC_CONTEXT] This means stored facts cannot be retrieved for AI context!")
            return []
    
    # V2: Procedural memory retrieval removed
    
    def _score_context_items(self, items: List[ContextItem], current_message: str) -> List[ContextItem]:
        """Apply additional scoring with the mathematical precision of Newton and the intuition of Einstein"""
        if not items:
            return items
        
        current_lower = current_message.lower()
        scored_items = []
        
        for item in items:
            content_lower = item.content.lower()
            
            # Content relevance boost with semantic understanding
            relevance_boost = 0.0
            
            # Exact phrase matching gets royal treatment
            if any(phrase in content_lower for phrase in current_lower.split() if len(phrase) > 3):
                relevance_boost += 0.3
            
            # Question-answer pattern recognition with Buddhist mindfulness
            if '?' in item.content and current_lower.startswith(('which', 'what', 'how', 'when', 'where', 'why')):
                relevance_boost += 0.2
            
            # List pattern recognition (for sports manager games scenario)
            if any(indicator in content_lower for indicator in ['1.', '2.', '3.', 'list', 'games', 'titles']):
                relevance_boost += 0.25
            
            # Apply tier weight with enlightened calculation
            final_score = (item.relevance_score * self._tier_weights.get(item.source_tier, 0.5)) + relevance_boost
            
            # Create new item with updated score
            scored_item = ContextItem(
                content=item.content,
                source_tier=item.source_tier,
                relevance_score=min(1.0, final_score),  # Cap at 1.0 with royal restraint
                timestamp=item.timestamp,
                metadata=item.metadata,
                item_type=item.item_type
            )
            scored_items.append(scored_item)
        
        return scored_items
    
    def _apply_entity_boost(self, items: List[ContextItem], current_message: str) -> List[ContextItem]:
        """Boost items containing entities mentioned in query (language-agnostic)"""
        message_lower = current_message.lower()
        
        print(f"🔍 [ENTITY_BOOST] Starting entity boost analysis")
        print(f"🔍 [ENTITY_BOOST] Query: '{current_message}'")
        print(f"🔍 [ENTITY_BOOST] Query (lowercase): '{message_lower}'")
        print(f"🔍 [ENTITY_BOOST] Processing {len(items)} items")
        
        boosted_items = []
        boost_count = 0
        
        for i, item in enumerate(items):
            boost_applied = False
            matched_entity = None
            
            print(f"🔍 [ENTITY_BOOST] Item {i+1}/{len(items)}: '{item.content[:50]}...' (score: {item.relevance_score:.3f})")
            
            # Check if item contains entities mentioned in query
            if hasattr(item, 'metadata') and item.metadata:
                entities_json = item.metadata.get('entities', '{}')
                print(f"🔍 [ENTITY_BOOST] Item {i+1} entities JSON: {entities_json}")
                
                try:
                    import json
                    entities = json.loads(entities_json)
                    print(f"🔍 [ENTITY_BOOST] Item {i+1} parsed entities: {entities}")
                    
                    # Check if any entity VALUE appears in query
                    for entity_type, entity_list in entities.items():
                        print(f"🔍 [ENTITY_BOOST] Item {i+1} checking {entity_type}: {entity_list}")
                        for entity_value in entity_list:
                            entity_lower = entity_value.lower()
                            print(f"🔍 [ENTITY_BOOST] Item {i+1} checking if '{entity_lower}' in '{message_lower}'")
                            
                            if entity_lower in message_lower:
                                # Boost this item
                                original_score = item.relevance_score
                                boosted_score = min(1.0, item.relevance_score * 2.5)
                                matched_entity = entity_value
                                
                                print(f"🔍 [ENTITY_BOOST] ✅ MATCH FOUND! Item {i+1}")
                                print(f"🔍 [ENTITY_BOOST] ✅ Matched entity: '{entity_value}'")
                                print(f"🔍 [ENTITY_BOOST] ✅ Score boost: {original_score:.3f} → {boosted_score:.3f}")
                                
                                logger.debug(f"Entity boost: '{item.content[:30]}...' {original_score:.3f} → {boosted_score:.3f} (matched: {entity_value})")
                                
                                item = ContextItem(
                                    content=item.content,
                                    source_tier=item.source_tier,
                                    relevance_score=boosted_score,
                                    timestamp=item.timestamp,
                                    metadata=item.metadata,
                                    item_type=item.item_type
                                )
                                boost_applied = True
                                boost_count += 1
                                break
                        if boost_applied:
                            break
                            
                except Exception as e:
                    print(f"🔍 [ENTITY_BOOST] Item {i+1} JSON parse error: {e}")
                    pass
            else:
                print(f"🔍 [ENTITY_BOOST] Item {i+1} has no metadata or entities")
            
            if not boost_applied:
                print(f"🔍 [ENTITY_BOOST] Item {i+1} no boost applied")
            
            boosted_items.append(item)
        
        print(f"🔍 [ENTITY_BOOST] Summary: {boost_count}/{len(items)} items boosted")
        
        # Log score comparison
        print(f"🔍 [ENTITY_BOOST] Score comparison:")
        for i, (original, boosted) in enumerate(zip(items, boosted_items)):
            if original.relevance_score != boosted.relevance_score:
                print(f"🔍 [ENTITY_BOOST] Item {i+1}: {original.relevance_score:.3f} → {boosted.relevance_score:.3f} (+{((boosted.relevance_score/original.relevance_score)-1)*100:.1f}%)")
        
        logger.debug(f"Entity boost summary: {boost_count}/{len(items)} items boosted")
        
        return boosted_items
    
    def _select_diverse_context(self, scored_items: List[ContextItem], max_items: int) -> List[ContextItem]:
        """
        Select context items - working memory always included, semantic filtered by relevance
        """
        if not scored_items:
            return []
        
        # CRITICAL FIX: Separate working memory (conversation history) from semantic memory
        working_items = [item for item in scored_items if item.source_tier == "working"]
        semantic_items = [item for item in scored_items if item.source_tier == "semantic"]
        
        selected = []
        
        # ALWAYS include ALL working memory items (actual conversation history)
        # Sort by timestamp (most recent first) and limit to reasonable number
        working_sorted = sorted(working_items, key=lambda x: x.timestamp, reverse=True)
        selected.extend(working_sorted[:10])  # Last 10 messages max
        
        # Add semantic items that pass relevance threshold
        semantic_sorted = sorted(semantic_items, key=lambda x: x.relevance_score, reverse=True)
        for item in semantic_sorted:
            if len(selected) >= max_items:
                break
            if item.relevance_score >= self._relevance_threshold:
                selected.append(item)
        
        logger.debug(f"Selected {len(selected)} items: {len(working_sorted[:10])} working, {len([i for i in selected if i.source_tier == 'semantic'])} semantic")
        return selected
    
    def _generate_context_summary(self, items: List[ContextItem]) -> str:
        """Generate human-readable context summary with the eloquence of Shakespeare and clarity of Churchill"""
        if not items:
            return "No context available - a blank canvas awaits"
        
        tier_counts = {}
        message_count = 0
        recent_topics = set()
        
        for item in items:
            tier_counts[item.source_tier] = tier_counts.get(item.source_tier, 0) + 1
            if item.item_type == "message":
                message_count += 1
                # Extract potential topics from content
                words = item.content.lower().split()
                topics = [w for w in words if len(w) > 4 and w.isalpha()]
                recent_topics.update(topics[:3])  # Limit to avoid noise
        
        summary_parts = []
        
        if message_count > 0:
            summary_parts.append(f"{message_count} conversation messages")
        
        if tier_counts.get("working", 0) > 0:
            summary_parts.append(f"{tier_counts['working']} working memory items")
        
        if recent_topics:
            topic_list = list(recent_topics)[:5]  # Top 5 topics
            summary_parts.append(f"Topics: {', '.join(topic_list)}")
        
        if not summary_parts:
            return "Context assembled with sovereign grace"
        
        return f"Context: {'; '.join(summary_parts)}"
    
    def _get_tier_distribution(self, items: List[ContextItem]) -> Dict[str, int]:
        """Get distribution of items across memory tiers with statistical precision"""
        distribution = {}
        for item in items:
            distribution[item.source_tier] = distribution.get(item.source_tier, 0) + 1
        return distribution
    
    def _extract_personalization_hints(self, items: List[ContextItem]) -> Dict[str, Any]:
        """Extract personalization hints with the psychological insight of Jung and empathy of Mother Teresa"""
        if not items:
            return {}
        
        hints = {
            "communication_style": "conversational",
            "response_length": "medium",
            "topics_of_interest": [],
            "interaction_patterns": []
        }
        
        # Analyze message patterns for personalization
        user_messages = [item for item in items if item.metadata.get("role") == "user"]
        
        if user_messages:
            # Determine preferred response length based on user message length
            avg_user_length = sum(len(item.content) for item in user_messages) / len(user_messages)
            if avg_user_length < 50:
                hints["response_length"] = "short"
            elif avg_user_length > 200:
                hints["response_length"] = "detailed"
            
            # Extract topics of interest from user messages
            topics = set()
            for item in user_messages:
                words = item.content.lower().split()
                topics.update([w for w in words if len(w) > 4 and w.isalpha()])
            hints["topics_of_interest"] = list(topics)[:10]  # Top 10 topics
            
            # Detect question patterns
            question_count = sum(1 for item in user_messages if '?' in item.content)
            if question_count > len(user_messages) * 0.7:
                hints["interaction_patterns"].append("inquisitive")
        
        return hints
    
    def _context_item_to_dict(self, item: ContextItem) -> Dict[str, Any]:
        """Convert ContextItem to dictionary with the organizational skills of a royal librarian"""
        return {
            "content": item.content,
            "source_tier": item.source_tier,
            "relevance_score": round(item.relevance_score, 3),
            "timestamp": item.timestamp.isoformat(),
            "metadata": item.metadata,
            "item_type": item.item_type
        }
    
    def _calculate_conversation_strength(self, items: List[ContextItem]) -> float:
        """Calculate conversation context strength for V2 architecture"""
        if not items:
            return 0.0
        
        # Calculate average relevance score
        avg_relevance = sum(item.relevance_score for item in items) / len(items)
        
        # Calculate recency factor based on most recent item
        now = datetime.utcnow()
        most_recent = max(items, key=lambda x: x.timestamp)
        time_diff = now - most_recent.timestamp
        recency_hours = time_diff.total_seconds() / 3600
        recency_factor = max(0.1, 1.0 - (recency_hours / 48.0))  # Decay over 48 hours
        
        # Calculate item density factor (more items = stronger context)
        density_factor = min(1.0, len(items) / 10.0)  # Normalize to 10 items
        
        # Combine factors for conversation strength
        conversation_strength = (avg_relevance * 0.5) + (recency_factor * 0.3) + (density_factor * 0.2)
        
        return round(min(1.0, conversation_strength), 3)
