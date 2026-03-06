"""
AICO Semantic Memory Store - Postgres/pgvector Backend

Conversation-segment storage with vector embeddings for context retrieval.
Hybrid search combining semantic similarity (pgvector) and keyword relevance (BM25).

Replaces ChromaDB with Postgres + pgvector for:
- Better integration with existing Postgres infrastructure
- Transactional consistency with relational data
- Simpler deployment (one database instead of two)
"""

import asyncio
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from dataclasses import dataclass
import uuid

from aico.core.config import ConfigurationManager
from aico.core.logging import get_logger
from .fusion import calculate_rrf_scores, calculate_weighted_scores
from .temporal import TemporalMetadata
from .metrics import track_query

logger = get_logger("shared.ai.memory.semantic_pgvector")


@dataclass
class ConversationSegment:
    """A chunk of conversation with metadata"""
    segment_id: str
    user_id: str
    conversation_id: str
    role: str  # 'user' or 'assistant'
    content: str
    timestamp: datetime
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage"""
        return {
            'segment_id': self.segment_id,
            'user_id': self.user_id,
            'conversation_id': self.conversation_id,
            'role': self.role,
            'content': self.content,
            'timestamp': self.timestamp.isoformat()
        }


class SemanticMemoryStore:
    """Semantic Memory Store - Postgres/pgvector backend with hybrid search"""
    
    def __init__(self, config_manager: ConfigurationManager, uow_factory):
        self.config = config_manager
        self.uow_factory = uow_factory
        self._initialized = False
        self._modelservice = None
        
        # Configuration
        memory_config = self.config.get("memory.semantic", {})
        self._embedding_model = "paraphrase-multilingual"
        self._max_results = memory_config.get("max_results", 10)
        self._min_similarity = memory_config.get("min_similarity", 0.4)
        
        # Hybrid search configuration
        self._fusion_method = memory_config.get("fusion_method", "rrf")
        self._rrf_rank_constant = memory_config.get("rrf_rank_constant", 0)
        self._bm25_min_idf = memory_config.get("bm25_min_idf", 0.3)
        self._min_semantic_score = memory_config.get("min_semantic_score", 0.0)
        self._semantic_weight = memory_config.get("semantic_weight", 0.7)
        self._bm25_weight = memory_config.get("bm25_weight", 0.3)
        
        # Temporal configuration
        temporal_config = self.config.get("memory.temporal", {})
        self._temporal_enabled = temporal_config.get("enabled", True)
        self._confidence_decay_rate = temporal_config.get("confidence_decay_rate", 0.001)
        
        logger.info(
            f"✅ SemanticMemoryStore (pgvector) initialized "
            f"(fusion={self._fusion_method}, rrf_k={self._rrf_rank_constant}, "
            f"bm25_min_idf={self._bm25_min_idf}, temporal={self._temporal_enabled})"
        )
    
    def set_modelservice(self, modelservice):
        """Set the ModelService instance for embedding generation"""
        self._modelservice = modelservice
        logger.info("ModelService set for semantic memory (pgvector)")
    
    async def initialize(self) -> bool:
        """Initialize - pgvector tables created via schema.sql"""
        if self._initialized:
            return True
        
        try:
            # Verify table exists
            async with self.uow_factory() as uow:
                result = await uow.session.execute(
                    "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_schema = 'aico_core' AND table_name = 'conversation_segments')"
                )
                exists = result.scalar()
                
                if not exists:
                    logger.error("conversation_segments table not found - run schema init")
                    return False
            
            self._initialized = True
            logger.info("✅ Semantic memory (pgvector) initialized")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize semantic memory (pgvector): {e}")
            return False
    
    async def store_segment(
        self,
        user_id: str,
        conversation_id: str,
        role: str,
        content: str,
        language: str = "en"
    ) -> bool:
        """
        Store a conversation segment with embedding.
        
        Args:
            user_id: User identifier
            conversation_id: Conversation identifier
            role: 'user' or 'assistant'
            content: Message content
            language: ISO/BCP-47 language code
            
        Returns:
            True if stored successfully
        """
        if not self._initialized:
            await self.initialize()
        
        if not self._modelservice:
            logger.error("ModelService not available for embeddings")
            return False
        
        try:
            # Generate embedding
            embedding_result = await self._modelservice.generate_embeddings([content])
            if not embedding_result or not embedding_result.get('embeddings'):
                logger.error("Failed to generate embedding")
                return False
            
            embedding = embedding_result['embeddings'][0]
            
            # Store in Postgres
            segment_id = str(uuid.uuid4())
            timestamp = datetime.utcnow()
            
            async with self.uow_factory() as uow:
                await uow.session.execute(
                    """
                    INSERT INTO aico_core.conversation_segments 
                    (id, user_id, conversation_id, role, content, embedding, timestamp, metadata)
                    VALUES (:id, :user_id, :conversation_id, :role, :content, :embedding::vector, :timestamp, :metadata::jsonb)
                    """,
                    {
                        'id': segment_id,
                        'user_id': user_id,
                        'conversation_id': conversation_id,
                        'role': role,
                        'content': content,
                        'embedding': '[' + ','.join(str(x) for x in embedding) + ']',
                        'timestamp': timestamp,
                        'metadata': '{"language": "' + language + '"}'
                    }
                )
                await uow.commit()
            
            logger.debug(f"Stored segment {segment_id} for user {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to store segment: {e}")
            return False
    
    async def query_segments(
        self,
        query_text: str,
        user_id: Optional[str] = None,
        conversation_id: Optional[str] = None,
        max_results: int = 10,
        min_similarity: float = 0.4
    ) -> List[Dict[str, Any]]:
        """
        Query conversation segments using hybrid search.
        
        Args:
            query_text: Search query
            user_id: Filter by user
            conversation_id: Filter by conversation
            max_results: Maximum results to return
            min_similarity: Minimum similarity threshold
            
        Returns:
            List of matching segments with scores
        """
        if not self._initialized:
            await self.initialize()
        
        if not self._modelservice:
            logger.error("ModelService not available for query embeddings")
            return []
        
        try:
            # Generate query embedding
            embedding_result = await self._modelservice.generate_embeddings([query_text])
            if not embedding_result or not embedding_result.get('embeddings'):
                logger.error("Failed to generate query embedding")
                return []
            
            query_embedding = embedding_result['embeddings'][0]
            embedding_str = '[' + ','.join(str(x) for x in query_embedding) + ']'
            
            # Build WHERE clause
            where_parts = []
            params = {'embedding': embedding_str, 'limit': max_results * 3}
            
            if user_id:
                where_parts.append("user_id = :user_id")
                params['user_id'] = user_id
            if conversation_id:
                where_parts.append("conversation_id = :conversation_id")
                params['conversation_id'] = conversation_id
            
            where_clause = " AND " + " AND ".join(where_parts) if where_parts else ""
            
            # Query with cosine similarity
            async with self.uow_factory() as uow:
                result = await uow.session.execute(
                    f"""
                    SELECT 
                        id,
                        user_id,
                        conversation_id,
                        role,
                        content,
                        timestamp,
                        metadata,
                        1 - (embedding <=> :embedding::vector) as similarity
                    FROM aico_core.conversation_segments
                    WHERE 1=1 {where_clause}
                    ORDER BY embedding <=> :embedding::vector
                    LIMIT :limit
                    """,
                    params
                )
                rows = result.fetchall()
            
            # Convert to documents for BM25 fusion
            documents = []
            for row in rows:
                documents.append({
                    'segment_id': row[0],
                    'user_id': row[1],
                    'conversation_id': row[2],
                    'role': row[3],
                    'content': row[4],
                    'timestamp': row[5],
                    'metadata': row[6] or {},
                    'distance': 1 - row[7],  # Convert similarity back to distance for fusion
                    'document': row[4]  # For BM25
                })
            
            # Apply hybrid search fusion
            if self._fusion_method == "rrf":
                k = None if self._rrf_rank_constant == 0 else self._rrf_rank_constant
                scored_documents = calculate_rrf_scores(
                    documents=documents,
                    query_text=query_text,
                    k=k,
                    min_idf=self._bm25_min_idf,
                    min_semantic_score=self._min_semantic_score
                )
            else:
                scored_documents = calculate_weighted_scores(
                    documents=documents,
                    query_text=query_text,
                    semantic_weight=self._semantic_weight,
                    bm25_weight=self._bm25_weight,
                    min_idf=self._bm25_min_idf
                )
            
            # Filter by minimum similarity and limit
            results = [
                doc for doc in scored_documents
                if doc.get('hybrid_score', 0) >= min_similarity
            ][:max_results]
            
            logger.debug(f"Query returned {len(results)} segments (hybrid search)")
            return results
            
        except Exception as e:
            logger.error(f"Failed to query segments: {e}")
            return []
    
    def get_stats(self) -> Dict[str, Any]:
        """Get semantic memory statistics"""
        # TODO: Implement stats query
        return {
            'backend': 'pgvector',
            'initialized': self._initialized,
            'total_segments': 0  # Placeholder
        }
