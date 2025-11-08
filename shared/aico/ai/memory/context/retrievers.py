"""
Context Retrievers

Tier-specific context retrieval methods.
"""

from typing import List, Optional
from datetime import datetime

from aico.core.logging import get_logger

from .models import ContextItem

logger = get_logger("ai", "memory.context.retrievers")


class ContextRetrievers:
    """
    Retrieves context from different memory tiers.
    """
    
    def __init__(self, working_store, episodic_store, semantic_store, behavioral_store):
        """
        Initialize retrievers with memory stores.
        
        Args:
            working_store: Working memory store (conversation history + context)
            episodic_store: Not implemented - kept for interface compatibility
            semantic_store: Semantic memory store (segments + KG)
            behavioral_store: Behavioral memory store (planned)
        """
        self.working_store = working_store
        self.episodic_store = episodic_store  # Not implemented
        self.semantic_store = semantic_store
        self.behavioral_store = behavioral_store  # Planned
    
    async def get_working_context(
        self,
        user_id: str,
        conversation_id: Optional[str] = None
    ) -> List[ContextItem]:
        """
        Retrieve context from working memory.
        
        Args:
            user_id: User ID
            conversation_id: Optional conversation ID
            
        Returns:
            List of context items from working memory
        """
        if not self.working_store:
            print(f"🔍 [RETRIEVER] ❌ No working_store available!")
            return []
        
        try:
            # Get recent messages from working memory
            print(f"🔍 [RETRIEVER] Getting messages: conversation_id={conversation_id}")
            if conversation_id:
                messages = await self.working_store.retrieve_conversation_history(conversation_id, limit=20)
                print(f"🔍 [RETRIEVER] Got {len(messages)} messages from conversation {conversation_id}")
            else:
                messages = await self.working_store.retrieve_user_history(user_id, limit=20)
                print(f"🔍 [RETRIEVER] Got {len(messages)} recent messages for user {user_id}")
            
            if messages:
                print(f"🔍 [RETRIEVER] Sample message: {messages[0]}")
            
            # Convert to ContextItems
            items = []
            for msg in messages:
                items.append(ContextItem(
                    content=msg.get('content', ''),
                    source_tier='working',
                    relevance_score=1.0,  # Working memory is always highly relevant
                    timestamp=datetime.fromisoformat(msg.get('timestamp', datetime.utcnow().isoformat())),
                    metadata={'role': msg.get('role', 'user')},
                    item_type='message'
                ))
            
            print(f"🔍 [RETRIEVER] Converted to {len(items)} ContextItems")
            logger.debug(f"Retrieved {len(items)} items from working memory")
            return items
            
        except Exception as e:
            print(f"🔍 [RETRIEVER] ❌ Exception: {e}")
            logger.error(f"Working memory retrieval failed: {e}")
            import traceback
            print(f"🔍 [RETRIEVER] Traceback: {traceback.format_exc()}")
            return []
    
    async def get_semantic_context(
        self,
        user_id: str,
        query: str,
        limit: int = 10
    ) -> List[ContextItem]:
        """
        Retrieve context from semantic memory.
        
        Args:
            user_id: User ID
            query: Query text
            limit: Maximum items to retrieve
            
        Returns:
            List of context items from semantic memory
        """
        if not self.semantic_store:
            return []
        
        try:
            # Query semantic memory
            results = await self.semantic_store.query(user_id, query, limit=limit)
            
            # Convert to ContextItems
            items = []
            for result in results:
                items.append(ContextItem(
                    content=result.get('content', ''),
                    source_tier='semantic',
                    relevance_score=result.get('score', 0.5),
                    timestamp=datetime.fromisoformat(result.get('timestamp', datetime.utcnow().isoformat())),
                    metadata=result.get('metadata', {}),
                    item_type='knowledge'
                ))
            
            logger.debug(f"Retrieved {len(items)} items from semantic memory")
            return items
            
        except Exception as e:
            logger.error(f"Semantic memory retrieval failed: {e}")
            return []
    
    async def get_episodic_context(
        self,
        user_id: str,
        query: str,
        limit: int = 5
    ) -> List[ContextItem]:
        """
        Retrieve context from episodic memory.
        
        Args:
            user_id: User ID
            query: Query text
            limit: Maximum items to retrieve
            
        Returns:
            List of context items from episodic memory
        """
        if not self.episodic_store:
            return []
        
        try:
            # Query episodic memory (conversation history)
            results = await self.episodic_store.query(user_id, query, limit=limit)
            
            # Convert to ContextItems
            items = []
            for result in results:
                items.append(ContextItem(
                    content=result.get('content', ''),
                    source_tier='episodic',
                    relevance_score=result.get('score', 0.5),
                    timestamp=datetime.fromisoformat(result.get('timestamp', datetime.utcnow().isoformat())),
                    metadata=result.get('metadata', {}),
                    item_type='message'
                ))
            
            logger.debug(f"Retrieved {len(items)} items from episodic memory")
            return items
            
        except Exception as e:
            logger.error(f"Episodic memory retrieval failed: {e}")
            return []
    
    async def get_behavioral_context(
        self,
        user_id: str
    ) -> List[ContextItem]:
        """
        Retrieve context from behavioral memory.
        
        Args:
            user_id: User ID
            
        Returns:
            List of context items from behavioral memory
        """
        if not self.behavioral_store:
            return []
        
        try:
            # Get user patterns, skills, and preferences
            patterns = await self.behavioral_store.get_user_patterns(user_id)
            
            # Convert to ContextItems
            items = []
            for pattern in patterns:
                items.append(ContextItem(
                    content=pattern.get('description', ''),
                    source_tier='behavioral',
                    relevance_score=pattern.get('confidence', 0.5),
                    timestamp=datetime.fromisoformat(pattern.get('timestamp', datetime.utcnow().isoformat())),
                    metadata=pattern.get('metadata', {}),
                    item_type='pattern'
                ))
            
            logger.debug(f"Retrieved {len(items)} items from behavioral memory")
            return items
            
        except Exception as e:
            logger.error(f"Behavioral memory retrieval failed: {e}")
            return []
