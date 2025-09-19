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

import chromadb
from chromadb.config import Settings

from aico.core.config import ConfigurationManager
from aico.core.logging import get_logger
from aico.core.paths import AICOPaths
from aico.ai.analysis.conversation_processor import ConversationSegmentProcessor
from aico.ai.analysis.fact_extractor import AdvancedFactExtractor
from aico.data.schemas.semantic import SemanticQuery, SemanticResult

logger = get_logger("shared", "ai.memory.semantic")


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
        
        # Dual collection architecture for comprehensive memory
        collections_config = memory_config.get("collections", {})
        self._user_facts_collection = collections_config.get("user_facts", "user_facts")
        self._conversation_segments_collection = collections_config.get("conversation_segments", "conversation_segments")
        
        # Validate collection names
        if not self._user_facts_collection.strip():
            self._user_facts_collection = "user_facts"
        if not self._conversation_segments_collection.strip():
            self._conversation_segments_collection = "conversation_segments"
        
        # Use modelservice embedding model instead of sentence-transformers
        self._embedding_model = self.config.get("core.modelservice.ollama.default_models.embedding.name", "paraphrase-multilingual")
        self._max_results = memory_config.get("max_results", 20)
        
        # Initialize conversation processor and fact extractor
        self.conversation_processor = ConversationSegmentProcessor(config_manager)
        self.fact_extractor = AdvancedFactExtractor(config_manager)
        
        # ChromaDB is required - no fallback
        logger.info(f"ChromaDB available - semantic memory ready with collections: user_facts='{self._user_facts_collection}', conversation_segments='{self._conversation_segments_collection}'")
    
    def set_modelservice(self, modelservice):
        """Inject modelservice dependency for embeddings and NER"""
        self._modelservice = modelservice
        # Also inject into conversation processor
        self.conversation_processor.modelservice = modelservice
    
    async def initialize(self) -> None:
        """Initialize ChromaDB client and collection with modelservice integration"""
        if self._initialized:
            return
            
        logger.info(f"Initializing semantic memory store at {self._db_path}")
        
        try:
            logger.info("Initializing ChromaDB client...")
            
            # Create ChromaDB client with proper settings (no default embedding function)
            self._client = chromadb.PersistentClient(
                path=str(self._db_path),
                settings=Settings(allow_reset=True, anonymized_telemetry=False)
            )
            
            # Get or create both collections with modelservice metadata
            dimensions = self.config.get("core.modelservice.ollama.default_models.embedding.dimensions", 768)
            collection_metadata = {
                "embedding_model": self._embedding_model,
                "dimensions": dimensions,
                "created_by": "semantic_memory_store",
                "version": "1.0"
            }
            
            # Initialize user_facts collection
            logger.info(f"Attempting to get user_facts collection: '{self._user_facts_collection}'")
            try:
                self._user_facts_collection_obj = self._client.get_collection(self._user_facts_collection)
                logger.info(f"Using existing user_facts collection: {self._user_facts_collection}")
            except Exception as e:
                logger.info(f"Creating new user_facts collection: {self._user_facts_collection}")
                self._user_facts_collection_obj = self._client.create_collection(
                    self._user_facts_collection, 
                    metadata={**collection_metadata, "collection_type": "user_facts"}
                )
                logger.info(f"Created user_facts collection: {self._user_facts_collection}")
            
            # Initialize conversation_segments collection  
            logger.info(f"Attempting to get conversation_segments collection: '{self._conversation_segments_collection}'")
            try:
                self._conversation_segments_collection_obj = self._client.get_collection(self._conversation_segments_collection)
                logger.info(f"Using existing conversation_segments collection: {self._conversation_segments_collection}")
            except Exception as e:
                logger.info(f"Creating new conversation_segments collection: {self._conversation_segments_collection}")
                self._conversation_segments_collection_obj = self._client.create_collection(
                    self._conversation_segments_collection,
                    metadata={**collection_metadata, "collection_type": "conversation_segments"}
                )
                logger.info(f"Created conversation_segments collection: {self._conversation_segments_collection}")
            
            # Set primary collection for backward compatibility (use conversation_segments for main operations)
            self._collection = self._conversation_segments_collection_obj
            
            # Modelservice dependency is handled directly in _generate_embedding
            
            self._initialized = True
            logger.info("Semantic memory store initialized with modelservice integration")
            
        except Exception as e:
            logger.error(f"Failed to initialize semantic memory store: {e}")
            raise
    
    async def store(self, data: Dict[str, Any]) -> bool:
        """Store semantic knowledge with embeddings via modelservice"""
        if not self._initialized:
            await self.initialize()
            
        logger.info(f"🧠 [SEMANTIC_MEMORY] Storing semantic entry: {data.get('content', '')[:50]}...")
        
        try:
            # Create semantic entry
            entry = SemanticEntry(
                id=data.get("id", f"fact_{datetime.utcnow().timestamp()}"),
                content=data.get("content", ""),
                embedding=data.get("embedding"),  # Optional pre-computed embedding
                metadata=data.get("metadata", {}),
                timestamp=data.get("timestamp", datetime.utcnow()),
                source=data.get("source", "user"),
                confidence=data.get("confidence", 1.0)
            )
            
            # Generate embeddings via modelservice if not provided
            if not entry.embedding:
                logger.info("🧠 [SEMANTIC_MEMORY] → Generating embeddings via modelservice")
                embedding_vector = await self._generate_embedding(entry.content)
                if not embedding_vector:
                    logger.error("🧠 [SEMANTIC_MEMORY] ❌ Failed to generate embeddings - semantic storage failed")
                    raise Exception("Embedding generation failed - semantic memory requires embeddings")
                entry.embedding = embedding_vector
                logger.info("🧠 [SEMANTIC_MEMORY] ✅ Embeddings generated successfully")
            
            # Store in ChromaDB with pre-computed embeddings
            if self._collection and chromadb:
                try:
                    # Enhanced metadata structure for administrative queries
                    enhanced_metadata = {
                        # Core identification
                        "user_id": entry.metadata.get("user_id", "unknown"),
                        "fact_id": entry.id or "unknown",
                        
                        # Semantic categorization
                        "category": entry.metadata.get("category", "context"),
                        "permanence": entry.metadata.get("permanence", "evolving"),
                        
                        # Quality metrics
                        "confidence": entry.confidence if entry.confidence is not None else 0.5,
                        "reasoning": entry.metadata.get("reasoning", ""),
                        
                        # Temporal data
                        "created_at": entry.timestamp.isoformat() if entry.timestamp else "",
                        "updated_at": entry.timestamp.isoformat() if entry.timestamp else "",
                        
                        # Source tracking
                        "source_thread": entry.metadata.get("source_thread", ""),
                        "source_message": entry.source or "",
                        "extraction_method": "llm_analysis",
                        
                        # Administrative
                        "version": 1,
                        "status": "active"
                    }
                    
                    # Add legacy fields but filter out None values
                    for key, value in entry.metadata.items():
                        if value is not None and key not in enhanced_metadata:
                            enhanced_metadata[key] = value
                    
                    # Final safety filter - remove any None values that might have slipped through
                    enhanced_metadata = {k: v for k, v in enhanced_metadata.items() if v is not None}
                    
                    # Debug log the final metadata to identify None values
                    logger.debug(f"🧠 [SEMANTIC_MEMORY] Final metadata for ChromaDB: {enhanced_metadata}")
                    none_values = [k for k, v in enhanced_metadata.items() if v is None]
                    if none_values:
                        logger.error(f"🧠 [SEMANTIC_MEMORY] ❌ Found None values in metadata: {none_values}")
                    
                    self._collection.add(
                        documents=[entry.content],
                        ids=[entry.id],
                        embeddings=[entry.embedding],  # Pre-computed via modelservice!
                        metadatas=[enhanced_metadata]
                    )
                    logger.info(f"🧠 [SEMANTIC_MEMORY] ✅ Entry stored in ChromaDB: {entry.id}")
                    return True
                except Exception as e:
                    logger.error(f"🧠 [SEMANTIC_MEMORY] ❌ ChromaDB storage failed: {e}")
                    raise Exception(f"Semantic memory storage failed: {e}")
            else:
                raise Exception("ChromaDB not initialized - semantic memory unavailable")
            
        except Exception as e:
            logger.error(f"Failed to store semantic memory: {e}")
            return False
    
    async def query(self, query_text: str, max_results: int = None, 
                   filters: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """Query semantic knowledge by similarity using modelservice embeddings"""
        if not self._initialized:
            await self.initialize()
            
        logger.info(f"🔍 [SEMANTIC_MEMORY] Querying: '{query_text[:50]}...' (max_results: {max_results or self._max_results})")
        
        max_results = max_results or self._max_results
        
        try:
            # Generate query embeddings via modelservice
            logger.info("🔍 [SEMANTIC_MEMORY] → Generating query embeddings via modelservice")
            query_embedding = await self._generate_embedding(query_text)
            if not query_embedding:
                logger.error("🔍 [SEMANTIC_MEMORY] ❌ Failed to generate query embeddings - semantic search failed")
                raise Exception("Query embedding generation failed - semantic search unavailable")
            
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
                    
                    logger.info(f"🔍 [SEMANTIC_MEMORY] ✅ Found {len(formatted_results)} semantic results")
                    return formatted_results
                    
                except Exception as e:
                    logger.error(f"🔍 [SEMANTIC_MEMORY] ❌ ChromaDB query failed: {e}")
                    raise Exception(f"Semantic memory query failed: {e}")
            else:
                raise Exception("ChromaDB not initialized - semantic memory unavailable")
        except Exception as e:
            logger.error(f"Failed to query semantic memory: {e}")
            return []
    
    async def get_user_segments(self, user_id: str, thread_id: Optional[str] = None, 
                              entity_filter: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get all conversation segments for a user with optional filtering (administrative query)"""
        if not self._initialized:
            await self.initialize()
        
        if not self._collection or not chromadb:
            return []
        
        try:
            # Build where clause for metadata filtering
            where_clause = {"user_id": user_id, "type": "conversation_segment"}
            
            if thread_id:
                where_clause["thread_id"] = thread_id
            
            if entity_filter:
                # Filter by entity presence (simplified for now)
                where_clause["entities"] = {"$contains": entity_filter}
            
            # Use get() for administrative queries (no embeddings needed)
            results = self._collection.get(
                where=where_clause,
                limit=1000  # Large limit for administrative queries
            )
            
            # Format results
            segments = []
            if results["documents"]:
                for i in range(len(results["documents"])):
                    segments.append({
                        "id": results["ids"][i],
                        "content": results["documents"][i],
                        "metadata": results["metadatas"][i] if results["metadatas"] else {}
                    })
            
            logger.debug(f"Retrieved {len(segments)} conversation segments for user {user_id}")
            return segments
            
        except Exception as e:
            logger.error(f"Failed to get user segments: {e}")
            return []
    
    async def delete_user_segments(self, user_id: str) -> bool:
        """Delete all conversation segments for a user (GDPR compliance)"""
        if not self._initialized:
            await self.initialize()
        
        if not self._collection or not chromadb:
            return False
        
        try:
            # Get all segment IDs for the user
            user_segments = await self.get_user_segments(user_id)
            
            if not user_segments:
                logger.info(f"No conversation segments found for user {user_id}")
                return True
            
            # Delete all segments
            segment_ids = [segment["id"] for segment in user_segments]
            self._collection.delete(ids=segment_ids)
            
            logger.info(f"Deleted {len(segment_ids)} conversation segments for user {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete user segments: {e}")
            return False
    
    async def store_conversation_segments(self, messages: List[Dict[str, Any]], thread_id: str, user_id: str) -> int:
        """
        Store conversation segments with advanced fact extraction.
        
        Args:
            messages: List of conversation messages
            thread_id: Conversation thread identifier  
            user_id: User identifier
            
        Returns:
            Number of segments successfully stored
        """
        logger.info(f"🔍 [SEMANTIC_MEMORY_DEBUG] ✅ store_conversation_segments CALLED with {len(messages) if messages else 0} messages")
        logger.info(f"🔍 [SEMANTIC_MEMORY_DEBUG] thread_id: {thread_id}, user_id: {user_id}")
        
        if not self._initialized:
            logger.info(f"🔍 [SEMANTIC_MEMORY_DEBUG] Not initialized, calling initialize()")
            await self.initialize()
            
        if not messages:
            logger.info(f"🔍 [SEMANTIC_MEMORY_DEBUG] No messages provided, returning 0")
            return 0
        
        logger.info(f"🧠 [SEMANTIC_MEMORY] Processing {len(messages)} messages for conversation segments")
        
        try:
            # Use conversation processor to create segments
            segments = await self.conversation_processor.process_conversation_history(
                messages=messages,
                thread_id=thread_id,
                user_id=user_id
            )
            
            segments_stored = 0
            facts_extracted = 0
            
            for segment in segments:
                # Debug log segment details including entities
                entities = segment.entities
                logger.debug(f"🧠 [SEMANTIC_MEMORY] Processing segment with entities: {entities}")
                logger.debug(f"🧠 [SEMANTIC_MEMORY] Segment fields - thread_id: {segment.thread_id}, user_id: {segment.user_id}, text: {segment.text[:50] if segment.text else 'None'}...")
                
                # Extract and store user facts using advanced fact extractor
                extracted_facts = await self.fact_extractor.extract_facts(segment)
                for fact in extracted_facts:
                    if await self._store_user_fact_advanced(fact):
                        facts_extracted += 1
                
                # Store each segment as semantic knowledge
                # Serialize complex data types for ChromaDB compatibility
                
                # Create metadata dictionary and filter out None values
                metadata = {
                    "type": "conversation_segment",
                    "thread_id": segment.thread_id or "",
                    "user_id": segment.user_id or "",
                    "segment_type": "general",
                    "entities_json": json.dumps(segment.entities) if segment.entities else "{}",
                    "topics_json": json.dumps([]),
                    "sentiment": segment.sentiment or "neutral",
                    "sentiment_confidence": segment.sentiment_confidence if segment.sentiment_confidence is not None else 0.5,
                    "importance": 0.5,
                    "turn_range_json": json.dumps(list(segment.turn_range)) if segment.turn_range else "[0,0]",
                    "message_count": len(segment.messages) if segment.messages else 0
                }
                
                # Filter out any None values that ChromaDB can't handle
                metadata = {k: v for k, v in metadata.items() if v is not None}
                
                segment_data = {
                    "id": f"segment_{segment.thread_id or 'unknown'}_{int(segment.timestamp.timestamp())}",
                    "content": segment.text or "",
                    "metadata": metadata,
                    "source": f"conversation_segment_{segment.thread_id or 'unknown'}",
                    "confidence": 0.8,
                    "timestamp": segment.timestamp
                }
                
                if await self.store(segment_data):
                    segments_stored += 1
                    logger.debug(f"🧠 [SEMANTIC_MEMORY] ✅ Stored segment with {sum(len(v) if isinstance(v, list) else 0 for v in entities.values())} entities")
            
            logger.info(f"🧠 [SEMANTIC_MEMORY] ✅ Stored {segments_stored} conversation segments and extracted {facts_extracted} user facts")
            return segments_stored
            
        except Exception as e:
            logger.error(f"🧠 [SEMANTIC_MEMORY] ❌ Failed to store conversation segments: {e}")
            return 0

    async def cleanup_old_facts(self, days_old: int = 90) -> int:
        """Clean up old temporary facts (scheduled maintenance)"""
        if not self._initialized:
            await self.initialize()
        
        if not self._collection or not chromadb:
            return 0
        
        try:
            from datetime import datetime, timedelta
            cutoff_date = (datetime.utcnow() - timedelta(days=days_old)).isoformat()
            
            # Find old temporary facts
            old_facts = self._collection.get(
                where={
                    "$and": [
                        {"permanence": "temporary"},
                        {"created_at": {"$lt": cutoff_date}},
                        {"status": "active"}
                    ]
                },
                limit=1000
            )
            
            if not old_facts["ids"]:
                logger.debug("No old temporary facts to clean up")
                return 0
            
            # Delete old facts
            self._collection.delete(ids=old_facts["ids"])
            
            logger.info(f"Cleaned up {len(old_facts['ids'])} old temporary facts")
            return len(old_facts["ids"])
            
        except Exception as e:
            logger.error(f"Failed to cleanup old facts: {e}")
            return 0
    
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
            if not self._modelservice:
                logger.error("Modelservice not available for embedding generation")
                return None
            
            # Add timeout handling for background embedding generation
            import asyncio
            response = await asyncio.wait_for(
                self._modelservice.get_embeddings(
                    model=self._embedding_model,
                    prompt=text
                ),
                timeout=30.0  # Shorter timeout for background tasks
            )
            
            if response.get("success") and "embedding" in response.get("data", {}):
                embedding = response["data"]["embedding"]
                logger.debug(f"Generated {len(embedding)}-dimensional embedding via modelservice")
                return embedding
            else:
                logger.error(f"Modelservice embedding generation failed: {response.get('error', 'Unknown error')}")
                return None
                
        except asyncio.TimeoutError:
            logger.warning(f"Embedding generation timed out after 30s - skipping fact storage")
            return None
        except Exception as e:
            logger.error(f"Failed to generate embedding via modelservice: {e}")
            return None
    
    async def _store_user_fact_advanced(self, extracted_fact) -> bool:
        """Store an advanced extracted fact in the user_facts collection"""
        try:
            if not self._user_facts_collection_obj:
                logger.error("User facts collection not initialized")
                return False
            
            # Generate embedding for the fact content
            embedding = await self._generate_embedding(extracted_fact.content)
            if not embedding:
                logger.error("Failed to generate embedding for user fact")
                return False
            
            # Create unique ID for the fact
            fact_id = f"fact_{extracted_fact.source_segment_id}_{hash(extracted_fact.content)}"
            
            # Create comprehensive metadata
            metadata = {
                "fact_type": extracted_fact.fact_type.value,
                "confidence": extracted_fact.confidence,
                "extraction_method": extracted_fact.extraction_method,
                "source_segment_id": extracted_fact.source_segment_id,
                "created_at": datetime.utcnow().isoformat(),
                "entities_count": len(extracted_fact.entities),
                "relations_count": len(extracted_fact.relations),
                **extracted_fact.metadata  # Include all additional metadata
            }
            
            # Store in ChromaDB user_facts collection
            self._user_facts_collection_obj.add(
                documents=[extracted_fact.content],
                ids=[fact_id],
                embeddings=[embedding],
                metadatas=[metadata]
            )
            
            logger.info(f"🧠 [USER_FACTS] ✅ Stored advanced fact: {extracted_fact.fact_type.value} - {extracted_fact.content[:50]}...")
            return True
            
        except Exception as e:
            logger.error(f"🧠 [USER_FACTS] ❌ Failed to store advanced fact: {e}")
            return False

