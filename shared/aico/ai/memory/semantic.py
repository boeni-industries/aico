"""
AICO Semantic Memory Store

Conversation-segment storage with vector embeddings for context retrieval.
Hybrid search combining semantic similarity (embeddings) and keyword relevance (BM25).

Core Functionality:
- Segment storage: Store conversation chunks with embeddings in ChromaDB
- Hybrid search: RRF fusion of semantic (cosine) + keyword (BM25) ranking
- Simple integration: Clean interface for memory manager

Architecture:
- ChromaDB: Vector storage for conversation segments with cosine similarity
- BM25: Keyword-based ranking with IDF filtering for relevance
- RRF Fusion: Reciprocal Rank Fusion for combining semantic + keyword scores
- Direct modelservice integration for embeddings

Note: Structured knowledge extraction (entities, relationships) is handled by
MemoryManager using the knowledge graph module (PropertyGraphStorage, MultiPassExtractor).
This store focuses solely on conversational segment retrieval.
"""

import asyncio
from typing import Dict, List, Optional, Any
from datetime import datetime
from dataclasses import dataclass
import uuid
import math
from collections import Counter
import chromadb
from chromadb.config import Settings

from aico.core.config import ConfigurationManager
from aico.core.paths import AICOPaths
from aico.core.logging import get_logger
from .fusion import calculate_rrf_scores, calculate_weighted_scores

logger = get_logger("shared", "ai.memory.semantic")


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
    """V3 Semantic Memory Store - Hybrid search with BM25 + semantic"""
    
    def __init__(self, config_manager: ConfigurationManager):
        self.config = config_manager
        self._initialized = False
        self._chroma_client = None
        self._collection = None
        self._modelservice = None
        
        # Configuration
        memory_config = self.config.get("core.memory.semantic", {})
        self._db_path = AICOPaths.get_semantic_memory_path()
        self._collection_name = "conversation_segments"
        self._embedding_model = "paraphrase-multilingual"
        self._max_results = memory_config.get("max_results", 10)
        self._min_similarity = memory_config.get("min_similarity", 0.4)
        
        # Hybrid search configuration
        self._fusion_method = memory_config.get("fusion_method", "rrf")
        self._rrf_rank_constant = memory_config.get("rrf_rank_constant", 0)  # 0 = adaptive
        self._bm25_min_idf = memory_config.get("bm25_min_idf", 0.6)  # IDF filtering threshold
        self._min_semantic_score = memory_config.get("min_semantic_score", 0.35)  # Relevance threshold
        self._semantic_weight = memory_config.get("semantic_weight", 0.7)
        self._bm25_weight = memory_config.get("bm25_weight", 0.3)
        
        # CRITICAL: This log MUST show all three parameters to confirm code is loaded
        logger.info(f"✅ SemanticMemoryStore V3 initialized (fusion={self._fusion_method}, rrf_k={self._rrf_rank_constant}, bm25_min_idf={self._bm25_min_idf})")
        logger.warning(f"🔍 DEBUG: Config values loaded - fusion={self._fusion_method}, rrf_k={self._rrf_rank_constant}, bm25_min_idf={self._bm25_min_idf}")
    
    def set_modelservice(self, modelservice):
        """Set the ModelService instance for embedding generation"""
        self._modelservice = modelservice
        logger.info("ModelService set for semantic memory")
    
    async def initialize(self) -> bool:
        """Initialize ChromaDB connection and collection"""
        if self._initialized:
            return True
        
        try:
            # Initialize ChromaDB client
            self._chroma_client = chromadb.PersistentClient(
                path=str(self._db_path),
                settings=Settings(
                    anonymized_telemetry=False,
                    allow_reset=True
                )
            )
            
            # Get or create collection with cosine similarity
            self._collection = self._chroma_client.get_or_create_collection(
                name=self._collection_name,
                metadata={
                    "description": "Conversation segments with embeddings",
                    "hnsw:space": "cosine"  # Use cosine similarity instead of L2
                }
            )
            
            self._initialized = True
            logger.info(f"✅ ChromaDB initialized: {self._collection_name} collection")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize ChromaDB: {e}")
            return False
    
    async def store_segment(
        self,
        user_id: str,
        conversation_id: str,
        role: str,
        content: str
    ) -> bool:
        """
        Store a conversation segment with embedding.
        
        Args:
            user_id: User identifier
            conversation_id: Conversation identifier
            role: 'user' or 'assistant'
            content: Message content
            
        Returns:
            True if stored successfully
        """
        if not self._initialized:
            await self.initialize()
        
        if not self._modelservice:
            logger.warning("ModelService not available - cannot generate embeddings")
            return False
        
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
                return False
            
            embedding = embedding_result.get("data", {}).get("embedding", [])
            if not embedding:
                logger.error("No embedding returned from modelservice")
                return False
            
            # Store in ChromaDB
            self._collection.add(
                ids=[segment.segment_id],
                embeddings=[embedding],
                documents=[content],
                metadatas=[{
                    'user_id': user_id,
                    'conversation_id': conversation_id,
                    'role': role,
                    'timestamp': segment.timestamp.isoformat()
                }]
            )
            
            logger.info(f"✅ Stored segment: {role} message ({len(content)} chars)")
            return True
            
        except Exception as e:
            logger.error(f"Failed to store segment: {e}")
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
        
        try:
            # Generate query embedding
            embedding_result = await self._modelservice.get_embeddings(
                model=self._embedding_model,
                prompt=query_text
            )
            if not embedding_result.get("success", False):
                logger.error(f"Failed to generate query embedding: {embedding_result.get('error')}")
                return []
            
            query_embedding = embedding_result.get("data", {}).get("embedding", [])
            if not query_embedding:
                logger.error("No embedding returned for query")
                return []
            
            # Build filter
            where_filter = {"user_id": user_id} if user_id else None
            
            # Get ALL documents for proper BM25 IDF calculation
            # Note: If user_id filter is set, we get all docs for that user
            collection_count = self._collection.count()
            
            results = self._collection.query(
                query_embeddings=[query_embedding],
                n_results=collection_count,  # Fetch ALL documents for proper BM25
                where=where_filter
            )
            
            # Prepare documents for hybrid scoring
            if not results or not results.get('ids') or not results['ids'][0]:
                return []
            
            # Build document list
            documents = []
            for i in range(len(results['ids'][0])):
                documents.append({
                    'id': results['ids'][0][i],
                    'document': results['documents'][0][i],
                    'metadata': results['metadatas'][0][i],
                    'distance': results['distances'][0][i] if 'distances' in results else 0.0
                })
            
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
            
            # Filter by threshold and format
            similarity_threshold = min_similarity if min_similarity is not None else self._min_similarity
            segments = []
            
            for doc in scored_docs:
                if doc['hybrid_score'] >= similarity_threshold:
                    segments.append({
                        'segment_id': doc['id'],
                        'content': doc['document'],
                        'metadata': doc['metadata'],
                        'distance': doc['distance'],
                        'similarity': doc['semantic_score'],
                        'bm25_score': doc['bm25_score'],
                        'hybrid_score': doc['hybrid_score']
                    })
            
            # Limit results
            segments = segments[:max_results or self._max_results]
            
            logger.info(f"Found {len(segments)} matching segments (hybrid search)")
            return segments
            
        except Exception as e:
            logger.error(f"Failed to query segments: {e}")
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
            # Query all segments for this conversation
            results = self._collection.get(
                where={
                    "user_id": user_id,
                    "conversation_id": conversation_id
                },
                limit=limit
            )
            
            # Format and sort by timestamp
            segments = []
            if results and results.get('ids'):
                for i, segment_id in enumerate(results['ids']):
                    segments.append({
                        'segment_id': segment_id,
                        'content': results['documents'][i],
                        'metadata': results['metadatas'][i]
                    })
                
                # Sort by timestamp (most recent last)
                segments.sort(key=lambda x: x['metadata']['timestamp'])
            
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
    
    def get_stats(self) -> Dict[str, Any]:
        """Get semantic memory statistics"""
        if not self._initialized or not self._collection:
            return {
                'initialized': False,
                'total_segments': 0
            }
        
        try:
            count = self._collection.count()
            return {
                'initialized': True,
                'total_segments': count,
                'collection_name': self._collection_name
            }
        except Exception as e:
            logger.error(f"Failed to get stats: {e}")
            return {
                'initialized': True,
                'total_segments': 0,
                'error': str(e)
            }
