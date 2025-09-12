# Memory System Architecture

## Overview

AICO's memory system implements a sophisticated four-tier architecture designed for local-first operation on consumer hardware. The system balances comprehensive relationship intelligence with performance efficiency, avoiding external dependencies while maintaining state-of-the-art conversational AI capabilities.

## Four-Tier Memory Architecture

### 1. Working Memory

**Purpose**: Real-time conversation state and immediate context management

**Implementation**:
- **Storage**: RocksDB for high-performance key-value operations
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

### 3. Semantic Memory

**Purpose**: Knowledge base with vector embeddings for similarity-based retrieval

**Implementation**:
- **Storage**: ChromaDB for vector operations, libSQL for structured data
- **Scope**: Cross-conversation knowledge, user facts, preferences
- **Lifecycle**: Accumulated knowledge with confidence scoring
- **Performance**: Vector similarity search, semantic clustering

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

**Responsibilities**:
- Store and retrieve user preferences and facts
- Enable semantic search across conversation history
- Maintain knowledge consistency and conflict resolution
- Support cross-conversation learning and adaptation

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

## System Integration

### Memory Manager Coordination

```python
class AICOMemoryManager:
    """Unified memory management with coordinated access across all tiers"""
    
    def __init__(self, config: MemoryConfig):
        # Storage backends
        self.working_memory = RocksDBStore(config.working_memory_path)
        self.episodic_store = EncryptedLibSQL(config.episodic_db_path)
        self.semantic_store = ChromaDBStore(config.semantic_db_path)
        self.procedural_store = LibSQLStore(config.procedural_db_path)
        
        # Coordination components
        self.context_assembler = ContextAssembler()
        self.relevance_scorer = RelevanceScorer()
        self.conflict_resolver = ConflictResolver()
        
    async def assemble_context(self, user_id: str, message: str) -> ConversationContext:
        """Coordinate memory retrieval across all tiers"""
        # 1. Get working memory (immediate context)
        working_ctx = await self.working_memory.get_active_context(user_id)
        
        # 2. Retrieve relevant episodic memories
        episodic_memories = await self.episodic_store.query_similar_episodes(
            message, user_id, limit=5
        )
        
        # 3. Get semantic knowledge
        semantic_facts = await self.semantic_store.query_relevant_facts(
            message, user_id, threshold=0.7
        )
        
        # 4. Apply procedural patterns
        interaction_patterns = await self.procedural_store.get_user_patterns(user_id)
        
        # 5. Assemble and optimize context
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

## Local-First Design Principles

### No External Dependencies
- All processing happens locally
- No cloud services or external APIs required
- Embedded databases with no server processes
- Offline-capable with full functionality

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

This architecture provides the foundation for AICO's sophisticated memory capabilities while maintaining the local-first, privacy-first principles essential to the companion's design philosophy.

## Related Documentation

- [Memory System Overview](overview.md) - Core memory capabilities and integration points
- [Context Management](context-management.md) - Context assembly and thread resolution
- [Implementation Concepts](implementation.md) - Conceptual implementation approach
- [Thread Resolution](thread-resolution.md) - Integrated thread resolution system
- [Memory Roadmap](memory_roadmap.md) - Detailed implementation timeline
