"""
AICO Semantic Memory Store (V3 - Simplified)

Conversation-segment storage with vector embeddings for context retrieval.
Minimal, focused architecture: store conversation chunks, retrieve via semantic search.

Core Functionality:
- Segment storage: Store conversation chunks with embeddings
- Semantic search: Query conversation history using natural language
- Simple integration: Clean interface for memory manager

V3 Simplification:
- NO fact extraction (broken, removed)
- NO coreference resolution (broken, removed)
- NO complex deduplication (unnecessary for segments)
- ChromaDB only: Vector storage for conversation segments
- Direct modelservice integration for embeddings
"""

import asyncio
from typing import Dict, List, Optional, Any
from datetime import datetime
from dataclasses import dataclass
import uuid

import chromadb
from chromadb.config import Settings

from aico.core.config import ConfigurationManager
from aico.core.logging import get_logger
from aico.core.paths import AICOPaths

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
    """V3 Semantic Memory Store - Simple conversation segment storage"""
    
    def __init__(self, config_manager: ConfigurationManager):
        self.config = config_manager
        self._initialized = False
        self._chroma_client = None
        self._collection = None
        self._modelservice = None
        
        # Configuration
        memory_config = self.config.get("core.memory.semantic", {})
        self._db_path = AICOPaths.get_semantic_memory_path()
        self._collection_name = "conversation_segments"  # New collection name
        # Embedding model name matches transformers manager key (configured in core.yaml line 190)
        self._embedding_model = "paraphrase-multilingual"  # Maps to mpnet-base-v2 (768 dim)
        self._max_results = memory_config.get("max_results", 10)
        self._min_similarity = memory_config.get("min_similarity", 0.4)  # Cosine similarity threshold
        
        logger.info("✅ SemanticMemoryStore V3 initialized (simplified)")
    
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
            
            # Query ChromaDB
            results = self._collection.query(
                query_embeddings=[query_embedding],
                n_results=max_results or self._max_results,
                where=where_filter
            )
            
            # Format results with similarity filtering
            segments = []
            similarity_threshold = min_similarity if min_similarity is not None else self._min_similarity
            
            if results and results.get('ids') and results['ids'][0]:
                for i, segment_id in enumerate(results['ids'][0]):
                    # Get distance and convert to similarity (cosine: similarity = 1 - distance/2)
                    distance = results['distances'][0][i] if 'distances' in results else 0.0
                    similarity = 1.0 - (distance / 2.0)
                    
                    # Filter by minimum similarity threshold
                    if similarity >= similarity_threshold:
                        segments.append({
                            'segment_id': segment_id,
                            'content': results['documents'][0][i],
                            'metadata': results['metadatas'][0][i],
                            'distance': distance,
                            'similarity': similarity
                        })
            
            logger.info(f"Found {len(segments)} matching segments for query")
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
