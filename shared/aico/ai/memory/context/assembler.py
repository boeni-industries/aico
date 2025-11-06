"""
Context Assembler

Main orchestrator for cross-tier context assembly.
"""

import asyncio
from typing import Dict, List, Optional, Any
from datetime import datetime

from aico.core.logging import get_logger

from .models import ContextItem
from .retrievers import ContextRetrievers
from .scorers import ContextScorer
from .graph_ranking import GraphContextRanker

logger = get_logger("ai", "memory.context.assembler")


class ContextAssembler:
    """
    Cross-tier memory context assembly coordinator.
    
    Retrieves and combines relevant context from all memory tiers:
    - Working memory: Current session context
    - Episodic memory: Conversation history
    - Semantic memory: Related knowledge
    - Behavioral memory: User patterns, skills, and preferences
    
    Provides unified, prioritized context for AI processing.
    """
    
    def __init__(self, working_store, episodic_store, semantic_store, behavioral_store, kg_storage=None, kg_modelservice=None, db_connection=None):
        """
        Initialize context assembler.
        
        Args:
            working_store: Working memory store
            episodic_store: Episodic memory store
            semantic_store: Semantic memory store
            behavioral_store: Behavioral memory store
            kg_storage: Knowledge graph storage (optional)
            kg_modelservice: KG modelservice client (optional)
            db_connection: Database connection for KG queries (optional)
        """
        self.retrievers = ContextRetrievers(
            working_store,
            episodic_store,
            semantic_store,
            behavioral_store
        )
        
        self.scorer = ContextScorer()
        self.graph_ranker = GraphContextRanker()
        
        # KG components
        self.kg_storage = kg_storage
        self.kg_modelservice = kg_modelservice
        self.db_connection = db_connection
        
        # Configuration
        self._max_context_items = 50
        self._relevance_threshold = 0.3
    
    async def assemble_context(
        self,
        user_id: str,
        current_message: str,
        max_context_items: int = None,
        conversation_id: str = None
    ) -> Dict[str, Any]:
        """
        Assemble comprehensive context from all memory tiers.
        
        Args:
            user_id: User ID
            current_message: Current message text
            max_context_items: Maximum context items to return
            conversation_id: Optional conversation ID
            
        Returns:
            Dictionary with assembled context and metadata
        """
        max_items = max_context_items or self._max_context_items
        assembly_start = datetime.utcnow()
        
        try:
            logger.info(f"Assembling context for user {user_id}")
            
            all_items = []
            
            # 1. Get working memory context (immediate conversation)
            try:
                working_items = await self.retrievers.get_working_context(user_id, conversation_id)
                all_items.extend(working_items or [])
                logger.debug(f"Retrieved {len(working_items or [])} items from working memory")
            except Exception as e:
                logger.warning(f"Working memory context retrieval failed: {e}")
            
            # 2. Get semantic memory context (knowledge base)
            try:
                semantic_items = await self.retrievers.get_semantic_context(
                    user_id,
                    current_message,
                    limit=10
                )
                all_items.extend(semantic_items or [])
                logger.debug(f"Retrieved {len(semantic_items or [])} items from semantic memory")
            except Exception as e:
                logger.warning(f"Semantic memory context retrieval failed: {e}")
            
            # 3. Get episodic memory context (conversation history)
            if self.retrievers.episodic_store:
                try:
                    episodic_items = await self.retrievers.get_episodic_context(
                        user_id,
                        current_message,
                        limit=5
                    )
                    all_items.extend(episodic_items or [])
                    logger.debug(f"Retrieved {len(episodic_items or [])} items from episodic memory")
                except Exception as e:
                    logger.warning(f"Episodic memory context retrieval failed: {e}")
            
            # 4. Get behavioral memory context (user patterns, skills, preferences)
            if self.retrievers.behavioral_store:
                try:
                    behavioral_items = await self.retrievers.get_behavioral_context(user_id)
                    all_items.extend(behavioral_items or [])
                    logger.debug(f"Retrieved {len(behavioral_items or [])} items from behavioral memory")
                except Exception as e:
                    logger.warning(f"Behavioral memory context retrieval failed: {e}")
            
            # 4.5 Get knowledge graph context (entities and relationships)
            kg_context = {}
            if self.kg_storage and self.kg_modelservice:
                try:
                    print(f"🕸️ [KG_CONTEXT] Retrieving KG context for query: {current_message[:50]}...")
                    
                    # Search for relevant nodes
                    kg_nodes = await self.kg_storage.search_nodes(
                        current_message, 
                        user_id, 
                        top_k=5
                    )
                    
                    # Get edges connecting these nodes
                    kg_edges = []
                    if kg_nodes and self.db_connection:
                        node_ids = [node.id for node in kg_nodes]
                        
                        # Query edges that connect any of these nodes
                        placeholders = ','.join(['?' for _ in node_ids])
                        edge_query = f"""
                            SELECT 
                                e.id, e.relation_type, e.confidence,
                                n1.properties as source_props,
                                n2.properties as target_props
                            FROM kg_edges e
                            JOIN kg_nodes n1 ON e.source_id = n1.id
                            JOIN kg_nodes n2 ON e.target_id = n2.id
                            WHERE e.user_id = ? 
                            AND e.is_current = 1
                            AND (e.source_id IN ({placeholders}) OR e.target_id IN ({placeholders}))
                            LIMIT 10
                        """
                        
                        params = [user_id] + node_ids + node_ids
                        
                        def _get_edges():
                            with self.db_connection:
                                return self.db_connection.execute(edge_query, params).fetchall()
                        
                        edge_results = await asyncio.to_thread(_get_edges)
                        
                        import json
                        for row in edge_results:
                            source_props = json.loads(row[3])
                            target_props = json.loads(row[4])
                            kg_edges.append({
                                "relation": row[1],
                                "source": source_props.get("name", "?"),
                                "target": target_props.get("name", "?"),
                                "confidence": row[2]
                            })
                    
                    kg_context = {
                        "entities": [
                            {
                                "name": node.properties.get("name", "?"),
                                "type": node.label,
                                "confidence": node.confidence
                            }
                            for node in kg_nodes
                        ],
                        "relationships": kg_edges
                    }
                    
                    print(f"🕸️ [KG_CONTEXT] Retrieved {len(kg_nodes)} entities, {len(kg_edges)} relationships")
                    logger.debug(f"Retrieved {len(kg_nodes)} KG entities, {len(kg_edges)} relationships")
                    
                except Exception as e:
                    logger.warning(f"Knowledge graph context retrieval failed: {e}")
                    print(f"🕸️ [KG_CONTEXT] ❌ Failed to retrieve KG context: {e}")
                    import traceback
                    print(f"🕸️ [KG_CONTEXT] Traceback:\n{traceback.format_exc()}")
            
            # 5. Score and rank context items
            ranked_items = self.scorer.score_and_rank(all_items, max_items=max_items)
            
            # 6. Calculate conversation strength
            conversation_strength = self.scorer.calculate_conversation_strength(ranked_items)
            
            # 7. Format context for LLM
            memory_context = self._format_context(ranked_items)
            
            # Calculate assembly time
            assembly_time = (datetime.utcnow() - assembly_start).total_seconds() * 1000
            
            logger.info(
                f"Context assembly complete: {len(ranked_items)} items, "
                f"strength={conversation_strength:.2f}, time={assembly_time:.1f}ms"
            )
            
            result = {
                "memory_context": memory_context,
                "knowledge_graph": kg_context,
                "metadata": {
                    "total_items": len(ranked_items),
                    "conversation_strength": conversation_strength,
                    "assembly_time_ms": assembly_time,
                    "tiers_accessed": self._get_accessed_tiers(ranked_items)
                }
            }
            
            print(f"🔍 [ASSEMBLER_DEBUG] Returning context with KG: {bool(kg_context)}")
            print(f"🔍 [ASSEMBLER_DEBUG] KG entities: {len(kg_context.get('entities', []))}, relationships: {len(kg_context.get('relationships', []))}")
            
            return result
            
        except Exception as e:
            logger.error(f"Context assembly failed: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return {
                "memory_context": {"user_facts": [], "recent_context": []},
                "metadata": {"error": str(e)}
            }
    
    async def rank_context_with_graph(
        self,
        context_items: List[ContextItem],
        user_id: str,
        kg_storage=None,
        kg_analytics=None
    ) -> List[ContextItem]:
        """
        Re-rank context items using knowledge graph centrality.
        
        Args:
            context_items: Initial context items
            user_id: User ID
            kg_storage: PropertyGraphStorage instance (optional)
            kg_analytics: GraphAnalytics instance (optional)
            
        Returns:
            Re-ranked context items
        """
        return await self.graph_ranker.rank_with_graph(
            context_items,
            user_id,
            kg_storage,
            kg_analytics
        )
    
    def _format_context(self, items: List[ContextItem]) -> Dict[str, Any]:
        """
        Format context items for LLM consumption.
        
        Args:
            items: Ranked context items
            
        Returns:
            Formatted context dictionary
        """
        # Separate by type
        facts = [item for item in items if item.item_type in ['knowledge', 'pattern']]
        messages = [item for item in items if item.item_type == 'message']
        
        return {
            "user_facts": [
                {
                    "content": item.content,
                    "source": item.source_tier,
                    "confidence": item.relevance_score
                }
                for item in facts
            ],
            "recent_context": [
                {
                    "content": item.content,
                    "role": item.metadata.get('role', 'user'),
                    "timestamp": item.timestamp.isoformat()
                }
                for item in messages
            ]
        }
    
    def _get_accessed_tiers(self, items: List[ContextItem]) -> List[str]:
        """Get list of memory tiers that were accessed."""
        tiers = set(item.source_tier for item in items)
        return sorted(list(tiers))
    
    async def query_memories(self, query) -> Any:
        """
        Query memories across tiers (legacy compatibility).
        
        Args:
            query: Memory query object
            
        Returns:
            Query results
        """
        # Legacy method for compatibility
        # In practice, use assemble_context instead
        logger.warning("query_memories is deprecated, use assemble_context instead")
        return None
    
    async def get_user_context(self, user_id: str) -> Dict[str, Any]:
        """
        Get user context for thread resolution (legacy compatibility).
        
        Args:
            user_id: User ID
            
        Returns:
            User context dictionary
        """
        # Simplified version for thread resolution
        try:
            working_items = await self.retrievers.get_working_context(user_id)
            
            return {
                "user_id": user_id,
                "working_memory": [item.content for item in working_items],
                "context_strength": self.scorer.calculate_conversation_strength(working_items)
            }
        except Exception as e:
            logger.error(f"Failed to get user context: {e}")
            return {"user_id": user_id, "context_strength": 0.0}
