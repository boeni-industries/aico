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
from .episodic import EpisodicMemoryStore  
from .semantic import SemanticMemoryStore
from .procedural import ProceduralMemoryStore
from .context import ContextAssembler
from .consolidation import MemoryConsolidator

logger = get_logger("shared", "ai.memory.manager")


@dataclass
class MemoryQuery:
    """Query structure for memory retrieval operations"""
    query_text: str
    query_type: str = "semantic"  # semantic, temporal, behavioral
    max_results: int = 10
    time_range: Optional[tuple] = None
    thread_id: Optional[str] = None
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
        
        # Memory stores (lazy initialization, implemented by phase)
        self._working_store: Optional[WorkingMemoryStore] = None
        self._episodic_store: Optional[EpisodicMemoryStore] = None
        self._semantic_store: Optional[SemanticMemoryStore] = None
        self._procedural_store: Optional[ProceduralMemoryStore] = None
        
        # Processing components
        self._context_assembler: Optional[ContextAssembler] = None
        self._consolidator: Optional[MemoryConsolidator] = None
        
        # Configuration following AICO patterns
        self._memory_config = self.config.get("memory", {})
        self._consolidation_interval = self._memory_config.get("consolidation_interval_hours", 24)
        
        logger.info("MemoryManager initialized with configuration")
        logger.debug(f"Memory config: {self._memory_config}")
        
    async def initialize(self) -> None:
        """Initialize memory components based on implementation phase"""
        if self._initialized:
            return
            
        logger.info("Initializing memory manager")
        
        try:
            # Phase 1: Initialize working memory (immediate)
            if self._memory_config.get("working.enabled", True):
                self._working_store = WorkingMemoryStore(self.config)
                await self._working_store.initialize()
                logger.info("Working memory store initialized")
            
            # Phase 2: Initialize episodic and semantic stores (when implemented)
            if self._memory_config.get("episodic.enabled", False):
                self._episodic_store = EpisodicMemoryStore(self.config)
                await self._episodic_store.initialize()
                logger.info("Episodic memory store initialized")
            
            if self._memory_config.get("semantic.enabled", False):
                self._semantic_store = SemanticMemoryStore(self.config)
                await self._semantic_store.initialize()
                logger.info("Semantic memory store initialized")
            
            # Phase 3: Initialize procedural store (when implemented)
            if self._memory_config.get("procedural.enabled", False):
                self._procedural_store = ProceduralMemoryStore(self.config)
                await self._procedural_store.initialize()
                logger.info("Procedural memory store initialized")
            
            # Initialize processing components based on available stores
            self._context_assembler = ContextAssembler(
                working_store=self._working_store,
                episodic_store=self._episodic_store,
                semantic_store=self._semantic_store,
                procedural_store=self._procedural_store
            )
            
            # Initialize consolidator if multiple stores available
            if any([self._episodic_store, self._semantic_store, self._procedural_store]):
                self._consolidator = MemoryConsolidator(
                    working_store=self._working_store,
                    episodic_store=self._episodic_store,
                    semantic_store=self._semantic_store,
                    procedural_store=self._procedural_store,
                    config_manager=self.config
                )
            
            self._initialized = True
            logger.info("Memory manager initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize memory manager: {e}")
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
        if not self._initialized:
            await self.initialize()
            
        start_time = datetime.utcnow()
        
        try:
            # Store current interaction (Phase 1+)
            if self._working_store:
                await self._store_interaction(context)
            
            # Assemble relevant context for processing
            memory_context = await self._assemble_context(context)
            
            # Update processing context with memory
            context.shared_state["memory_context"] = memory_context
            
            processing_time = (datetime.utcnow() - start_time).total_seconds() * 1000
            
            # Determine which tiers were accessed
            tiers_accessed = []
            if self._working_store:
                tiers_accessed.append("working")
            if self._episodic_store:
                tiers_accessed.append("episodic")
            if self._semantic_store:
                tiers_accessed.append("semantic")
            if self._procedural_store:
                tiers_accessed.append("procedural")
            
            return ProcessingResult(
                processor_name=self.name,
                success=True,
                data={
                    "context_assembled": True, 
                    "memory_entries": len(memory_context.get("memories", [])),
                    "phase": self._get_current_phase()
                },
                processing_time_ms=processing_time,
                metadata={"memory_tiers_accessed": tiers_accessed}
            )
            
        except Exception as e:
            logger.error(f"Memory processing failed: {e}")
            processing_time = (datetime.utcnow() - start_time).total_seconds() * 1000
            
            return ProcessingResult(
                processor_name=self.name,
                success=False,
                error=str(e),
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
            # Fallback for Phase 1 - basic working memory query
            logger.warning("Context assembler not available, using basic query")
            return MemoryResult(
                memories=[],
                context_summary="Limited query capability in current phase",
                relevance_scores=[],
                total_found=0,
                processing_time_ms=0.0
            )
    
    async def store_memory(self, memory_data: Dict[str, Any], memory_type: str = "working") -> bool:
        """Store memory in appropriate tier (based on available stores)"""
        if not self._initialized:
            await self.initialize()
            
        try:
            if memory_type == "working" and self._working_store:
                return await self._working_store.store(memory_data)
            elif memory_type == "episodic" and self._episodic_store:
                return await self._episodic_store.store(memory_data)
            elif memory_type == "semantic" and self._semantic_store:
                return await self._semantic_store.store(memory_data)
            elif memory_type == "procedural" and self._procedural_store:
                return await self._procedural_store.store(memory_data)
            else:
                logger.warning(f"Memory type {memory_type} not available in current phase")
                return False
                
        except Exception as e:
            logger.error(f"Failed to store {memory_type} memory: {e}")
            return False
    
    async def consolidate_memories(self, force: bool = False) -> Dict[str, Any]:
        """Trigger memory consolidation process (Phase 2+)"""
        if not self._initialized:
            await self.initialize()
            
        if self._consolidator:
            return await self._consolidator.consolidate(force=force)
        else:
            logger.info("Memory consolidation not available in current phase")
            return {"status": "not_available", "phase": self._get_current_phase()}
    
    async def get_thread_context(self, thread_id: str, user_id: str) -> Dict[str, Any]:
        """Get context for thread resolution"""
        if not self._initialized:
            await self.initialize()
            
        if self._context_assembler:
            return await self._context_assembler.get_thread_context(thread_id, user_id)
        else:
            # Phase 1 fallback - basic working memory context
            if self._working_store:
                context_data = await self._working_store.get_thread_context(thread_id)
                return {
                    "thread_id": thread_id,
                    "user_id": user_id,
                    "working_memory": context_data,
                    "context_strength": 0.5 if context_data else 0.0
                }
            return {"thread_id": thread_id, "user_id": user_id, "context_strength": 0.0}
    
    async def cleanup(self) -> None:
        """Cleanup resources for all initialized stores"""
        logger.info("Starting memory manager cleanup")
        
        cleanup_tasks = []
        if self._working_store:
            cleanup_tasks.append(self._working_store.cleanup())
        if self._episodic_store:
            cleanup_tasks.append(self._episodic_store.cleanup())
        if self._semantic_store:
            cleanup_tasks.append(self._semantic_store.cleanup())
        if self._procedural_store:
            cleanup_tasks.append(self._procedural_store.cleanup())
            
        if cleanup_tasks:
            await asyncio.gather(*cleanup_tasks, return_exceptions=True)
            
        self._initialized = False
        logger.info("Memory manager cleanup completed")
    
    def _get_current_phase(self) -> int:
        """Determine current implementation phase based on available stores"""
        if self._procedural_store:
            return 3
        elif self._episodic_store or self._semantic_store:
            return 2
        elif self._working_store:
            return 1
        else:
            return 0
    
    async def _store_interaction(self, context: ProcessingContext) -> None:
        """Store current interaction in working memory"""
        if not self._working_store:
            logger.warning("Working memory store not available")
            return
            
        interaction_data = {
            "thread_id": context.thread_id,
            "user_id": context.user_id,
            "message_content": context.message_content,
            "message_type": context.message_type,
            "timestamp": context.timestamp,
            "turn_number": context.turn_number,
            "conversation_phase": context.conversation_phase
        }
        
        await self._working_store.store(interaction_data)
    
    async def _assemble_context(self, context: ProcessingContext) -> Dict[str, Any]:
        """Assemble relevant memory context for processing"""
        if self._context_assembler:
            return await self._context_assembler.assemble_context(
                thread_id=context.thread_id,
                user_id=context.user_id,
                current_message=context.message_content,
                max_context_items=self._memory_config.get("max_context_items", 20)
            )
        else:
            # Phase 1 fallback - basic context from working memory
            basic_context = {
                "thread_id": context.thread_id,
                "user_id": context.user_id,
                "current_message": context.message_content,
                "assembled_at": datetime.utcnow().isoformat(),
                "total_items": 0,
                "context_summary": "Basic working memory context",
                "memories": [],
                "phase": 1
            }
            
            if self._working_store:
                working_context = await self._working_store.get_thread_context(context.thread_id)
                basic_context["memories"] = working_context
                basic_context["total_items"] = len(working_context)
                
            return basic_context
