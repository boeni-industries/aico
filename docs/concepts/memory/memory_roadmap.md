# Memory System Roadmap

## Implementation Phases

### ✅ Phase 1: Session Context Management (COMPLETE)

**Core Deliverables:**
- ✅ Working memory implementation with LMDB (`shared/aico/ai/memory/working.py`)
- ✅ Conversation-scoped context retrieval by conversation_id
- ✅ Context assembly framework (`shared/aico/ai/memory/context.py`)
- ✅ MemoryManager coordination layer (`shared/aico/ai/memory/manager.py`)

#### Implemented Features
- ✅ **Conversation Isolation**: Each conversation_id has independent context
- ✅ **User-Driven Selection**: Frontend UI handles conversation selection
- ✅ **No Thread Resolution**: Explicit conversation_id pattern eliminates need
- ✅ **TTL-Based Expiration**: Automatic cleanup of old messages (24h default)

#### Key Components
- ✅ Working Memory Store (LMDB) for fast message retrieval
- ✅ Conversation ID pattern: `{user_id}_{timestamp}` (industry standard)
- ✅ Context assembly with deduplication and relevance scoring
- ✅ Cross-conversation message queries for semantic memory

---

### ✅ Phase 2: Semantic Memory & Knowledge Graph (COMPLETE)
**Status**: Production deployment with 204 nodes, 27 edges  
**Goal**: Hybrid search + structured knowledge extraction

#### Implemented Features
- ✅ **Hybrid Search**: Semantic + BM25 with IDF filtering and RRF fusion
- ✅ **Conversation Segments**: ChromaDB storage with embeddings
- ✅ **Knowledge Graph**: Multi-pass extraction, entity resolution, graph fusion
- ✅ **Production Data**: 204 nodes, 27 edges, 552 indexed properties

#### Key Components
- ✅ Semantic Memory Store (`shared/aico/ai/memory/semantic.py`) - Hybrid search
- ✅ Knowledge Graph Module (`shared/aico/ai/knowledge_graph/`) - Complete implementation
  - ✅ Multi-pass extractor with GLiNER + LLM
  - ✅ Entity resolver (semantic blocking → LLM matching → merging)
  - ✅ Graph fusion with conflict resolution
  - ✅ Hybrid storage (ChromaDB + libSQL)
- ✅ Database schema v7 + v8 (kg_nodes, kg_edges, temporal fields, triggers)

#### Phase 2 Implementation Notes:
- ✅ Semantic memory uses ChromaDB-only with enhanced metadata (no libSQL duplication)
- ✅ Each fact tied to specific `user_id` with confidence scoring
- ✅ Source episodes reference LMDB conversation_history keys (format: `thread_id:timestamp`)
- ✅ Single multilingual embedding model: `paraphrase-multilingual` (768 dimensions) - **Updated to use Ollama modelservice**
- ✅ Fallback JSON storage when ChromaDB unavailable
- ✅ Integration with existing conversation context assembly
- ✅ Rich metadata structure supports administrative queries without separate database

#### Infrastructure Completed:
- ✅ **ChromaDB Integration**: Proper ChromaDB client setup with modelservice embeddings
- ✅ **Ollama Modelservice**: `paraphrase-multilingual` model auto-download and integration
- ✅ **CLI Management**: Complete `aico chroma` command suite (status, ls, add, query, clear)
- ✅ **No External Downloads**: ChromaDB bypasses default embedding function, uses modelservice exclusively
- ✅ **Hierarchical Paths**: Uses `AICOPaths.get_semantic_memory_path()` for consistent storage
- ✅ **Collection Metadata**: Embedding model and dimensions tracked in ChromaDB collections
- ✅ **Memory Integration**: ContextAssembler now queries semantic memory alongside working memory
- ✅ **Fact Extraction**: Automatic personal fact extraction from user messages via LLM analysis
- ✅ **Centralized Schemas**: Type-safe schemas in `/shared/aico/data/schemas/semantic.py`
- ✅ **Administrative CLI**: Complete admin commands (`user-facts`, `delete-user`, `cleanup`)
- ✅ **Enhanced Metadata**: Rich metadata structure supports complex administrative queries
- ✅ **GDPR Compliance**: User data deletion and privacy controls implemented

#### Critical User Facts Supported:
- **Personal Information**: Names, birthdates, contact details
- **Preferences**: Communication style, topics of interest, response preferences  
- **Relationships**: Family members, friends, professional contacts
- **Important Dates**: Anniversaries, appointments, significant events
- **Context Facts**: Work details, hobbies, personal history

**Memory Execution Flow:**
```
User Message → MemoryManager → ContextAssembler → LLM Response
     ↓              ↓              ↓              ↓
1. Store in    2. Extract KG   3. Query by    4. Generate
   Working        Entities       conv_id +      Personalized
   Memory         Relations      user_id        Response
     ↓              ↓              ↓
   LMDB      ChromaDB+libSQL  Combined Context
```

**Production Status:** Fully operational with hybrid search and knowledge graph extraction.

---

### ❌ Phase 3: Thread Resolution (OBSOLETE - NOT NEEDED)
**Status**: Removed from roadmap  
**Reason**: conversation_id pattern eliminates need for AI-driven thread resolution

#### Why Not Needed
- **User-Driven Selection**: Frontend UI provides conversation picker
- **Explicit Scoping**: conversation_id = `{user_id}_{timestamp}` pattern
- **Industry Standard**: Follows LangGraph, Azure AI Foundry, OpenAI patterns
- **No Ambiguity**: Users explicitly choose "continue" or "new conversation"
- **Memory Already Scoped**: Working memory filters by conversation_id

#### What Was Planned (Now Removed)
- ~~Semantic thread matching with embeddings~~
- ~~Topic coherence detection~~
- ~~Automatic "should this continue thread X?" decisions~~
- ~~Vector similarity for thread continuation~~

**Conclusion**: The problem thread resolution aimed to solve doesn't exist in AICO's architecture.

---

### ❌ Phase 3: Behavioral Learning (NOT IMPLEMENTED)
**Status**: Future enhancement  
**Goal**: Learn user-specific patterns and preferences

#### Planned Features (Not Implemented)
- ❌ Procedural memory store (libSQL)
- ❌ User behavior pattern recognition
- ❌ Adaptive personalization thresholds
- ❌ Communication style learning
- ❌ Interaction timing optimization

#### Why Not Implemented
- Phase 1-2 provide sufficient functionality
- Knowledge graph already captures user facts
- Behavioral learning requires significant data collection
- Privacy considerations for pattern tracking

---

### ❌ Phase 4: Proactive Engagement (NOT IMPLEMENTED)
**Status**: Future research  
**Goal**: Proactive initiative generation

#### Planned Features (Not Implemented)
- ❌ Proactive engagement triggers
- ❌ Initiative generation based on context
- ❌ Predictive conversation starters
- ❌ Multi-modal context integration
- ❌ Advanced relationship modeling

#### Why Not Implemented
- Requires Phase 3 behavioral learning foundation
- Complex AI reasoning beyond current scope
- Privacy and user control considerations
- Focus on reactive conversation quality first

## Migration Strategy

### Phase Transitions
1. **Phase 1 → Phase 2**: Add semantic memory store for user facts, maintain LMDB working memory
2. **Phase 2 → Phase 3**: Add vector storage for thread resolution, build on Phase 2 ChromaDB infrastructure
3. **Phase 3 → Phase 4**: Add behavioral learning for behavior patterns, maintain existing systems
4. **Phase 4 → Phase 5**: Add advanced features and system coordination

### Simplified Architecture
- **No episodic memory migration**: LMDB conversation_history serves as permanent episodic memory
- **Single source of truth**: All source_episodes reference LMDB conversation_history keys
- **KISS principle**: Three storage systems total (LMDB, ChromaDB, libSQL) - no redundancy
- **Zero migration complexity**: No backward compatibility issues between storage systems

## Configuration Evolution

### Phase 1 Configuration
```yaml
memory:
  working_memory:
    context_window_size: 10
    max_tokens: 4000
    persistence_interval: 30  # seconds
  
  thread_management:
    dormancy_threshold_hours: 2
    max_thread_age_days: 30
```

### Phase 2 Configuration
```yaml
memory:
  semantic:
    db_path: "data/memory/semantic"
    collection_name: "user_facts"
    embedding_model: "paraphrase-multilingual-mpnet-base-v2"
    dimensions: 768
    max_results: 20
    confidence_threshold: 0.8
    fact_retention_days: 365  # Long-term storage
    supported_languages: ["en", "de", "es", "it", "fr"]
    enable_fallback_storage: true
```

### Phase 3 Configuration
```yaml
memory:
  semantic_analysis:
    # Reuse same model as Phase 2 for consistency
    embedding_model: "paraphrase-multilingual-mpnet-base-v2"
    dimensions: 768
    similarity_threshold: 0.7
    max_dormant_threads: 10
    # Uses existing ChromaDB infrastructure from Phase 2
```

### Phase 4 Configuration
```yaml
memory:
  behavioral:
    db_path: "data/memory/procedural.db"
    pattern_retention_days: 180
    min_pattern_frequency: 3
    confidence_threshold: 0.6
  behavioral_learning:
    learning_rate: 0.1
    adaptation_interval: 24  # hours
    min_interactions_for_learning: 10
    feedback_weight: 0.8
```

### Phase 5 Configuration
```yaml
memory:
  advanced_features:
    proactive_engagement: true
    cross_conversation_learning: true
    relationship_modeling: true
    multi_modal_context: true
```

## Hardware Adaptation Strategy

### Performance Modes
- **Minimal**: Phase 1 only, basic context management (LMDB working memory)
- **Essential**: Phases 1-2, user facts storage with semantic memory (+ ChromaDB)
- **Balanced**: Phases 1-3, semantic thread resolution (+ thread embeddings)
- **Advanced**: Phases 1-4, behavioral learning (+ libSQL behavioral learning)
- **Full**: All phases, complete proactive system

### Resource Management
```yaml
hardware:
  performance_mode: "adaptive"  # minimal, balanced, full
  max_memory_mb: 500
  background_processing: true
  battery_aware: true
  
  # Adaptive thresholds based on available resources
  adaptive_thresholds:
    low_memory_fallback: "minimal"
    battery_saver_mode: "balanced"
    high_performance_mode: "full"
```

## Success Metrics

### Phase 1 Metrics
- Session context retention rate: >95%
- Thread resolution accuracy: >85%
- Context assembly time: <100ms
- Memory usage: <50MB

### Phase 2 Metrics
- User fact storage accuracy: >99%
- Cross-user contamination rate: 0%
- Fact retrieval time: <20ms
- User recognition accuracy: >95%

### Phase 3 Metrics
- Semantic thread matching accuracy: >90%
- Vector search performance: <50ms
- Topic coherence score: >0.8
- User satisfaction with thread decisions: >85%

### Phase 4 Metrics
- Personalization effectiveness: >80% user preference alignment
- Adaptive threshold convergence: <2 weeks
- Pattern recognition accuracy: >85%
- User engagement improvement: >20%

### Phase 5 Metrics
- Proactive engagement success rate: >70%
- Cross-conversation knowledge retention: >90%
- Relationship model accuracy: >85%
- Overall system intelligence rating: >4.5/5

## Risk Mitigation

### Technical Risks
- **Performance Degradation**: Implement adaptive resource management
- **Memory Leaks**: Comprehensive testing and monitoring
- **Data Corruption**: Robust backup and recovery mechanisms
- **Model Drift**: Regular retraining and validation

### User Experience Risks
- **Over-Personalization**: Configurable adaptation limits
- **Privacy Concerns**: Local-first processing, transparent data handling
- **Complexity Overwhelm**: Progressive disclosure, simple defaults
- **Feature Regression**: Comprehensive testing across all phases

## Dependencies

### External Dependencies
- **ChromaDB**: Vector storage for semantic analysis
- **Sentence Transformers**: Embedding models for semantic similarity
- **libSQL**: Encrypted conversation persistence
- **LMDB**: High-performance working memory storage

### Internal Dependencies
- **ThreadManager Service**: Core thread resolution logic
- **Message Bus**: Real-time context updates
- **Encryption System**: Data protection and privacy
- **Configuration Management**: Dynamic feature control

## Timeline Summary

| Phase | Duration | Cumulative | Key Milestone |
|-------|----------|------------|---------------|
| Phase 1 | 2-3 weeks | 3 weeks | Session context working (LMDB) |
| Phase 2 | 2-3 weeks | 6 weeks | User facts storage (ChromaDB) |
| Phase 3 | 3-4 weeks | 10 weeks | Semantic thread resolution |
| Phase 4 | 4-5 weeks | 15 weeks | Behavioral patterns (libSQL) |
| Phase 5 | 6-8 weeks | 23 weeks | Full proactive intelligence |

**Total Timeline**: ~6 months for complete memory system implementation

**Simplified Architecture**: 3 storage systems total (LMDB + ChromaDB + libSQL) with zero migration complexity

This roadmap ensures systematic development of AICO's memory capabilities while maintaining user value at each phase.
