"""
AICO Semantic Memory Store (V2)

Fact-centric memory storage with vector embeddings for intelligent context retrieval.
Simplified architecture focused on storing and retrieving structured facts.

Core Functionality:
- Fact storage: Store structured user facts with confidence scoring
- Semantic search: Query facts using natural language with embeddings
- Simple integration: Clean interface for memory manager

V2 Architecture:
- ChromaDB: Vector storage for facts with embeddings
- libSQL: Metadata storage using schema V5 fact tables
- Direct modelservice integration: No complex queuing or circuit breakers
- Fail-fast design: No fallbacks or degraded functionality
"""

import json
import asyncio
from typing import Dict, List, Optional, Any
from datetime import datetime
from dataclasses import dataclass

import chromadb
from chromadb.config import Settings

from aico.core.config import ConfigurationManager
from aico.core.logging import get_logger
from aico.core.paths import AICOPaths
# Queue system removed - using direct ModelService calls

logger = get_logger("shared", "ai.memory.semantic")


@dataclass
class UserFact:
    """Structured user fact for V2 architecture"""
    content: str
    fact_type: str  # identity, preference, relationship, temporal
    category: str   # personal_info, preferences, relationships
    confidence: float
    is_immutable: bool
    valid_from: datetime
    valid_until: Optional[datetime]
    entities: List[str]
    source_conversation_id: str
    user_id: str


class SemanticMemoryStore:
    """V2 Semantic Memory Store - Simple fact-centric storage"""
    
    def __init__(self, config_manager: ConfigurationManager):
        self.config = config_manager
        self._initialized = False
        self._chroma_client = None
        self._collection = None
        
        # Direct ModelService calls - no queue needed
        self._modelservice = None  # Will be set during initialization
        
        # Configuration
        memory_config = self.config.get("core.memory.semantic", {})
        # CRITICAL: Check for empty config - always indicates a major issue
        if not memory_config:
            logger.error("🚨 [CONFIG_ERROR] Semantic memory configuration is EMPTY! This indicates a critical config loading failure.")
            logger.error(f"🚨 [CONFIG_ERROR] Attempted to load config key: 'core.memory.semantic'")
            logger.error("🚨 [CONFIG_ERROR] This will cause semantic memory to use default values and may fail!")
        
        self._db_path = AICOPaths.get_semantic_memory_path()
        self._collection_name = memory_config.get("collections", {}).get("user_facts", "user_facts")
        self._embedding_model = memory_config.get("embedding_model", "paraphrase-multilingual")
        self._max_results = memory_config.get("max_results", 20)
        
        # Deduplication configuration
        dedup_config = memory_config.get("deduplication", {})
        self._dedup_enabled = dedup_config.get("enabled", True)
        self._dedup_threshold = dedup_config.get("similarity_threshold", 0.92)
        self._dedup_check_top_n = dedup_config.get("check_top_n", 5)
    
    def set_modelservice(self, modelservice):
        """Set the ModelService instance for embedding generation"""
        self._modelservice = modelservice
        logger.info("ModelService set for semantic memory store - using direct calls")
    
    async def initialize(self) -> None:
        """Initialize semantic memory store with request queue"""
        if self._initialized:
            return
            
        try:
            logger.info("Semantic memory store initializing with direct ModelService calls")
            
            # Initialize ChromaDB
            self._chroma_client = chromadb.PersistentClient(
                path=str(self._db_path),
                settings=Settings(allow_reset=False, anonymized_telemetry=False)
            )
            
            # Get or create collection
            try:
                self._collection = self._chroma_client.get_collection(self._collection_name)
                logger.info(f"Connected to existing collection: {self._collection_name}")
            except Exception:
                # Create collection with metadata
                self._collection = self._chroma_client.create_collection(
                    name=self._collection_name,
                    metadata={
                        "embedding_model": self._embedding_model,
                        "schema_version": "2.0",
                        "description": "Structured facts with confidence scoring"
                    }
                )
                logger.info(f"Created new collection: {self._collection_name}")
            
            self._initialized = True
            logger.info("Semantic memory store initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize semantic memory store: {e}")
            raise
    
    async def shutdown(self, timeout: float = 20.0) -> None:
        """Gracefully shutdown semantic memory store - integrates with AICO service shutdown"""
        if not self._initialized:
            return
            
        logger.warning(f"🔄 SEMANTIC STORE: Shutting down with {timeout}s timeout")
        start_time = time.time()
        
        try:
            # Direct ModelService calls - no queue to stop
            logger.info("Semantic memory store shutdown (direct ModelService calls)")
            
            # Close ChromaDB connection
            if self._chroma_client:
                # ChromaDB doesn't need explicit closing
                self._chroma_client = None
                self._collection = None
            
            self._initialized = False
            
            total_time = time.time() - start_time
            logger.warning(f"✅ SEMANTIC STORE: Shutdown completed in {total_time:.2f}s")
            
        except Exception as e:
            logger.error(f"Error during semantic memory shutdown: {e}")
            raise
    
    def get_queue_stats(self) -> Dict[str, Any]:
        """Get statistics for monitoring (direct ModelService calls)"""
        return {
            'mode': 'direct_modelservice_calls',
            'initialized': self._initialized,
            'modelservice_available': self._modelservice is not None,
            'collection_name': self._collection_name
        }
    
    async def store_fact(self, fact: UserFact) -> bool:
        """
        Store a fact in semantic memory with deduplication.
        
        Deduplication Strategy:
        1. Generate embedding for the fact
        2. Check for semantic duplicates (similarity >= threshold)
        3. If duplicate found: update existing fact
        4. If new: insert as new fact
        
        Args:
            fact: UserFact to store
            
        Returns:
            bool: True if stored/updated successfully
        """
        import time
        store_fact_start = time.time()
        
        if not self._initialized:
            await self.initialize()
        
        if not self._modelservice:
            raise RuntimeError("Modelservice required for fact storage")
        
        try:
            # Stage 1: Generate embedding
            embedding = await self._generate_embedding(fact.content)
            if not embedding:
                logger.error(f"Failed to generate embedding for fact: {fact.content[:50]}...")
                return False
            
            # Stage 2: Check for duplicates (if enabled)
            if self._dedup_enabled:
                duplicate = await self._find_duplicate_fact(
                    content=fact.content,
                    embedding=embedding,
                    user_id=fact.user_id
                )
                
                if duplicate:
                    # Update existing fact instead of creating duplicate
                    logger.info(f"📋 [DEDUP] Duplicate detected (similarity: {duplicate['similarity']:.3f})")
                    logger.info(f"📋 [DEDUP] Existing: {duplicate['content'][:50]}...")
                    logger.info(f"📋 [DEDUP] New: {fact.content[:50]}...")
                    
                    success = await self._update_fact(
                        fact_id=duplicate['id'],
                        new_fact=fact,
                        new_embedding=embedding
                    )
                    
                    store_fact_total = time.time() - store_fact_start
                    logger.info(f"🔍 [STORE] Fact updated in {store_fact_total*1000:.2f}ms")
                    return success
            
            # Stage 3: No duplicate found, insert as new fact
            success = await self._insert_new_fact(fact, embedding)
            
            store_fact_total = time.time() - store_fact_start
            logger.info(f"🔍 [STORE] Fact stored in {store_fact_total*1000:.2f}ms")
            return success
            
        except Exception as e:
            logger.error(f"🔍 [CHROMADB_STORE] ❌ FAILED to store fact: {e}")
            logger.error(f"🔍 [CHROMADB_STORE] Fact content: {fact.content}")
            return False
    
    async def _generate_embedding(self, text: str) -> Optional[List[float]]:
        """
        Generate embedding for text using ModelService.
        
        Args:
            text: Text to generate embedding for
            
        Returns:
            List[float]: Embedding vector or None if failed
        """
        import time
        try:
            embedding_start = time.time()
            result = await self._modelservice.get_embeddings(
                model=self._embedding_model,
                prompt=text
            )
            
            if result and result.get('success'):
                embedding = result.get('data', {}).get('embedding')
                if embedding:
                    embedding_duration = time.time() - embedding_start
                    logger.debug(f"🔍 [EMBEDDING] Generated in {embedding_duration*1000:.2f}ms")
                    return embedding
                else:
                    logger.error("No embedding data in successful response")
                    return None
            else:
                error_msg = result.get('error', 'Unknown error') if result else 'No result returned'
                logger.error(f"Embedding request failed: {error_msg}")
                return None
                
        except Exception as e:
            logger.error(f"Embedding generation failed: {e}")
            return None
    
    async def _find_duplicate_fact(
        self,
        content: str,
        embedding: List[float],
        user_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Find duplicate fact using semantic similarity.
        
        Args:
            content: Fact content to check
            embedding: Pre-computed embedding
            user_id: User ID to filter by
            
        Returns:
            Dict with duplicate info if found, None otherwise
        """
        try:
            # Query ChromaDB for similar facts (user-specific)
            results = self._collection.query(
                query_embeddings=[embedding],
                n_results=self._dedup_check_top_n,
                where={"user_id": user_id}
            )
            
            if not results['ids'] or not results['ids'][0]:
                return None
            
            # Check if any result exceeds similarity threshold
            for i, (doc_id, distance, document, metadata) in enumerate(zip(
                results['ids'][0],
                results['distances'][0],
                results['documents'][0],
                results['metadatas'][0]
            )):
                # ChromaDB uses L2 distance - convert to cosine similarity
                # For normalized embeddings: similarity ≈ 1 - (distance² / 2)
                similarity = 1 - (distance * distance / 2)
                
                if similarity >= self._dedup_threshold:
                    logger.debug(f"📋 [DEDUP] Found duplicate: similarity={similarity:.3f}, threshold={self._dedup_threshold}")
                    return {
                        'id': doc_id,
                        'content': document,
                        'similarity': similarity,
                        'metadata': metadata
                    }
            
            return None
            
        except Exception as e:
            logger.error(f"Duplicate detection failed: {e}")
            return None
    
    async def _update_fact(
        self,
        fact_id: str,
        new_fact: UserFact,
        new_embedding: List[float]
    ) -> bool:
        """
        Update existing fact with new information.
        
        Strategy:
        - Keep higher confidence value
        - Update timestamp to most recent
        - Preserve immutability flag if already set
        
        Args:
            fact_id: ID of existing fact
            new_fact: New fact data
            new_embedding: New embedding
            
        Returns:
            bool: True if updated successfully
        """
        try:
            # Get existing fact
            existing = self._collection.get(ids=[fact_id])
            if not existing['ids']:
                # Fact disappeared, insert as new
                logger.warning(f"📋 [DEDUP] Fact {fact_id} not found, inserting as new")
                return await self._insert_new_fact(new_fact, new_embedding)
            
            existing_metadata = existing['metadatas'][0]
            
            # Merge logic: keep higher confidence
            updated_confidence = max(
                float(existing_metadata.get('confidence', 0.0)),
                new_fact.confidence
            )
            
            # Preserve immutability if already set to True
            is_immutable = existing_metadata.get('is_immutable', 'False')
            if is_immutable == 'True' or new_fact.is_immutable:
                is_immutable = 'True'
            
            # Update metadata
            updated_metadata = {
                "user_id": new_fact.user_id,
                "fact_type": new_fact.fact_type,
                "category": new_fact.category,
                "confidence": updated_confidence,
                "is_immutable": is_immutable,
                "valid_from": new_fact.valid_from.isoformat(),
                "entities": json.dumps(new_fact.entities),
                "entities_json": json.dumps(new_fact.entities),
                "source_conversation_id": new_fact.source_conversation_id,
                "created_at": existing_metadata.get('created_at', datetime.utcnow().isoformat()),
                "updated_at": datetime.utcnow().isoformat()
            }
            
            if new_fact.valid_until:
                updated_metadata["valid_until"] = new_fact.valid_until.isoformat()
            
            # Update in ChromaDB
            self._collection.update(
                ids=[fact_id],
                embeddings=[new_embedding],
                metadatas=[updated_metadata],
                documents=[new_fact.content]
            )
            
            logger.info(f"✅ [DEDUP] Updated fact: {fact_id} (confidence: {updated_confidence:.2f})")
            return True
            
        except Exception as e:
            logger.error(f"Failed to update fact: {e}")
            return False
    
    async def _insert_new_fact(
        self,
        fact: UserFact,
        embedding: List[float]
    ) -> bool:
        """
        Insert new fact into ChromaDB.
        
        Args:
            fact: UserFact to insert
            embedding: Pre-computed embedding
            
        Returns:
            bool: True if inserted successfully
        """
        import time
        try:
            # Create fact ID
            fact_id = f"fact_{fact.user_id}_{int(fact.valid_from.timestamp())}"
            
            # Prepare metadata for ChromaDB (no None values allowed)
            metadata = {
                "user_id": fact.user_id,
                "fact_type": fact.fact_type,
                "category": fact.category,
                "confidence": fact.confidence,
                "is_immutable": str(fact.is_immutable),
                "valid_from": fact.valid_from.isoformat(),
                "entities": json.dumps(fact.entities),
                "entities_json": json.dumps(fact.entities),
                "source_conversation_id": fact.source_conversation_id,
                "created_at": datetime.utcnow().isoformat()
            }
            
            if fact.valid_until:
                metadata["valid_until"] = fact.valid_until.isoformat()
            
            # Store in ChromaDB
            chromadb_start = time.time()
            self._collection.add(
                documents=[fact.content],
                embeddings=[embedding],
                metadatas=[metadata],
                ids=[fact_id]
            )
            chromadb_duration = time.time() - chromadb_start
            
            logger.info(f"✅ [CHROMADB_STORE] Stored new fact in {chromadb_duration*1000:.2f}ms: {fact.content[:50]}... (confidence: {fact.confidence})")
            return True
            
        except Exception as e:
            logger.error(f"Failed to insert fact: {e}")
            return False
    
    async def query(self, query_text: str, max_results: int = None, 
                   filters: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """Query facts by semantic similarity"""
        if not self._initialized:
            await self.initialize()
        
        if not self._modelservice:
            logger.error("🚨 [SEMANTIC_QUERY] CRITICAL: Modelservice required for querying but not available!")
            logger.error("🚨 [SEMANTIC_QUERY] This means stored facts cannot be retrieved!")
            logger.error("🚨 [SEMANTIC_QUERY] Check memory manager modelservice injection during initialization!")
            raise RuntimeError("Modelservice required for querying")
        
        try:
            # Generate query embedding using direct ModelService calls
            try:
                logger.debug(f"🔍 [SEMANTIC_QUERY] Generating embedding for query: '{query_text[:50]}...'")
                embedding_result = await self._modelservice.get_embeddings(
                    prompt=query_text,
                    model=self._embedding_model
                )
                
                if not embedding_result.get("success", False):
                    logger.error(f"🔍 [SEMANTIC_QUERY] Failed to generate query embedding: {embedding_result.get('error', 'Unknown error')}")
                    return []
                
                query_embedding = embedding_result.get("data", {}).get("embedding")
                if not query_embedding:
                    logger.error("🔍 [SEMANTIC_QUERY] No embedding data in response")
                    return []
                    
                logger.debug(f"🔍 [SEMANTIC_QUERY] ✅ Generated {len(query_embedding)}-dimensional embedding")
            except Exception as e:
                logger.error(f"🔍 [SEMANTIC_QUERY] Direct ModelService embedding failed: {e}")
                return []
            
            # Prepare ChromaDB filters
            where_clause = {}
            if filters:
                if "user_id" in filters:
                    where_clause["user_id"] = filters["user_id"]
                if "fact_type" in filters:
                    where_clause["fact_type"] = filters["fact_type"]
                if "category" in filters:
                    where_clause["category"] = filters["category"]
            
            # Query ChromaDB with timeout protection
            import asyncio
            try:
                results = await asyncio.wait_for(
                    asyncio.to_thread(
                        self._collection.query,
                        query_embeddings=[query_embedding],
                        n_results=max_results or self._max_results,
                        where=where_clause if where_clause else None
                    ),
                    timeout=0.5  # 500ms timeout for ChromaDB queries
                )
            except asyncio.TimeoutError:
                logger.warning(f"ChromaDB query timed out after 500ms for query: {query_text[:50]}...")
                return []
            
            # Format results
            formatted_results = []
            if results["documents"] and results["documents"][0]:
                for i, doc in enumerate(results["documents"][0]):
                    metadata = results["metadatas"][0][i] if results["metadatas"] else {}
                    distance = results["distances"][0][i] if results["distances"] else 0.0
                    formatted_results.append({
                        "content": doc,
                        "metadata": metadata,
                        "distance": distance
                    })
            
            return formatted_results
            
        except Exception as e:
            logger.error(f"Failed to query semantic memory: {e}")
            return []
    
    async def store_message(self, user_id: str, conversation_id: str, content: str, role: str) -> bool:
        """Store message and extract facts"""
        import time
        start_time = time.time()
        print(f"🔍 [NER_DEEP_ANALYSIS] SemanticMemoryStore.store_message() STARTED [{start_time:.6f}]")
        logger.info(f"🔍 [SEMANTIC_TIMING] SemanticMemoryStore.store_message() started")
        
        try:
            if role == "user" and content.strip() and len(content.strip()) > 5:
                logger.info(f"🔍 [FACT_PIPELINE] ✅ STARTING fact extraction for user message: '{content[:100]}...'")
                
                extract_start = time.time()
                logger.info(f"🔍 [SEMANTIC_TIMING] Starting fact extraction...")
                facts = await self._extract_facts(content, user_id, conversation_id)
                extract_duration = time.time() - extract_start
                logger.info(f"🔍 [SEMANTIC_TIMING] Fact extraction completed in {extract_duration:.3f}s, found {len(facts)} facts")
                
                if not facts:
                    logger.info(f"🔍 [FACT_PIPELINE] ❌ NO FACTS extracted - nothing to store")
                    total_duration = time.time() - start_time
                    logger.info(f"🔍 [SEMANTIC_TIMING] SemanticMemoryStore.store_message() completed in {total_duration:.3f}s")
                    return True
                
                store_start = time.time()
                print(f"🔍 [FULL_TRACE] Starting storage of {len(facts)} facts [{store_start:.6f}]")
                logger.info(f"🔍 [SEMANTIC_TIMING] Starting fact storage for {len(facts)} facts...")
                stored_count = 0
                for i, fact in enumerate(facts):
                    fact_start = time.time()
                    print(f"🔍 [FULL_TRACE] Storing fact {i+1}/{len(facts)}: '{fact.content[:30]}...' [{fact_start:.6f}]")
                    success = await self.store_fact(fact)
                    fact_duration = time.time() - fact_start
                    print(f"🔍 [FULL_TRACE] Fact {i+1} storage completed in {fact_duration*1000:.2f}ms (success: {success}) [{time.time():.6f}]")
                    if success:
                        stored_count += 1
                        logger.info(f"🔍 [SEMANTIC_TIMING] Fact {i+1}/{len(facts)} stored in {fact_duration:.3f}s")
                    else:
                        logger.error(f"🔍 [SEMANTIC_TIMING] Fact {i+1}/{len(facts)} failed to store in {fact_duration:.3f}s")
                
                store_duration = time.time() - store_start
                logger.info(f"🔍 [SEMANTIC_TIMING] All fact storage completed in {store_duration:.3f}s")
                
                if stored_count > 0:
                    logger.info(f"Extracted and stored {stored_count} facts using fact extraction pipeline")
            else:
                logger.info(f"🔍 [FACT_PIPELINE] ❌ SKIPPED - role='{role}', content_length={len(content.strip()) if content else 0}")
            
            total_duration = time.time() - start_time
            logger.info(f"🔍 [SEMANTIC_TIMING] SemanticMemoryStore.store_message() completed in {total_duration:.3f}s")
            return True
            
        except Exception as e:
            total_duration = time.time() - start_time
            logger.error(f"🔍 [SEMANTIC_TIMING] Failed to store message after {total_duration:.3f}s: {e}")
            return False
    
    async def _extract_facts(self, content: str, user_id: str, conversation_id: str) -> List[UserFact]:
        """V2: Simple direct fact extraction using basic NER"""
        if not self._modelservice:
            logger.warning("Modelservice not available for fact extraction")
            return []
        
        try:
            import time
            ner_start = time.time()
            print(f"🔍 [NER_DEEP_ANALYSIS] _extract_facts() STARTING NER call [{ner_start:.6f}]")
            logger.info(f"🔍 [FACT_EXTRACTION] Starting simple fact extraction for: {content[:50]}...")
            
            # Simple NER call without complex optimization
            ner_result = await self._modelservice.get_ner_entities(content)
            ner_end = time.time()
            ner_duration = ner_end - ner_start
            print(f"🔍 [NER_DEEP_ANALYSIS] NER call COMPLETED in {ner_duration*1000:.2f}ms [{ner_end:.6f}]")
            
            if not ner_result.get("success", False):
                logger.warning(f"🔍 [FACT_EXTRACTION] NER failed: {ner_result.get('error', 'Unknown error')}")
                return []
            
            entities_dict = ner_result.get("data", {}).get("entities", {})
            logger.info(f"🔍 [FACT_EXTRACTION] Extracted entities by type: {entities_dict}")
            
            # Convert entities dict to list of entity objects
            entities = []
            for entity_type, entity_texts in entities_dict.items():
                for entity_text in entity_texts:
                    entities.append({
                        'text': entity_text,
                        'label': entity_type.lower(),
                        'confidence': 0.8  # Default confidence since GLiNER filtered already
                    })
            
            logger.info(f"🔍 [FACT_EXTRACTION] Converted to {len(entities)} entity objects: {entities}")
            
            if not entities:
                logger.info(f"🔍 [FACT_STORAGE] ❌ NO ENTITIES - No facts will be created from text: '{content[:100]}...'")
                return []
            
            facts_start = time.time()
            print(f"🔍 [FULL_TRACE] Starting fact creation from {len(entities)} entities [{facts_start:.6f}]")
            
            facts = []
            for i, entity in enumerate(entities):
                entity_start = time.time()
                entity_text = entity.get('text', '')
                entity_label = entity.get('label', 'unknown')
                entity_confidence = entity.get('confidence', 0.8)
                
                print(f"🔍 [FULL_TRACE] Creating fact {i+1}/{len(entities)}: '{entity_text}' [{entity_start:.6f}]")
                logger.info(f"🔍 [FACT_CREATION_{i}] Creating fact from entity: text='{entity_text}', label='{entity_label}', confidence={entity_confidence}")
                
                # Create simple facts from entities
                fact = UserFact(
                    user_id=user_id,
                    content=f"{entity_label}: {entity_text}",
                    fact_type="entity",
                    category="personal",
                    confidence=entity_confidence,
                    source_conversation_id=conversation_id,
                    is_immutable=False,  # Entity facts can change
                    valid_from=datetime.utcnow(),
                    valid_until=None,  # No expiration for entity facts
                    entities=entities_dict  # Store the original entities by type for evaluation compatibility
                )
                facts.append(fact)
                entity_end = time.time()
                print(f"🔍 [FULL_TRACE] Fact {i+1} created in {(entity_end-entity_start)*1000:.2f}ms [{entity_end:.6f}]")
                logger.info(f"🔍 [FACT_CREATION_{i}] ✅ Created fact: '{fact.content}'")
            
            logger.info(f"🔍 [FACT_EXTRACTION] ✅ Created {len(facts)} facts from {len(entities)} entities")
            return facts
            
        except Exception as e:
            logger.error(f"🔍 [FACT_EXTRACTION] Simple fact extraction failed: {e}")
            return []
    
    # V2: Removed complex GLiNER and LLM fact classification methods
    # Using simple direct NER-based fact extraction instead
    
    async def assemble_context(self, user_id: str, current_message: str) -> Dict[str, Any]:
        """Assemble context from stored facts"""
        try:
            # Query relevant facts for the user
            user_facts = await self.query(
                query_text=current_message,
                max_results=10,
                filters={"user_id": user_id}
            )
            
            # Simple context structure
            context = {
                "user_facts": user_facts,
                "recent_context": [],  # Will be populated by working memory
                "conversation_id": f"{user_id}_{int(datetime.utcnow().timestamp())}"
            }
            
            logger.debug(f"Assembled context with {len(user_facts)} facts for user {user_id}")
            return context
            
        except Exception as e:
            logger.error(f"Failed to assemble context: {e}")
            return {"user_facts": [], "recent_context": [], "conversation_id": ""}
    
    async def _generate_embedding(self, text: str) -> Optional[List[float]]:
        """Generate embedding using modelservice"""
        import time
        embed_start = time.time()
        print(f"🔍 [FULL_TRACE] _generate_embedding() STARTED for: '{text[:30]}...' [{embed_start:.6f}]")
        
        if not self._modelservice:
            return None
        
        try:
            # Call modelservice for embedding generation
            modelservice_start = time.time()
            print(f"🔍 [FULL_TRACE] Calling modelservice.get_embeddings() [{modelservice_start:.6f}]")
            embedding_result = await self._modelservice.get_embeddings(
                model=self._embedding_model, 
                prompt=text
            )
            modelservice_duration = time.time() - modelservice_start
            print(f"🔍 [FULL_TRACE] modelservice.get_embeddings() completed in {modelservice_duration*1000:.2f}ms [{time.time():.6f}]")
            
            if embedding_result and embedding_result.get("success"):
                embed_total = time.time() - embed_start
                print(f"🔍 [FULL_TRACE] _generate_embedding() SUCCESS in {embed_total*1000:.2f}ms [{time.time():.6f}]")
                return embedding_result.get("data", {}).get("embedding")
            
            print(f"🔍 [FULL_TRACE] _generate_embedding() FAILED - no success in result [{time.time():.6f}]")
            return None
            
        except Exception as e:
            embed_total = time.time() - embed_start
            print(f"🔍 [FULL_TRACE] _generate_embedding() EXCEPTION in {embed_total*1000:.2f}ms: {e} [{time.time():.6f}]")
            logger.error(f"Failed to generate embedding: {e}")
            return None
    
    async def cleanup(self) -> None:
        """Cleanup resources"""
        if self._chroma_client:
            # ChromaDB client cleanup is automatic
            pass
        self._initialized = False
        logger.info("Semantic memory store cleanup completed")
