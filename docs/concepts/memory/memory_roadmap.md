# Memory System Roadmap

## Implementation Phases

### Phase 1: Session Context Management (Month 1)

**Core Deliverables:**
- ✅ Working memory implementation with LMDB (`shared/aico/ai/memory/working.py`)
- ✅ Basic session state persistence following AICO patterns
- ✅ Simple thread continuation logic integrated with existing ThreadManager
- ✅ Foundation context assembly framework (`shared/aico/ai/memory/context.py`)
- ✅ MemoryManager base implementation extending BaseAIProcessor

#### Deliverables
- ✅ **Session Continuity**: Conversations maintain context within active sessions
- ✅ **Basic Thread Management**: Simple time-based thread creation/continuation
- ✅ **Context Persistence**: Working memory survives application restarts
- ✅ **Foundation Architecture**: Database schema and core classes established

#### Key Components
- ✅ Working Memory Manager for real-time conversation state
- ✅ Basic Thread Manager with time-based heuristics
- ✅ Core database schema for threads and messages
- ✅ Working memory persistence for session recovery

---

### Phase 2: User-Specific Long-Term Memory (Relationship Building)
**Priority**: After Phase 1 completion  
**Timeline**: 2-3 weeks  
**Goal**: Zero-ambiguity storage of critical user facts for relationship building

#### Deliverables
- **Personal Facts Storage**: Names, birthdates, and key personal information per user
- **Multi-User Support**: Isolated storage preventing cross-user contamination
- **Zero-Ambiguity Retrieval**: Guaranteed correct facts for the right user
- **Relationship Context**: Foundation for personalized interactions

#### Key Components
- ✅ Semantic Memory Store implementation (`shared/aico/ai/memory/semantic.py`)
- ✅ User-scoped fact storage with ChromaDB vector embeddings
- ⏳ Confidence-based fact validation and contradiction detection
- ⏳ Encrypted libSQL metadata storage for structured user facts

#### Phase 2 Implementation Notes:
- ✅ Semantic memory uses ChromaDB for vector similarity and libSQL for metadata
- ⏳ Each fact tied to specific `user_id` with confidence scoring
- ⏳ Source episodes reference LMDB conversation_history keys (format: `thread_id:timestamp`)
- ✅ Single multilingual embedding model: `paraphrase-multilingual` (768 dimensions) - **Updated to use Ollama modelservice**
- ✅ Fallback JSON storage when ChromaDB unavailable
- ⏳ Integration with existing conversation context assembly

#### Infrastructure Completed:
- ✅ **ChromaDB Integration**: Proper ChromaDB client setup with modelservice embeddings
- ✅ **Ollama Modelservice**: `paraphrase-multilingual` model auto-download and integration
- ✅ **CLI Management**: Complete `aico chroma` command suite (status, ls, add, query, clear)
- ✅ **No External Downloads**: ChromaDB bypasses default embedding function, uses modelservice exclusively
- ✅ **Hierarchical Paths**: Uses `AICOPaths.get_semantic_memory_path()` for consistent storage
- ✅ **Collection Metadata**: Embedding model and dimensions tracked in ChromaDB collections

#### Critical User Facts Supported:
- **Personal Information**: Names, birthdates, contact details
- **Preferences**: Communication style, topics of interest, response preferences  
- **Relationships**: Family members, friends, professional contacts
- **Important Dates**: Anniversaries, appointments, significant events
- **Context Facts**: Work details, hobbies, personal history

---

### Phase 3: Semantic Thread Resolution (Intelligence)
**Priority**: After Phase 2 completion  
**Timeline**: 3-4 weeks  
**Goal**: Intelligent thread switching based on content similarity

#### Deliverables
- **Semantic Thread Matching**: Content-based thread resolution
- **Vector Storage**: Efficient similarity search for thread matching
- **Topic Coherence**: Maintain conversation topics across sessions
- **Enhanced Context**: Richer context assembly with semantic relevance

#### Key Components
- Semantic Thread Resolver with embedding models
- Vector Storage Integration (ChromaDB) - building on Phase 2 foundation
- Cosine similarity-based thread matching
- Enhanced database schema with embeddings

#### Phase 3 Implementation Notes:
- Builds on Phase 2 ChromaDB infrastructure for thread embeddings
- Uses same multilingual embedding model for consistency
- Thread resolution integrates with existing ThreadManager service
- Source episodes continue to reference LMDB conversation_history keys
- Performance remains viable on consumer hardware with proper model selection

---

### Phase 4: Behavioral Learning (Personalization)
**Priority**: After Phase 3 completion  
**Timeline**: 4-5 weeks  
**Goal**: Learn user-specific conversation patterns and preferences

#### Deliverables
- **Personalized Thresholds**: User-specific decision parameters
- **Pattern Recognition**: Learn individual conversation rhythms
- **Adaptive Behavior**: Continuous improvement based on user interactions
- **Preference Learning**: Understand user communication style preferences

#### Key Components
- User Behavior Analyzer for pattern recognition
- Adaptive Threshold Manager for dynamic adjustment
- User Conversation Profile system
- Feedback learning mechanisms
- Procedural Memory Store implementation (`shared/aico/ai/memory/procedural.py`)

#### Phase 4 Implementation Notes:
- Procedural memory uses libSQL for behavior pattern storage requiring SQL queries
- Source episodes reference LMDB conversation_history keys (same as other tiers)
- Statistical analysis and pattern recognition from conversation data
- Integration with semantic memory for comprehensive user understanding

---

### Phase 5: Advanced Relationship Intelligence (Full System)
**Priority**: After Phase 4 completion  
**Timeline**: 6-8 weeks  
**Goal**: Complete memory system with proactive capabilities

#### Deliverables
- **Complete Memory System**: All four memory tiers fully operational
- **Proactive Capabilities**: Initiative generation and engagement triggers
- **Relationship Intelligence**: Deep understanding of user relationships
- **Advanced Context**: Multi-modal context integration

#### Key Components
- Proactive Engagement Engine for initiative generation
- Advanced relationship modeling and cross-conversation learning
- Multi-modal context integration
- Complete memory system coordination and optimization

#### Phase 5 Implementation Notes:
- Unified memory system with all tiers working together
- LMDB conversation_history remains the permanent episodic memory store
- Advanced context assembly across all memory tiers
- Proactive capabilities based on comprehensive user understanding

## Migration Strategy

### Phase Transitions
1. **Phase 1 → Phase 2**: Add semantic memory store for user facts, maintain LMDB working memory
2. **Phase 2 → Phase 3**: Add vector storage for thread resolution, build on Phase 2 ChromaDB infrastructure
3. **Phase 3 → Phase 4**: Add procedural memory for behavior patterns, maintain existing systems
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
  procedural:
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
- **Advanced**: Phases 1-4, behavioral learning (+ libSQL procedural memory)
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
