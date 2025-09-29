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
        """Store a single user fact"""
        import time
        store_fact_start = time.time()
        print(f"🔍 [FULL_TRACE] store_fact() STARTED for: '{fact.content[:30]}...' [{store_fact_start:.6f}]")
        
        if not self._initialized:
            init_start = time.time()
            await self.initialize()
            init_duration = time.time() - init_start
            print(f"🔍 [FULL_TRACE] Initialization took {init_duration*1000:.2f}ms [{time.time():.6f}]")
        
        if not self._modelservice:
            raise RuntimeError("Modelservice required for fact storage")
        
        try:
            # EMERGENCY BYPASS: Skip queue entirely and call ModelService directly
            embedding_start = time.time()
            print(f"🔍 [FULL_TRACE] Starting DIRECT ModelService call (bypassing queue) [{embedding_start:.6f}]")
            try:
                # Direct call to ModelService - no queue at all
                result = await self._modelservice.get_embeddings(
                    model="paraphrase-multilingual",
                    prompt=fact.content
                )
                
                if result and result.get('success'):
                    embedding = result.get('data', {}).get('embedding')
                    if embedding:
                        embedding_duration = time.time() - embedding_start
                        print(f"🔍 [FULL_TRACE] DIRECT embedding completed in {embedding_duration*1000:.2f}ms [{time.time():.6f}]")
                    else:
                        raise RuntimeError("No embedding data in successful response")
                else:
                    error_msg = result.get('error', 'Unknown error') if result else 'No result returned'
                    raise RuntimeError(f"Embedding request failed: {error_msg}")
                    
            except Exception as e:
                embedding_duration = time.time() - embedding_start
                print(f"🔍 [FULL_TRACE] DIRECT embedding FAILED in {embedding_duration*1000:.2f}ms: {e} [{time.time():.6f}]")
                logger.error(f"Direct embedding failed: {e}")
                return False
            
            if not embedding:
                logger.error(f"Failed to generate embedding for fact: {fact.content[:50]}...")
                return False
            
            # Create fact ID
            fact_id = f"fact_{fact.user_id}_{int(fact.valid_from.timestamp())}"
            
            # Prepare metadata for ChromaDB (no None values allowed)
            metadata = {
                "user_id": fact.user_id,
                "fact_type": fact.fact_type,
                "category": fact.category,
                "confidence": fact.confidence,
                "is_immutable": str(fact.is_immutable),  # Convert bool to string
                "valid_from": fact.valid_from.isoformat(),
                "entities": json.dumps(fact.entities),
                "source_conversation_id": fact.source_conversation_id,
                "created_at": datetime.utcnow().isoformat()
            }
            
            # Only add valid_until if it exists (ChromaDB doesn't accept None)
            if fact.valid_until:
                metadata["valid_until"] = fact.valid_until.isoformat()
            
            # Store in ChromaDB
            chromadb_start = time.time()
            print(f"🔍 [FULL_TRACE] Starting ChromaDB storage [{chromadb_start:.6f}]")
            logger.info(f"🔍 [CHROMADB_STORE] Attempting to store fact with metadata: {metadata}")
            self._collection.add(
                documents=[fact.content],
                embeddings=[embedding],
                metadatas=[metadata],
                ids=[fact_id]
            )
            chromadb_duration = time.time() - chromadb_start
            print(f"🔍 [FULL_TRACE] ChromaDB storage completed in {chromadb_duration*1000:.2f}ms [{time.time():.6f}]")
            
            store_fact_total = time.time() - store_fact_start
            print(f"🔍 [FULL_TRACE] store_fact() COMPLETED in {store_fact_total*1000:.2f}ms [{time.time():.6f}]")
            logger.info(f"🔍 [CHROMADB_STORE] ✅ SUCCESS: Stored fact: {fact.content[:50]}... (confidence: {fact.confidence})")
            return True
            
        except Exception as e:
            logger.error(f"🔍 [CHROMADB_STORE] ❌ FAILED to store fact: {e}")
            logger.error(f"🔍 [CHROMADB_STORE] Fact content: {fact.content}")
            logger.error(f"🔍 [CHROMADB_STORE] Metadata: {metadata}")
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
                    entities=[entity_text]  # Store the entity text
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
