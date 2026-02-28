"""
Semantic Entity Ranker for Knowledge Graph Extraction.

Implements two-stage semantic retrieval:
1. Semantic similarity search using pgvector embeddings
2. Multi-factor reranking (semantic, temporal, centrality, frequency)

Follows AICO guidelines: DRY, KISS, explicit over implicit.
"""

import logging
from datetime import datetime, UTC
from math import exp
from typing import List, Tuple, Dict, Any, Optional

from aico.ai.knowledge_graph.models import Node

logger = logging.getLogger(__name__)


class SemanticEntityRanker:
    """
    Ranks entities by semantic relevance to current text.
    
    Uses pgvector embeddings and HNSW index for fast similarity search.
    Applies multi-factor scoring to select most relevant entities for LLM context.
    
    Scoring Factors:
    - Semantic relevance (40%): Cosine similarity from pgvector
    - Temporal recency (30%): Exponential decay with 30-day half-life
    - Graph centrality (20%): PageRank score (future implementation)
    - Co-occurrence frequency (10%): Entity mention count
    """
    
    def __init__(
        self,
        modelservice_client,
        uow_factory
    ):
        """
        Initialize semantic entity ranker.
        
        Args:
            modelservice_client: Client for generating embeddings
            uow_factory: Unit of Work factory for PostgreSQL access
        """
        self.modelservice = modelservice_client
        self.uow_factory = uow_factory
        
        # Scoring weights (tunable)
        self.SEMANTIC_WEIGHT = 0.4
        self.TEMPORAL_WEIGHT = 0.3
        self.CENTRALITY_WEIGHT = 0.2
        self.FREQUENCY_WEIGHT = 0.1
        
        # Temporal decay half-life in days
        self.TEMPORAL_HALFLIFE = 30.0
        
        logger.info(
            f"🎯 [SEMANTIC_RANKER] Initialized with weights: "
            f"semantic={self.SEMANTIC_WEIGHT}, temporal={self.TEMPORAL_WEIGHT}, "
            f"centrality={self.CENTRALITY_WEIGHT}, frequency={self.FREQUENCY_WEIGHT}"
        )
    
    async def rank_entities(
        self,
        text: str,
        user_id: str,
        existing_entities: List[Dict[str, Any]],
        max_results: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Rank entities by composite relevance score.
        
        Two-stage process:
        1. Semantic search in ChromaDB (top 30-50 candidates)
        2. Multi-factor reranking (top max_results)
        
        Args:
            text: Current text to extract relationships from
            user_id: User ID for entity filtering
            existing_entities: List of entity dicts with 'id', 'name', 'label'
            max_results: Number of top entities to return
            
        Returns:
            List of entity dicts, ranked by relevance (highest first)
        """
        if not existing_entities:
            return []
        
        if len(existing_entities) <= max_results:
            # No ranking needed
            return existing_entities
        
        logger.info(
            f"🎯 [SEMANTIC_RANKER] Ranking {len(existing_entities)} entities "
            f"for text: '{text[:50]}...'"
        )
        
        # Stage 1: Semantic similarity search
        semantic_candidates = await self._semantic_search(
            text=text,
            user_id=user_id,
            n_results=min(len(existing_entities), max_results * 2)  # Get 2x for reranking
        )
        
        if not semantic_candidates:
            # Fallback to most recent if semantic search fails
            logger.warning("🎯 [SEMANTIC_RANKER] Semantic search failed, using recency fallback")
            return existing_entities[-max_results:]
        
        # Stage 2: Multi-factor reranking
        ranked_entities = await self._rerank_entities(
            candidates=semantic_candidates,
            existing_entities=existing_entities,
            max_results=max_results
        )
        
        logger.info(
            f"🎯 [SEMANTIC_RANKER] ✅ Ranked {len(ranked_entities)} entities "
            f"(avg score: {sum(e.get('_rank_score', 0) for e in ranked_entities) / len(ranked_entities):.3f})"
        )
        
        return ranked_entities
    
    async def _semantic_search(
        self,
        text: str,
        user_id: str,
        n_results: int
    ) -> List[Tuple[str, float]]:
        """
        Perform semantic similarity search using pgvector.
        
        Args:
            text: Query text
            user_id: User ID for filtering
            n_results: Number of results to return
            
        Returns:
            List of (entity_id, similarity_score) tuples
        """
        try:
            # Get text embedding from modelservice
            embedding_response = await self.modelservice.generate_embeddings([text])
            if not embedding_response or not embedding_response.get('embeddings'):
                logger.error("🎯 [SEMANTIC_RANKER] Failed to generate text embedding")
                return []
            
            text_embedding = embedding_response['embeddings'][0]
            embedding_str = '[' + ','.join(str(x) for x in text_embedding) + ']'
            
            # Query pgvector for similar entities
            async with self.uow_factory() as uow:
                result = await uow.session.execute(
                    """
                    SELECT 
                        e.node_id,
                        1 - (e.embedding <=> :embedding::vector) as similarity
                    FROM aico_core.kg_node_embeddings e
                    JOIN aico_core.kg_nodes n ON e.node_id = n.id
                    WHERE n.user_id = :user_id AND n.is_current = true
                    ORDER BY e.embedding <=> :embedding::vector
                    LIMIT :limit
                    """,
                    {
                        'embedding': embedding_str,
                        'user_id': user_id,
                        'limit': n_results
                    }
                )
                rows = result.fetchall()
            
            if not rows:
                return []
            
            # Extract (id, similarity) pairs
            candidates = [(row[0], row[1]) for row in rows]
            
            logger.info(
                f"🎯 [SEMANTIC_RANKER] Found {len(candidates)} semantic candidates "
                f"(top similarity: {candidates[0][1]:.3f})"
            )
            
            return candidates
            
        except Exception as e:
            logger.error(f"🎯 [SEMANTIC_RANKER] Semantic search failed: {e}")
            return []
    
    async def _rerank_entities(
        self,
        candidates: List[Tuple[str, float]],
        existing_entities: List[Dict[str, Any]],
        max_results: int
    ) -> List[Dict[str, Any]]:
        """
        Apply multi-factor reranking to semantic candidates.
        
        Args:
            candidates: List of (entity_id, semantic_score) from pgvector
            existing_entities: Full list of entity dicts
            max_results: Number of top entities to return
            
        Returns:
            Top-ranked entities with composite scores
        """
        # Build entity lookup by ID
        entity_by_id = {e.get('id'): e for e in existing_entities if e.get('id')}
        
        # Calculate composite scores
        scored_entities = []
        now = datetime.now(UTC)
        
        for entity_id, semantic_score in candidates:
            entity = entity_by_id.get(entity_id)
            if not entity:
                continue
            
            # Calculate composite score
            composite_score = self._calculate_composite_score(
                entity=entity,
                semantic_score=semantic_score,
                now=now
            )
            
            # Attach score to entity for debugging
            entity['_rank_score'] = composite_score
            entity['_semantic_score'] = semantic_score
            
            scored_entities.append((composite_score, entity))
        
        # Sort by composite score (descending)
        scored_entities.sort(key=lambda x: x[0], reverse=True)
        
        # Return top entities
        top_entities = [entity for score, entity in scored_entities[:max_results]]
        
        return top_entities
    
    def _calculate_composite_score(
        self,
        entity: Dict[str, Any],
        semantic_score: float,
        now: datetime
    ) -> float:
        """
        Calculate composite relevance score for entity.
        
        Args:
            entity: Entity dict with metadata
            semantic_score: Semantic similarity score from ChromaDB
            now: Current timestamp for temporal decay
            
        Returns:
            Composite score ∈ [0, 1]
        """
        # Semantic relevance (40%)
        semantic_component = semantic_score * self.SEMANTIC_WEIGHT
        
        # Temporal recency (30%) - exponential decay
        created_at = entity.get('created_at')
        if created_at:
            if isinstance(created_at, str):
                created_at = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
            days_old = (now - created_at).days
            temporal_score = exp(-days_old / self.TEMPORAL_HALFLIFE)
        else:
            temporal_score = 0.5  # Default if no timestamp
        temporal_component = temporal_score * self.TEMPORAL_WEIGHT
        
        # Graph centrality (20%) - placeholder for future PageRank
        # TODO: Implement PageRank calculation
        centrality_score = 0.5  # Neutral default
        centrality_component = centrality_score * self.CENTRALITY_WEIGHT
        
        # Co-occurrence frequency (10%)
        # Normalize mention count to [0, 1] with soft cap at 100
        mention_count = entity.get('mention_count', 1)
        frequency_score = min(mention_count / 100.0, 1.0)
        frequency_component = frequency_score * self.FREQUENCY_WEIGHT
        
        composite = (
            semantic_component +
            temporal_component +
            centrality_component +
            frequency_component
        )
        
        return composite
