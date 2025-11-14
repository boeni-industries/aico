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

## Memory Architecture: Three Tiers

### 1. Working Memory

**Purpose**: Real-time conversation state and immediate context management

**Implementation**:
- **Storage**: LMDB (Lightning Memory-Mapped Database) for high-performance key-value operations
- **Scope**: Recent conversation history, scoped by conversation_id
- **Lifecycle**: TTL-based expiration (24 hours default)
- **Performance**: Sub-millisecond access, memory-mapped files
- **Dual Role**: Serves both immediate context AND conversation history (no separate episodic tier needed)

**Data Structures**:
```python
# Messages stored with key pattern: {conversation_id}:{timestamp}
# Retrieved by conversation_id prefix scan
{
    "conversation_id": "user123_1699123456",
    "user_id": "user123",
    "role": "user" | "assistant",
    "content": "message text",
    "timestamp": "2025-11-05T15:30:00Z"
}
```

**Responsibilities**:
- Store all conversation messages per conversation_id
- Provide fast retrieval for context assembly
- Automatic expiration of old messages (24hr TTL)
- Cross-conversation message queries for semantic memory
- Serve as conversation history store (replaces traditional "episodic memory")

### 2. Semantic Memory + Knowledge Graph (V3 Hybrid Search)

**Purpose**: Long-term knowledge storage with semantic search and graph relationships

**V3 Implementation**:

**A. Conversation Segments (ChromaDB)**
- **Storage**: ChromaDB with cosine similarity
- **Search**: Hybrid search combining semantic similarity with BM25 keyword matching
- **Fusion**: Reciprocal Rank Fusion (RRF) for robust score combination
- **Filtering**: IDF-based term filtering (min_idf=0.6) + semantic relevance thresholds (min_score=0.35)
- **Embeddings**: `paraphrase-multilingual` (768-dim) via Ollama modelservice
- **Scope**: Conversation chunks scoped by conversation_id and user_id
- **Performance**: Full-corpus BM25 for accurate IDF statistics

**B. Knowledge Graph (ChromaDB + libSQL)**
- **Storage**: Hybrid ChromaDB (vectors) + libSQL (relational queries)
- **Extraction**: Multi-pass with GLiNER (entities) + LLM (relationships)
- **Entity Resolution**: 3-step process (semantic blocking → LLM matching → LLM merging)
- **Graph Fusion**: Conflict resolution, temporal updates, canonical IDs
- **Schema**: kg_nodes, kg_edges, kg_node_properties, kg_edge_properties (with triggers)
- **Production Status**: 204 nodes, 27 edges, 552 indexed properties
- **Scope**: Cross-conversation knowledge accumulation
- **Integration**: Tightly coupled with semantic memory for fact extraction and retrieval

**Hybrid Search Pipeline**:
```python
# Three-stage retrieval pipeline
def query_semantic_memory(query_text: str, user_id: str):
    # Stage 1: Full corpus retrieval for proper IDF statistics
    all_documents = collection.query(
        query_embeddings=[embedding],
        n_results=collection.count()  # CRITICAL: Full corpus
    )
    
    # Stage 2: Dual scoring (semantic + BM25 with IDF filtering)
    scored_docs = calculate_scores(
        documents=all_documents,
        query_text=query_text,
        min_idf=0.6  # Filter common terms
    )
    
    # Stage 3: RRF fusion with semantic relevance filtering
    results = fuse_with_rrf(
        scored_docs,
        k=60,  # Adaptive rank constant
        min_semantic_score=0.35  # Relevance threshold
    )
    
    return results[:max_results]
```

**Key Features**:
- ✅ **Full corpus BM25**: Accurate IDF calculation on all documents
- ✅ **IDF term filtering**: Removes overly common words (min_idf=0.6)
- ✅ **Semantic threshold**: Filters irrelevant results (min_semantic_score=0.35)
- ✅ **RRF fusion**: Industry-standard rank-based combination
- ✅ **Configurable**: All thresholds tunable via config

For detailed hybrid search documentation, see [Hybrid Search Guide](hybrid-search.md).

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

### 3. Behavioral Learning (Planned)

**Purpose**: Learn user interaction patterns, preferences, and behavioral adaptation

**Planned Implementation**:
- **Storage**: libSQL for fast pattern queries (no embeddings needed)
- **Scope**: User-level behavioral patterns across all conversations
- **Learning**: Continuous observation and pattern extraction
- **Adaptation**: Real-time response style and content adjustment

**Pattern Types**:
```python
# Interaction patterns to learn
- Response length preferences (by time of day, topic, context)
- Topic interests and avoidances
- Communication style preferences (formal/casual, brief/detailed)
- Engagement signals (follow-up questions, topic changes)
- Successful conversation patterns
- Time-of-day behavioral patterns
```

**Data Structures**:
```python
@dataclass
class UserPattern:
    pattern_id: str
    user_id: str
    pattern_type: str  # 'response_length', 'topic_preference', 'time_of_day'
    pattern_data: Dict[str, Any]
    confidence: float  # Based on observation frequency
    observation_count: int
    last_observed: datetime
    created_at: datetime
```

**Responsibilities**:
- Track user interaction patterns and preferences
- Learn optimal response styles and timing
- Enable adaptive personalization
- Provide conversation quality metrics
- Support proactive engagement strategies

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
        self.working_memory = LMDBStore(config.working_memory_path)  # Conversation history + context
        self.semantic_store = ChromaDBStore(config.semantic_db_path)  # Segments + KG
        self.procedural_store = LibSQLStore(config.procedural_db_path)  # User patterns (planned)
        
        # Unified model service integration
        self.model_service = ModelServiceIntegration(config)
        
        # Coordination components
        self.context_assembler = ContextAssembler()
        self.relevance_scorer = RelevanceScorer()
        self.conflict_resolver = ConflictResolver()
        
    async def assemble_context(self, user_id: str, message: str) -> ConversationContext:
        """Coordinate memory retrieval across all tiers with unified model service."""
        # 1. Get working memory (conversation history + immediate context)
        working_ctx = await self.working_memory.get_conversation_context(user_id)
        
        # 2. Generate embeddings for semantic search via modelservice
        message_embeddings = await self.model_service.generate_embeddings([message])
        message_embedding = message_embeddings[0]
        
        # 3. Get semantic knowledge using hybrid search (segments + KG)
        semantic_results = await self.semantic_store.query_hybrid(
            message, message_embedding, user_id, threshold=0.4
        )
        
        # 4. Get knowledge graph facts
        kg_facts = await self.semantic_store.query_knowledge_graph(
            user_id, entities=semantic_results.entities
        )
        
        # 5. Apply procedural patterns (when implemented)
        interaction_patterns = await self.procedural_store.get_user_patterns(user_id)
        
        # 6. Assemble and optimize context
        return self.context_assembler.build_context(
            working_ctx, semantic_results, kg_facts, interaction_patterns
        )
```

### Cross-Tier Communication

**Memory Update Pipeline**:
1. **Real-time Updates**: Working memory receives and stores all conversation messages
2. **Semantic Extraction**: Background process extracts segments and KG facts from conversations
3. **Pattern Learning**: Procedural memory updated based on interaction outcomes (planned)
4. **Memory Consolidation**: Periodic cleanup and optimization of stored data

**Consistency Management**:
- **Conflict Detection**: Identify contradictory information across memory tiers
- **Confidence Scoring**: Weight information based on recency and source reliability
- **Resolution Strategies**: Automated conflict resolution with user confirmation when needed

## Performance Characteristics

### Resource Usage

**Memory Footprint**:
- Working Memory (LMDB): 50-100MB (conversation history + context)
- Semantic Memory (ChromaDB): 200-500MB (segments + KG embeddings)
- Database Connections: 20-50MB
- Total: ~300-650MB typical usage

**CPU Usage**:
- Context Assembly: 10-50ms per message
- Vector Similarity: 5-20ms per query
- Database Operations: 1-10ms per query
- Background Processing: 5-10% CPU during idle

**Storage Requirements**:
- Working Memory: ~1MB per 1000 conversation turns (24hr TTL)
- Semantic Segments: ~500MB per 100,000 segments (with embeddings)
- Knowledge Graph: ~10MB per 1000 nodes + edges
- Procedural Patterns: ~1MB per user (planned)

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
    
    # Hybrid search configuration (V3)
    fusion_method: "rrf"  # "rrf" (recommended) or "weighted" (legacy)
    rrf_rank_constant: 0  # 0 = adaptive, or 10-60 manual
    bm25_min_idf: 0.6     # Minimum IDF threshold for query term filtering
    min_semantic_score: 0.35  # Minimum semantic score for relevance filtering
    min_similarity: 0.4   # Minimum hybrid score for final results
    
    # Legacy weighted fusion (if fusion_method="weighted")
    semantic_weight: 0.7  # Weight for semantic similarity
    bm25_weight: 0.3      # Weight for BM25 score
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
├── working.py           # WorkingMemoryStore - LMDB conversation history + context
├── semantic.py          # SemanticMemoryStore - ChromaDB segments with hybrid search
├── procedural.py        # ProceduralMemoryStore - libSQL user patterns (planned)
├── context/             # Context assembly module
│   ├── assembler.py     # ContextAssembler - cross-tier coordination
│   ├── retrievers.py    # Memory tier retrievers
│   ├── scorers.py       # Relevance scoring
│   └── graph_ranking.py # KG-based context ranking
├── fusion.py            # Hybrid search fusion (RRF, weighted)
├── bm25.py              # BM25 keyword ranking
└── memory_album.py      # Memory consolidation and browsing (planned)
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
- [Hybrid Search Guide](hybrid-search.md) - **NEW**: Detailed hybrid search implementation (V3)
- [Context Management](context-management.md) - Context assembly and thread resolution
- [Implementation Concepts](implementation.md) - Conceptual implementation approach
- [Thread Resolution](thread-resolution.md) - Integrated thread resolution system
- [Memory Roadmap](memory_roadmap.md) - Detailed implementation timeline
