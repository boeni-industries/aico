"""
AICO Conversation Segment Processor

This module processes conversation segments for semantic memory storage.
It creates meaningful conversation chunks with NER metadata for enhanced
retrieval and context understanding.

Key Features:
- Conversation segmentation (3-5 message chunks)
- NER entity extraction via modelservice
- Metadata enrichment for semantic search
- Clean, local-first processing (no external API dependencies)

The processor creates semantically coherent conversation segments that
can be stored with embeddings for long-term conversational memory.
"""

from datetime import datetime
from typing import List, Optional, Dict, Any, Tuple
from dataclasses import dataclass

from aico.core.config import ConfigurationManager
from aico.core.logging import get_logger

logger = get_logger("shared", "ai.conversation_processor")


@dataclass
class ConversationSegment:
    """A semantically coherent conversation segment with metadata."""
    text: str
    messages: List[Dict[str, Any]]
    entities: Dict[str, List[str]]
    sentiment: str  # "positive", "negative", "neutral"
    sentiment_confidence: float  # confidence score 0.0-1.0
    conversation_id: str
    user_id: str
    timestamp: datetime
    turn_range: Tuple[int, int]  # (start_turn, end_turn)


class ConversationSegmentProcessor:
    """
    Processes conversation messages into semantic segments with NER metadata.
    
    This class creates meaningful conversation chunks that capture complete
    conversational exchanges and enriches them with entity information
    via modelservice NER endpoints (following AICO architecture).
    """
    
    def __init__(self, config_manager: ConfigurationManager):
        self.config = config_manager
        self.modelservice = None  # Injected dependency
        
        # Configuration
        self.chunk_size = self.config.get("memory.semantic.chunk_size", 4)  # 3-5 messages
        self.min_chunk_size = self.config.get("memory.semantic.min_chunk_size", 3)
        self.max_chunk_size = self.config.get("memory.semantic.max_chunk_size", 5)
    
    async def process_conversation_history(self, messages: List[Dict[str, Any]], conversation_id: str, user_id: str) -> List[ConversationSegment]:
        """
        Process a conversation history into semantic segments.
        
        Args:
            messages: List of conversation messages
            conversation_id: Conversation identifier
            user_id: User identifier
            
        Returns:
            List of conversation segments with extracted entities and metadata
        """
        logger.info(f" [CONVERSATION_PROCESSOR_DEBUG] process_conversation_history CALLED with {len(messages) if messages else 0} messages")
        logger.info(f" [CONVERSATION_PROCESSOR_DEBUG] conversation_id: {conversation_id}, user_id: {user_id}")
        
        if not messages:
            logger.info(f" [CONVERSATION_PROCESSOR_DEBUG] No messages provided, returning empty list")
            return []
            
        segments = []
        
        try:
            logger.debug(f" [CONVERSATION_PROCESSOR] Processing {len(messages)} messages with chunk_size={self.chunk_size}, min_chunk_size={self.min_chunk_size}")
            
            # Create overlapping chunks of 3-5 messages
            for i in range(0, len(messages), self.chunk_size - 1):  # Overlap by 1 message
                chunk_messages = messages[i:i + self.chunk_size]
                
                logger.debug(f" [CONVERSATION_PROCESSOR] Created chunk {i} with {len(chunk_messages)} messages")
                
                # Skip if chunk is too small (but allow smaller chunks for short conversations)
                if len(chunk_messages) < self.min_chunk_size:
                    # For short conversations (2 messages), allow smaller chunks
                    if len(messages) <= 2 and len(chunk_messages) >= 2:
                        logger.debug(f" [CONVERSATION_PROCESSOR] Allowing small chunk for short conversation: {len(chunk_messages)} messages")
                    else:
                        logger.debug(f" [CONVERSATION_PROCESSOR] Skipping chunk {i}: {len(chunk_messages)} < {self.min_chunk_size}")
                        continue
                    
                segment = await self._create_segment(chunk_messages, conversation_id, user_id, i)
                if segment:
                    segments.append(segment)
                    logger.debug(f" [CONVERSATION_PROCESSOR] Created segment {i} successfully")
                else:
                    logger.debug(f" [CONVERSATION_PROCESSOR] Failed to create segment {i}")
                
            logger.info(f" [CONVERSATION_PROCESSOR] Created {len(segments)} conversation segments from {len(messages)} messages")
            return segments
            
        except Exception as e:
            logger.error(f" [CONVERSATION_PROCESSOR_DEBUG] EXCEPTION in process_conversation_history: {e}")
            import traceback
            logger.error(f"🔍 [CONVERSATION_PROCESSOR_DEBUG] ❌ Traceback: {traceback.format_exc()}")
            return []
    
    async def _create_segment(self, messages: List[Dict[str, Any]], conversation_id: str, user_id: str, start_index: int) -> Optional[ConversationSegment]:
        """Create a conversation segment from a chunk of messages."""
        try:
            logger.debug(f"🔄 [CONVERSATION_PROCESSOR] _create_segment: Processing {len(messages)} messages")
            
            # Combine messages into coherent text for sentiment analysis
            text_parts = []
            user_text_parts = []  # Separate collection for entity extraction
            
            for i, msg in enumerate(messages):
                role = msg.get("message_type", "unknown")
                content = msg.get("message_content", "")
                
                logger.debug(f"🔄 [CONVERSATION_PROCESSOR] Message {i}: role='{role}', content_length={len(content)}")
                
                if role == "user_input":
                    text_parts.append(f"User: {content}")
                    user_text_parts.append(content)  # Collect only user content for NER
                elif role == "ai_response":
                    text_parts.append(f"AI: {content}")
                else:
                    text_parts.append(content)
            
            segment_text = "\n".join(text_parts)
            user_only_text = "\n".join(user_text_parts)  # Only user messages for entity extraction
            
            logger.debug(f"🔄 [CONVERSATION_PROCESSOR] Combined segment text length: {len(segment_text)}")
            logger.debug(f"🔄 [CONVERSATION_PROCESSOR] User-only text length: {len(user_only_text)}")
            
            # Extract entities using modelservice NER - ONLY from user messages
            logger.info(f"🔄 [CONVERSATION_PROCESSOR] → Extracting entities from USER messages only ({len(user_only_text)} chars)")
            logger.info(f"🔍 [CONVERSATION_PROCESSOR] User text for NER: '{user_only_text[:200]}...'")
            
            if not user_only_text.strip():
                logger.warning(f"🔄 [CONVERSATION_PROCESSOR] ⚠️ No user text found for entity extraction!")
                entities = {}
            else:
                try:
                    logger.info(f"🔄 [CONVERSATION_PROCESSOR] ⚡ CALLING NER for user text: '{user_only_text[:100]}...'")
                    entities = await self._extract_entities_via_modelservice(user_only_text)
                    logger.info(f"🔄 [CONVERSATION_PROCESSOR] ⚡ NER RETURNED: {entities}")
                except Exception as e:
                    logger.error(f"🔄 [CONVERSATION_PROCESSOR] ❌ NER FAILED: {e}")
                    import traceback
                    logger.error(f"🔄 [CONVERSATION_PROCESSOR] ❌ NER TRACEBACK: {traceback.format_exc()}")
                    entities = {}
            entity_count = sum(len(v) for v in entities.values())
            logger.info(f"🔄 [CONVERSATION_PROCESSOR] ✅ Extracted {entity_count} entities from segment")
            
            logger.info(f"🔍 [CONVERSATION_PROCESSOR_DEBUG] About to start sentiment analysis...")
            
            # Extract sentiment using modelservice
            logger.info(f"🔄 [CONVERSATION_PROCESSOR] → Analyzing sentiment for segment")
            try:
                sentiment, sentiment_confidence = await self._extract_sentiment_via_modelservice(segment_text)
                logger.info(f"🔄 [CONVERSATION_PROCESSOR] ✅ Sentiment: {sentiment} (confidence: {sentiment_confidence:.3f})")
            except Exception as e:
                logger.error(f"🔍 [CONVERSATION_PROCESSOR_DEBUG] ❌ EXCEPTION during sentiment analysis: {e}")
                import traceback
                logger.error(f"🔍 [CONVERSATION_PROCESSOR_DEBUG] ❌ Sentiment traceback: {traceback.format_exc()}")
                sentiment, sentiment_confidence = "neutral", 0.5
            
            logger.info(f"🔍 [CONVERSATION_PROCESSOR_DEBUG] Sentiment analysis completed, continuing...")
            
            # Get timestamp from first message
            timestamp = datetime.utcnow()
            if messages and "timestamp" in messages[0]:
                try:
                    timestamp = datetime.fromisoformat(messages[0]["timestamp"].replace("Z", "+00:00"))
                except (ValueError, AttributeError):
                    pass
            
            # Determine turn range
            turn_range = (start_index, start_index + len(messages) - 1)
            
            return ConversationSegment(
                text=segment_text,
                messages=messages,
                entities=entities,
                sentiment=sentiment,
                sentiment_confidence=sentiment_confidence,
                conversation_id=conversation_id,
                user_id=user_id,
                timestamp=timestamp,
                turn_range=turn_range
            )
            
        except Exception as e:
            logger.error(f"Failed to create conversation segment: {e}")
            return None
    
    async def _extract_entities_via_modelservice(self, text: str) -> Dict[str, List[str]]:
        """Extract named entities from text using modelservice NER endpoint."""
        try:
            if not self.modelservice:
                logger.warning("Modelservice not available for NER extraction")
                return {}
            
            # Call modelservice NER endpoint
            response = await self.modelservice.get_ner_entities(text)
            
            if not response.get("success"):
                logger.error(f"Modelservice NER failed: {response.get('error')}")
                return {}
            
            # Parse NER response
            entities = response.get("data", {}).get("entities", {})
            
            # Debug log raw NER response
            logger.info(f"🔍 [NER] Input text: '{text[:100]}...'")
            logger.info(f"🔍 [NER] Raw modelservice response: {entities}")
            
            # Filter out common false positives
            filtered_entities = self._filter_entities(entities, text)
            
            # Debug log filtered results
            logger.info(f"🔍 [NER] Filtered entities: {filtered_entities}")
            if filtered_entities:
                logger.debug(f"[NER] Filtered entities: {filtered_entities}")
                for entity_type, entity_list in filtered_entities.items():
                    logger.debug(f"[NER] {entity_type}: {entity_list}")
            else:
                logger.debug(f"[NER] No entities remaining after filtering")
            
            return filtered_entities
            
        except Exception as e:
            logger.error(f"Modelservice NER extraction failed: {e}")
            return {}
    
    def _filter_entities(self, entities: Dict[str, List[str]], text: str) -> Dict[str, List[str]]:
        """Filter out common false positives and irrelevant entities."""
        filtered = {}
        
        for entity_type, entity_list in entities.items():
            filtered_list = []
            
            for entity in entity_list:
                entity_lower = entity.lower()
                
                # Skip common false positives
                if entity_type == "PERSON":
                    # Skip if it's likely referring to AI or generic terms
                    if entity_lower in ["ai", "assistant", "user", "bot", "system"]:
                        continue
                    # Only include if it appears in user context (not AI context)
                    if "User:" in text and entity in text.split("User:")[1].split("AI:")[0]:
                        filtered_list.append(entity)
                elif entity_type == "GPE":
                    # Include locations mentioned by user
                    if len(entity) > 2:  # Skip very short location names
                        filtered_list.append(entity)
                elif entity_type == "ORG":
                    # Include organizations mentioned by user
                    if len(entity) > 2:
                        filtered_list.append(entity)
                else:
                    # Include other entity types with basic filtering
                    if len(entity) > 1:
                        filtered_list.append(entity)
            
            if filtered_list:
                filtered[entity_type] = filtered_list
        
        return filtered
    
    async def extract_key_entities_from_message(self, message: str) -> Dict[str, List[str]]:
        """
        Extract key entities from a single message.
        
        Useful for real-time entity extraction during conversation.
        """
        return await self._extract_entities_via_modelservice(message)
    
    async def _extract_sentiment_via_modelservice(self, text: str) -> Tuple[str, float]:
        """Extract sentiment from text using modelservice sentiment analysis endpoint."""
        try:
            if not self.modelservice:
                logger.warning("🔍 [SENTIMENT_DEBUG] No modelservice client available for sentiment analysis")
                return "neutral", 0.5
            
            logger.info(f"🔍 [SENTIMENT_DEBUG] Starting sentiment analysis for text: '{text[:100]}...'")
            
            # Call modelservice for sentiment analysis
            logger.info(f"🔍 [SENTIMENT_DEBUG] Calling modelservice.get_sentiment_analysis()")
            result = await self.modelservice.get_sentiment_analysis(text)
            
            logger.info(f"🔍 [SENTIMENT_DEBUG] Raw modelservice response: {result}")
            
            if result.get('success', False) and 'data' in result:
                sentiment_data = result['data']
                sentiment = sentiment_data.get('sentiment', 'neutral')
                confidence = sentiment_data.get('confidence', 0.5)
                
                logger.info(f"🔍 [SENTIMENT_DEBUG] ✅ SUCCESS - Sentiment: {sentiment}, Confidence: {confidence:.3f}")
                return sentiment, confidence
            else:
                error_msg = result.get('error', 'Unknown error')
                logger.error(f"🔍 [SENTIMENT_DEBUG] ❌ FAILED - Modelservice sentiment analysis failed: {error_msg}")
                logger.error(f"🔍 [SENTIMENT_DEBUG] ❌ Full result: {result}")
                return "neutral", 0.5
                
        except Exception as e:
            logger.error(f"🔍 [SENTIMENT_DEBUG] ❌ EXCEPTION - Sentiment analysis error: {e}")
            import traceback
            logger.error(f"🔍 [SENTIMENT_DEBUG] ❌ Traceback: {traceback.format_exc()}")
            return "neutral", 0.5
