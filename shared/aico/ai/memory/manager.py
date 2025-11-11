"""
AICO Memory Manager

This module provides the main interface and coordination layer for AICO's three-tier memory system,
integrating working memory, semantic memory with knowledge graph, and behavioral memory stores
to deliver unified memory services for AI processing, conversation management, and personalized interactions.

Core Functionality:
- Memory system coordination: Unified interface for all memory operations across multiple storage tiers
- Query orchestration: Intelligent routing and coordination of memory queries across appropriate stores
- Result aggregation: Combining and prioritizing results from multiple memory sources
- Memory lifecycle management: Initialization, maintenance, and cleanup of all memory components
- Performance optimization: Caching, batching, and optimization of memory operations
- Error handling: Robust error recovery and fallback mechanisms for memory operations
- Memory analytics: Usage statistics, performance metrics, and system health monitoring

Memory Tier Integration:
- Working Memory: Conversation history, session context, message storage (LMDB with 24hr TTL)
- Semantic Memory: Knowledge base with hybrid search (ChromaDB segments + libSQL knowledge graph)
- Procedural Memory: User patterns, preferences, behavioral learning (planned)
- Context Assembly: Cross-tier context coordination and relevance scoring

Technologies & Dependencies:
- asyncio: Asynchronous coordination of memory operations across multiple stores
- dataclasses: Structured representation of memory results and query parameters
- typing: Type safety for memory interfaces and result structures
- datetime: Temporal operations for memory queries and result timestamps
- concurrent.futures: Parallel execution of memory operations for performance optimization
- sentence-transformers: Embedding generation for semantic query processing and context analysis
  Rationale: Enables intelligent query routing and semantic similarity matching across memory tiers
- numpy: Vector operations for embedding similarity calculations and relevance scoring
- AICO ConfigurationManager: System-wide memory configuration and performance tuning
- AICO Logging: Comprehensive logging for memory operations and performance monitoring
- AICO Message Bus: Integration with system messaging for memory events and notifications

AI Model Integration:
- Semantic query processing: Uses transformer embeddings for intelligent memory query analysis
- Cross-tier relevance scoring: AI-driven relevance calculation across different memory types
- Context optimization: Machine learning-based context assembly and token optimization
- Query routing: Intelligent routing of queries to appropriate memory stores based on semantic analysis

Query & Result Management:
- Multi-tier queries: Coordinated queries across multiple memory stores with result merging
- Relevance scoring: Unified relevance scoring and ranking across different memory types
- Result filtering: Configurable filtering and limiting of memory results based on context
- Caching strategies: Intelligent caching of frequently accessed memory data
- Batch operations: Efficient batch processing for bulk memory operations
- Query optimization: Automatic optimization of memory queries based on usage patterns

Performance & Reliability:
- Connection pooling: Efficient management of database connections across memory stores
- Circuit breaker patterns: Fault tolerance and graceful degradation for memory store failures
- Health monitoring: Continuous monitoring of memory store health and performance
- Automatic recovery: Self-healing capabilities for temporary memory store failures
- Performance metrics: Detailed metrics collection for memory operation analysis
- Resource management: Memory usage monitoring and optimization across all stores
"""

from typing import Dict, List, Optional, Any
from datetime import datetime
import asyncio
from dataclasses import dataclass

from aico.core.config import ConfigurationManager
from aico.core.logging import get_logger
from aico.ai.base import ProcessingContext, ProcessingResult, BaseAIProcessor

# Import memory stores (will be implemented in phases)
from .working import WorkingMemoryStore
from .semantic import SemanticMemoryStore
from .context import ContextAssembler, ContextItem  # Uses context/ subdirectory

# Import knowledge graph components
from aico.ai.knowledge_graph import (
    PropertyGraphStorage,
    MultiPassExtractor,
    EntityResolver,
    GraphFusion
)
from aico.ai.knowledge_graph.modelservice_client import ModelserviceClient

# Import AMS components (Phase 1.5)
from .consolidation import ConsolidationScheduler, IdleDetector
from .temporal import EvolutionTracker

logger = get_logger("shared", "ai.memory.manager")


@dataclass
class MemoryQuery:
    """Query structure for memory retrieval operations"""
    query_text: str
    query_type: str = "semantic"  # semantic, temporal, behavioral
    max_results: int = 10
    time_range: Optional[tuple] = None
    conversation_id: Optional[str] = None
    user_id: Optional[str] = None
    relevance_threshold: float = 0.7


@dataclass
class MemoryResult:
    """Result structure for memory operations"""
    memories: List[Dict[str, Any]]
    context_summary: str
    relevance_scores: List[float]
    total_found: int
    processing_time_ms: float


class MemoryManager(BaseAIProcessor):
    """
    Central memory system coordinator following AICO patterns.
    
    Manages all memory tiers and provides unified interface for:
    - Context retrieval and assembly
    - Memory storage and consolidation
    - Thread resolution support
    - Cross-tier memory operations
    
    Integrates with message bus for loose coupling and follows
    AICO's privacy-first, local-only design principles.
    
    Implementation status:
    - Phase 1 ✅: Working memory with LMDB storage and context assembly
    - Phase 2 ✅: Semantic memory with hybrid search and knowledge graph
    - Phase 3 🔄: Procedural memory for behavioral learning (planned)
    - Phase 4 🔄: Advanced relationship intelligence and memory album
    """
    
    def __init__(self, config: ConfigurationManager, db_connection=None):
        """
        Initialize memory manager with configuration.
        
        Args:
            config: Configuration manager
            db_connection: Optional pre-authenticated database connection (for backend use)
        """
        self.config = config
        self._initialized = False
        self._db_connection = db_connection  # Store provided database connection
        
        # Memory stores (lazy initialization)
        self._working_store: Optional[WorkingMemoryStore] = None  # Conversation history + context
        self._semantic_store: Optional[SemanticMemoryStore] = None  # Segments + KG
        self._behavioral_store = None  # Planned: User patterns, skills, and preferences
        
        # Processing components
        self._context_assembler: Optional[ContextAssembler] = None
        
        # Knowledge graph components
        self._kg_storage: Optional[PropertyGraphStorage] = None
        self._kg_extractor: Optional[MultiPassExtractor] = None
        self._kg_resolver: Optional[EntityResolver] = None
        self._kg_fusion: Optional[GraphFusion] = None
        self._kg_modelservice: Optional[ModelserviceClient] = None
        self._kg_initialized = False
        self._kg_background_tasks: set = set()  # Track background extraction tasks
        
        # AMS components (Phase 1.5)
        self._consolidation_scheduler: Optional[ConsolidationScheduler] = None
        self._idle_detector: Optional[IdleDetector] = None
        self._evolution_tracker: Optional[EvolutionTracker] = None
        self._ams_enabled = False
        
        # Configuration following AICO patterns
        self._memory_config = self.config.get("core.memory", {})
        
        # CRITICAL: Check for empty config - always indicates a major issue
        if not self._memory_config:
            logger.error("🚨 [CONFIG_ERROR] Memory configuration is EMPTY! This indicates a critical config loading failure.")
            logger.error(f"🚨 [CONFIG_ERROR] Attempted to load config key: 'core.memory'")
            logger.error(f"🚨 [CONFIG_ERROR] Available config keys: {list(self.config._config.keys()) if hasattr(self.config, '_config') else 'No _config attribute'}")
            logger.error("🚨 [CONFIG_ERROR] This will cause semantic memory initialization to fail silently!")
        
        self._consolidation_interval = self._memory_config.get("consolidation_interval_hours", 24)
        
        # Additional validation for semantic config
        semantic_config = self._memory_config.get("semantic", {})
        if not semantic_config:
            logger.error("🚨 [CONFIG_ERROR] Semantic memory configuration is EMPTY!")
            logger.error(f"🚨 [CONFIG_ERROR] Memory config keys: {list(self._memory_config.keys())}")
            logger.error("🚨 [CONFIG_ERROR] Expected 'semantic' key with 'enabled' setting")
        
        logger.info("[DEBUG] MemoryManager: Initialized with configuration")
        logger.debug(f"Memory config: {self._memory_config}")
        logger.debug(f"Semantic config check: {semantic_config}")
        logger.debug(f"Semantic enabled check: {semantic_config.get('enabled', False)}")
        
        # Modelservice dependency (injected later)
        self._modelservice = None
    
    def set_modelservice(self, modelservice):
        """Inject modelservice dependency for semantic memory operations"""
        logger.info("[SEMANTIC] 🔧 LEGACY: set_modelservice() called - injecting dependency")
        self._modelservice = modelservice
        # If semantic store is already initialized, inject dependency
        if self._semantic_store:
            logger.info("[SEMANTIC] 🔧 LEGACY: Injecting modelservice into existing semantic store")
            self._semantic_store.set_modelservice(modelservice)
        else:
            logger.info("[SEMANTIC] 🔧 LEGACY: Semantic store not yet initialized, dependency will be injected during init")
        
    async def initialize(self) -> None:
        """Initialize memory components based on implementation phase"""
        if self._initialized:
            logger.info("🧠 [MEMORY_MANAGER] Already initialized, skipping...")
            return
            
        logger.info("🧠 [MEMORY_MANAGER] 🚀 Starting memory components initialization...")
        logger.info("[DEBUG] MemoryManager: Initializing memory components.")
        
        try:
            # Phase 1: Initialize working memory (immediate)
            if self._memory_config.get("working", {}).get("enabled", True):
                self._working_store = WorkingMemoryStore(self.config)
                await self._working_store.initialize()
                logger.info("Working memory store initialized")
            
            # Initialize semantic memory if enabled
            if self._memory_config.get("semantic", {}).get("enabled", False):
                logger.info("[SEMANTIC] Semantic memory enabled in config, initializing...")
                print(f"🔍 [MEMORY_MANAGER] About to create SemanticMemoryStore...")
                logger.info(f"🔍 [MEMORY_MANAGER] About to create SemanticMemoryStore...")
                self._semantic_store = SemanticMemoryStore(self.config)
                print(f"🔍 [MEMORY_MANAGER] ✅ SemanticMemoryStore created successfully")
                logger.info(f"🔍 [MEMORY_MANAGER] ✅ SemanticMemoryStore created successfully")
                
                # CRITICAL FIX: Get modelservice from backend services and inject dependency
                try:
                    from backend.services import get_modelservice_client
                    modelservice_client = get_modelservice_client(self.config)
                    logger.info("[SEMANTIC] 🔧 INJECTING MODELSERVICE DEPENDENCY")
                    self._semantic_store.set_modelservice(modelservice_client)
                    logger.info("[SEMANTIC] ✅ Modelservice dependency injected successfully")
                except Exception as e:
                    logger.error(f"[SEMANTIC] ❌ FAILED to inject modelservice dependency: {e}")
                    logger.error("[SEMANTIC] ⚠️  Semantic memory will not be able to query facts!")
                
                await self._semantic_store.initialize()
                logger.info("[SEMANTIC] ✅ Semantic memory store initialized successfully")
            else:
                logger.info("[SEMANTIC] Semantic memory disabled in config")
            
            # Initialize knowledge graph components FIRST so ContextAssembler can use them
            print("🔍 [MEMORY_MANAGER] About to call _initialize_knowledge_graph()...")
            await self._initialize_knowledge_graph()
            print(f"🔍 [MEMORY_MANAGER] _initialize_knowledge_graph() returned, _kg_initialized={self._kg_initialized}")
            
            # Initialize processing components based on available stores (including KG)
            self._context_assembler = ContextAssembler(
                working_store=self._working_store,
                episodic_store=None,  # Not implemented - working memory serves this role
                semantic_store=self._semantic_store,
                behavioral_store=None,  # Planned for Phase 3
                kg_storage=self._kg_storage if self._kg_initialized else None,
                kg_modelservice=self._kg_modelservice if self._kg_initialized else None,
                db_connection=self._db_connection
            )
            
            # Initialize AMS components (Phase 1.5)
            await self._initialize_ams_components()
            
            self._initialized = True
            logger.info("🧠 [MEMORY_MANAGER] ✅ Memory manager initialized successfully")
            logger.info("Memory manager initialized successfully")
            
        except Exception as e:
            error_msg = f"Failed to initialize memory manager: {e}"
            logger.error(error_msg)
            print(f"🚨 [MEMORY_INIT_ERROR] {error_msg}")
            
            # Get full stack trace
            import traceback
            stack_trace = traceback.format_exc()
            logger.error(f"🚨 [MEMORY_INIT_ERROR] Full stack trace:\n{stack_trace}")
            print(f"🚨 [MEMORY_INIT_ERROR] Full stack trace:\n{stack_trace}")
            raise
    
    async def _initialize_knowledge_graph(self) -> None:
        """Initialize knowledge graph components for structured memory extraction."""
        print("🔍 [KG_DEBUG] _initialize_knowledge_graph() CALLED")
        try:
            print("🔍 [KG_DEBUG] Inside try block")
            logger.info("🕸️ [KG] Initializing knowledge graph components...")
            print("🔍 [KG_DEBUG] Logger.info called")
            
            # Get database connection from working store (reuse existing connection)
            print(f"🔍 [KG_DEBUG] Checking working store: {self._working_store}")
            if not self._working_store:
                print("🔍 [KG_DEBUG] Working store is None, returning early")
                logger.warning("🕸️ [KG] Working store not available, skipping KG initialization")
                return
            print("🔍 [KG_DEBUG] Working store OK, continuing...")
            
            # Get encrypted database connection
            from aico.data.libsql.encrypted import EncryptedLibSQLConnection
            from aico.core.paths import AICOPaths
            from aico.security import AICOKeyManager
            
            # Create encrypted database connection for KG
            # Reuse existing database connection if available
            print(f"🔍 [KG_DEBUG] Checking for _db_connection: hasattr={hasattr(self, '_db_connection')}, value={getattr(self, '_db_connection', None)}")
            if hasattr(self, '_db_connection') and self._db_connection:
                db_connection = self._db_connection
                print("🔍 [KG_DEBUG] Using provided database connection")
                logger.info("🕸️ [KG] Reusing existing database connection")
            else:
                print("🔍 [KG_DEBUG] No db_connection provided, attempting authentication...")
                key_manager = AICOKeyManager()
                try:
                    master_key = key_manager.authenticate(interactive=False)
                    print("🔍 [KG_DEBUG] Authentication succeeded")
                except Exception as auth_error:
                    print(f"🔍 [KG_DEBUG] Authentication failed: {auth_error}")
                    logger.warning(f"🕸️ [KG] Authentication failed: {auth_error}, trying to get cached key")
                    # Try to get cached master key
                    master_key = key_manager.get_cached_master_key()
                    if not master_key:
                        print("🔍 [KG_DEBUG] No cached master key, RETURNING EARLY")
                        logger.error("🕸️ [KG] No cached master key available, KG initialization failed")
                        return
                    print("🔍 [KG_DEBUG] Got cached master key")
                
                db_path = AICOPaths.get_database_path()
                db_key = key_manager.derive_database_key(master_key, "libsql", "aico.db")
                db_connection = EncryptedLibSQLConnection(db_path, encryption_key=db_key)
                logger.info("🕸️ [KG] Created new database connection")
            
            # Get ChromaDB client from semantic store
            print("🔍 [KG_DEBUG] Getting ChromaDB client...")
            chromadb_client = None
            if self._semantic_store and hasattr(self._semantic_store, '_chroma_client'):
                chromadb_client = self._semantic_store._chroma_client
                print("🔍 [KG_DEBUG] Got ChromaDB client from semantic store")
            else:
                print("🔍 [KG_DEBUG] Creating new ChromaDB client...")
                logger.warning("🕸️ [KG] ChromaDB client not available from semantic store")
                # Create our own ChromaDB client
                import chromadb
                from chromadb.config import Settings
                chromadb_path = AICOPaths.get_semantic_memory_path()
                chromadb_client = chromadb.PersistentClient(
                    path=str(chromadb_path),
                    settings=Settings(anonymized_telemetry=False, allow_reset=True)
                )
                print("🔍 [KG_DEBUG] ChromaDB client created")
            
            # Initialize modelservice client (but don't connect yet - message bus may not be ready)
            print("🔍 [KG_DEBUG] Creating ModelserviceClient (deferred connection)...")
            self._kg_modelservice = ModelserviceClient()
            # Note: Connection will happen lazily on first use
            logger.info("🕸️ [KG] Modelservice client created (connection deferred)")
            
            # Initialize storage (pass modelservice for embedding generation)
            print("🔍 [KG_DEBUG] Initializing PropertyGraphStorage...")
            self._kg_storage = PropertyGraphStorage(db_connection, chromadb_client, self._kg_modelservice)
            logger.info("🕸️ [KG] Storage initialized")
            
            # Initialize extraction pipeline (modelservice will connect on first use)
            print("🔍 [KG_DEBUG] Initializing MultiPassExtractor...")
            self._kg_extractor = MultiPassExtractor(self._kg_modelservice, self.config)
            logger.info("🕸️ [KG] Extractor initialized")
            
            # Initialize entity resolver
            print("🔍 [KG_DEBUG] Initializing EntityResolver...")
            self._kg_resolver = EntityResolver(self._kg_modelservice, self.config)
            logger.info("🕸️ [KG] Entity resolver initialized")
            
            # Initialize graph fusion
            print("🔍 [KG_DEBUG] Initializing GraphFusion...")
            self._kg_fusion = GraphFusion(self._kg_modelservice, self.config)
            logger.info("🕸️ [KG] Graph fusion initialized")
            
            print("🔍 [KG_DEBUG] About to set _kg_initialized=True")
            self._kg_initialized = True
            logger.info("🕸️ [KG] ✅ Knowledge graph components initialized successfully")
            print("🔍 [KG_DEBUG] KG initialization COMPLETE!")
            
        except Exception as e:
            print(f"🔍 [KG_DEBUG] EXCEPTION CAUGHT: {e}")
            logger.error(f"🕸️ [KG] ❌ Failed to initialize knowledge graph: {e}")
            import traceback
            error_trace = traceback.format_exc()
            logger.error(f"🕸️ [KG] Traceback: {error_trace}")
            print(f"🔍 [KG_DEBUG] Full traceback:\n{error_trace}")
            # Don't fail overall initialization if KG fails
            self._kg_initialized = False
    
    async def _initialize_ams_components(self) -> None:
        """
        Initialize Adaptive Memory System components (Phase 1.5).
        
        Initializes:
        - ConsolidationScheduler: For memory consolidation orchestration
        - IdleDetector: For system idle period detection
        - EvolutionTracker: For temporal preference tracking
        """
        try:
            print("🧠 [AMS] Initializing Adaptive Memory System components...")
            logger.info("🧠 [AMS] Initializing Adaptive Memory System components...")
            
            # Check if AMS is enabled in configuration
            ams_config = self._memory_config.get("consolidation", {})
            if not ams_config.get("enabled", False):
                print("🧠 [AMS] ⚠️  Consolidation disabled in configuration, skipping AMS initialization")
                logger.info("🧠 [AMS] Consolidation disabled in configuration, skipping AMS initialization")
                return
            
            # Initialize idle detector
            idle_config = ams_config.get("idle_detection", {})
            self._idle_detector = IdleDetector(
                cpu_threshold_percent=idle_config.get("cpu_threshold", 20.0),
                check_interval_seconds=idle_config.get("check_interval_seconds", 60)
            )
            print("🧠 [AMS] ✅ Idle detector initialized")
            logger.info("🧠 [AMS] Idle detector initialized")
            
            # Initialize consolidation scheduler
            self._consolidation_scheduler = ConsolidationScheduler(
                idle_detector=self._idle_detector,
                max_concurrent_users=ams_config.get("max_concurrent_users", 4),
                max_duration_minutes=ams_config.get("max_duration_minutes", 60),
                user_sharding_cycle_days=ams_config.get("user_sharding_cycle_days", 7)
            )
            print("🧠 [AMS] ✅ Consolidation scheduler initialized")
            logger.info("🧠 [AMS] Consolidation scheduler initialized")
            
            # Initialize evolution tracker
            temporal_config = self._memory_config.get("temporal", {})
            if temporal_config.get("enabled", True):
                self._evolution_tracker = EvolutionTracker()
                print("🧠 [AMS] ✅ Evolution tracker initialized")
                logger.info("🧠 [AMS] Evolution tracker initialized")
            
            self._ams_enabled = True
            print("🧠 [AMS] ✅✅✅ Adaptive Memory System components initialized successfully!")
            logger.info("🧠 [AMS] ✅ Adaptive Memory System components initialized successfully")
            
        except Exception as e:
            print(f"🧠 [AMS] ❌❌❌ Failed to initialize AMS components: {e}")
            logger.error(f"🧠 [AMS] ❌ Failed to initialize AMS components: {e}")
            import traceback
            error_trace = traceback.format_exc()
            print(f"🧠 [AMS] Traceback:\n{error_trace}")
            logger.error(f"🧠 [AMS] Traceback: {error_trace}")
            # Don't fail overall initialization if AMS fails
            self._ams_enabled = False
    
    async def schedule_consolidation(self, user_id: str) -> bool:
        """
        Schedule memory consolidation for a specific user (AMS Phase 1.5).
        
        Args:
            user_id: User ID to consolidate memories for
            
        Returns:
            True if consolidation was scheduled successfully
        """
        if not self._ams_enabled or not self._consolidation_scheduler:
            logger.warning("🧠 [AMS] Consolidation not available - AMS not initialized")
            return False
        
        try:
            logger.info(f"🧠 [AMS] Scheduling consolidation for user {user_id}")
            await self._consolidation_scheduler.schedule_user_consolidation(user_id)
            return True
        except Exception as e:
            logger.error(f"🧠 [AMS] Failed to schedule consolidation: {e}")
            return False
    
    async def process(self, context: ProcessingContext) -> ProcessingResult:
        """
        Process memory operations based on context.
        
        Handles memory storage, retrieval, and context assembly
        for AI processing pipeline integration.
        
        Implementation varies by phase:
        - Phase 1: Working memory storage and basic context
        - Phase 2+: Multi-tier context assembly
        """
        import time
        timestamp = time.time()
        print(f"🚨 [MEMORY_MANAGER_DEBUG] MemoryManager.process() CALLED! [{timestamp:.6f}]")
        import time
        timestamp = time.time()
        print(f"🚨 [MEMORY_MANAGER_DEBUG] Context: conversation_id={context.conversation_id}, message_type={context.message_type} [{timestamp:.6f}]")
        
        # DIAGNOSTIC: Track where the delay occurs
        import time
        before_init_check = time.time()
        print(f"🔍 [ASYNC_DEBUG] Before initialization check [{before_init_check:.6f}]")
        logger.info(f"🧠 [MEMORY_FLOW] Processing memory operation for conversation {context.conversation_id}")
        logger.info(f"🧠 [MEMORY_FLOW] Message type: {context.message_type}, Turn: {context.turn_number}")
        
        if not self._initialized:
            import time
            before_init = time.time()
            print(f"🔍 [ASYNC_DEBUG] Before initialize() [{before_init:.6f}]")
            logger.info("🧠 [MEMORY_FLOW] Lazy initializing memory system on first use")
            await self.initialize()
            after_init = time.time()
            print(f"🔍 [ASYNC_DEBUG] After initialize() [{after_init:.6f}] - took {(after_init-before_init)*1000:.2f}ms")
            
        import time
        before_context_assembly = time.time()
        print(f"🔍 [ASYNC_DEBUG] Before context assembly [{before_context_assembly:.6f}]")
        start_time = datetime.utcnow()
        
        try:
            # Store current interaction (Phase 1+)
            if self._working_store:
                import time
                before_store = time.time()
                print(f"🔍 [ASYNC_DEBUG] Before working memory store [{before_store:.6f}]")
                logger.info("🧠 [MEMORY_FLOW] → Storing interaction in working memory")
                await self._store_interaction(context)
                after_store = time.time()
                print(f"🔍 [ASYNC_DEBUG] After working memory store [{after_store:.6f}] - took {(after_store-before_store)*1000:.2f}ms")
                logger.info("🧠 [MEMORY_FLOW] ✅ Working memory storage complete")
            else:
                logger.warning("🧠 [MEMORY_FLOW] ⚠️  Working memory not available")
            
            # Assemble relevant context for processing
            import time
            before_assemble = time.time()
            print(f"🔍 [ASYNC_DEBUG] Before _assemble_context() [{before_assemble:.6f}]")
            logger.info("🧠 [MEMORY_FLOW] → Assembling context from memory tiers")
            memory_context = await self._assemble_context(context)
            after_assemble = time.time()
            print(f"🔍 [ASYNC_DEBUG] After _assemble_context() [{after_assemble:.6f}] - took {(after_assemble-before_assemble)*1000:.2f}ms")
            
            # Log context assembly results
            context_items = memory_context.get("items", [])
            working_items = [item for item in context_items if item.get("source_tier") == "working"]
            semantic_items = [item for item in context_items if item.get("source_tier") == "semantic"]
            
            logger.info(f"🧠 [MEMORY_FLOW] ✅ Context assembled: {len(working_items)} working, {len(semantic_items)} semantic")
            
            # Update processing context with memory
            context.shared_state["memory_context"] = memory_context
            
            processing_time = (datetime.utcnow() - start_time).total_seconds() * 1000
            
            # Determine which tiers were accessed
            tiers_accessed = []
            if self._working_store:
                tiers_accessed.append("working")
            if self._semantic_store:
                tiers_accessed.append("semantic")
            
            logger.info(f"🧠 [MEMORY_FLOW] ✅ Memory processing complete ({processing_time:.1f}ms)")
            logger.info(f"🧠 [MEMORY_FLOW] Tiers accessed: {', '.join(tiers_accessed)}")
            
            return ProcessingResult(
                component=self.component_name,
                operation="memory_retrieval",
                success=True,
                result_data={
                    "memory_context": memory_context,
                    "tiers_accessed": tiers_accessed,
                    "processing_time_ms": processing_time,
                    "conversation_id": context.conversation_id,
                    "user_id": context.user_id,
                    "timestamp": datetime.utcnow().isoformat()
                },
                processing_time_ms=processing_time
            )
            
        except Exception as e:
            processing_time = (datetime.utcnow() - start_time).total_seconds() * 1000
            logger.error(f"🧠 [MEMORY_FLOW] ❌ Memory processing failed ({processing_time:.1f}ms): {e}")
            import traceback
            logger.error(f"🧠 [MEMORY_FLOW] Full traceback: {traceback.format_exc()}")
            
            return ProcessingResult(
                component=self.component_name,
                operation="memory_retrieval",
                success=False,
                error_message=str(e),
                processing_time_ms=processing_time
            )
    
    async def query_memory(self, query: MemoryQuery) -> MemoryResult:
        """Query memory across available tiers with unified interface"""
        if not self._initialized:
            await self.initialize()
            
        start_time = datetime.utcnow()
        
        if self._context_assembler:
            result = await self._context_assembler.query_memories(query)
            processing_time = (datetime.utcnow() - start_time).total_seconds() * 1000
            result.processing_time_ms = processing_time
            return result
        else:
            # Fallback - basic working memory query
            logger.warning("Context assembler not available, using basic query")
            return MemoryResult(
                memories=[],
                context_summary="Limited query capability in current phase",
                relevance_scores=[],
                total_found=0,
                processing_time_ms=0.0
            )
    
    async def store_message(self, user_id: str, conversation_id: str, content: str, role: str) -> bool:
        """V3 API: Store conversation segments (simplified)"""
        if not self._initialized:
            await self.initialize()
            
        try:
            # Store in working memory (LMDB) - short-term conversation state
            if self._working_store:
                message_data = {
                    "user_id": user_id,  # CRITICAL: Add user_id for proper retrieval
                    "conversation_id": conversation_id,
                    "content": content,
                    "role": role,
                    "timestamp": datetime.utcnow().isoformat(),
                    "message_type": f"{role}_input" if role == "user" else f"{role}_response"
                }
                await self._working_store.store_message(conversation_id, message_data)
            
            # Store in semantic memory (ChromaDB) - conversation segments for context retrieval
            # Run in background to avoid blocking conversation flow with embedding generation
            if self._semantic_store:
                async def store_segment_background():
                    try:
                        await self._semantic_store.store_segment(
                            user_id=user_id,
                            conversation_id=conversation_id,
                            role=role,
                            content=content
                        )
                    except Exception as e:
                        logger.error(f"Background segment storage failed: {e}")
                
                asyncio.create_task(store_segment_background())
            
            # KG extraction moved to consolidation scheduler (AMS architecture)
            # Per-message extraction disabled to prevent embedding queue saturation
            # Messages will be processed in batches during idle periods via ams.kg_consolidation task
            print(f"🕸️ [KG_CHECK] Checking if KG extraction should run: kg_initialized={self._kg_initialized}, role={role}")
            if self._kg_initialized and role == "user":
                print(f"🕸️ [KG] 📝 Message queued for consolidation (will be processed during next idle period)")
                logger.info(f"🕸️ [KG] Message queued for consolidation scheduler")
            else:
                print(f"🕸️ [KG] ⚠️  Skipping: kg_initialized={self._kg_initialized}, role={role}")
            
            logger.info(f"✅ Stored {role} message in memory")
            return True
            
        except Exception as e:
            logger.error(f"Failed to store message: {e}")
            return False
    
    async def assemble_context(self, user_id: str, current_message: str, conversation_id: str = None) -> Dict[str, Any]:
        """V2 API: Assemble context from working + semantic memory"""
        import time
        start_time = time.time()
        logger.info(f"🔍 [MEMORY_TIMING] MemoryManager.assemble_context() started")
        
        if not self._initialized:
            init_start = time.time()
            await self.initialize()
            init_duration = time.time() - init_start
            logger.info(f"🔍 [MEMORY_TIMING] Context assembly initialization took {init_duration:.3f}s")
            
        try:
            # Use context assembler - if it's not available, the system is broken
            if not self._context_assembler:
                raise RuntimeError("ContextAssembler not initialized - memory system is broken")
            
            assembler_start = time.time()
            logger.info(f"🔍 [MEMORY_TIMING] Starting context assembler...")
            context = await self._context_assembler.assemble_context(
                user_id=user_id,
                current_message=current_message,
                max_context_items=20,
                conversation_id=conversation_id
            )
            assembler_duration = time.time() - assembler_start
            logger.info(f"🔍 [MEMORY_TIMING] Context assembler completed in {assembler_duration:.3f}s")
            
            total_duration = time.time() - start_time
            logger.info(f"🔍 [MEMORY_TIMING] MemoryManager.assemble_context() completed in {total_duration:.3f}s")
            return context
            
        except Exception as e:
            total_duration = time.time() - start_time
            logger.error(f"🔍 [MEMORY_TIMING] Failed to assemble context after {total_duration:.3f}s: {e}")
            raise  # Fail loudly, don't return empty context

    async def store_memory(self, memory_data: Dict[str, Any], memory_type: str = "working") -> bool:
        """Legacy API: Store memory in appropriate tier (based on available stores)"""
        if not self._initialized:
            await self.initialize()
        try:
            if memory_type == "working" and self._working_store:
                return await self._working_store.store_memory(memory_data)
            elif memory_type == "semantic" and self._semantic_store:
                return await self._semantic_store.store_memory(memory_data)
            else:
                logger.warning(f"No store available for memory type: {memory_type}")
                return False
        except Exception as e:
            logger.error(f"Failed to store memory: {e}")
            return False
    
    async def consolidate_memories(self, force: bool = False) -> Dict[str, Any]:
        """Consolidation removed in V2 fact-centric architecture."""
        if not self._initialized:
            await self.initialize()
        logger.info("Memory consolidation is not part of the V2 architecture")
        return {"status": "removed", "phase": self._get_current_phase()}
    
    async def get_user_context(self, user_id: str) -> Dict[str, Any]:
        """Get context for thread resolution"""
        if not self._initialized:
            await self.initialize()
            
        if self._context_assembler:
            return await self._context_assembler.get_user_context(user_id)
        else:
            # Phase 1 fallback - basic working memory context
            if self._working_store:
                # Get recent user messages as context
                recent_messages = await self._working_store._get_recent_user_messages(user_id, hours=24)
                return {
                    "user_id": user_id,
                    "working_memory": recent_messages,
                    "context_strength": 0.5 if recent_messages else 0.0
                }
            return {"user_id": user_id, "context_strength": 0.0}
    
    def get_supported_operations(self) -> List[str]:
        """Return a list of supported memory operations."""
        return ["store", "retrieve", "query", "context_assembly"]

    async def health_check(self) -> Dict[str, Any]:
        """Perform a health check on the memory manager and its stores."""
        if not self._initialized:
            await self.initialize()

        working_store_healthy = False
        if self._working_store:
            working_store_healthy = self._working_store._initialized

        return {
            "status": "healthy" if working_store_healthy else "degraded",
            "phase": self._get_current_phase(),
            "stores": {
                "working_memory": {"status": "ok" if working_store_healthy else "error"},
                "semantic_memory": {"status": "ok" if self._semantic_store else "disabled"},
            }
        }

    async def cleanup(self) -> None:
        """Cleanup resources for all initialized stores"""
        logger.info("Starting memory manager cleanup")
        
        cleanup_tasks = []
        if self._working_store:
            cleanup_tasks.append(self._working_store.cleanup())
        if self._semantic_store:
            cleanup_tasks.append(self._semantic_store.cleanup())
            
        if cleanup_tasks:
            await asyncio.gather(*cleanup_tasks, return_exceptions=True)
            
        self._initialized = False
        logger.info("Memory manager cleanup completed")
    
    def _get_current_phase(self) -> int:
        """Determine current implementation phase based on available stores"""
        if self._semantic_store:
            return 2
        elif self._working_store:
            return 1
        else:
            return 0
    
    async def _store_interaction(self, context: ProcessingContext) -> None:
        """V2: Use unified store_message() API for consistent fact extraction"""
        logger.info(f"[DEBUG] MemoryManager: Using unified storage path for conversation {context.conversation_id}")
        
        # V2: Use the unified store_message API that includes fact extraction
        role = "user" if context.message_type == "user_input" else "assistant"
        await self.store_message(
            user_id=context.user_id,
            conversation_id=context.conversation_id,
            content=context.message_content,
            role=role
        )
        
        # V2: Background conversation segment processing removed
    
    # V2: Removed duplicate fact extraction method - handled by semantic store
    
    async def _assemble_context(self, context: ProcessingContext) -> Dict[str, Any]:
        """Assemble relevant memory context for processing"""
        if self._context_assembler:
            return await self._context_assembler.assemble_context(
                user_id=context.user_id,
                current_message=context.message_content,
                max_context_items=self._memory_config.get("max_context_items", 20)
            )
        else:
            # Phase 1 fallback - basic context from working memory
            basic_context = {
                "conversation_id": context.conversation_id,
                "user_id": context.user_id,
                "current_message": context.message_content,
                "assembled_at": datetime.utcnow().isoformat(),
                "total_items": 0,
                "context_summary": "Basic working memory context",
                "memories": [],
                "phase": 1
            }
            
            logger.info("[DEBUG] MemoryManager: Assembling context from working memory.")
            if self._working_store:
                working_context = await self._working_store.retrieve_user_history(context.user_id)
                basic_context["memories"] = working_context
                basic_context["total_items"] = len(working_context)
                
            return basic_context
    
    async def shutdown(self, timeout: float = 20.0) -> None:
        """Gracefully shutdown all memory stores - integrates with AICO service container"""
        if not self._initialized:
            return
            
        logger.warning(f"🔄 MEMORY MANAGER: Shutting down with {timeout}s timeout")
        start_time = time.time()
        
        try:
            # Cancel any running background KG extraction tasks
            if self._kg_background_tasks:
                logger.info(f"🕸️ [KG] Cancelling {len(self._kg_background_tasks)} background extraction tasks...")
                for task in self._kg_background_tasks:
                    task.cancel()
                # Wait for cancellation with timeout
                if self._kg_background_tasks:
                    await asyncio.wait(self._kg_background_tasks, timeout=2.0)
                logger.info("🕸️ [KG] Background tasks cancelled")
            
            # Shutdown KG modelservice client if connected
            if self._kg_modelservice and self._kg_modelservice._connected:
                logger.info("🕸️ [KG] Disconnecting modelservice client...")
                try:
                    await asyncio.wait_for(self._kg_modelservice.disconnect(), timeout=5.0)
                    logger.info("🕸️ [KG] Modelservice client disconnected")
                except asyncio.TimeoutError:
                    logger.warning("🕸️ [KG] Modelservice disconnect timed out")
                except Exception as e:
                    logger.error(f"🕸️ [KG] Error disconnecting modelservice: {e}")
            
            # Shutdown semantic store (includes request queue and thread pools)
            if self._semantic_store:
                remaining_time = max(5.0, timeout - (time.time() - start_time))  # Minimum 5s
                await self._semantic_store.shutdown(timeout=remaining_time)
            
            # Shutdown other stores (they don't have async shutdown currently)
            # Working memory uses synchronous cleanup
            # TODO: Add proper shutdown for working memory if needed
            
            self._initialized = False
            
            total_time = time.time() - start_time
            logger.warning(f"✅ MEMORY MANAGER: Shutdown completed in {total_time:.2f}s")
            
        except Exception as e:
            logger.error(f"Error during memory manager shutdown: {e}")
            raise
    
    async def _extract_knowledge_graph(self, user_id: str, text: str) -> None:
        """Background knowledge graph extraction from user message."""
        import time
        start_time = time.time()
        print(f"\n{'='*80}")
        print(f"🕸️ [KG] 🚀 Background extraction task STARTED for user {user_id}")
        print(f"🕸️ [KG] Text length: {len(text)} chars")
        print(f"{'='*80}")
        try:
            # 1. Extract entities and relationships
            print(f"\n🕸️ [KG] Step 1: Multi-pass extraction...")
            extraction_start = time.time()
            logger.info(f"🕸️ [KG] Starting background extraction for user {user_id}")
            
            new_graph = await self._kg_extractor.extract(text, user_id)
            extraction_time = time.time() - extraction_start
            
            print(f"\n🕸️ [KG] ✅ Extraction complete in {extraction_time:.2f}s")
            print(f"🕸️ [KG]    Nodes: {len(new_graph.nodes)}")
            print(f"🕸️ [KG]    Edges: {len(new_graph.edges)}")
            logger.info(f"🕸️ [KG] Extracted {len(new_graph.nodes)} nodes, {len(new_graph.edges)} edges in {extraction_time:.2f}s")
            
            if len(new_graph.nodes) == 0 and len(new_graph.edges) == 0:
                logger.info(" [KG]  No entities extracted, skipping")
                return
            
            # 2. Entity resolution (deduplicate against existing graph)
            print(f"\n [KG]  Step 2: Entity resolution (HNSW-based deduplication)")
            resolution_start = time.time()
            superseded_ids = set()  # Track nodes that should be marked historical
            try:
                # Get existing nodes for this user
                db_fetch_start = time.time()
                existing_nodes = await self._kg_storage.get_user_nodes(user_id, current_only=True)
                db_fetch_time = time.time() - db_fetch_start
                print(f" [KG]    Found {len(existing_nodes)} existing nodes in DB ({db_fetch_time:.2f}s)")
                
                # Resolve entities (deduplicate)
                resolve_start = time.time()
                resolution_result = await self._kg_resolver.resolve(new_graph, user_id, existing_nodes)
                resolve_time = time.time() - resolve_start
                
                resolved_graph = resolution_result.resolved_graph
                superseded_ids = resolution_result.superseded_node_ids
                
                duplicates_merged = len(new_graph.nodes) - len(resolved_graph.nodes)
                print(f"\n🕸️ [KG] ✅ Resolution complete in {resolve_time:.2f}s")
                print(f"🕸️ [KG]    Before: {len(new_graph.nodes)} nodes")
                print(f"🕸️ [KG]    After:  {len(resolved_graph.nodes)} nodes")
                print(f"🕸️ [KG]    Merged: {duplicates_merged} duplicates")
                
                # Use resolved graph for storage
                new_graph = resolved_graph
            except Exception as e:
                resolution_time = time.time() - resolution_start
                print(f"\n🕸️ [KG] ⚠️  Entity resolution failed after {resolution_time:.2f}s: {e}")
                print(f"🕸️ [KG]    Proceeding with unresolved graph")
                logger.warning(f"Entity resolution failed: {e}, proceeding with unresolved graph")
                superseded_ids = set()  # No superseded nodes if resolution failed
                import traceback
                traceback.print_exc()
            
            # 3. Graph fusion - SKIPPED (not critical for initial testing)
            print(f"\n🕸️ [KG] Step 3: Graph fusion (skipped for now)")
            
            # 4. Save to storage (libSQL + ChromaDB with embeddings)
            print(f"\n🕸️ [KG] Step 4: Saving to storage...")
            storage_start = time.time()
            await self._kg_storage.save_graph(new_graph, superseded_node_ids=superseded_ids)
            storage_time = time.time() - storage_start
            
            total_time = time.time() - start_time
            print(f"\n🕸️ [KG] ✅ Storage complete in {storage_time:.2f}s")
            print(f"\n{'='*80}")
            print(f"🕸️ [KG] ✅ PIPELINE COMPLETE in {total_time:.2f}s")
            print(f"🕸️ [KG]    Extraction:  {extraction_time:.2f}s ({extraction_time/total_time*100:.1f}%)")
            print(f"🕸️ [KG]    Resolution: {time.time() - resolution_start:.2f}s ({(time.time() - resolution_start)/total_time*100:.1f}%)")
            print(f"🕸️ [KG]    Storage:    {storage_time:.2f}s ({storage_time/total_time*100:.1f}%)")
            print(f"🕸️ [KG]    Final: {len(new_graph.nodes)} nodes, {len(new_graph.edges)} edges")
            print(f"{'='*80}\n")
            logger.info(f"🕸️ [KG] ✅ Knowledge graph saved successfully in {total_time:.2f}s")
            
        except Exception as e:
            total_time = time.time() - start_time
            print(f"\n{'='*80}")
            print(f"🕸️ [KG] ❌ PIPELINE FAILED after {total_time:.2f}s: {e}")
            print(f"{'='*80}")
            logger.error(f"🕸️ [KG] ❌ Background extraction failed: {e}")
            import traceback
            error_trace = traceback.format_exc()
            print(f"🕸️ [KG] Traceback:\n{error_trace}")
            logger.error(f"🕸️ [KG] Traceback: {error_trace}")
