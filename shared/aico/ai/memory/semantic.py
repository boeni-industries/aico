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
        self._modelservice = None
        
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
        """Inject modelservice dependency"""
        self._modelservice = modelservice
    
    async def initialize(self) -> None:
        """Initialize ChromaDB connection"""
        if self._initialized:
            return
            
        try:
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
    
    async def store_fact(self, fact: UserFact) -> bool:
        """Store a single user fact"""
        if not self._initialized:
            await self.initialize()
        
        if not self._modelservice:
            raise RuntimeError("Modelservice required for fact storage")
        
        try:
            # Generate embedding for fact content
            embedding = await self._generate_embedding(fact.content)
            if not embedding:
                logger.error(f"Failed to generate embedding for fact: {fact.content[:50]}...")
                return False
            
            # Create fact ID
            fact_id = f"fact_{fact.user_id}_{int(fact.valid_from.timestamp())}"
            
            # Prepare metadata for ChromaDB
            metadata = {
                "user_id": fact.user_id,
                "fact_type": fact.fact_type,
                "category": fact.category,
                "confidence": fact.confidence,
                "is_immutable": fact.is_immutable,
                "valid_from": fact.valid_from.isoformat(),
                "valid_until": fact.valid_until.isoformat() if fact.valid_until else None,
                "entities": json.dumps(fact.entities),
                "source_conversation_id": fact.source_conversation_id,
                "created_at": datetime.utcnow().isoformat()
            }
            
            # Store in ChromaDB
            self._collection.add(
                documents=[fact.content],
                embeddings=[embedding],
                metadatas=[metadata],
                ids=[fact_id]
            )
            
            logger.info(f"Stored fact: {fact.content[:50]}... (confidence: {fact.confidence})")
            return True
            
        except Exception as e:
            logger.error(f"Failed to store fact: {e}")
            return False
    
    async def query(self, query_text: str, max_results: int = None, 
                   filters: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """Query facts by semantic similarity"""
        if not self._initialized:
            await self.initialize()
        
        if not self._modelservice:
            raise RuntimeError("Modelservice required for querying")
        
        try:
            # Generate query embedding
            query_embedding = await self._generate_embedding(query_text)
            if not query_embedding:
                logger.error("Failed to generate query embedding")
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
            
            # Query ChromaDB (make async to prevent blocking)
            import asyncio
            results = await asyncio.to_thread(
                self._collection.query,
                query_embeddings=[query_embedding],
                n_results=max_results or self._max_results,
                where=where_clause if where_clause else None
            )
            
            # Format results
            formatted_results = []
            if results["documents"] and results["documents"][0]:
                for i, doc in enumerate(results["documents"][0]):
                    metadata = results["metadatas"][0][i] if results["metadatas"] else {}
                    distance = results["distances"][0][i] if results["distances"] else 0.0
                    similarity = 1.0 - distance  # Convert distance to similarity
                    
                    formatted_results.append({
                        "content": doc,
                        "similarity": similarity,
                        "metadata": metadata
                    })
            
            logger.debug(f"Query '{query_text}' returned {len(formatted_results)} results")
            return formatted_results
            
        except Exception as e:
            logger.error(f"Failed to query facts: {e}")
            return []
    
    async def store_message(self, user_id: str, conversation_id: str, 
                          content: str, role: str) -> bool:
        """Store message with fact extraction using GLiNER + LLM"""
        try:
            # Only extract facts from user messages
            if role == "user" and content.strip() and len(content.strip()) > 5:
                facts = await self._extract_facts(content, user_id, conversation_id)
                
                # Store extracted facts
                stored_count = 0
                for fact in facts:
                    if await self.store_fact(fact):
                        stored_count += 1
                
                if stored_count > 0:
                    logger.info(f"Extracted and stored {stored_count} facts using fact extraction pipeline")
                
            return True
            
        except Exception as e:
            logger.error(f"Failed to extract facts using fact extraction pipeline: {e}")
            return False
    
    async def _extract_facts(self, content: str, user_id: str, conversation_id: str) -> List[UserFact]:
        """Fact extraction using GLiNER + LLM via modelservice"""
        if not self._modelservice:
            logger.warning("Modelservice not available for fact extraction")
            return []
        
        try:
            # Step 1: Extract entities using GLiNER via modelservice
            entities = await self._extract_entities_gliner(content)
            
            # Step 2: Classify facts using LLM via modelservice  
            facts = await self._classify_facts_llm(content, entities, user_id, conversation_id)
            
            return facts
            
        except Exception as e:
            logger.error(f"Fact extraction failed: {e}")
            return []
    
    async def _extract_entities_gliner(self, text: str) -> List[Dict[str, Any]]:
        """Extract entities using GLiNER via modelservice NER endpoint"""
        try:
            # Call modelservice NER endpoint (GLiNER-based)
            ner_result = await self._modelservice.get_ner_entities(text)
            
            if ner_result and "entities" in ner_result:
                entities = []
                for entity in ner_result["entities"]:
                    entities.append({
                        "text": entity.get("text", ""),
                        "label": entity.get("label", ""),
                        "confidence": entity.get("confidence", 0.0),
                        "start": entity.get("start", 0),
                        "end": entity.get("end", 0)
                    })
                
                logger.debug(f"GLiNER extracted {len(entities)} entities: {[e['text'] for e in entities]}")
                return entities
            
            return []
            
        except Exception as e:
            logger.error(f"GLiNER entity extraction failed: {e}")
            return []
    
    async def _classify_facts_llm(self, content: str, entities: List[Dict], 
                                 user_id: str, conversation_id: str) -> List[UserFact]:
        """Classify extracted entities into structured facts using LLM"""
        if not entities:
            return []
        
        try:
            # Build LLM prompt for fact classification
            entities_text = ", ".join([f"{e['text']} ({e['label']})" for e in entities])
            
            classification_prompt = f"""Analyze this user message and extracted entities to create structured facts.

Message: "{content}"
Entities: {entities_text}

For each meaningful fact, provide:
1. fact_type: identity, preference, relationship, or temporal
2. category: personal_info, preferences, relationships, or general
3. confidence: 0.0-1.0 based on certainty
4. is_immutable: true for identity facts, false for preferences
5. content: clean factual statement

Only extract clear, meaningful facts. Ignore casual mentions.

Format as JSON array of facts."""

            # Call modelservice LLM endpoint
            llm_result = await self._modelservice.get_completions([{
                "role": "user", 
                "content": classification_prompt
            }])
            
            if llm_result and len(llm_result) > 0:
                response_text = llm_result[0].get("content", "")
                facts = await self._parse_llm_facts(response_text, entities, user_id, conversation_id)
                
                logger.debug(f"LLM classified {len(facts)} facts from entities")
                return facts
            
            return []
            
        except Exception as e:
            logger.error(f"LLM fact classification failed: {e}")
            return []
    
    async def _parse_llm_facts(self, llm_response: str, entities: List[Dict], 
                              user_id: str, conversation_id: str) -> List[UserFact]:
        """Parse LLM response into UserFact objects"""
        facts = []
        now = datetime.utcnow()
        
        try:
            # Try to extract JSON from LLM response
            import re
            json_match = re.search(r'\[.*\]', llm_response, re.DOTALL)
            if json_match:
                facts_data = json.loads(json_match.group())
                
                for fact_data in facts_data:
                    if isinstance(fact_data, dict) and "content" in fact_data:
                        # Extract entity names for this fact
                        fact_entities = [e["text"] for e in entities 
                                       if e["text"].lower() in fact_data["content"].lower()]
                        
                        # Determine temporal validity
                        is_immutable = fact_data.get("is_immutable", False)
                        valid_until = None if is_immutable else now + timedelta(days=365)
                        
                        fact = UserFact(
                            content=fact_data["content"],
                            fact_type=fact_data.get("fact_type", "temporal"),
                            category=fact_data.get("category", "general"),
                            confidence=min(1.0, max(0.0, fact_data.get("confidence", 0.5))),
                            is_immutable=is_immutable,
                            valid_from=now,
                            valid_until=valid_until,
                            entities=fact_entities,
                            source_conversation_id=conversation_id,
                            user_id=user_id
                        )
                        
                        # Only include facts with reasonable confidence
                        if fact.confidence >= 0.3:
                            facts.append(fact)
                
                logger.debug(f"Parsed {len(facts)} valid facts from LLM response")
            
        except Exception as e:
            logger.error(f"Failed to parse LLM facts: {e}")
        
        return facts
    
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
        if not self._modelservice:
            return None
        
        try:
            # Call modelservice for embedding generation
            embedding_result = await self._modelservice.get_embeddings(
                model=self._embedding_model, 
                prompt=text
            )
            if embedding_result and embedding_result.get("success"):
                return embedding_result.get("data", {}).get("embedding")
            return None
            
        except Exception as e:
            logger.error(f"Failed to generate embedding: {e}")
            return None
    
    async def cleanup(self) -> None:
        """Cleanup resources"""
        if self._chroma_client:
            # ChromaDB client cleanup is automatic
            pass
        self._initialized = False
        logger.info("Semantic memory store cleanup completed")
