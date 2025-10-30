"""
Graph-Based Context Ranking

Uses knowledge graph centrality to boost important entities in context.
"""

from typing import List, Optional

from aico.core.logging import get_logger

from .models import ContextItem

logger = get_logger("ai", "memory.context.graph_ranking")


class GraphContextRanker:
    """
    Re-ranks context using knowledge graph importance scores.
    """
    
    async def rank_with_graph(
        self,
        context_items: List[ContextItem],
        user_id: str,
        kg_storage=None,
        kg_analytics=None
    ) -> List[ContextItem]:
        """
        Re-rank context items using knowledge graph centrality.
        
        Entities that are more central in the knowledge graph get higher priority.
        This ensures important/frequently-mentioned entities are prioritized.
        
        Args:
            context_items: Initial context items
            user_id: User ID
            kg_storage: PropertyGraphStorage instance (optional)
            kg_analytics: GraphAnalytics instance (optional)
            
        Returns:
            Re-ranked context items
        """
        if not kg_storage or not kg_analytics or not context_items:
            return context_items
        
        try:
            # Calculate PageRank scores for all entities
            pagerank_scores = await kg_analytics.calculate_pagerank(user_id)
            
            if not pagerank_scores:
                return context_items
            
            # Boost relevance scores based on entity importance
            for item in context_items:
                # Extract entities mentioned in this context item
                # For now, use simple keyword matching
                # In production, use NER to extract entities
                
                max_boost = 0.0
                for node_id, importance in pagerank_scores.items():
                    node = await kg_storage.get_node(node_id)
                    if node and node.properties.get('name'):
                        entity_name = node.properties['name'].lower()
                        if entity_name in item.content.lower():
                            # Boost based on entity importance
                            max_boost = max(max_boost, importance * 0.3)  # Up to 30% boost
                
                # Apply boost
                item.relevance_score = min(1.0, item.relevance_score + max_boost)
            
            # Re-sort by relevance
            context_items.sort(key=lambda x: x.relevance_score, reverse=True)
            
            logger.info(f"Re-ranked {len(context_items)} context items using graph centrality")
            
        except Exception as e:
            logger.error(f"Graph-based ranking failed: {e}")
            # Return original ranking on error
        
        return context_items
