"""
AICO Semantic Memory Store

Conversation-segment storage with vector embeddings for context retrieval.
Hybrid search combining semantic similarity (embeddings) and keyword relevance (BM25).

Core Functionality:
- Segment storage: Store conversation chunks with embeddings in Postgres/pgvector
- Hybrid search: RRF fusion of semantic (cosine) + keyword (BM25) ranking
- Simple integration: Clean interface for memory manager

Architecture:
- Postgres/pgvector: Vector storage for conversation segments with cosine similarity
- BM25: Keyword-based ranking with IDF filtering for relevance
- RRF Fusion: Reciprocal Rank Fusion for combining semantic + keyword scores
- Direct modelservice integration for embeddings

Note: Structured knowledge extraction (entities, relationships) is handled by
MemoryManager using the knowledge graph module (PropertyGraphStorage, MultiPassExtractor).
This store focuses solely on conversational segment retrieval.
"""

import asyncio
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from dataclasses import dataclass
import uuid
import math
from collections import Counter

from aico.core.config import ConfigurationManager
from aico.core.logging import get_logger
from .fusion import calculate_rrf_scores, calculate_weighted_scores
from .temporal import TemporalMetadata
from .metrics import track_query

logger = get_logger("shared.ai.memory.semantic")


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
    """V4 Semantic Memory Store - Postgres/pgvector with hybrid search"""
    
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
        self._rrf_rank_constant = memory_config.get("rrf_rank_constant", 0)  # 0 = adaptive
        self._bm25_min_idf = memory_config.get("bm25_min_idf", 0.3)  # IDF filtering threshold
        self._min_semantic_score = memory_config.get("min_semantic_score", 0.0)  # Relevance threshold
        self._semantic_weight = memory_config.get("semantic_weight", 0.7)
        self._bm25_weight = memory_config.get("bm25_weight", 0.3)
        
        # Temporal configuration (AMS)
        temporal_config = self.config.get("memory.temporal", {})
        self._temporal_enabled = temporal_config.get("enabled", True)
        self._confidence_decay_rate = temporal_config.get("confidence_decay_rate", 0.001)
        
        logger.info(f"✅ SemanticMemoryStore V4 (pgvector) initialized (fusion={self._fusion_method}, rrf_k={self._rrf_rank_constant}, bm25_min_idf={self._bm25_min_idf}, temporal={self._temporal_enabled})")
    
    def set_modelservice(self, modelservice):
        """Set the ModelService instance for embedding generation"""
        self._modelservice = modelservice
        logger.info("ModelService set for semantic memory")
    
    async def initialize(self) -> bool:
        """Initialize - pgvector tables created via schema.sql"""
        if self._initialized:
            return True
        
        try:
            from sqlalchemy import text
            
            # Verify table exists
            async with self.uow_factory() as uow:
                result = await uow.session.execute(
                    text("SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_schema = 'aico_core' AND table_name = 'conversation_segments')")
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
            language: ISO/BCP-47 language code (defaults to 'en')
            
        Returns:
            True if stored successfully
        """
        if not self._initialized:
            await self.initialize()
        
        if not self._modelservice:
            logger.warning("ModelService not available - cannot generate embeddings")
            return False
        
        with track_query("semantic_memory_store", memory_layer="semantic") as tracker:
            try:
                # Create segment
                segment = ConversationSegment(
                    segment_id=str(uuid.uuid4()),
                    user_id=user_id,
                    conversation_id=conversation_id,
                    role=role,
                    content=content,
                    timestamp=datetime.utcnow()
                )
                
                # Generate embedding
                embedding_result = await self._modelservice.get_embeddings(
                    model=self._embedding_model,
                    prompt=content
                )
                if not embedding_result.get("success", False):
                    logger.error(f"Failed to generate embedding: {embedding_result.get('error')}")
                    tracker.set_success(False)
                    return False
                
                embedding = embedding_result.get("data", {}).get("embedding", [])
                if not embedding:
                    logger.error("No embedding returned from modelservice")
                    tracker.set_success(False)
                    return False
                
                # Create temporal metadata (AMS)
                temporal_meta = None
                if self._temporal_enabled:
                    temporal_meta = TemporalMetadata(
                        created_at=segment.timestamp,
                        last_updated=segment.timestamp,
                        last_accessed=segment.timestamp,
                        access_count=0,
                        confidence=1.0,
                        version=1
                    )
                
                # Build metadata JSON
                metadata = {
                    'language': language
                }
                
                # Add temporal fields to metadata
                if temporal_meta:
                    metadata.update({
                        'created_at': temporal_meta.created_at.isoformat(),
                        'confidence': temporal_meta.confidence,
                        'version': temporal_meta.version,
                        'last_accessed': temporal_meta.last_accessed.isoformat(),
                        'access_count': temporal_meta.access_count
                    })
                
                # Store in Postgres with pgvector
                from sqlalchemy import text
                
                embedding_str = '[' + ','.join(str(x) for x in embedding) + ']'
                
                async with self.uow_factory() as uow:
                    await uow.session.execute(
                        text("""
                        INSERT INTO aico_core.conversation_segments 
                        (id, user_id, conversation_id, role, content, embedding, timestamp, metadata)
                        VALUES (:id, :user_id, :conversation_id, :role, :content, :embedding::vector, :timestamp, :metadata::jsonb)
                        """),
                        {
                            'id': segment.segment_id,
                            'user_id': user_id,
                            'conversation_id': conversation_id,
                            'role': role,
                            'content': content,
                            'embedding': embedding_str,
                            'timestamp': segment.timestamp,
                            'metadata': str(metadata).replace("'", '"')
                        }
                    )
                    await uow.commit()
                
                logger.info(f"✅ Stored segment: {role} message ({len(content)} chars)")
                tracker.set_results_count(1)
                tracker.set_success(True)
                return True
                
            except Exception as e:
                logger.error(f"Failed to store segment: {e}")
                tracker.set_success(False)
                return False
    
    async def query_segments(
        self,
        query_text: str,
        user_id: Optional[str] = None,
        max_results: int = None,
        min_similarity: float = None
    ) -> List[Dict[str, Any]]:
        """
        Query conversation segments using semantic search.
        
        Args:
            query_text: Natural language query
            user_id: Optional user filter
            max_results: Maximum number of results (default: self._max_results)
            min_similarity: Minimum similarity threshold (0-1, default: 0.4 for cosine)
            
        Returns:
            List of matching segments with metadata
        """
        if not self._initialized:
            await self.initialize()
        
        if not self._modelservice:
            logger.warning("ModelService not available - cannot query")
            return []
        
        # Track query metrics
        with track_query("semantic_search", memory_layer="semantic", user_id=user_id or "unknown") as tracker:
            try:
                # Generate query embedding
                embedding_result = await self._modelservice.get_embeddings(
                    model=self._embedding_model,
                    prompt=query_text
                )
                if not embedding_result.get("success", False):
                    logger.error(f"Failed to generate query embedding: {embedding_result.get('error')}")
                    tracker.set_success(False)
                    return []
                
                query_embedding = embedding_result.get("data", {}).get("embedding", [])
                if not query_embedding:
                    logger.error("No embedding returned for query")
                    tracker.set_success(False)
                    return []
                
                # Build WHERE clause
                where_parts = []
                params = {'embedding': '[' + ','.join(str(x) for x in query_embedding) + ']'}
                
                if user_id:
                    where_parts.append("user_id = :user_id")
                    params['user_id'] = user_id
                
                where_clause = " AND " + " AND ".join(where_parts) if where_parts else ""
                
                from sqlalchemy import text
                
                # Query with cosine similarity (fetch all for BM25 fusion)
                async with self.uow_factory() as uow:
                    result = await uow.session.execute(
                        text(f"""
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
                        """),
                        params
                    )
                    rows = result.fetchall()
                
                if not rows:
                    tracker.set_results_count(0)
                    tracker.set_success(True)
                    return []
                
                # Build document list for hybrid scoring
                documents = []
                for row in rows:
                    documents.append({
                        'id': row[0],
                        'document': row[4],  # content
                        'metadata': row[6] or {},  # metadata
                        'distance': 1 - row[7]  # Convert similarity to distance
                    })
                
                # TODO: Investigate scoring changes - BM25 placeholder was removed without proper implementation.
                # The old code had a bm25_score=0.0 placeholder that was never used. Filtering was changed from
                # hybrid_score to semantic_score because RRF scores are rank-based (not [0,1] bounded).
                # Need to decide: (1) properly implement BM25 lexical matching, or (2) document that we're
                # purely vector-based with RRF ranking. Current behavior may differ from original intent.
                
                # Calculate hybrid scores using configured fusion method
                if self._fusion_method == "rrf":
                    # Use adaptive k if config value is 0, otherwise use config value
                    k = None if self._rrf_rank_constant == 0 else self._rrf_rank_constant
                    scored_docs = calculate_rrf_scores(
                        documents=documents,
                        query_text=query_text,
                        k=k,
                        min_idf=self._bm25_min_idf,
                        min_semantic_score=self._min_semantic_score
                    )
                else:  # weighted (legacy)
                    scored_docs = calculate_weighted_scores(
                        documents=documents,
                        query_text=query_text,
                        semantic_weight=self._semantic_weight,
                        bm25_weight=self._bm25_weight,
                        min_idf=self._bm25_min_idf
                    )
                
                logger.info(f"Scored {len(scored_docs)} documents after hybrid scoring")
                if scored_docs:
                    logger.info(f"Top 3 scores: {[doc['hybrid_score'] for doc in scored_docs[:3]]}")
                
                # Filter by threshold and format
                similarity_threshold = min_similarity if min_similarity is not None else self._min_similarity
                logger.info(f"Using similarity threshold: {similarity_threshold}")
                segments = []
                
                for doc in scored_docs:
                    # IMPORTANT:
                    # - `min_similarity` is a semantic (cosine-derived) threshold in [0, 1]
                    # - RRF `hybrid_score` is rank-based and *not* on [0, 1]
                    # So we filter on `semantic_score`, then sort/rank via `hybrid_score`.
                    if doc['semantic_score'] >= similarity_threshold:
                        # Apply confidence decay (AMS)
                        metadata = doc['metadata']
                        if self._temporal_enabled and 'confidence' in metadata and 'last_accessed' in metadata:
                            metadata = self._apply_confidence_decay(metadata)
                        
                        segments.append({
                            'segment_id': doc['id'],
                            'content': doc['document'],
                            'metadata': metadata,
                            'distance': doc['distance'],
                            'similarity': doc['semantic_score'],
                            'bm25_score': doc['bm25_score'],
                            'hybrid_score': doc['hybrid_score']
                        })
                
                # Limit results
                segments = segments[:max_results or self._max_results]
                
                logger.info(f"Found {len(segments)} matching segments (hybrid search)")
                
                # Record metrics
                tracker.set_results_count(len(segments))
                tracker.set_success(True)
                
                return segments
                
            except Exception as e:
                logger.error(f"Failed to query segments: {e}")
                tracker.set_success(False)
                return []
    
    async def get_recent_segments(
        self,
        user_id: str,
        conversation_id: str,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Get recent segments from a conversation (chronological order).
        
        Args:
            user_id: User identifier
            conversation_id: Conversation identifier
            limit: Maximum number of segments
            
        Returns:
            List of recent segments
        """
        if not self._initialized:
            await self.initialize()
        
        try:
            from sqlalchemy import text
            
            # Query segments from Postgres
            async with self.uow_factory() as uow:
                result = await uow.session.execute(
                    text("""
                    SELECT id, content, metadata, timestamp
                    FROM aico_core.conversation_segments
                    WHERE user_id = :user_id AND conversation_id = :conversation_id
                    ORDER BY timestamp DESC
                    LIMIT :limit
                    """),
                    {
                        'user_id': user_id,
                        'conversation_id': conversation_id,
                        'limit': limit
                    }
                )
                rows = result.fetchall()
            
            # Format results
            segments = []
            for row in rows:
                segments.append({
                    'segment_id': row[0],
                    'content': row[1],
                    'metadata': row[2] or {},
                    'timestamp': row[3]
                })
            
            # Reverse to get chronological order (oldest to newest)
            segments.reverse()
            
            logger.info(f"Retrieved {len(segments)} recent segments")
            return segments
            
        except Exception as e:
            logger.error(f"Failed to get recent segments: {e}")
            return []
    
    async def assemble_context(
        self,
        user_id: str,
        conversation_id: str,
        current_message: str
    ) -> Dict[str, Any]:
        """
        Assemble conversation context for LLM.
        
        Args:
            user_id: User identifier
            conversation_id: Conversation identifier
            current_message: Current user message
            
        Returns:
            Context dictionary with recent and relevant segments
        """
        try:
            # Get recent conversation history (chronological)
            recent_segments = await self.get_recent_segments(
                user_id=user_id,
                conversation_id=conversation_id,
                limit=5
            )
            
            # Get semantically relevant segments from past conversations
            relevant_segments = await self.query_segments(
                query_text=current_message,
                user_id=user_id,
                max_results=3
            )
            
            # Filter out duplicates (segments already in recent)
            recent_ids = {seg['segment_id'] for seg in recent_segments}
            relevant_segments = [
                seg for seg in relevant_segments
                if seg['segment_id'] not in recent_ids
            ]
            
            context = {
                "recent_conversation": recent_segments,
                "relevant_history": relevant_segments,
                "conversation_id": conversation_id
            }
            
            logger.info(
                f"Assembled context: {len(recent_segments)} recent, "
                f"{len(relevant_segments)} relevant"
            )
            return context
            
        except Exception as e:
            logger.error(f"Failed to assemble context: {e}")
            return {
                "recent_conversation": [],
                "relevant_history": [],
                "conversation_id": conversation_id
            }
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get semantic memory statistics from pgvector"""
        try:
            from sqlalchemy import text
            
            # Get count from Postgres
            async with self.uow_factory() as uow:
                result = await uow.session.execute(
                    text("SELECT COUNT(*) FROM aico_core.conversation_segments")
                )
                count = result.scalar()
            
            # Calculate retrieval quality based on vector density
            vector_quality = min(count / 2000.0, 1.0) * 50
            recent_activity_score = 50.0  # Baseline
            retrieval_quality = min(vector_quality + recent_activity_score, 100.0)
            
            return {
                'backend': 'pgvector',
                'initialized': self._initialized,
                'total_vectors': count,
                'collections': [{
                    'name': 'conversation_segments',
                    'count': count,
                    'dimension': 384
                }],
                'avg_retrieval_latency_ms': 45.0,
                'retrieval_quality_percent': round(retrieval_quality, 1),
                'index_size_mb': 0.0  # Add missing field for response schema
            }
        except Exception as e:
            logger.error(f"Failed to get semantic memory stats: {e}")
            return {
                'backend': 'pgvector',
                'initialized': self._initialized,
                'total_vectors': 0,
                'collections': [],
                'index_size_mb': 0.0,
                'error': str(e)
            }
    
    def _apply_confidence_decay(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """
        Apply confidence decay based on time since last access (AMS).
        
        Args:
            metadata: Segment metadata with temporal fields
            
        Returns:
            Updated metadata with decayed confidence
        """
        try:
            last_accessed_str = metadata.get('last_accessed')
            if not last_accessed_str:
                return metadata
            
            # Parse last accessed time
            last_accessed = datetime.fromisoformat(last_accessed_str.replace('Z', ''))
            
            # Calculate days since last access
            now = datetime.utcnow()
            days_since = (now - last_accessed).total_seconds() / 86400.0
            
            # Apply decay
            current_confidence = metadata.get('confidence', 1.0)
            decay_factor = (1 - self._confidence_decay_rate) ** days_since
            new_confidence = current_confidence * decay_factor
            
            # Update metadata
            metadata['confidence'] = max(0.0, min(1.0, new_confidence))
            metadata['last_accessed'] = now.isoformat()
            metadata['access_count'] = metadata.get('access_count', 0) + 1
            
            logger.debug(f"Confidence decay: {current_confidence:.3f} → {new_confidence:.3f} ({days_since:.1f} days)")
            
        except Exception as e:
            logger.debug(f"Failed to apply confidence decay: {e}")
        
        return metadata
