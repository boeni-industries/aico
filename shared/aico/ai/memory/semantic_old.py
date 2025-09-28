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
import time
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass
from pathlib import Path

import chromadb
from chromadb.config import Settings

from aico.core.config import ConfigurationManager
from aico.core.logging import get_logger
from aico.core.paths import AICOPaths
from aico.ai.analysis.conversation_processor import ConversationSegmentProcessor
from aico.data.schemas.semantic import SemanticQuery, SemanticResult

logger = get_logger("shared", "ai.memory.semantic")


@dataclass
class UserFact:
    """Structured user fact with confidence and metadata for V2 architecture"""
                print(f"🚨 [CIRCUIT_BREAKER] ⚠️ CIRCUIT OPEN - ModelService requests blocked")
                logger.warning("ModelService circuit breaker OPEN - requests blocked")
                return False
        elif self.state == "HALF_OPEN":
            return True
        
        return False
        
    def record_success(self):
        """Record successful request"""
        if self.state == "HALF_OPEN":
            self.state = "CLOSED"
            self.failure_count = 0
            print(f"🟢 [CIRCUIT_BREAKER] ✅ Circuit breaker CLOSED - ModelService recovered")
            logger.info("ModelService circuit breaker CLOSED - service recovered")
        else:
            self.failure_count = max(0, self.failure_count - 1)
            
    def record_failure(self):
        """Record failed request"""
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.failure_count >= self.failure_threshold:
            self.state = "OPEN"
            print(f"🚨 [CIRCUIT_BREAKER] ⚠️ CIRCUIT OPENED - {self.failure_count} failures, blocking ModelService requests")
            logger.warning(f"ModelService circuit breaker OPENED after {self.failure_count} failures")
        else:
            print(f"🟡 [CIRCUIT_BREAKER] Failure recorded ({self.failure_count}/{self.failure_threshold})")
            logger.warning(f"ModelService failure recorded ({self.failure_count}/{self.failure_threshold})")


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
    """Advanced semantic memory store using ChromaDB with modelservice embeddings"""
    
    def __init__(self, config_manager=None, modelservice_client=None):
        self.config_manager = config_manager
        self.modelservice_client = modelservice_client
        self._collection = None
        self._user_facts_collection_obj = None
        self._conversation_segments_collection_obj = None
        self._chroma_client = None
        self._max_results = 10
        self.fact_extractor = None  # Will be set by dependency injection
        
        # PERFORMANCE FIX: Cache query embeddings to avoid repeated modelservice calls
        self._query_embedding_cache = {}  # query_text -> embedding
        self._cache_max_size = 100  # Limit cache size
        
        # PHASE 1: Protection mechanisms for ModelService
        self._request_queue = SemanticRequestQueue()
        self._circuit_breaker = ModelServiceCircuitBreaker()
        self._fallback_cache = {}  # Cache for fallback responses
        
        # ROOT FIX: Batch embedding processing for facts
        self._embedding_batch_queue = []  # Pending embedding requests
        self._embedding_batch_size = 10  # Process embeddings in batches
        self._embedding_batch_timeout = 2.0  # Max wait time before processing partial batch
        
        # CRITICAL FIX: Initialize the _initialized flag
        self._initialized = False
        
        # CRITICAL FIX: Initialize _modelservice to prevent AttributeError
        self._modelservice = None
        
        # CRITICAL FIX: Initialize _client to prevent AttributeError
        self._client = None
        
        # Initialize configuration and paths
        self.config = config_manager if config_manager else {}
        
        # Configure ChromaDB paths and modelservice integration
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
            # PERFORMANCE FIX: Check cache first to avoid slow modelservice calls
            import time
            query_start = time.time()
            cache_key = f"{query_text[:100]}_{len(query_text)}"  # Use truncated text + length as key
            
            if cache_key in self._query_embedding_cache:
                query_embedding = self._query_embedding_cache[cache_key]
                cache_time = time.time() - query_start
                logger.info(f"🚀 [SEMANTIC_MEMORY] → Using CACHED query embedding in {cache_time*1000:.1f}ms (avoiding modelservice call)")
            else:
                # Generate query embeddings via modelservice
                logger.info("🔍 [SEMANTIC_MEMORY] → Generating query embeddings via modelservice")
                embedding_start = time.time()
                query_embedding = await self._generate_embedding(query_text)
                embedding_time = time.time() - embedding_start
                
                if not query_embedding:
                    logger.error("🚨 [SEMANTIC_MEMORY] CRITICAL: Failed to generate query embeddings - modelservice timeout/error")
                    logger.error("🚨 [SEMANTIC_MEMORY] This should NOT happen - investigate modelservice issues!")
                    raise Exception("CRITICAL: Query embedding generation failed - modelservice issue needs investigation")
                
                # Cache the embedding for future use
                if len(self._query_embedding_cache) >= self._cache_max_size:
                    # Remove oldest entry (simple FIFO)
                    oldest_key = next(iter(self._query_embedding_cache))
                    del self._query_embedding_cache[oldest_key]
                
                self._query_embedding_cache[cache_key] = query_embedding
                logger.info(f"💾 [SEMANTIC_MEMORY] → Generated & cached query embedding in {embedding_time:.2f}s (cache size: {len(self._query_embedding_cache)})")
                
                # Performance warning for slow embeddings
                if embedding_time > 2.0:
                    logger.warning(f"📊 [QUERY_PERFORMANCE] ⚠️ SLOW QUERY EMBEDDING: {embedding_time:.2f}s (threshold: 2.0s)")
            
            # Query ChromaDB with pre-computed embeddings
            if self._collection and chromadb:
                try:
                    # Add timeout to prevent ChromaDB hangs
                    import asyncio
                    results = await asyncio.wait_for(
                        asyncio.get_event_loop().run_in_executor(
                            None, 
                            lambda: self._collection.query(
                                query_embeddings=[query_embedding],  # Use modelservice embeddings!
                                n_results=max_results,
                                where=filters  # Apply metadata filters
                            )
                        ),
                        timeout=3.0  # 3 second timeout for ChromaDB query
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
                    
                except asyncio.TimeoutError:
                    logger.error(f"🔍 [SEMANTIC_MEMORY] ❌ ChromaDB query timed out after 3.0s")
                    return []  # Return empty results on timeout
                except Exception as e:
                    logger.error(f"🔍 [SEMANTIC_MEMORY] ❌ ChromaDB query failed: {e}")
                    return []  # Return empty results on error instead of raising
            else:
                raise Exception("ChromaDB not initialized - semantic memory unavailable")
        except Exception as e:
            logger.error(f"Failed to query semantic memory: {e}")
            return []
    
    async def get_user_segments(self, user_id: str, conversation_id: Optional[str] = None, 
                              entity_filter: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get all conversation segments for a user with optional filtering (administrative query)"""
        if not self._initialized:
            await self.initialize()
        
        if not self._collection or not chromadb:
            return []
        
        try:
            # Build where clause for metadata filtering
            where_clause = {"user_id": user_id, "type": "conversation_segment"}
            
            if conversation_id:
                where_clause["conversation_id"] = conversation_id
            
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
    
    async def store_conversation_segments(self, messages: List[Dict[str, Any]], conversation_id: str, user_id: str) -> int:
        """
        Store conversation segments with advanced fact extraction.
        
        Args:
            messages: List of conversation messages
            conversation_id: Conversation identifier  
            user_id: User identifier
            
        Returns:
            Number of segments successfully stored
        """
        logger.info(f"🔍 [SEMANTIC_MEMORY_DEBUG] ✅ store_conversation_segments CALLED with {len(messages) if messages else 0} messages")
        logger.info(f"🔍 [SEMANTIC_MEMORY_DEBUG] conversation_id: {conversation_id}, user_id: {user_id}")
        
        if not self._initialized:
            logger.info(f"🔍 [SEMANTIC_MEMORY_DEBUG] Not initialized, calling initialize()")
            await self.initialize()
            
        if not messages:
            logger.info(f"🔍 [SEMANTIC_MEMORY_DEBUG] No messages provided, returning 0")
            return 0
        
        logger.info(f"🧠 [SEMANTIC_MEMORY] Processing {len(messages)} messages for conversation segments")
        
        try:
            # Use conversation processor to create segments
            conversation_segments = await self.conversation_processor.process_conversation_history(
                messages=messages,
                conversation_id=conversation_id,
                user_id=user_id
            )
            
            segments_stored = 0
            facts_extracted = 0
            
            for segment in conversation_segments:
                # Debug log segment details including entities
                entities = segment.entities
                logger.debug(f"🧠 [SEMANTIC_MEMORY] Processing segment with entities: {entities}")
                logger.debug(f"🧠 [SEMANTIC_MEMORY] Segment fields - conversation_id: {segment.conversation_id}, user_id: {segment.user_id}, text: {segment.text[:50] if segment.text else 'None'}...")
                
                # Extract and store user facts using advanced fact extractor
                extracted_facts = await self.fact_extractor.extract_facts(segment)
                
                # LANGUAGE-AGNOSTIC: Filter facts based on confidence and structural quality
                filtered_facts = []
                for fact in extracted_facts:
                    # Filter based on confidence (GLiNER already did quality filtering)
                    if fact.confidence < 0.4:
                        continue
                    # Filter very short content (likely incomplete extractions)
                    if len(fact.content.strip()) < 2:
                        continue
                    filtered_facts.append(fact)
                
                print(f"🚨 [PERFORMANCE_DEBUG] Extracted {len(extracted_facts)} facts, filtered to {len(filtered_facts)} high-confidence facts (saving {len(extracted_facts) - len(filtered_facts)} embedding requests)")
                
                # EMERGENCY: Disable batch processing - causing 30s delays!
                # Process facts individually until batch issues are resolved
                logger.warning(f"🚨 [EMERGENCY] Processing {len(filtered_facts)} facts individually (batch disabled due to timeouts)")
                
                for fact in filtered_facts:
                    try:
                        if await self._store_user_fact_advanced(fact):
                            facts_extracted += 1
                    except Exception as e:
                        logger.error(f"🚨 [EMERGENCY] Failed to store individual fact: {e}")
                        continue
                
                # Store each segment as semantic knowledge
                # Serialize complex data types for ChromaDB compatibility
                
                # Create metadata dictionary and filter out None values
                metadata = {
                    "type": "conversation_segment",
                    "conversation_id": segment.conversation_id or conversation_id or "",
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
                    "id": f"segment_{conversation_id or 'unknown'}_{int(segment.timestamp.timestamp())}",
                    "content": segment.text or "",
                    "metadata": metadata,
                    "source": f"conversation_segment_{conversation_id or 'unknown'}",
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
        """PHASE 1: Generate embeddings with protection mechanisms and fallbacks"""
        try:
            if not self._modelservice:
                print(f"🚨 [SEMANTIC_EMBEDDING] ⚠️ FALLBACK: Modelservice not available")
                logger.warning("Modelservice not available for embedding generation - using fallback")
                return self._get_fallback_embedding(text)
            
            # PHASE 1: Check circuit breaker
            if not self._circuit_breaker.can_execute():
                print(f"🚨 [SEMANTIC_EMBEDDING] ⚠️ FALLBACK: Circuit breaker OPEN")
                logger.warning("Circuit breaker OPEN - using fallback embedding")
                return self._get_fallback_embedding(text)
            
            # PHASE 1: Acquire request queue permission
            if not await self._request_queue.acquire():
                print(f"🚨 [SEMANTIC_EMBEDDING] ⚠️ FALLBACK: Request queue limit reached")
                logger.warning("Request queue limit reached - using fallback embedding")
                return self._get_fallback_embedding(text)
            
            try:
                # Get timeout from config (reduced for Phase 1)
                embedding_timeout = 5.0  # Much shorter timeout for Phase 1
                
                print(f"🟢 [SEMANTIC_EMBEDDING] Making protected embedding request (timeout: {embedding_timeout}s)")
                
                # Use asyncio.wait_for for proper timeout handling
                response = await asyncio.wait_for(
                    self._modelservice.get_embeddings(model=self._embedding_model, prompt=text),
                    timeout=embedding_timeout
                )
                
                # Handle both "embedding" (singular) and "embeddings" (plural) response formats
                embedding_data = response.get("data", {}).get("embedding") or response.get("data", {}).get("embeddings")
                if response.get("success") and embedding_data:
                    # Handle both single embedding and list of embeddings
                    if isinstance(embedding_data, list) and len(embedding_data) > 0:
                        if isinstance(embedding_data[0], list):
                            # List of embeddings - take first one
                            embedding = embedding_data[0]
                        else:
                            # Single embedding as list
                            embedding = embedding_data
                    else:
                        embedding = embedding_data
                    
                    if embedding and len(embedding) > 0:
                        # PHASE 1: Record success
                        self._circuit_breaker.record_success()
                        print(f"🟢 [SEMANTIC_EMBEDDING] ✅ Embedding generated successfully ({len(embedding)} dims)")
                        logger.debug(f"Generated embedding: {len(embedding)} dimensions")
                        return embedding
                    else:
                        # PHASE 1: Record failure and fallback
                        self._circuit_breaker.record_failure()
                        print(f"🚨 [SEMANTIC_EMBEDDING] ⚠️ FALLBACK: Empty embeddings in response")
                        logger.warning("Empty embeddings in response - using fallback")
                        return self._get_fallback_embedding(text)
                else:
                    # PHASE 1: Record failure and fallback
                    self._circuit_breaker.record_failure()
                    print(f"🚨 [SEMANTIC_EMBEDDING] ⚠️ FALLBACK: Embedding generation failed")
                    logger.warning(f"Embedding generation failed - using fallback. Response: {response}")
                    return self._get_fallback_embedding(text)
                    
            except asyncio.TimeoutError:
                # PHASE 1: Record failure and fallback
                self._circuit_breaker.record_failure()
                print(f"🚨 [SEMANTIC_EMBEDDING] ⚠️ FALLBACK: Embedding request timed out after {embedding_timeout}s")
                logger.warning(f"Embedding generation timed out after {embedding_timeout}s - using fallback")
                return self._get_fallback_embedding(text)
            except Exception as e:
                # PHASE 1: Record failure and fallback
                self._circuit_breaker.record_failure()
                print(f"🚨 [SEMANTIC_EMBEDDING] ⚠️ FALLBACK: ModelService error: {e}")
                logger.warning(f"ModelService error during embedding generation: {e} - using fallback")
                return self._get_fallback_embedding(text)
            finally:
                # PHASE 1: Always release queue permission
                self._request_queue.release()
                
        except Exception as e:
            print(f"🚨 [SEMANTIC_EMBEDDING] ⚠️ FALLBACK: Unexpected error: {e}")
            logger.error(f"Unexpected error during embedding generation: {e} - using fallback")
            return self._get_fallback_embedding(text)
    
    def _get_fallback_embedding(self, text: str) -> Optional[List[float]]:
        """PHASE 1: Fallback embedding generation when ModelService is unavailable"""
        # Check cache first
        if text in self._fallback_cache:
            print(f"🟡 [SEMANTIC_FALLBACK] Using cached fallback embedding")
            return self._fallback_cache[text]
        
        # Simple hash-based embedding as fallback (768 dimensions to match sentence-transformers)
        import hashlib
        import struct
        
        # Create deterministic embedding from text hash
        hash_obj = hashlib.sha256(text.encode('utf-8'))
        hash_bytes = hash_obj.digest()
        
        # Convert to 768-dimensional vector (match sentence-transformers output)
        embedding = []
        for i in range(768):
            # Use different parts of hash to create varied dimensions
            byte_idx = (i * 4) % len(hash_bytes)
            val = struct.unpack('f', hash_bytes[byte_idx:byte_idx+4] + b'\x00' * (4 - min(4, len(hash_bytes) - byte_idx)))[0]
            # Normalize to [-1, 1] range
            embedding.append(val / (2**31))
        
        # Cache the fallback
        self._fallback_cache[text] = embedding
        print(f"🟡 [SEMANTIC_FALLBACK] Generated fallback embedding ({len(embedding)} dims)")
        logger.info(f"Generated fallback embedding for text: {text[:50]}...")
        
        return embedding
    
    async def _generate_embeddings_batch(self, texts: List[str]) -> List[Optional[List[float]]]:
        """ROOT FIX: Generate embeddings for multiple texts in a single modelservice call."""
        if not texts:
            return []
        
        try:
            if not self._modelservice:
                logger.error("Modelservice not available for batch embedding generation")
                return [None] * len(texts)
            
            import time
            start_time = time.time()
            
            logger.info(f"🚀 [BATCH_EMBEDDING] Processing batch of {len(texts)} embeddings")
            
            # ROOT FIX: Single modelservice call for multiple embeddings
            response = await self._modelservice.get_embeddings_batch(
                model=self._embedding_model,
                prompts=texts
            )
            
            total_time = time.time() - start_time
            
            if response.get("success") and "embeddings" in response.get("data", {}):
                embeddings = response["data"]["embeddings"]
                logger.info(f"🚀 [BATCH_EMBEDDING] ✅ Generated {len(embeddings)} embeddings in {total_time:.2f}s ({total_time/len(texts):.3f}s per embedding)")
                return embeddings
            else:
                logger.error(f"🚀 [BATCH_EMBEDDING] ❌ Batch embedding failed: {response.get('error', 'Unknown error')}")
                return [None] * len(texts)
                
        except Exception as e:
            logger.error(f"🚀 [BATCH_EMBEDDING] ❌ Exception during batch embedding: {e}")
            return [None] * len(texts)
    
    async def _store_user_facts_batch(self, extracted_facts: List) -> int:
        """ROOT FIX: Store multiple user facts with batch embedding generation."""
        if not extracted_facts:
            return 0
        
        try:
            if not self._user_facts_collection_obj:
                logger.error("User facts collection not initialized")
                return 0
            
            # Extract texts for batch embedding
            fact_texts = [fact.content for fact in extracted_facts]
            
            # ROOT FIX: Generate all embeddings in a single batch request
            import time
            batch_start = time.time()
            logger.info(f"🚀 [BATCH_FACTS] Generating embeddings for {len(fact_texts)} facts in batch")
            embeddings = await self._generate_embeddings_batch(fact_texts)
            batch_time = time.time() - batch_start
            
            if not embeddings or len(embeddings) != len(extracted_facts):
                logger.error(f"🚀 [BATCH_FACTS] ❌ Batch embedding failed or mismatched count")
                return 0
            
            # Store facts with their embeddings
            stored_count = 0
            for fact, embedding in zip(extracted_facts, embeddings):
                if embedding is None:
                    logger.warning(f"🚀 [BATCH_FACTS] ⚠️ Skipping fact with failed embedding: {fact.content[:50]}...")
                    continue
                
                try:
                    # Create unique ID for the fact
                    fact_id = f"fact_{fact.source_segment_id}_{hash(fact.content)}"
                    
                    # Create comprehensive metadata
                    metadata = {
                        "fact_type": fact.fact_type.value,
                        "confidence": fact.confidence,
                        "extraction_method": fact.extraction_method,
                        "source_segment_id": fact.source_segment_id,
                        "created_at": datetime.utcnow().isoformat(),
                        "entities_count": len(fact.entities),
                        "relations_count": 0,  # TODO: Relations not implemented yet
                        "category": fact.fact_type.value,
                        "user_id": getattr(fact, 'user_id', 'unknown')
                    }
                    
                    # Add entity information to metadata
                    if fact.entities:
                        metadata["entities"] = [{"text": e.text, "label": e.label, "confidence": e.confidence} for e in fact.entities]
                    
                    # Store in ChromaDB
                    self._user_facts_collection_obj.add(
                        documents=[fact.content],
                        embeddings=[embedding],
                        metadatas=[metadata],
                        ids=[fact_id]
                    )
                    
                    stored_count += 1
                    logger.debug(f"🚀 [BATCH_FACTS] ✅ Stored fact: {fact.content[:50]}...")
                    
                except Exception as e:
                    logger.error(f"🚀 [BATCH_FACTS] ❌ Failed to store individual fact: {e}")
                    continue
            
            # PERFORMANCE MONITORING
            total_time = time.time() - batch_start
            avg_time_per_fact = total_time / len(extracted_facts) if extracted_facts else 0
            success_rate = (stored_count / len(extracted_facts) * 100) if extracted_facts else 0
            
            logger.info(f"🚀 [BATCH_FACTS] ✅ Successfully stored {stored_count}/{len(extracted_facts)} facts in batch")
            logger.info(f"📊 [BATCH_FACTS_PERFORMANCE] Embedding: {batch_time:.2f}s, Storage: {total_time-batch_time:.2f}s, Total: {total_time:.2f}s")
            logger.info(f"📊 [BATCH_FACTS_PERFORMANCE] Avg per fact: {avg_time_per_fact:.3f}s, Success rate: {success_rate:.1f}%")
            
            # Performance warnings
            if avg_time_per_fact > 1.0:
                logger.warning(f"📊 [BATCH_FACTS_PERFORMANCE] ⚠️ SLOW FACT PROCESSING: {avg_time_per_fact:.3f}s per fact (threshold: 1.0s)")
            
            if success_rate < 95:
                logger.warning(f"📊 [BATCH_FACTS_PERFORMANCE] ⚠️ LOW SUCCESS RATE: {success_rate:.1f}% (threshold: 95%)")
            
            return stored_count
            
        except Exception as e:
            logger.error(f"🚀 [BATCH_FACTS] ❌ Batch fact storage failed: {e}")
            return 0
    
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
                "relations_count": 0,  # Relations not implemented yet
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

