"""
AICO Memory Manager

This module provides the main interface and coordination layer for AICO's multi-tier memory system,
integrating working, episodic, semantic, and procedural memory stores to deliver unified memory
services for AI processing, conversation management, and personalized user interactions.

Core Functionality:
- Memory system coordination: Unified interface for all memory operations across multiple storage tiers
- Query orchestration: Intelligent routing and coordination of memory queries across appropriate stores
- Result aggregation: Combining and prioritizing results from multiple memory sources
- Memory lifecycle management: Initialization, maintenance, and cleanup of all memory components
- Performance optimization: Caching, batching, and optimization of memory operations
- Error handling: Robust error recovery and fallback mechanisms for memory operations
- Memory analytics: Usage statistics, performance metrics, and system health monitoring

Memory Tier Integration:
- Working Memory: Session context, active threads, temporary conversation state
- Episodic Memory: Conversation history, thread sequences, temporal context patterns
- Semantic Memory: Knowledge base, factual information, concept relationships
- Procedural Memory: User patterns, preferences, behavioral learning, personalization data
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
from .context import ContextAssembler

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
    
    Implementation phases:
    - Phase 1: Working memory and basic context assembly
    - Phase 2: Episodic storage and semantic analysis  
    - Phase 3: Behavioral learning and procedural memory
    - Phase 4: Advanced relationship intelligence
    """
    
    def __init__(self, config_manager: ConfigurationManager):
        super().__init__("memory_manager")
        self.config = config_manager
        self._initialized = False
        
        # Memory stores (lazy initialization)
        self._working_store: Optional[WorkingMemoryStore] = None
        self._semantic_store: Optional[SemanticMemoryStore] = None
        
        # Processing components
        self._context_assembler: Optional[ContextAssembler] = None
        
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
            
            # Initialize processing components based on available stores
            self._context_assembler = ContextAssembler(
                working_store=self._working_store,
                episodic_store=None,
                semantic_store=self._semantic_store,
                procedural_store=None
            )
            
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
            if self._semantic_store:
                await self._semantic_store.store_segment(
                    user_id=user_id,
                    conversation_id=conversation_id,
                    role=role,
                    content=content
                )
            
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
            # Use the context assembler if available
            if self._context_assembler:
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
            else:
                # Fallback: Direct store access
                logger.info(f"🔍 [MEMORY_TIMING] No context assembler, using direct store access...")
                context = {}
                
                # Get working memory (recent conversation)
                if self._working_store:
                    working_start = time.time()
                    logger.info(f"🔍 [MEMORY_TIMING] Starting working memory context retrieval...")
                    working_context = await self._working_store.get_context(user_id)
                    working_duration = time.time() - working_start
                    logger.info(f"🔍 [MEMORY_TIMING] Working memory context completed in {working_duration:.3f}s")
                    context["working"] = working_context
                
                # Get semantic memory (facts and entities)
                if self._semantic_store:
                    semantic_start = time.time()
                    logger.info(f"🔍 [MEMORY_TIMING] Starting semantic memory query...")
                    semantic_context = await self._semantic_store.query(user_id, current_message, limit=5)
                    semantic_duration = time.time() - semantic_start
                    logger.info(f"🔍 [MEMORY_TIMING] Semantic memory query completed in {semantic_duration:.3f}s")
                    context["semantic"] = semantic_context
                
                total_duration = time.time() - start_time
                logger.info(f"🔍 [MEMORY_TIMING] MemoryManager.assemble_context() completed in {total_duration:.3f}s")
                return context
            
        except Exception as e:
            total_duration = time.time() - start_time
            logger.error(f"🔍 [MEMORY_TIMING] Failed to assemble context after {total_duration:.3f}s: {e}")
            return {}

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
            # Shutdown semantic store (includes request queue and thread pools)
            if self._semantic_store:
                remaining_time = max(5.0, timeout - (time.time() - start_time))  # Minimum 5s
                await self._semantic_store.shutdown(timeout=remaining_time)
            
            # Shutdown other stores (they don't have async shutdown currently)
            # Working and episodic stores use synchronous cleanup
            # TODO: Add proper shutdown for working/episodic stores if needed
            
            self._initialized = False
            
            total_time = time.time() - start_time
            logger.warning(f"✅ MEMORY MANAGER: Shutdown completed in {total_time:.2f}s")
            
        except Exception as e:
            logger.error(f"Error during memory manager shutdown: {e}")
            raise
