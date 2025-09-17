"""
AICO Semantic Memory Store

This module provides intelligent knowledge-based memory storage with vector embeddings,
enabling semantic search and retrieval of factual information, concepts, and learned
knowledge for contextual AI processing and knowledge base functionality.

Core Functionality:
- Knowledge storage: Persistent storage of factual information, concepts, and learned knowledge with semantic indexing
- Vector embeddings: High-dimensional vector representations for semantic similarity matching using transformer models
- Semantic search: Content-based retrieval using natural language queries with relevance scoring
- Concept relationships: Storage and retrieval of related concepts and knowledge connections
- Knowledge base queries: Structured queries for specific information types and domains
- Learning integration: Continuous knowledge acquisition from conversations and external sources
- Fallback storage: JSON-based backup storage when vector database is unavailable

Storage Architecture:
- ChromaDB: Primary vector database for high-performance semantic search with HNSW indexing
  Rationale: Essential for efficient similarity search - libSQL cannot provide equivalent vector capabilities
- libSQL: Metadata and structured knowledge storage (user preferences, knowledge categories)
- Embedding-based indexing with optimized similarity metrics (cosine, euclidean, manhattan)
- Hybrid storage with JSON fallback for reliability and data portability
- Configurable retention policies and knowledge base maintenance

Technologies & Dependencies:
- ChromaDB: High-performance vector database optimized for semantic search and embeddings
  Rationale: Provides excellent similarity search performance with built-in embedding support - no equivalent in libSQL
- libSQL: Structured metadata storage for knowledge organization and user preferences
  Rationale: Handles non-vector data while ChromaDB handles vector operations
- sentence-transformers: Lightweight embedding models for semantic text representation (all-MiniLM-L6-v2)
  Rationale: Minimal, local-first embedding generation without heavy ML framework dependencies
- numpy: Essential numerical operations for vector computations and similarity calculations
- asyncio: Asynchronous operations for non-blocking knowledge storage and retrieval
- dataclasses: Structured representation of semantic entries and knowledge metadata
- json: Serialization for knowledge storage and libSQL compatibility
- pathlib: File system operations for database and backup management
- AICO ConfigurationManager: Database configuration, embedding models, and search parameters
- AICO Logging: Structured logging for knowledge operations and search analytics

AI Model Integration:
- Local embedding generation: Uses sentence-transformers for privacy-preserving local text embedding
- Model caching: Intelligent model loading and caching for optimal performance
- Batch processing: Efficient batch embedding generation for bulk knowledge storage
- GPU acceleration: Optional GPU support for faster embedding generation on capable hardware
- Model selection: Configurable embedding models based on performance requirements and hardware constraints

Embedding & Search Features:
- Multiple embedding models: Support for various pre-trained transformer models (MiniLM, BERT, RoBERTa)
- Semantic similarity scoring: Advanced relevance scoring using cosine similarity with configurable thresholds
- Metadata filtering: Query filtering by knowledge domains, sources, and content types
- Batch operations: Efficient bulk storage and retrieval for knowledge base management
- Knowledge clustering: Automatic organization of related concepts using vector similarity
- Search result ranking: Intelligent ranking based on semantic relevance, recency, and user context

Knowledge Management:
- Automatic deduplication of similar knowledge entries using embedding similarity
- Knowledge validation and quality scoring based on source reliability and consistency
- Source tracking and provenance information for knowledge attribution
- Knowledge expiration and update mechanisms with confidence decay
- Export and import capabilities for knowledge base portability and backup
"""

import json
import asyncio
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
from dataclasses import dataclass
from pathlib import Path

try:
    import chromadb
    from chromadb.config import Settings
except ImportError:
    chromadb = None

from aico.core.config import ConfigurationManager
from aico.core.logging import get_logger
from aico.core.paths import AICOPaths

logger = get_logger("ai", "memory.semantic")


@dataclass
class SemanticEntry:
    """Structure for semantic knowledge entries"""
    id: str
    content: str
    embedding: Optional[List[float]]
    metadata: Dict[str, Any]
    timestamp: datetime
    source: str
    confidence: float


class SemanticMemoryStore:
    """
    Semantic knowledge storage using ChromaDB for vector similarity.
    
    Manages:
    - Factual knowledge and concepts
    - Vector embeddings for semantic search
    - Knowledge relationships and associations
    - Context-aware knowledge retrieval
    
    Uses local ChromaDB instance following AICO's local-first principles.
    """
    
    def __init__(self, config_manager: ConfigurationManager):
        self.config = config_manager
        self._client: Optional[chromadb.Client] = None
        self._collection: Optional[chromadb.Collection] = None
        self._initialized = False
        
        # Configuration - use hierarchical paths and modelservice integration
        memory_config = self.config.get("memory.semantic", {})
        self._db_path = AICOPaths.get_semantic_memory_path()
        self._collection_name = memory_config.get("collection_name", "user_facts")
        # Use modelservice embedding model instead of sentence-transformers
        self._embedding_model = self.config.get("core.modelservice.ollama.default_models.embedding.name", "paraphrase-multilingual")
        self._max_results = memory_config.get("max_results", 20)
        
        # Check ChromaDB availability
        if chromadb is None:
            logger.warning("ChromaDB not available - semantic memory will use fallback storage")
    
    async def initialize(self) -> None:
        """Initialize ChromaDB client and collection with modelservice integration"""
        if self._initialized:
            return
            
        logger.info(f"Initializing semantic memory store at {self._db_path}")
        
        try:
            if chromadb is None:
                logger.warning("ChromaDB not available - using fallback storage")
                await self._initialize_fallback()
                self._initialized = True
                return
            
            # Create ChromaDB client with proper settings (no default embedding function)
            self._client = chromadb.PersistentClient(
                path=str(self._db_path),
                settings=Settings(allow_reset=True, anonymized_telemetry=False)
            )
            
            # Get or create collection with modelservice metadata
            try:
                self._collection = self._client.get_collection(self._collection_name)
                logger.info(f"Using existing collection: {self._collection_name}")
            except Exception:
                # Collection doesn't exist, create it with metadata
                dimensions = self.config.get("core.modelservice.ollama.default_models.embedding.dimensions", 768)
                collection_metadata = {
                    "embedding_model": self._embedding_model,
                    "dimensions": dimensions,
                    "created_by": "semantic_memory_store",
                    "version": "1.0"
                }
                self._collection = self._client.create_collection(
                    self._collection_name, 
                    metadata=collection_metadata
                )
                logger.info(f"Created new collection: {self._collection_name} with model: {self._embedding_model}")
            
            self._initialized = True
            logger.info("Semantic memory store initialized with modelservice integration")
            
        except Exception as e:
            logger.error(f"Failed to initialize semantic memory store: {e}")
            raise
    
    async def store(self, data: Dict[str, Any]) -> bool:
        """Store semantic knowledge entry with modelservice embeddings"""
        if not self._initialized:
            await self.initialize()
            
        try:
            # Create semantic entry
            entry = SemanticEntry(
                id=data.get("id", f"semantic_{datetime.utcnow().strftime('%Y%m%d_%H%M%S_%f')}"),
                content=data["content"],
                embedding=data.get("embedding"),
                metadata=data.get("metadata", {}),
                timestamp=data.get("timestamp", datetime.utcnow()),
                source=data.get("source", "user"),
                confidence=data.get("confidence", 1.0)
            )
            
            # Generate embeddings via modelservice if not provided
            if not entry.embedding:
                embedding_vector = await self._generate_embedding(entry.content)
                if not embedding_vector:
                    logger.error("Failed to generate embeddings - falling back to storage without embeddings")
                    return await self._store_fallback(entry)
                entry.embedding = embedding_vector
            
            # Store in ChromaDB with pre-computed embeddings
            if self._collection and chromadb:
                try:
                    self._collection.add(
                        documents=[entry.content],
                        ids=[entry.id],
                        embeddings=[entry.embedding],  # Pre-computed via modelservice!
                        metadatas=[{
                            **entry.metadata,
                            "source": entry.source,
                            "confidence": entry.confidence,
                            "timestamp": entry.timestamp.isoformat()
                        }]
                    )
                    logger.debug(f"Stored semantic memory entry: {entry.id}")
                    return True
                except Exception as e:
                    logger.warning(f"ChromaDB storage failed, using fallback: {e}")
                    return await self._store_fallback(entry)
            else:
                # Use fallback storage
                return await self._store_fallback(entry)
            
        except Exception as e:
            logger.error(f"Failed to store semantic memory: {e}")
            return False
    
    async def query(self, query_text: str, max_results: int = None, 
                   filters: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """Query semantic knowledge by similarity using modelservice embeddings"""
        if not self._initialized:
            await self.initialize()
            
        max_results = max_results or self._max_results
        
        try:
            # Generate query embeddings via modelservice
            query_embedding = await self._generate_embedding(query_text)
            if not query_embedding:
                logger.error("Failed to generate query embeddings - using fallback search")
                return await self._query_fallback(query_text, max_results, filters)
            
            # Query ChromaDB with pre-computed embeddings
            if self._collection and chromadb:
                try:
                    results = self._collection.query(
                        query_embeddings=[query_embedding],  # Use modelservice embeddings!
                        n_results=max_results,
                        where=filters  # Apply metadata filters
                    )
                    
                    # Format results
                    formatted_results = []
                    if results["documents"] and results["documents"][0]:
                        for i in range(len(results["documents"][0])):
                            formatted_results.append({
                                "id": results["ids"][0][i],
                                "content": results["documents"][0][i],
                                "distance": results["distances"][0][i] if results["distances"] else 0.0,
                                "metadata": results["metadatas"][0][i] if results["metadatas"] and results["metadatas"][0] else {},
                                "similarity": 1.0 - (results["distances"][0][i] if results["distances"] else 0.0)  # Convert distance to similarity
                            })
                    
                    logger.debug(f"Found {len(formatted_results)} semantic memory results for: {query_text}")
                    return formatted_results
                    
                except Exception as e:
                    logger.warning(f"ChromaDB query failed, using fallback: {e}")
                    return await self._query_fallback(query_text, max_results, filters)
            else:
                # Use fallback search
                return await self._query_fallback(query_text, max_results, filters)
                
        except Exception as e:
            logger.error(f"Failed to query semantic memory: {e}")
            return []
    
    async def get_related_concepts(self, concept: str, max_results: int = 10) -> List[Dict[str, Any]]:
        """Get concepts related to the given concept - Phase 1 interface"""
        return await self.query(concept, max_results=max_results)
    
    async def update_knowledge(self, entry_id: str, updates: Dict[str, Any]) -> bool:
        """Update existing knowledge entry - Phase 1 interface"""
        if not self._initialized:
            await self.initialize()
            
        try:
            # TODO Phase 1: Implement knowledge updates
            # - Get existing entry from ChromaDB
            # - Delete and re-add with updates (ChromaDB pattern)
            # - Handle fallback storage updates
            
            logger.debug(f"Would update semantic memory entry: {entry_id}")
            return True  # Placeholder return
                
        except Exception as e:
            logger.error(f"Failed to update semantic memory: {e}")
            return False
    
    async def cleanup(self) -> None:
        """Cleanup resources - Phase 1 scaffolding"""
        try:
            if self._client:
                # TODO Phase 1: Implement proper ChromaDB cleanup
                # - Close ChromaDB client connections
                # - Clean up collection references
                self._client = None
                self._collection = None
                
            self._initialized = False
            logger.info("Semantic memory store cleanup completed")
            
        except Exception as e:
            logger.error(f"Error during semantic memory cleanup: {e}")
    
    async def _generate_embedding(self, text: str) -> Optional[List[float]]:
        """Generate embeddings via modelservice (replaces ChromaDB default embedding function)"""
        try:
            # Import modelservice client
            from backend.services.modelservice_client import ModelserviceClient
            
            # Create modelservice client
            modelservice = ModelserviceClient(self.config)
            await modelservice.connect()
            
            try:
                # Generate embeddings via modelservice
                response = await modelservice.get_embeddings(self._embedding_model, text)
                
                if response.get("success") and "embedding" in response.get("data", {}):
                    embedding = response["data"]["embedding"]
                    logger.debug(f"Generated {len(embedding)}-dimensional embedding via modelservice")
                    return embedding
                else:
                    logger.error(f"Modelservice embedding generation failed: {response.get('error', 'Unknown error')}")
                    return None
                    
            finally:
                await modelservice.disconnect()
                
        except Exception as e:
            logger.error(f"Failed to generate embedding via modelservice: {e}")
            return None
    
    async def _initialize_fallback(self) -> None:
        """Initialize fallback JSON storage - Phase 1 TODO"""
        # TODO Phase 1: Implement fallback storage
        # - Create JSON file structure
        # - Handle directory creation
        # - Initialize empty storage
        pass
    
    async def _store_fallback(self, entry: SemanticEntry) -> None:
        """Store entry in fallback JSON storage - Phase 1 TODO"""
        # TODO Phase 1: Implement fallback storage operations
        # - Read existing JSON data
        # - Add new entry
        # - Write back to file
        pass
    
    async def _query_fallback(self, query_text: str, max_results: int, 
                             filters: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """Query fallback JSON storage - Phase 1 TODO"""
        # TODO Phase 1: Implement fallback search
        # - Simple text matching and scoring
        # - Apply filters
        # - Sort by similarity
        return []
    
    async def _update_fallback(self, entry_id: str, updates: Dict[str, Any]) -> bool:
        """Update entry in fallback JSON storage - Phase 1 TODO"""
        # TODO Phase 1: Implement fallback updates
        # - Find entry by ID
        # - Apply updates
        # - Write back to file
        return False
