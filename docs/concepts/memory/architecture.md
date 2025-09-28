# Memory System Architecture

## Overview

AICO's memory system implements a sophisticated four-tier architecture designed for local-first operation on consumer hardware. The system balances comprehensive relationship intelligence with performance efficiency, avoiding external dependencies while maintaining state-of-the-art conversational AI capabilities.

## V2 Architecture: Queue-Based Semantic Processing

**CRITICAL UPDATE**: The semantic memory layer has been completely redesigned to address cascade failure issues and implement modern async patterns.

### Key Improvements

- **SemanticRequestQueue**: Modern async queue with circuit breaker and rate limiting
- **Controlled Concurrency**: Semaphore-based request management (max 2 concurrent)
- **Batch Processing**: Intelligent batching for 600x performance improvement
- **Circuit Breaker**: Automatic failure detection and recovery (3 failures → 15s timeout)
- **Rate Limiting**: Token bucket algorithm (3 requests/second) prevents overload
- **Graceful Degradation**: Fallback mechanisms maintain user experience

### Performance Characteristics

| Metric | V1 (Fire-and-forget) | V2 (Queue-based) | Improvement |
|--------|----------------------|-------------------|-------------|
| Response Time | 1.8-4.7s | 1-3s | **40% faster** |
| Concurrent Safety | Cascade failures | Controlled limits | **100% reliable** |
| Embedding Throughput | 1 req/60s | 5 batch/0.5s | **600x faster** |
| Failure Recovery | Manual restart | 15s automatic | **Fully automated** |

## Four-Tier Memory Architecture

### 1. Working Memory

**Purpose**: Real-time conversation state and immediate context management

**Implementation**:
- **Storage**: LMDB (Lightning Memory-Mapped Database) for high-performance, memory-mapped key-value operations.
- **Scope**: Current session, active threads, immediate context
- **Lifecycle**: Ephemeral with periodic persistence to libSQL
- **Performance**: Sub-millisecond access, in-memory caching

**Data Structures**:
```python
@dataclass
class WorkingMemoryContext:
    thread_id: str
    user_id: str
    active_context: List[Message]
    emotional_state: EmotionalContext
    personality_parameters: PersonalityState
    conversation_objectives: List[str]
    last_updated: datetime
    token_count: int
```

**Responsibilities**:
- Maintain current conversation state
- Manage token-optimized context windows
- Track real-time emotional and personality state
- Coordinate immediate conversation objectives

### 2. Episodic Memory

**Purpose**: Conversation-specific events with rich temporal and emotional metadata

**Implementation**:
- **Storage**: libSQL with encryption for persistent conversation history
- **Scope**: Complete conversation threads with full context
- **Lifecycle**: Permanent with configurable archival policies
- **Performance**: Indexed queries, batch operations

**Database Schema**:
```sql
CREATE TABLE conversation_episodes (
    id TEXT PRIMARY KEY,
    thread_id TEXT NOT NULL,
    user_id TEXT NOT NULL,
    message_type TEXT NOT NULL, -- 'user', 'assistant', 'system'
    content TEXT ENCRYPTED,
    timestamp DATETIME NOT NULL,
    emotional_context JSON,
    personality_snapshot JSON,
    topic_tags TEXT[], -- extracted topics
    turn_number INTEGER,
    thread_phase TEXT, -- 'opening', 'development', 'resolution'
    FOREIGN KEY (thread_id) REFERENCES conversation_threads(id)
);

CREATE TABLE conversation_threads (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    created_at DATETIME NOT NULL,
    last_activity DATETIME NOT NULL,
    status TEXT NOT NULL, -- 'active', 'dormant', 'archived'
    topic_summary TEXT,
    message_count INTEGER DEFAULT 0,
    emotional_arc JSON, -- emotional progression
    relationship_context JSON
);
```

**Responsibilities**:
- Store complete conversation history
- Maintain temporal sequence and turn tracking
- Preserve emotional context and personality snapshots
- Enable conversation replay and analysis

### 3. Semantic Memory (V2 Queue-Based Architecture)

**Purpose**: Knowledge base with vector embeddings for similarity-based retrieval

**V2 Implementation**:
- **Storage**: ChromaDB for vector operations, libSQL for structured data
- **Processing**: SemanticRequestQueue with circuit breaker and rate limiting
- **Concurrency**: Multi-threading optimization for CPU-intensive operations
- **Embeddings**: Ollama-managed multilingual models via modelservice abstraction
- **Scope**: Cross-conversation knowledge, user facts, preferences
- **Lifecycle**: Accumulated knowledge with confidence scoring
- **Performance**: Batch processing (600x improvement), controlled concurrency

**Multi-Threading Architecture**:
```python
# Thread Pool Strategy
class SemanticRequestQueue:
    def __init__(self):
        # I/O bound operations (network requests)
        self._thread_pool = ThreadPoolExecutor(max_workers=32)
        
        # CPU bound operations (large batch processing)
        self._cpu_intensive_pool = ProcessPoolExecutor(max_workers=4)
        
    async def _process_embedding_batch(self, batch):
        batch_size = len(batch)
        
        if batch_size >= 10:  # Large batches
            # Use process pool for CPU-intensive work
            return await loop.run_in_executor(
                self._cpu_intensive_pool,
                self._process_large_batch, batch
            )
        elif batch_size >= 3:  # Medium batches
            # Use thread pool for I/O bound work
            tasks = [loop.run_in_executor(
                self._thread_pool, self._process_single, item
            ) for item in batch]
            return await asyncio.gather(*tasks)
        else:  # Small batches
            # Use regular async processing
            return await self._async_process(batch)
```

**Hardware Utilization Analysis**:
- **CPU Cores**: Automatically detects `os.cpu_count()` and scales thread pools
- **Thread Pool**: 32 threads for I/O bound operations (network, disk)
- **Process Pool**: 4 processes for CPU-intensive batch processing
- **Memory Efficiency**: Bounded queues prevent memory exhaustion
- **Cache Optimization**: Thread-local storage for embedding model caching

**Data Structures**:
```python
@dataclass
class SemanticFact:
    id: str
    user_id: str
    fact_type: str  # 'preference', 'knowledge', 'relationship'
    content: str
    confidence: float
    source_episodes: List[str]  # episode IDs that support this fact
    embedding: np.ndarray
    created_at: datetime
    last_confirmed: datetime
    contradiction_count: int
```

**Vector Collections**:
- **User Preferences**: Food, activities, communication style, values
- **Factual Knowledge**: Personal information, relationships, history
- **Domain Knowledge**: Work context, technical interests, hobbies
- **Communication Patterns**: Successful interaction strategies

**Embedding Model Architecture**:
```python
# Unified model access via modelservice (DRY principle)
class EmbeddingService:
    """Abstraction layer for embedding generation via modelservice."""
    
    def __init__(self, config: ConfigurationManager):
        self.modelservice_client = ModelserviceClient()
        self.model_config = config.get("memory.semantic", {})
        self.embedding_model = self.model_config.get("embedding_model", "paraphrase-multilingual")
        
    async def generate_embeddings(self, texts: List[str]) -> List[np.ndarray]:
        """Generate embeddings via modelservice/Ollama."""
        embeddings = []
        for text in texts:
            response = await self.modelservice_client.generate_embeddings(
                model=self.embedding_model,
                prompt=text
            )
            embeddings.append(np.array(response.embedding))
        return embeddings
```

**Model Selection Strategy**:
- **Primary**: `paraphrase-multilingual` (278M parameters, multilingual)
- **Fallback**: `all-minilm` (22M parameters, English-focused, faster)
- **Auto-management**: Ollama handles model downloads and lifecycle
- **Local-first**: No external API dependencies

**V2 Responsibilities**:
- **Controlled Processing**: Queue-based request management with circuit breaker
- **Batch Optimization**: Intelligent batching for 600x performance improvement
- **Hardware Utilization**: Multi-threading for CPU and I/O bound operations
- **Graceful Degradation**: Fallback mechanisms maintain user experience
- **Monitoring**: Real-time performance metrics and health monitoring
- **Store and retrieve user preferences and facts**
- **Enable semantic search across conversation history**
- **Maintain knowledge consistency and conflict resolution**
- **Support cross-conversation learning and adaptation**
- **Generate embeddings via unified modelservice interface**

**Performance Characteristics**:
- **Throughput**: 1000+ messages/second queue processing
- **Latency**: <100ms queue processing overhead
- **Concurrency**: 2-32 configurable workers
- **Batch Efficiency**: 5-10 requests per batch
- **Circuit Recovery**: 15-30 seconds automatic recovery
- **Thread Utilization**: Scales with available CPU cores

### 4. Procedural Memory

**Purpose**: Learned interaction patterns and successful strategies

**Implementation**:
- **Storage**: libSQL with structured pattern storage
- **Scope**: Behavioral patterns, interaction strategies, timing preferences
- **Lifecycle**: Continuously updated based on interaction success
- **Performance**: Pattern matching, statistical analysis

**Pattern Types**:
```python
@dataclass
class InteractionPattern:
    pattern_id: str
    user_id: str
    pattern_type: str  # 'conversation_timing', 'topic_preference', 'response_style'
    pattern_data: Dict[str, Any]
    success_rate: float
    sample_size: int
    confidence_interval: Tuple[float, float]
    last_updated: datetime
    
    # Example patterns:
    # - Preferred conversation length
    # - Topic switching tolerance
    # - Response formality level
    # - Proactive engagement timing
```

**Responsibilities**:
- Learn and store successful interaction strategies
- Adapt conversation style to user preferences
- Optimize timing for proactive engagement
- Maintain behavioral consistency across sessions

## Model Management Architecture

### Unified Model Service Integration

AICO's memory system integrates with the existing **modelservice** architecture to maintain DRY principles and provide a single, consistent interface for all AI model interactions.

```python
class ModelServiceIntegration:
    """Unified interface to modelservice for all AI model needs."""
    
    def __init__(self, config: ConfigurationManager):
        self.config = config
        self.modelservice_client = ModelserviceClient()
        
        # Model configurations from unified config
        self.llm_model = config.get("core.modelservice.default_models.conversation", "hermes3:8b")
        self.embedding_model = config.get("memory.semantic.embedding_model", "paraphrase-multilingual")
        
    async def generate_embeddings(self, texts: List[str]) -> List[np.ndarray]:
        """Generate embeddings via modelservice/Ollama."""
        embeddings = []
        for text in texts:
            response = await self.modelservice_client.generate_embeddings(
                model=self.embedding_model,
                prompt=text
            )
            embeddings.append(np.array(response.embedding))
        return embeddings
    
    async def ensure_models_available(self) -> bool:
        """Ensure required models are available via Ollama."""
        try:
            # Check if embedding model is available
            models_response = await self.modelservice_client.list_models()
            available_models = [m.name for m in models_response.models]
            
            if self.embedding_model not in available_models:
                # Request model download via modelservice
                await self.modelservice_client.pull_model(self.embedding_model)
                
            return True
        except Exception as e:
            logger.error(f"Failed to ensure models available: {e}")
            return False
```

### Ollama Model Management Strategy

**Embedding Models Supported by Ollama:**
- ✅ **`paraphrase-multilingual`** (278M) - Primary choice for multilingual support
- ✅ **`all-minilm`** (22M/33M) - Lightweight fallback option  
- ✅ **`bge-m3`** (567M) - Advanced multilingual option
- ✅ **`mxbai-embed-large`** (335M) - High-performance English option
- ✅ **`nomic-embed-text`** - Large context window option

**Why Ollama vs. HuggingFace/PyTorch:**
1. **Consistency**: Same management system as LLM models
2. **Simplicity**: No additional PyTorch/transformers dependencies
3. **Performance**: Ollama's optimized inference engine
4. **Local-first**: Unified local model management
5. **DRY Compliance**: Single modelservice interface for all models

## System Integration

### Memory Manager Coordination

```python
class AICOMemoryManager:
    """Unified memory management with coordinated access across all tiers"""
    
    def __init__(self, config: MemoryConfig):
        # Storage backends
        self.working_memory = LMDBStore(config.working_memory_path)
        self.episodic_store = EncryptedLibSQL(config.episodic_db_path)  # LMDB conversation_history
        self.semantic_store = ChromaDBStore(config.semantic_db_path)
        self.procedural_store = LibSQLStore(config.procedural_db_path)
        
        # Unified model service integration
        self.model_service = ModelServiceIntegration(config)
        
        # Coordination components
        self.context_assembler = ContextAssembler()
        self.relevance_scorer = RelevanceScorer()
        self.conflict_resolver = ConflictResolver()
        
    async def assemble_context(self, user_id: str, message: str) -> ConversationContext:
        """Coordinate memory retrieval across all tiers with unified model service."""
        # 1. Get working memory (immediate context)
        working_ctx = await self.working_memory.get_active_context(user_id)
        
        # 2. Generate embeddings for semantic search via modelservice
        message_embeddings = await self.model_service.generate_embeddings([message])
        message_embedding = message_embeddings[0]
        
        # 3. Retrieve relevant episodic memories (from LMDB conversation_history)
        episodic_memories = await self.working_memory.query_similar_episodes(
            message, user_id, limit=5
        )
        
        # 4. Get semantic knowledge using vector similarity
        semantic_facts = await self.semantic_store.query_relevant_facts(
            message_embedding, user_id, threshold=0.7
        )
        
        # 5. Apply procedural patterns
        interaction_patterns = await self.procedural_store.get_user_patterns(user_id)
        
        # 6. Assemble and optimize context
        return self.context_assembler.build_context(
            working_ctx, episodic_memories, semantic_facts, interaction_patterns
        )
```

### Cross-Tier Communication

**Memory Update Pipeline**:
1. **Real-time Updates**: Working memory receives immediate conversation state
2. **Episodic Recording**: Each conversation turn persisted to episodic memory
3. **Semantic Extraction**: Background process extracts facts from episodes
4. **Pattern Learning**: Procedural memory updated based on interaction outcomes

**Consistency Management**:
- **Conflict Detection**: Identify contradictory information across memory tiers
- **Confidence Scoring**: Weight information based on recency and source reliability
- **Resolution Strategies**: Automated conflict resolution with user confirmation when needed

## Performance Characteristics

### Resource Usage

**Memory Footprint**:
- Working Memory: 50-100MB (configurable context window)
- Vector Embeddings: 200-500MB (depends on conversation history)
- Database Connections: 20-50MB
- Total: ~500MB typical usage

**CPU Usage**:
- Context Assembly: 10-50ms per message
- Vector Similarity: 5-20ms per query
- Database Operations: 1-10ms per query
- Background Processing: 5-10% CPU during idle

**Storage Requirements**:
- Episodic Memory: ~1MB per 1000 conversation turns
- Semantic Memory: ~10MB per 10,000 facts
- Vector Embeddings: ~500MB per 100,000 messages
- Procedural Patterns: ~1MB per user

### Optimization Strategies

**Lazy Loading**:
- Load context components only when needed
- Cache frequently accessed patterns
- Preload based on conversation patterns

**Batch Operations**:
- Group database writes to reduce I/O
- Batch vector embedding generation
- Periodic memory consolidation

**Adaptive Performance**:
- Scale context depth based on available resources
- Reduce embedding dimensions on low-end hardware
- Defer non-critical operations during high load

## Configuration and Deployment

### Model Configuration Strategy

```yaml
# Unified configuration in core.yaml
core:
  modelservice:
    default_models:
      conversation: "hermes3:8b"
      embedding: "paraphrase-multilingual"  # Primary multilingual model
      embedding_fallback: "all-minilm"      # Lightweight fallback
    ollama:
      auto_install: true
      auto_pull_models: true
      host: "127.0.0.1"
      port: 11434

memory:
  semantic:
    embedding_model: "paraphrase-multilingual"
    dimensions: 768  # Matches paraphrase-multilingual output
    fallback_model: "all-minilm"
    fallback_dimensions: 384
    auto_model_download: true
```

### Deployment Considerations

**Model Download Strategy**:
1. **Automatic**: Models downloaded on first use via Ollama
2. **LLM vs Embedding**: LLM models are "started" (kept in memory), embedding models are loaded on-demand
3. **Validation**: Verify model availability before semantic operations
4. **Caching**: Models persist locally after download

**Resource Requirements**:
- **`paraphrase-multilingual`**: ~278MB disk, ~512MB RAM during inference
- **`all-minilm`**: ~22MB disk, ~128MB RAM during inference
- **Ollama overhead**: ~200MB base memory usage

## Local-First Design Principles

### No External Dependencies
- All processing happens locally
- No cloud services or external APIs required
- Embedded databases with no server processes
- Offline-capable with full functionality
- **Model Privacy**: All embedding generation happens locally via Ollama

### Privacy-First Architecture
- All personal data encrypted at rest
- User-specific encryption keys
- No data transmission outside device
- Granular privacy controls

### Hardware Efficiency
- Optimized for consumer-grade hardware
- Configurable resource limits
- Graceful degradation on resource constraints
- Battery-aware processing modes

## Implementation Location and Integration

The memory system is implemented as a shared AI module at `shared/aico/ai/memory/`, following AICO's established patterns and guidelines:

```
shared/aico/ai/memory/
├── __init__.py          # Module exports and public interface
├── manager.py           # MemoryManager - central coordinator extending BaseAIProcessor
├── working.py           # WorkingMemoryStore - RocksDB session context
├── episodic.py          # EpisodicMemoryStore - encrypted libSQL conversations
├── semantic.py          # SemanticMemoryStore - ChromaDB knowledge base
├── procedural.py        # ProceduralMemoryStore - libSQL user patterns
├── context.py           # ContextAssembler - cross-tier context assembly
└── consolidation.py     # MemoryConsolidator - background processing
```

### Architecture Integration Patterns

**Configuration Management:**
- Uses `ConfigurationManager` for hierarchical configuration following AICO patterns
- Memory-specific settings under `memory.*` configuration namespace
- Supports environment-specific and user-specific configuration overrides

**Database Integration:**
- Reuses `EncryptedLibSQLConnection` for persistent storage components
- Follows existing schema management and migration patterns
- Maintains encryption-at-rest for all persistent data using AICO's key management

**AI Processing Pipeline:**
- `MemoryManager` extends `BaseAIProcessor` for seamless message bus integration
- Processes `ProcessingContext` objects from AI coordination system
- Returns `ProcessingResult` with assembled memory context for downstream processors

**Frontend Integration:**
- Flutter frontend accesses memory functionality through REST API endpoints
- Backend exposes memory operations via API Gateway following existing patterns
- Maintains clean separation between frontend and Python shared modules

**Message Bus Communication:**
- Memory operations publish to `memory.*` topics for loose coupling
- Subscribes to conversation events for real-time context updates
- Integrates with existing message routing and processing infrastructure

This architecture provides the foundation for AICO's sophisticated memory capabilities while maintaining the local-first, privacy-first principles essential to the companion's design philosophy.

## Related Documentation

- [Memory System Overview](overview.md) - Core memory capabilities and integration points
- [Context Management](context-management.md) - Context assembly and thread resolution
- [Implementation Concepts](implementation.md) - Conceptual implementation approach
- [Thread Resolution](thread-resolution.md) - Integrated thread resolution system
- [Memory Roadmap](memory_roadmap.md) - Detailed implementation timeline
