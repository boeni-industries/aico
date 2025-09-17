"""
AICO Conversation Segment Processor

This module processes conversation segments for semantic memory storage.
It creates meaningful conversation chunks with NER metadata for enhanced
retrieval and context understanding.

Key Features:
- Conversation segmentation (3-5 message chunks)
- NER entity extraction using spaCy
- Metadata enrichment for semantic search
- Clean, local-first processing (no LLM dependencies)

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
    thread_id: str
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
    
    def process_conversation_history(self, messages: List[Dict[str, Any]], thread_id: str, user_id: str) -> List[ConversationSegment]:
        """
        Process conversation history into semantic segments.
        
        Args:
            messages: List of conversation messages with metadata
            thread_id: Thread identifier
            user_id: User identifier
            
        Returns:
            List of conversation segments ready for embedding storage
        """
        if not messages:
            return []
            
        segments = []
        
        # Create overlapping chunks of 3-5 messages
        for i in range(0, len(messages), self.chunk_size - 1):  # Overlap by 1 message
            chunk_messages = messages[i:i + self.chunk_size]
            
            # Skip if chunk is too small
            if len(chunk_messages) < self.min_chunk_size:
                continue
                
            segment = await self._create_segment(chunk_messages, thread_id, user_id, i)
            if segment:
                segments.append(segment)
                
        logger.debug(f"Created {len(segments)} conversation segments from {len(messages)} messages")
        return segments
    
    async def _create_segment(self, messages: List[Dict[str, Any]], thread_id: str, user_id: str, start_index: int) -> Optional[ConversationSegment]:
        """Create a conversation segment from a chunk of messages."""
        try:
            # Combine messages into coherent text
            text_parts = []
            for msg in messages:
                role = msg.get("message_type", "unknown")
                content = msg.get("message_content", "")
                
                if role == "user_input":
                    text_parts.append(f"User: {content}")
                elif role == "ai_response":
                    text_parts.append(f"AI: {content}")
                else:
                    text_parts.append(content)
            
            segment_text = "\n".join(text_parts)
            
            # Extract entities using modelservice NER
            entities = await self._extract_entities_via_modelservice(segment_text)
            
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
                thread_id=thread_id,
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
            
            # Filter out common false positives
            entities = self._filter_entities(entities, text)
            
            logger.debug(f"Extracted entities via modelservice: {entities}")
            return entities
            
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
