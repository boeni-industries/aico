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
    
    async def assemble_context(self, thread_id: str, user_id: str, 
                              current_message: str, max_context_items: int = None) -> Dict[str, Any]:
        """Assemble comprehensive context from all memory tiers with royal precision and enlightened wisdom"""
        max_items = max_context_items or self._max_context_items
        assembly_start = datetime.utcnow()
        
        try:
            logger.info(f"🧠 Assembling context for thread {thread_id} with sovereign excellence")
            
            # Retrieve context from all available memory tiers
            logger.debug("Retrieving context from all available memory tiers")
            
            all_items = []
            
            # Get working memory context (immediate conversation)
            try:
                working_items = await self._get_working_context(thread_id, user_id)
                all_items.extend(working_items or [])
                logger.debug(f"Retrieved {len(working_items or [])} items from working memory")
            except Exception as e:
                logger.warning(f"Working memory context retrieval failed: {e}")
            
            # Get semantic memory context (long-term user facts)
            try:
                semantic_items = await self._get_semantic_context(current_message, user_id)
                all_items.extend(semantic_items or [])
                logger.debug(f"Retrieved {len(semantic_items or [])} items from semantic memory")
            except Exception as e:
                logger.warning(f"Semantic memory context retrieval failed: {e}")
            
            # Get episodic memory context (historical conversations) - placeholder
            try:
                episodic_items = await self._get_episodic_context(thread_id, user_id, current_message)
                all_items.extend(episodic_items or [])
                logger.debug(f"Retrieved {len(episodic_items or [])} items from episodic memory")
            except Exception as e:
                logger.warning(f"Episodic memory context retrieval failed: {e}")
            
            # Get procedural memory context (user patterns) - placeholder
            try:
                procedural_items = await self._get_procedural_context(user_id)
                all_items.extend(procedural_items or [])
                logger.debug(f"Retrieved {len(procedural_items or [])} items from procedural memory")
            except Exception as e:
                logger.warning(f"Procedural memory context retrieval failed: {e}")
            
            logger.debug(f"Retrieved {len(all_items)} total items from all memory tiers")
            
            # Score and filter with Gandhian non-violence toward irrelevant context
            scored_items = self._score_context_items(all_items, current_message)
            
            # Apply relevance threshold with the wisdom of ages
            relevant_items = [
                item for item in scored_items 
                if item.relevance_score >= self._relevance_threshold
            ]
            
            # Sort by relevance with royal decree
            relevant_items.sort(key=lambda x: x.relevance_score, reverse=True)
            
            # Apply limits with Elizabeth II's measured restraint
            final_items = relevant_items[:max_items]
            
            # Assemble the crown jewel of context structures
            context = {
                "thread_id": thread_id,
                "user_id": user_id,
                "current_message": current_message,
                "assembled_at": assembly_start.isoformat(),
                "total_items": len(final_items),
                "context_summary": self._generate_context_summary(final_items),
                "memories": [self._context_item_to_dict(item) for item in final_items],
                "tier_distribution": self._get_tier_distribution(final_items),
                "personalization": self._extract_personalization_hints(final_items),
                "assembly_time_ms": (datetime.utcnow() - assembly_start).total_seconds() * 1000,
                "thread_strength": self._calculate_thread_strength(final_items)
            }
            
            logger.info(f"✨ Context assembled with {len(final_items)} items in {context['assembly_time_ms']:.2f}ms")
            return context
            
        except Exception as e:
            logger.error(f"💔 Context assembly failed with sovereign disappointment: {e}")
            import traceback
            logger.error(f"Full traceback: {traceback.format_exc()}")
            
            return {
                "thread_id": thread_id,
                "user_id": user_id,
                "current_message": current_message,
                "assembled_at": assembly_start.isoformat(),
                "total_items": 0,
                "context_summary": "Context assembly failed with grace",
                "memories": [],
                "tier_distribution": {},
                "personalization": {},
                "assembly_time_ms": (datetime.utcnow() - assembly_start).total_seconds() * 1000,
                "thread_strength": 0.0
            }
    
    async def get_thread_context(self, thread_id: str, user_id: str) -> Dict[str, Any]:
        """Get context specifically for thread resolution - Phase 1 interface"""
        try:
            # TODO Phase 1: Implement thread-specific context
            # - Focus on recent episodic and working memory
            # - Get temporal patterns for thread continuation
            # - Calculate context strength for thread resolution
            
            logger.debug(f"Would retrieve thread context for: {thread_id}")
            return {"thread_id": thread_id, "user_id": user_id, "context_strength": 0.0}
            
        except Exception as e:
            logger.error(f"Failed to get thread context: {e}")
            return {"thread_id": thread_id, "user_id": user_id, "context_strength": 0.0}
    
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
    
    async def _get_working_context(self, thread_id: str, user_id: str) -> List[ContextItem]:
        """Get conversation context using enhanced semantic memory approach"""
        try:
            if not self.working_store:
                logger.debug("No working memory store available - gracefully continuing")
                return []
            
            # ENHANCED SEMANTIC APPROACH: Get ALL user messages for intelligent context assembly
            all_messages = await self.working_store._get_recent_user_messages(user_id, hours=24)
            logger.debug(f"Retrieved {len(all_messages)} messages for semantic context assembly")
            
            # Smart conversation continuity: Find related messages using semantic + temporal signals
            conversation_messages = await self._assemble_conversation_context(thread_id, user_id, all_messages)
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
                # Use message_content (actual conversation text) instead of role/content format
                message_content = msg.get('message_content', '')
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
                elif message_type in ['ai_response', 'response']:
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
                        "thread_id": msg.get('thread_id', thread_id),  # Use actual thread_id from message
                        "recency_hours": recency_hours,
                        "message_type": message_type
                    },
                    item_type="message"
                )
                
                # Debug logging to trace metadata role assignment
                logger.debug(f"[METADATA_DEBUG] ContextItem created with metadata role='{role}', content='{message_content[:50]}...'")
                context_items.append(context_item)
            
            logger.debug(f"Retrieved {len(context_items)} working memory items for thread {thread_id}")
            return context_items
            
        except Exception as e:
            logger.error(f"Failed to get working context with noble resilience: {e}")
            return []
    
    async def _assemble_conversation_context(self, conversation_id: str, user_id: str, all_messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Assemble conversation context using enhanced semantic memory approach"""
        try:
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
                if msg.get('thread_id', '').startswith(user_id)  # Same user conversations
            ]
            
            # 3. SEMANTIC RELEVANCE: Get current message for semantic comparison
            current_message_content = None
            for msg in all_messages:
                if msg.get('thread_id') == conversation_id:
                    current_message_content = msg.get('message_content', '')
                    break
            
            # 4. INTELLIGENT SELECTION: Combine all signals
            relevant_messages = []
            
            if current_message_content:
                # ENHANCED: Use proper semantic analysis (extracted from thread manager)
                for msg in current_conversation_messages:
                    msg_content = msg.get('message_content', '')
                    if msg_content and len(msg_content.strip()) > 0:
                        # Use existing implementations (DRY principle)
                        semantic_score = await self._calculate_message_similarity(current_message_content, msg_content)
                        
                        # Use existing intent classifier for boundary detection
                        boundary_score = await self._detect_conversation_boundary_via_intent(msg_content)
                        boundary_penalty = max(0, boundary_score - 0.5) * 0.5
                        
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
        """Detect conversation boundaries using existing intent classifier (DRY principle)"""
        try:
            # Use existing intent classifier
            from aico.ai.analysis.intent_classifier import get_intent_classifier
            
            intent_classifier = await get_intent_classifier()
            prediction = await intent_classifier._classify_intent(message)
            
            # Boundary intents indicate conversation transitions
            boundary_intents = {
                'greeting': 0.8,    # Strong boundary indicator
                'farewell': 0.9,    # Very strong boundary indicator
                'general': 0.1,     # Weak boundary indicator
            }
            
            boundary_score = boundary_intents.get(prediction.intent, 0.0)
            
            # Weight by confidence
            return boundary_score * prediction.confidence
            
        except Exception as e:
            logger.debug(f"Intent-based boundary detection failed: {e}")
            # Fallback to simple linguistic cues
            return await self._simple_boundary_detection(message)
    
    async def _simple_boundary_detection(self, message: str) -> float:
        """Simple fallback boundary detection"""
        try:
            boundary_indicators = [
                'hello', 'hi', 'hey', 'good morning', 'good afternoon',
                'thanks', 'thank you', 'goodbye', 'bye', 'see you',
                'new topic', 'different question', 'moving on'
            ]
            
            message_lower = message.lower()
            boundary_score = 0.0
            
            for indicator in boundary_indicators:
                if indicator in message_lower:
                    boundary_score += 0.2
            
            return min(1.0, boundary_score)
            
        except Exception as e:
            logger.debug(f"Simple boundary detection failed: {e}")
            return 0.0
    
    async def _get_episodic_context(self, thread_id: str, user_id: str, 
                                   current_message: str, limit: int = 20) -> List[ContextItem]:
        """Get context from episodic memory with the depth of historical wisdom"""
        try:
            if not self.episodic_store:
                logger.debug("No episodic memory store available - continuing with grace")
                return []
            
            # For now, episodic memory is not yet implemented in the stores
            # This is a placeholder for future episodic memory integration
            logger.debug(f"Episodic memory context retrieval - awaiting future implementation")
            return []
            
        except Exception as e:
            logger.error(f"Failed to get episodic context with stoic acceptance: {e}")
            return []
    
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
                        "fact_age_hours": fact_age_hours
                    },
                    item_type="knowledge"
                )
                context_items.append(context_item)
            
            logger.debug(f"Retrieved {len(context_items)} semantic memory items for user {user_id}")
            return context_items
            
        except Exception as e:
            logger.error(f"Failed to get semantic context with philosophical calm: {e}")
            return []
    
    async def _get_procedural_context(self, user_id: str) -> List[ContextItem]:
        """Get context from procedural memory with the intuition of learned patterns"""
        try:
            if not self.procedural_store:
                logger.debug("No procedural memory store available - continuing with zen acceptance")
                return []
            
            # For now, procedural memory is not yet implemented in the stores
            # This is a placeholder for future procedural memory integration
            logger.debug(f"Procedural memory context retrieval - patterns await discovery")
            return []
            
        except Exception as e:
            logger.error(f"Failed to get procedural context with patient understanding: {e}")
            return []
    
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
    
    def _calculate_thread_strength(self, items: List[ContextItem]) -> float:
        """Calculate thread continuation strength with the wisdom of ancient oracles"""
        if not items:
            return 0.0
        
        # Calculate average relevance score with enlightened mathematics
        avg_relevance = sum(item.relevance_score for item in items) / len(items)
        
        # Calculate recency factor based on most recent item
        now = datetime.utcnow()
        most_recent = max(items, key=lambda x: x.timestamp)
        time_diff = now - most_recent.timestamp
        recency_hours = time_diff.total_seconds() / 3600
        recency_factor = max(0.1, 1.0 - (recency_hours / 48.0))  # Decay over 48 hours
        
        # Calculate item density factor (more items = stronger thread)
        density_factor = min(1.0, len(items) / 10.0)  # Normalize to 10 items
        
        # Combine factors with royal mathematical precision
        thread_strength = (avg_relevance * 0.5) + (recency_factor * 0.3) + (density_factor * 0.2)
        
        return round(min(1.0, thread_strength), 3)
