# Adaptive Memory System (AMS): Brain-Inspired Learning Architecture

## Summary

**What It Does**: The Adaptive Memory System (AMS) is AICO's brain-inspired memory **orchestration layer** that coordinates and enhances existing memory components (working, semantic, knowledge graph) with new capabilities (consolidation, behavioral learning, unified indexing). It implements complementary learning systems to enable genuine relationship evolution through dynamic memory consolidation, temporal preference tracking, and cross-tier memory integration.

**Important**: AMS is **not a replacement**—it's an architectural pattern that:
- **Keeps 80%** of existing memory code (working.py, semantic.py, knowledge_graph/)
- **Adds 20%** new components (consolidation, behavioral learning, unified indexing)
- **Enhances** existing components with temporal metadata and evolution tracking
- **Coordinates** all memory tiers through brain-inspired principles

**Value Proposition**: 
- **Genuine Evolution**: Not just learning preferences, but understanding how relationships and behaviors change over time
- **Brain-Inspired Architecture**: Dual-system design (fast hippocampal + slow cortical learning) prevents catastrophic forgetting
- **Dynamic Consolidation**: Background "sleep phases" integrate new experiences without disrupting existing knowledge
- **Temporal Intelligence**: Tracks preference evolution, recognizes changing patterns, maintains historical context
- **Unified Memory**: Seamless integration across raw data, structured knowledge, and behavioral patterns
- **Multi-User Intelligence**: Distinct, evolving profiles for each family member with temporal awareness
- **Zero Configuration**: Learns automatically from natural interactions and feedback

**How It Works**: AMS implements a complementary learning systems architecture inspired by the mammalian hippocampus-cortex system. Fast learning captures immediate experiences in working memory, while background consolidation gradually integrates knowledge into semantic memory and behavioral patterns. Temporal knowledge graphs track how preferences evolve, and unified memory representation enables seamless retrieval across all memory types.

**Research Foundation**:
- Rudroff et al. (2024): "Neuroplasticity Meets Artificial Intelligence: A Hippocampus-Inspired Approach to the Stability–Plasticity Dilemma"
- Wei & Shang (2024): "Long Term Memory: The Foundation of AI Self-Evolution"
- Contextual Memory Intelligence (2025): "A Foundational Paradigm for Human-AI Collaboration"
- Rethinking Memory in AI (2025): "Taxonomy, Operations, Topics, and Future Directions"

**System Integration**:
- **Module Location**: `/shared/aico/ai/memory/` - Core Intelligence & Memory domain
- **Orchestration Role**: Coordinates existing + new memory components
- **Fast Learning System**: ✅ Existing `working.py` (enhanced with temporal metadata)
- **Slow Learning System**: ✅ Existing `semantic.py` + `knowledge_graph/` (enhanced with temporal tracking)
- **Consolidation Engine**: ❌ NEW `consolidation/` module (background replay and transfer)
- **Behavioral Learning**: ❌ NEW `behavioral/` module (skill library with RLHF)
- **Unified Indexing**: ❌ NEW `unified/` module (cross-layer retrieval)
- **Message-Driven Communication**: All module interactions via ZeroMQ message bus with Protocol Buffers

**Storage Footprint**: ~38-88KB per user (76-176% increase from 50KB baseline)
- Temporal metadata: ~10KB
- Knowledge graphs: ~15KB
- Preference vectors (100 context buckets × 16 dimensions × 4 bytes): ~6.4KB
- User-skill confidence (100 skills): ~10KB
- Trajectories (90 days, ~1000 turns): ~30-50KB

**Performance**: 
- Context assembly: <50ms (multi-tier retrieval)
- Consolidation: Daily task, 5-10 min per user, processes 1/7 of users each day (7-day cycle)
- Memory overhead: +175-350MB system-wide

---

## Architecture Overview: Complementary Learning Systems

AMS implements a dual-system architecture inspired by the mammalian hippocampus-cortex system, solving the stability-plasticity dilemma through complementary learning mechanisms.

### The Stability-Plasticity Dilemma

AI systems face a fundamental challenge: how to learn new information quickly without forgetting existing knowledge (catastrophic forgetting). Traditional approaches either:
- Learn slowly to preserve stability (poor user experience)
- Learn quickly but forget previous knowledge (unreliable)

Biological brains solve this through **complementary learning systems**: the hippocampus rapidly encodes new experiences, while the neocortex slowly integrates them into stable knowledge through memory consolidation during sleep.

### AMS Dual-System Design

```
┌─────────────────────────────────────────────────────────────┐
│                  Adaptive Memory System                      │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌──────────────────────────────────────────────────────┐  │
│  │    Fast Learning System (Hippocampal Component)       │  │
│  │  - Working Memory (LMDB, 24hr TTL)                    │  │
│  │  - Rapid experience encoding                          │  │
│  │  - Temporal metadata tracking                         │  │
│  │  - Pattern separation for distinct experiences        │  │
│  └──────────────────────────────────────────────────────┘  │
│                          ↓ Consolidation                     │
│  ┌──────────────────────────────────────────────────────┐  │
│  │   Memory Consolidation Engine (Transfer Layer)        │  │
│  │  - Replay scheduler (idle detection)                  │  │
│  │  - Experience replay generator                        │  │
│  │  - Memory reconsolidation                             │  │
│  │  - Temporal knowledge graph updates                   │  │
│  │  - Consolidation state tracking                       │  │
│  └──────────────────────────────────────────────────────┘  │
│                          ↓ Integration                       │
│  ┌──────────────────────────────────────────────────────┐  │
│  │     Slow Learning System (Cortical Component)         │  │
│  │  - Semantic Memory (ChromaDB + libSQL)                │  │
│  │  - Temporal Knowledge Graph (property graph)          │  │
│  │  - Behavioral Learning Store (skill library)          │  │
│  │  - Preference evolution tracking                      │  │
│  │  - Pattern completion for generalization              │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                               │
│  ┌──────────────────────────────────────────────────────┐  │
│  │         Unified Memory Representation Layer            │  │
│  │  L0: Raw data (conversations, events, interactions)   │  │
│  │  L1: Structured memory (summaries, profiles, facts)   │  │
│  │  L2: Parameterized memory (behavioral models, skills) │  │
│  │  Cross-layer indexing & unified retrieval             │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                               │
│  ┌──────────────────────────────────────────────────────┐  │
│  │         Context Assembly & Fusion Engine               │  │
│  │  - Multi-tier retrieval coordination                  │  │
│  │  - Temporal-aware ranking                             │  │
│  │  - Hybrid search (BM25 + semantic + graph)            │  │
│  │  - Relevance scoring with recency weighting           │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

### Key Mechanisms

**1. Fast Learning (Hippocampal)**
- Rapid encoding of new experiences in working memory
- Temporary storage with 24-hour TTL
- Pattern separation: Distinct encoding of similar experiences
- Immediate availability for context assembly

**2. Memory Consolidation (Transfer)**
- Background "sleep phases" during system idle periods
- Experience replay: Reprocessing recent interactions
- Memory reconsolidation: Updating existing knowledge with new information
- Temporal graph evolution: Tracking preference changes over time

**3. Slow Learning (Cortical)**
- Gradual integration into stable semantic memory
- Knowledge graph updates with temporal metadata
- Behavioral pattern extraction and skill refinement
- Long-term storage with efficient retrieval

**4. Unified Memory Representation**
- L0 (Raw Data): Unprocessed conversations and events
- L1 (Structured): Summaries, profiles, extracted facts
- L2 (Parameterized): Behavioral models and learned skills
- Cross-layer indexing for seamless retrieval

---

## Implementation Structure

### Directory Organization

Following AICO's modular design principles (see `/docs/guides/developer/guidelines.md`), AMS is implemented as focused, single-responsibility modules:

```
/shared/aico/ai/memory/
├── __init__.py                      # ✅ Existing: Module exports
├── manager.py                       # ✅ Existing: Main orchestrator (enhanced)
├── working.py                       # ✅ Existing: Fast learning (enhanced)
├── semantic.py                      # ✅ Existing: Slow learning (enhanced)
├── context/                         # ✅ Existing: Context assembly
│   ├── __init__.py
│   ├── assembler.py                 # Enhanced with temporal ranking
│   ├── retrievers.py                # Enhanced with temporal queries
│   ├── scorers.py                   # Enhanced with recency weighting
│   ├── models.py                    # Enhanced with temporal metadata
│   └── graph_ranking.py             # Existing graph-based ranking
├── consolidation/                   # ❌ NEW: Memory consolidation engine
│   ├── __init__.py
│   ├── scheduler.py                 # Idle detection & replay scheduling
│   ├── replay.py                    # Experience replay generator
│   ├── reconsolidation.py           # Memory update mechanisms
│   └── state.py                     # Consolidation state tracking
├── behavioral/                      # ❌ NEW: Behavioral learning store
│   ├── __init__.py
│   ├── skills.py                    # Skill library management
│   ├── rlhf.py                      # RLHF integration
│   ├── preferences.py               # User preference tracking
│   └── templates.py                 # Prompt template management
├── unified/                         # ❌ NEW: Unified memory indexing
│   ├── __init__.py
│   ├── index.py                     # Cross-layer indexing
│   ├── lifecycle.py                 # Memory lifecycle management
│   └── retrieval.py                 # Unified retrieval interface
└── temporal/                        # ❌ NEW: Temporal metadata utilities
    ├── __init__.py
    ├── metadata.py                  # Temporal metadata structures
    ├── evolution.py                 # Preference evolution tracking
    └── queries.py                   # Temporal query support
```

### Module Responsibilities

#### Existing Modules (Enhanced)

**`manager.py`** - Memory Manager (Orchestrator)
- **Current**: Coordinates working, semantic, knowledge graph
- **Enhancement**: Add consolidation scheduling, unified indexing coordination
- **Size**: ~800 lines → ~1000 lines
- **Changes**: Add consolidation triggers, unified retrieval methods

**`working.py`** - Working Memory Store (Fast Learning)
- **Current**: LMDB-based conversation history with 24hr TTL
- **Enhancement**: Add temporal metadata to all stored messages
- **Size**: ~290 lines → ~350 lines
- **Changes**: Extend storage schema with temporal fields

**`semantic.py`** - Semantic Memory Store (Slow Learning)
- **Current**: ChromaDB with hybrid search (BM25 + vector)
- **Enhancement**: Add temporal awareness to fact storage and retrieval
- **Size**: ~450 lines → ~550 lines
- **Changes**: Temporal metadata in ChromaDB, evolution tracking

**`context/assembler.py`** - Context Assembly
- **Current**: Multi-tier retrieval with relevance scoring
- **Enhancement**: Add temporal-aware ranking and recency weighting
- **Size**: ~350 lines → ~450 lines
- **Changes**: Temporal scoring algorithms, evolution-aware retrieval

#### New Modules (To Implement)

**`consolidation/scheduler.py`** - Replay Scheduler
- **Purpose**: Detect idle periods, schedule consolidation jobs
- **Size**: ~200 lines
- **Key Functions**:
  - `detect_idle_period()`: Monitor system activity
  - `schedule_consolidation()`: Trigger replay jobs
  - `estimate_consolidation_time()`: Resource planning

**`consolidation/replay.py`** - Experience Replay
- **Purpose**: Generate replay sequences from working memory
- **Size**: ~250 lines
- **Key Functions**:
  - `generate_replay_sequence()`: Select experiences to replay
  - `prioritize_experiences()`: Importance-based selection
  - `replay_to_semantic()`: Transfer to semantic memory

**`consolidation/reconsolidation.py`** - Memory Reconsolidation
- **Purpose**: Update existing memories with new information
- **Size**: ~200 lines
- **Key Functions**:
  - `identify_conflicts()`: Find contradictory memories
  - `merge_memories()`: Integrate new information
  - `update_confidence()`: Adjust memory strength

**`consolidation/state.py`** - Consolidation State
- **Purpose**: Track consolidation progress and state
- **Size**: ~150 lines
- **Key Functions**:
  - `get_consolidation_status()`: Current state
  - `mark_consolidated()`: Update completion status
  - `get_pending_items()`: Items awaiting consolidation

**`behavioral/skills.py`** - Skill Library
- **Purpose**: Manage skill definitions and selection
- **Size**: ~300 lines
- **Key Functions**:
  - `register_skill()`: Add new skill
  - `select_skill()`: Context-based selection
  - `update_confidence()`: Adjust skill scores

**`behavioral/rlhf.py`** - RLHF Integration
- **Purpose**: Process user feedback for skill learning
- **Size**: ~250 lines
- **Key Functions**:
  - `process_feedback()`: Handle thumbs up/down
  - `update_skill_weights()`: Adjust based on feedback
  - `calculate_reward()`: Compute reward signal

**`behavioral/feedback_classifier.py`** - Multilingual Feedback Classification
- **Purpose**: Classify free text feedback across 50+ languages using embeddings
- **Size**: ~200 lines
- **Key Functions**:
  - `initialize()`: Generate category embeddings at startup
  - `classify()`: Classify feedback text using cosine similarity
  - `extract_preference_signals()`: Map categories to preference adjustments
  - `get_category_definitions()`: Return feedback category examples

**`behavioral/preferences.py`** - Preference Tracking
- **Purpose**: Track user preference evolution over time
- **Size**: ~200 lines
- **Key Functions**:
  - `store_preference()`: Record preference with timestamp
  - `get_preference_history()`: Retrieve evolution
  - `detect_preference_shift()`: Identify changes

**`behavioral/templates.py`** - Prompt Templates
- **Purpose**: Manage and apply prompt templates
- **Size**: ~200 lines
- **Key Functions**:
  - `load_template()`: Retrieve template
  - `apply_template()`: Inject into context
  - `update_template()`: Refine based on feedback

**`unified/index.py`** - Cross-Layer Indexing
- **Purpose**: Unified indexing across L0/L1/L2
- **Size**: ~250 lines
- **Key Functions**:
  - `build_unified_index()`: Create cross-layer index
  - `query_unified()`: Search across all layers
  - `update_index()`: Maintain index consistency

**`unified/lifecycle.py`** - Memory Lifecycle
- **Purpose**: Manage memory transitions between tiers
- **Size**: ~200 lines
- **Key Functions**:
  - `promote_to_semantic()`: Working → Semantic
  - `archive_memory()`: Long-term storage
  - `cleanup_expired()`: TTL enforcement

**`unified/retrieval.py`** - Unified Retrieval
- **Purpose**: Single interface for all memory queries
- **Size**: ~250 lines
- **Key Functions**:
  - `retrieve_unified()`: Query all tiers
  - `rank_results()`: Cross-tier relevance
  - `merge_results()`: Combine from multiple sources

**`temporal/metadata.py`** - Temporal Metadata
- **Purpose**: Data structures for temporal tracking
- **Size**: ~150 lines
- **Key Classes**:
  - `TemporalMetadata`: Base temporal data
  - `EvolutionRecord`: Preference change tracking
  - `HistoricalState`: Point-in-time snapshots

**`temporal/evolution.py`** - Evolution Tracking
- **Purpose**: Track how preferences/behaviors evolve
- **Size**: ~200 lines
- **Key Functions**:
  - `track_evolution()`: Record changes over time
  - `analyze_trends()`: Identify patterns
  - `predict_future()`: Anticipate changes

**`temporal/queries.py`** - Temporal Queries
- **Purpose**: Time-aware memory queries
- **Size**: ~200 lines
- **Key Functions**:
  - `query_at_time()`: Point-in-time queries
  - `query_range()`: Time-range queries
  - `query_evolution()`: Change-over-time queries

### Design Principles Applied

**Modularity** (AICO Guideline: "Modular, Message-Driven Design")
- Each module has single, clear responsibility
- No module exceeds ~350 lines (existing) or ~300 lines (new)
- Clear interfaces between modules
- Message bus for inter-module communication

**Simplicity** (AICO Guideline: "Simplicity First, KISS")
- Focused, understandable modules
- Clear naming conventions
- Avoid overengineering
- Solve problems with simplest viable approach

**Extensibility** (AICO Guideline: "Modularity & Extensibility")
- Well-defined interfaces
- Composition over inheritance
- Easy to add new consolidation strategies
- Easy to add new behavioral learning methods

**Resource Awareness** (AICO Guideline: "Resource Awareness")
- Background consolidation during idle periods
- Efficient temporal metadata storage
- Incremental index updates
- Memory-conscious data structures

### Implementation Phases

**Phase 1: Temporal Foundation** (Week 1-2)
- Implement `temporal/` module
- Enhance existing modules with temporal metadata
- Add temporal queries to context assembly

**Phase 2: Consolidation Engine** (Week 3-4)
- Implement `consolidation/` module
- Add replay scheduler and experience replay
- Integrate with working → semantic transfer

**Phase 3: Behavioral Learning** (Week 5-6)
- Implement `behavioral/` module
- Add skill library and RLHF integration
- Implement preference tracking

**Phase 4: Unified Indexing** (Week 7-8)
- Implement `unified/` module
- Add cross-layer indexing
- Implement unified retrieval interface

---

## AI Components & Computational Impact

### AI Libraries & Models Used

**1. Embedding Generation** (via ModelService)
- **Library**: `sentence-transformers` (Hugging Face)
- **Model**: `paraphrase-multilingual-mpnet-base-v2` (768 dimensions)
- **Purpose**: Generate embeddings for semantic search and feedback classification
- **Memory**: ~500MB model size
- **Compute**: ~50-100ms per embedding (CPU), ~10-20ms (GPU)
- **Usage**: Every semantic query, fact storage, context retrieval, feedback classification

**2. Vector Database**
- **Library**: `chromadb` (persistent client)
- **Storage**: Local file-based (ChromaDB format)
- **Purpose**: Store and query conversation segment embeddings
- **Memory**: ~100-200MB in-memory index
- **Compute**: ~5-20ms per vector search query
- **Usage**: Semantic memory queries, hybrid search

**3. Keyword Search**
- **Library**: Custom BM25 implementation (pure Python)
- **Purpose**: Keyword-based relevance ranking
- **Memory**: Minimal (~1-5MB for IDF statistics)
- **Compute**: ~2-5ms per query
- **Usage**: Hybrid search fusion with semantic results

**4. Knowledge Graph**
- **Library**: `libSQL` (embedded SQLite)
- **Storage**: Local file-based (SQLite format)
- **Purpose**: Store entities, relations, temporal metadata
- **Memory**: ~50-100MB for typical graphs
- **Compute**: ~1-10ms per graph query
- **Usage**: Entity resolution, relationship traversal

**5. NLP Models** (via ModelService)
- **Sentiment Analysis**: `nlptown/bert-base-multilingual-uncased-sentiment`
  - Memory: ~500MB
  - Compute: ~100-200ms per analysis
- **Entity Extraction**: GLiNER (planned)
  - Memory: ~300-500MB
  - Compute: ~50-150ms per extraction
- **Intent Classification**: Custom transformer
  - Memory: ~400MB
  - Compute: ~80-150ms per classification

**6. Behavioral Learning** (Custom Lightweight - Prompt Selection Only)
- **Library**: Custom Python implementation in `behavioral/thompson_sampling.py` (no external RL framework)
- **Algorithm**: Thompson Sampling (contextual bandit) for skill selection
- **Memory**: Minimal (~10-20MB)
- **Compute**: 5-10ms per feedback, <1s per user batch update/day
- **What We Learn**: 
  - **Prompt template SELECTION** via Thompson Sampling Beta distributions
  - **NOT LLM retraining**: No model weights modified, no fine-tuning, no DPO/TRL
  - **Statistical learning only**: Track success/failure rates per (context, skill) pair
  - **Privacy-preserving**: Local-only processing, aggregated counts only
- **Clarification**: We select between pre-written prompt templates based on which works best in each context. The LLM itself is never retrained or modified.

### Computational Impact Analysis

#### Real-Time Operations (User-Facing)

**Context Assembly** (every conversation turn)
- **Components**: Working memory + Semantic memory + Knowledge graph
- **Compute Time**: 30-50ms total
  - Working memory retrieval: 5-10ms (LMDB)
  - Semantic query (with embedding): 60-80ms (embedding + vector search)
  - Knowledge graph query: 5-10ms (libSQL)
  - Fusion & ranking: 5-10ms (RRF algorithm)
- **Memory Impact**: +50-100MB during query
- **Frequency**: Every user message
- **Optimization**: Results cached for conversation context

**Behavioral Skill Selection** (when implemented)
- **Components**: Skill library + User preferences
- **Compute Time**: 5-15ms (preference vectors pre-computed, no embedding generation)
  - Skill matching: 2-5ms (pattern matching)
  - Preference lookup: 1-3ms (libSQL, returns cached vector)
  - Preference alignment: 2-5ms (Euclidean distance with skill dimension vectors)
  - Template application: 1-2ms (string operations)
- **Memory Impact**: Minimal (~5-10MB)
- **Frequency**: Every AI response generation

#### Background Operations (Non-Blocking)

**Memory Consolidation** (scheduled via AICO Scheduler)
- **Trigger**: Daily at 2 AM ("0 2 * * *") with idle detection
- **User Sharding**: Round-robin 7-day cycle - processes 1/7 of users each day
  - Each user consolidated once per week
  - Example: 70 users = ~10 users/day × 10 min = ~100 min/night
  - Day 0 (Mon): Users 0,7,14,21... | Day 1 (Tue): Users 1,8,15,22... etc.
- **Components**: Experience replay + Semantic storage + Graph updates
- **Compute Time**: 5-10 minutes per user
  - Experience selection: 30-60s (working memory scan)
  - Embedding generation: 2-5 min (batch processing)
  - Semantic storage: 1-2 min (ChromaDB batch insert)
  - Graph updates: 1-2 min (entity resolution + storage)
- **Memory Impact**: +200-400MB peak during consolidation
- **Parallelization**: Max 4 concurrent users (Semaphore(4))

**Temporal Graph Evolution** (scheduled)
- **Trigger**: Weekly (e.g., "0 3 * * 0" = Sunday 3 AM)
- **Components**: Preference analysis + Evolution tracking
- **Compute Time**: 2-5 minutes per user
  - Preference history scan: 30-60s
  - Trend analysis: 1-2 min
  - Graph metadata updates: 30-60s
- **Memory Impact**: +100-200MB
- **Frequency**: Weekly (configurable)

**Behavioral Learning Updates** (event-driven + scheduled)
- **Trigger**: User feedback (immediate) + Batch learning (daily at 4 AM)
- **Components**: Confidence updates + Contextual bandit learning
- **Compute Time**: 
  - Per feedback: 5-10ms (immediate confidence update)
  - Batch learning: 2-5 min/day (Thompson Sampling parameter updates)
- **Memory Impact**: Minimal for feedback, +100-200MB for batch
- **Frequency**: Immediate + daily batch

### Scheduler Integration

**AICO Backend Scheduler** (`/backend/scheduler/`)
- **Type**: Cron-like task scheduler with async execution
- **Features**: 
  - Standard cron expressions (5-field format)
  - Idle detection via `TaskContext.system_idle()`
  - Task priority and resource limits
  - Execution history and monitoring

**AMS Scheduled Tasks**:

```python
# 1. Daily Memory Consolidation (2 AM, idle-aware, 7-day user sharding)
{
    "task_id": "ams.consolidation.daily",
    "schedule": "0 2 * * *",  # 2 AM daily
    "enabled": True,
    "config": {
        "require_idle": True,
        "max_duration_minutes": 120,  # 2 hours max
        "user_sharding_cycle_days": 7,  # Process 1/7 of users each day
        "max_concurrent_users": 4  # Semaphore limit
    }
}

# 2. Weekly Temporal Evolution Analysis (Sunday 3 AM)
{
    "task_id": "ams.temporal.evolution",
    "schedule": "0 3 * * 0",  # Sunday 3 AM
    "enabled": True,
    "config": {
        "lookback_days": 30,
        "min_interactions": 10
    }
}

# 3. Daily Behavioral Learning Batch (3 AM)
{
    "task_id": "ams.behavioral.batch_refinement",
    "schedule": "0 3 * * *",  # 3 AM daily
    "enabled": True,
    "config": {
        "min_feedback_count": 5,
        "dpo_iterations": 3
    }
}

# 4. Hourly Unified Index Maintenance (top of hour, idle-aware)
{
    "task_id": "ams.unified.index_maintenance",
    "schedule": "0 * * * *",  # Every hour
    "enabled": True,
    "config": {
        "require_idle": True,
        "incremental": True
    }
}
```

**Task Implementation Pattern**:

```python
# /backend/scheduler/tasks/ams_consolidation.py
from backend.scheduler.tasks.base import BaseTask, TaskContext, TaskResult

class MemoryConsolidationTask(BaseTask):
    task_id = "ams.consolidation.daily"
    description = "Daily memory consolidation from working to semantic memory"
    
    async def execute(self, context: TaskContext) -> TaskResult:
        # Check if system is idle (if required)
        if context.get_config("require_idle", True):
            if not context.system_idle():
                return TaskResult(
                    success=True,
                    message="Skipped: system not idle",
                    skipped=True
                )
        
        # Get memory manager
        memory_manager = await self._get_memory_manager(context)
        
        # Run consolidation
        result = await memory_manager.consolidate_memories(
            max_duration_minutes=context.get_config("max_duration_minutes", 30)
        )
        
        return TaskResult(
            success=True,
            message=f"Consolidated {result['users_processed']} users",
            data=result
        )
```

### Resource Management

**Peak Resource Usage** (all operations combined)
- **Memory**: +400-600MB (during consolidation)
- **CPU**: 1-2 cores (background tasks)
- **Disk I/O**: Moderate (ChromaDB writes, libSQL updates)
- **Network**: None (all local)

**Optimization Strategies**:
1. **Batch Processing**: Process users in small batches (5-10 at a time)
2. **Idle Detection**: Run heavy operations only when system idle
3. **Incremental Updates**: Update indices incrementally, not full rebuilds
4. **Model Caching**: Keep embedding models loaded in ModelService
5. **Query Caching**: Cache frequent context assembly results
6. **Async Execution**: All background operations use async/await

**Scaling Considerations** (with 7-day user sharding):
- **10 users**: ~1GB total memory, ~15 min consolidation/day (1-2 users)
- **50 users**: ~3GB total memory, ~70 min consolidation/day (~7 users)
- **100 users**: ~5GB total memory, ~140 min consolidation/day (~14 users)
- **500 users**: ~20GB total memory, ~700 min consolidation/day (~70 users)

**Optimization Strategies**:
- **User sharding**: Round-robin 7-day cycle (default, already included above)
- **GPU acceleration**: 10x speedup for embedding generation (optional)
- **Priority scheduling**: Active users consolidated more frequently
- **Adaptive batching**: Adjust batch size based on system load

---

## Core Function: Behavioral Learning & Skill-Based Interaction

The Behavioral Learning component of AMS maintains a **Skill Store**, a library of discrete, context-aware procedures that AICO learns and applies. This is more modular and interpretable than monolithic learned patterns.

### What is a Skill?

A skill is a specialized, context-dependent procedure. Examples:
- `summarize_technical_document`: Provides concise, bulleted summaries.
- `casual_chat_evening`: Uses informal language and shows more proactivity.
- `code_review_feedback`: Delivers constructive feedback on code snippets politely.
- `empathy_expression_direct`: Uses explicit empathetic statements.
- `empathy_expression_subtle`: Suggests supportive actions rather than stating feelings.

### Skill Attributes

Each skill has:
- **Trigger Context**: Conditions that determine when the skill applies (user, topic, time of day, conversation state).
- **Procedure Template**: The action to take (e.g., a prompt template, response formatting rules).
- **Confidence Score**: A measure of how well the skill has performed (updated via feedback).
- **Usage Metadata**: Tracking when and how often the skill is applied.

---

## Learning System Architecture

### 1. Reinforcement Learning from Human Feedback (RLHF)

Explicit user feedback is the primary driver for skill acquisition and refinement. This provides a much stronger learning signal than relying on implicit pattern detection alone.

#### Conceptual Model

- **Feedback Mechanism**: After AICO applies a skill, the user is presented with a simple, non-intrusive feedback UI with three levels:
  1. **Primary**: Thumbs up/down (required, zero friction)
  2. **Secondary**: Optional dropdown with common reasons ("Too verbose", "Wrong tone", "Not helpful", "Incorrect info")
  3. **Tertiary**: Optional free text field (max 300 chars) for additional context
  
- **Reward Signal**: This feedback acts as a reward signal. Positive feedback reinforces the skill by increasing its confidence score, while negative feedback weakens it and encourages the system to try an alternative.

- **Multi-User Personalization**: For a multi-user environment like a family, the system learns a unique preference profile (a latent vector) for each user. This allows AICO to resolve conflicting preferences, learning that "Dad prefers concise answers" while "Sarah prefers detailed explanations."

- **What We Learn**: We learn **prompt templates** (text instructions), NOT neural network weights. This means:
  - Fast: Instant application, no training time
  - Interpretable: Can read/edit/debug learned patterns
  - Reversible: Easy to undo bad learning
  - Storage-efficient: ~10-50KB per user vs. 4-8GB for model checkpoints
  - Local-first friendly: Small text files, easy to sync/backup

#### Implementation Details

**Frontend UI Requirements**:
- Add thumbs up/down buttons to each AI message in the conversation view
- Buttons should be subtle and non-intrusive (icon-only, positioned near message)
- On click, show feedback dialog with:
  - Optional dropdown: "Too verbose", "Too brief", "Wrong tone", "Not helpful", "Incorrect info"
  - Optional free text field (max 300 chars)
  - Submit button sends to `POST /api/v1/memory/feedback`
- Use existing Flutter HTTP client (http/dio) for API calls

**How Verbal/Text Feedback is Used**: When users provide free-text feedback (in any of 50+ languages), the system uses embedding-based classification to extract preference signals without translation. The text is converted to a 768-dimensional embedding using AICO's existing multilingual model, then compared via cosine similarity to pre-defined category centroids (too_verbose, too_brief, wrong_tone, etc.) to identify the user's concern. This classification happens during nightly batch processing (not real-time) and updates the user's preference vector—a learned representation of their interaction style preferences (verbosity, formality, tone). These preference vectors then influence future skill selection through Thompson Sampling, allowing the system to adapt to each user's unique communication style across languages without requiring explicit translation or language-specific rules.

**Backend API Endpoint**: `POST /api/v1/memory/feedback`

**Request Schema** (`backend/api/memory/schemas.py`):
- Fields: message_id, skill_id, reward (1/-1/0), optional reason, optional free_text (max 300 chars)
- Response: success status, skill_updated flag, new_confidence score

**Router Implementation** (`backend/api/memory/router.py`):
- Follows AICO's message-driven architecture
- Publishes feedback event to message bus for async processing
- Updates skill confidence score using exponential moving average
- Tracks feedback counters (positive/negative/total usage)
- Returns immediate response with updated confidence
- Logs feedback events with performance metrics

**Multilingual Feedback Processing** (`shared/aico/ai/memory/behavioral/feedback_classifier.py`):

AICO is a multilingual system, so feedback text can be in any language. Traditional keyword matching ("verbose" in text) only works for English and fails for German ("zu ausführlich"), French ("trop verbeux"), Arabic ("مطول جدا"), etc.

**Solution: Embedding-Based Classification**

We leverage AICO's existing multilingual embedding model (`paraphrase-multilingual-mpnet-base-v2`) which maps semantically similar phrases to nearby points in a shared 768-dimensional space across 50+ languages.

**How It Works**:

1. **Define Reference Patterns** (once, in English):
   - Define feedback categories with example phrases
   - Categories: `too_verbose`, `too_brief`, `wrong_tone`, `not_helpful`, `incorrect_info`
   - Each category has 5-10 example phrases in English

2. **Generate Category Embeddings** (once, at startup):
   - Generate embeddings for all reference phrases using ModelService
   - Average embeddings per category to create category centroids
   - Store centroids in memory (~30KB total)

3. **Classify User Feedback** (any language):
   - Generate embedding for user's free text feedback
   - Calculate cosine similarity to each category centroid
   - Return categories above threshold (0.6) with confidence scores
   - Works identically for English, German, French, Spanish, Arabic, etc.

**Example**:
- English: "Too verbose, make it shorter" → `{too_verbose: 0.85}`
- German: "Zu ausführlich, mach es kürzer" → `{too_verbose: 0.82}`
- French: "Trop verbeux, soyez plus concis" → `{too_verbose: 0.84}`
- Arabic: "مطول جدا، اجعله أقصر" → `{too_verbose: 0.79}`

**Performance**:
- Startup: Generate ~30 category embeddings in 2-3 seconds
- Per feedback: 50-100ms (embedding generation) + <1ms (similarity calculation)
- Expected accuracy: 80-90% cross-lingual classification (based on similar multilingual sentiment analysis systems)
- Languages: 50+ supported by the multilingual model
- **Note**: Actual accuracy will be measured during Phase 3 implementation with real user feedback

**Processing Pipeline**:

1. **Real-Time** (when feedback submitted):
   - Store feedback text in database
   - Update skill confidence based on thumbs up/down only
   - Return immediately (no text analysis yet)

2. **Batch Processing** (daily scheduled task at 3 AM):
   - Retrieve all feedback from past 24 hours
   - Classify free text using embedding similarity
   - Extract preference signals (verbosity, formality, tone)
   - Update user preference vectors
   - Aggregate patterns for skill template refinement

**Why This Works**:
- **Cross-lingual embeddings**: Multilingual models learn language-agnostic semantic representations
- **Zero-shot transfer**: Train on English examples, works on 50+ languages automatically
- **No translation needed**: Direct classification in user's native language
- **Proven approach**: Used in production by Google, Meta, Microsoft for multilingual sentiment analysis

**Implementation** (`shared/aico/ai/memory/behavioral/feedback_classifier.py`):
- `FeedbackClassifier` class with `initialize()` and `classify()` methods
- Uses existing ModelService for embedding generation
- Numpy/scipy for cosine similarity calculations
- Configurable similarity threshold and category definitions
- Integrates with daily batch refinement task

### 2. Meta-Learning for Rapid Adaptation

To quickly adapt to new users or changing preferences, AICO uses a meta-learning approach. It learns *how to learn* interaction styles, rather than starting from scratch with each user.

#### Conceptual Model

- **How it Works**: The model's parameters are split into two parts:
    1. **Shared Parameters**: Capture general principles of good interaction, trained across all users.
    2. **Context Parameters**: A small, user-specific set of parameters that are quickly updated based on a few interactions.
- **Benefit**: This allows for extremely fast personalization and reduces the amount of data needed to learn a new user's preferences.

#### Implementation Details

**User Preference Vectors** (`shared/aico/ai/memory/user_preferences.py`):
- **Context-Aware Preferences**: Each user has preference vectors per context bucket (not global)
- **Storage**: (user_id, context_bucket) → 16 explicit preference dimensions
- **Dimensions**: Explicit style attributes (not semantic embeddings):
  - `verbosity`: 0.0 (concise) to 1.0 (verbose)
  - `formality`: 0.0 (casual) to 1.0 (formal)
  - `technical_depth`: 0.0 (simple) to 1.0 (technical)
  - `proactivity`: 0.0 (reactive) to 1.0 (proactive)
  - `emotional_expression`: 0.0 (neutral) to 1.0 (expressive)
  - `structure`: 0.0 (freeform) to 1.0 (structured/bullet-points)
  - `explanation_depth`: 0.0 (brief) to 1.0 (detailed)
  - `example_usage`: 0.0 (none) to 1.0 (many examples)
  - `question_asking`: 0.0 (declarative) to 1.0 (inquisitive)
  - `reassurance_level`: 0.0 (minimal) to 1.0 (supportive)
  - `directness`: 0.0 (indirect) to 1.0 (direct)
  - `enthusiasm`: 0.0 (reserved) to 1.0 (energetic)
  - `patience`: 0.0 (efficient) to 1.0 (thorough)
  - `creativity`: 0.0 (conventional) to 1.0 (creative)
- **Multi-Language**: Dimensions are language-agnostic style attributes, not semantic content
- **Context Integration**: Uses same context bucketing as Thompson Sampling (intent + sentiment + time_of_day)
- **Example**: User wants verbosity=0.2 for technical topics (bucket 42) but verbosity=0.8 for casual chat (bucket 17)
- **Storage per user**: 100 buckets × 16 dimensions × 4 bytes = 6.4KB (vs 3KB for single 768-dim vector)

**Hybrid Skill Selection Algorithm**:
1. **Hash context**: Get context_bucket from current conversation context
2. **Filter applicable skills**: Trigger matching score ≥ 0.5 (see trigger matching above)
3. **Load context-specific preferences**: Retrieve user's preference vector for this context_bucket
4. **Compute preference alignment**: Euclidean distance between user preference vector and skill's dimension vector
5. **Final score**: 40% trigger match + 30% Thompson Sampling + 30% preference alignment
6. **Return**: Highest scoring skill (or exploration candidate if ε-greedy triggers)

**Note**: Preference vectors are explicit dimensions (not embeddings), ensuring interpretability, efficiency (<1KB per context), and no embedding generation during selection (<15ms latency).

#### Why 16 Dimensions? Research-Backed Design Decision

The choice of **16 dimensions** is grounded in extensive research across multiple domains:

**Psychological Foundation (Big Five Model)**:
- Big Five personality traits use 5 core dimensions with 6 facets each = 30 sub-dimensions
- Research shows 8-12 dimensions capture most conversational style variations
- 16 dimensions aligns with validated psychological models of human preferences

**Collaborative Filtering Research (Netflix Prize)**:
- Large-scale systems (millions of items): 50-100 latent factors optimal
- Human preference modeling: 8-20 dimensions sufficient (more structured than item similarities)
- Diminishing returns beyond 20 dimensions for user modeling

**Computational Efficiency**:
- 16 dims: 6.4KB per user (100 contexts) - optimal storage
- 32 dims: 12.8KB per user - 2x storage for marginal gains
- Euclidean distance: <1ms for 100 skills with 16 dimensions
- Real-time selection: <15ms total latency maintained

**Interpretability & Debugging**:
- Each dimension has clear semantic meaning (verbosity, formality, etc.)
- Easy to explain to users and debug preference evolution
- Transparent tracking of how preferences change over time

**Overfitting Prevention**:
- Limited feedback data (sparse user signals)
- Fewer dimensions prevent overfitting with limited training data
- 16 dimensions provides sufficient expressiveness without redundancy

**Alternative Configurations**:
- **Minimal (12 dims)**: Core style only - 4.8KB per user
- **Extended (20 dims)**: Advanced personalization - 8KB per user
- **Current (16 dims)**: Optimal balance - 6.4KB per user ✓

**Research Sources**: Netflix Prize matrix factorization, Big Five personality research, contextual bandits literature, conversational AI style modeling studies.

### 3. Self-Correction and Exploration (Agent Q Model)

AICO actively refines its skills by learning from both its successes and failures.

#### Conceptual Model

- **Exploration**: Occasionally, AICO will try a slightly different interaction style and ask for feedback (e.g., "I usually use bullet points, but would a paragraph be better here?"). This is a form of active learning to discover better procedures.
- **Self-Critique**: When an interaction receives negative feedback, the system logs it as an "unsuccessful trajectory."
- **Template Refinement**: The system learns which prompt templates work best through statistical learning (Thompson Sampling). No LLM retraining occurs - we select between pre-written prompt templates based on user feedback.

#### Implementation Details

**Exploration Strategy** (`shared/aico/ai/memory/exploration.py`):
- With probability ε (e.g., 0.1), select lower-confidence skills for exploration
- Explicitly request user feedback on new approaches
- Track exploration outcomes separately to measure learning effectiveness

**Trajectory Logging** (`backend/services/trajectory_logger.py`):
- Log each conversation turn: user input, selected skill, AI response, user feedback
- Store successful (positive feedback) and unsuccessful (negative feedback) trajectories
- Use trajectories for offline learning and skill refinement

**Template Selection Refinement** (Phase 3 implementation):
- Batch process analyzes trajectories periodically
- Updates Thompson Sampling parameters (Beta distributions) based on success/failure patterns
- Adjusts skill selection probabilities without modifying LLM weights or templates

---

## Data Model & Storage

### Database Schema (`shared/aico/data/schemas/behavioral.py`)

**Skills Table** (user-agnostic templates):
- Primary key: skill_id
- Fields: skill_name, skill_type (base/user_created), trigger_context (JSON), procedure_template, created_at, updated_at
- Indices: skill_type
- Note: No user_id or confidence (stored in separate user_skill_confidence table)

**User Preferences Table**:
- Primary key: user_id
- Fields: preference_vector (JSON latent vector), learning_rate (default 0.1), exploration_rate (default 0.1), last_updated_timestamp

**Feedback Events Table**:
- Primary key: event_id
- Fields: user_id, message_id, skill_id, reward (-1/0/1), timestamp
- Indices: user_id, skill_id

### Python Data Classes (`shared/aico/ai/memory/behavioral.py`)

**Skill**: Pydantic model with skill_id, skill_name, skill_type, trigger_context, procedure_template, created_at, updated_at

**UserPreferences**: Pydantic model with user_id, preference_vector, learning_rate, exploration_rate, last_updated_timestamp

**FeedbackEvent**: Pydantic model with event_id, user_id, message_id, skill_id, reward, timestamp

---

## Implementation Strategy

The behavioral learning system will be implemented as a complete, integrated solution with all components working together from the start. This approach ensures consistency and avoids technical debt from incremental builds.

### Core Implementation Components

**1. Data Layer**
- Database schema for `skills`, `user_skill_confidence`, `user_preferences`, and `feedback_events` tables
- Python data classes (`Skill`, `UserPreferences`, `FeedbackEvent`)
- `SkillStore` class with CRUD operations (no vector search needed for small skill sets)

**2. Learning System**
- Real-time feedback processing via `POST /api/v1/memory/feedback` endpoint
- Confidence score updates using weighted learning
- User preference vector management with explicit dimension updates
- Trajectory logging for successful/unsuccessful interactions

**3. Skill Selection Engine**
- Context extraction using existing NLP models (intent, entities, sentiment)
- Hybrid skill matching: pattern matching (40%) + confidence (30%) + preference (30%)
- Simple in-memory matching (no vector DB for ~10-20 skills)
- Thompson Sampling for exploration/exploitation balance

**4. Contextual Bandit Learning** (Thompson Sampling)
- Offline batch process (scheduled task, runs daily)
- Trajectory analysis: success rate per (context, skill) pair
- Update skill selection probabilities using Thompson Sampling
- Balances exploration (try new skills) vs. exploitation (use proven skills)
- No LLM fine-tuning needed (prompt template selection only)

**5. Integration Points**
- `ConversationEngine`: Apply selected skills during response generation
- `ContextAssembly`: Inject skill guidance into LLM prompts
- Frontend: Feedback UI components in message views
- Logging: Track all skill applications and feedback events

**6. Foundational Skills**
- 10-15 base skills covering common interaction patterns:
  - `concise_response`: Brief, bullet-point answers
  - `detailed_explanation`: In-depth explanations with examples
  - `casual_chat`: Informal, conversational tone
  - `technical_precision`: Formal, precise language for technical topics
  - `empathy_direct`: Explicit empathetic statements
  - `empathy_subtle`: Supportive actions without emotional statements
  - `proactive_suggestions`: Offer next steps and recommendations
  - `reactive_only`: Wait for explicit user requests
  - `code_review_constructive`: Polite, constructive code feedback
  - `summarize_key_points`: Extract and highlight main ideas

### Implementation Order

**Weeks 1-2**: Database schema, SkillStore, base skills (no ChromaDB needed)
**Weeks 3-4**: Feedback API, UI components, confidence updates, skill selection  
**Weeks 5-6**: Preference vectors, context extraction, trajectory logging  
**Weeks 7-8**: Contextual bandit learning, exploration strategy, metrics dashboard

### Success Criteria

**Functional Requirements**:
- ✅ Users can provide feedback on AI responses
- ✅ Skill confidence scores update based on feedback
- ✅ System learns distinct preferences for different users
- ✅ ConversationEngine applies appropriate skills based on context
- ✅ New users receive personalized interactions within 5-10 exchanges
- ✅ Skill library grows organically through learning

**Performance Requirements**:
- ✅ Skill selection latency: <10ms
- ✅ Feedback processing: <5ms
- ✅ Context extraction: <30ms (reuses existing NLP pipeline)
- ✅ No additional memory overhead (reuses existing models)

**Quality Requirements**:
- ✅ Skill accuracy: >70% positive feedback rate
- ✅ User satisfaction: Measurable improvement over baseline
- ✅ System stability: No degradation in response quality
- ✅ Privacy: All data stored locally, encrypted at rest

---

## Technology Stack & Dependencies

This section details all AI models, libraries, and technologies required to implement the behavioral learning system. **We maximize reuse of existing AICO infrastructure** to minimize dependencies and maintain consistency.

### Core AI & Machine Learning

#### 1. **Embedding Models** (for Feedback Classification ONLY)

**Purpose**: Multilingual feedback text classification (not for preference vectors).

**Model**: **REUSE EXISTING** - `sentence-transformers/paraphrase-multilingual-mpnet-base-v2`
- Already configured in `core.yaml` at `modelservice.transformers.models.embeddings`
- Already managed by `TransformersManager` in modelservice
- 768 dimensions (used for semantic memory and feedback classification)
- **NOT used for preference vectors** - those use explicit 16 dimensions

**Use Case**: Classify user feedback text ("too verbose", "too brief", etc.) across 50+ languages using embedding similarity to category centroids.

**No Implementation Needed Here**: Preference vectors use explicit dimensions (see lines 786-810), not embeddings.

#### 2. **Contextual Bandit Learning** (Thompson Sampling)

**Purpose**: Learn which skills work best in which contexts through statistical learning.

**Algorithm**: **Thompson Sampling** (Bayesian contextual bandit)
- No external library needed - custom Python implementation
- Use case: Select optimal skill based on context and past feedback
- Runs real-time for selection + offline batch analysis (daily)
- No neural network training required

**How It Works**: Each (context_bucket, skill) pair maintains separate Beta distribution parameters (α, β) representing success/failure counts in that specific context. Context bucketing hashes conversation context (intent + sentiment + time_of_day) into ~100 buckets, allowing the system to learn context-specific skill effectiveness. Thompson Sampling draws from these distributions to balance exploration vs. exploitation.

**Context Bucketing**: Contexts are hashed into buckets to make learning tractable:
- Hash function: `bucket_id = hash(intent + sentiment + time_of_day) % 100`
- Example: "technical_question + neutral + morning" → bucket 42
- Separate Beta(α, β) parameters stored for each (bucket_id, skill_id) pair
- Allows learning "concise works for technical questions" vs "detailed works for learning questions"

**Key Point**: This learns which **prompt template to select** in each context type, not how to modify the LLM. Skills are pre-written prompt templates (e.g., "Be concise", "Provide detailed explanation"). Thompson Sampling learns which template works best for each context bucket through statistical learning from user feedback.

**Implementation** (`shared/aico/ai/memory/behavioral/thompson_sampling.py`):
```python
"""
Thompson Sampling for Skill Selection

Contextual bandit algorithm that learns which skills work best through
Bayesian statistical learning. No neural network training required.

Follows AICO's privacy-by-design principles - all learning is local.
"""

import numpy as np
from aico.ai.memory.behavioral import SkillStore
from aico.core.logging import get_logger

logger = get_logger("backend", "behavioral.thompson_sampling")

class ThompsonSamplingSelector:
    """
    Select skills using Thompson Sampling (contextual bandit).
    
    Maintains Beta(α, β) distributions for each (context, skill) pair.
    Balances exploration vs. exploitation automatically.
    """
    
    def __init__(self, prior_alpha=1.0, prior_beta=1.0):
        self.prior_alpha = prior_alpha
        self.prior_beta = prior_beta
    
    def _hash_context(self, context: dict) -> int:
        """Hash context into bucket ID for contextual learning."""
        context_str = f"{context.get('intent', 'unknown')}_" \
                     f"{context.get('sentiment', 'neutral')}_" \
                     f"{context.get('time_of_day', 'any')}"
        return hash(context_str) % 100  # 100 context buckets
    
    async def select_skill(self, context: dict, candidate_skills: list) -> str:
        """
        Select best skill for given context using Thompson Sampling.
        
        Args:
            context: Current conversation context (intent, sentiment, time_of_day, etc.)
            candidate_skills: List of applicable skills
        
        Returns:
            skill_id of selected skill
        """
        # Hash context into bucket for contextual learning
        context_bucket = self._hash_context(context)
        
        # Get success/failure counts for each skill in this context bucket
        skill_scores = {}
        for skill in candidate_skills:
            stats = await self._get_skill_stats(skill.skill_id, context_bucket)
            
            # Sample from Beta distribution
            alpha = self.prior_alpha + stats['successes']
            beta = self.prior_beta + stats['failures']
            sampled_score = np.random.beta(alpha, beta)
            
            skill_scores[skill.skill_id] = sampled_score
        
        # Select skill with highest sampled score
        selected_skill_id = max(skill_scores, key=skill_scores.get)
        
        logger.info("Skill selected via Thompson Sampling", extra={
            "skill_id": selected_skill_id,
            "context_bucket": context_bucket,
            "sampled_score": skill_scores[selected_skill_id],
            "metric_type": "behavioral_memory_selection"
        })
        
        return selected_skill_id
    
    async def update_from_feedback(self, skill_id: str, context: dict, 
                                   reward: int):
        """
        Update skill statistics based on user feedback.
        
        Args:
            skill_id: ID of skill that was applied
            context: Context in which skill was used (will be hashed to bucket)
            reward: 1 (success), -1 (failure), 0 (neutral - no update)
        """
        if reward == 0:
            return  # Neutral feedback doesn't update statistics
        
        # Hash context into bucket
        context_bucket = self._hash_context(context)
        
        # Get stats for this (context_bucket, skill) pair
        stats = await self._get_skill_stats(skill_id, context_bucket)
        
        if reward > 0:
            stats['successes'] += 1
        else:
            stats['failures'] += 1
        
        # Save stats for this specific context bucket
        await self._save_skill_stats(skill_id, context_bucket, stats)
```

#### 3. **Meta-Learning Framework**

**Purpose**: Implement rapid adaptation to new users with minimal data.

**Approach**: **Lightweight custom implementation** using existing infrastructure
- Store user-specific preference vectors (16 explicit dimensions per context bucket)
- Use Euclidean distance for preference alignment
- No embeddings, no neural networks - just explicit style dimensions

**Why Lightweight**: Uses explicit preference dimensions (16 floats) + text templates instead of neural network training or semantic embeddings. Simple vector math, <10ms selection, fully interpretable, ~6.4KB per user.

**Implementation** (`shared/aico/ai/memory/behavioral/preferences.py`):
```python
"""
User Preference Management

Manages context-aware user preference vectors with explicit dimensions.
Part of AICO's behavioral learning system.

Follows AICO's privacy-by-design: all data stored locally and encrypted.
"""

import numpy as np
from aico.core.logging import get_logger

logger = get_logger("backend", "memory.behavioral.preferences")

class ContextPreferenceManager:
    """
    Manages context-aware preference vectors with explicit dimensions.
    
    Each (user_id, context_bucket) pair has a separate preference vector
    with 16 explicit style dimensions (verbosity, formality, etc.).
    
    Attributes:
        num_dimensions: Number of preference dimensions (default: 16)
    """
    
    def __init__(self, num_dimensions: int = 16):
        self.num_dimensions = num_dimensions
        
    def initialize_preferences(self, user_id: str, context_bucket: int) -> np.ndarray:
        """Initialize with neutral preference vector (all 0.5)."""
        return np.full(self.num_dimensions, 0.5, dtype=np.float32)
    
    def update_preferences(self, current_prefs: np.ndarray, 
                          skill_dimensions: np.ndarray, 
                          reward: int, 
                          learning_rate: float = 0.1) -> np.ndarray:
        """Update preferences based on feedback.
        
        Args:
            current_prefs: Current preference vector
            skill_dimensions: Dimension values of applied skill
            reward: 1 (positive), -1 (negative), 0 (neutral)
            learning_rate: Adaptation rate (default 0.1)
        """
        if reward == 0:
            return current_prefs
        
        # Move toward skill dimensions if positive, away if negative
        direction = reward * learning_rate
        new_prefs = current_prefs + direction * (skill_dimensions - current_prefs)
        
        # Clamp to [0, 1] range
        return np.clip(new_prefs, 0.0, 1.0)
    
    def compute_alignment(self, user_prefs: np.ndarray, 
                         skill_dimensions: np.ndarray) -> float:
        """Compute preference alignment score.
        
        Returns:
            Alignment score in [0, 1] range (1 = perfect match)
        """
        # Euclidean distance, normalized to [0, 1]
        distance = np.linalg.norm(user_prefs - skill_dimensions)
        max_distance = np.sqrt(len(user_prefs))
        return 1.0 - (distance / max_distance)
```

### Data Storage & Retrieval

#### 4. **Database: libSQL (SQLite with Extensions)**

**Purpose**: Store skills, preferences, and feedback events.

**Library**: **REUSE EXISTING** - `libsql-client` (Python)
- Already used throughout AICO for encrypted local storage
- Supports JSON columns for flexible schema (trigger_context, preference_vector)
- Full-text search capabilities for skill descriptions
- Encryption at rest (already configured)

**Schema Features**:
- JSON storage for complex fields (trigger_context, preference_profile)
- Indexes for fast user-based and confidence-based queries
- Foreign key constraints for data integrity

#### 5. **Preference Alignment Computation**

**Purpose**: Fast preference matching for skill selection.

**Library**: **NumPy** (already present)
- Use case: Compute Euclidean distance between preference vectors and skill dimension vectors
- Advantages: No additional dependencies, <1ms for 100 skills
- Library: `numpy` only (no scipy needed)

**Why NumPy Instead of ChromaDB**: 
- **Small scale**: 10-20 base skills + user-created skills = typically <100 total
- **In-memory efficiency**: NumPy Euclidean distance is <1ms for 100 vectors
- **Simplicity**: No additional database, simpler architecture
- **Explicit dimensions**: No embedding generation needed

**Implementation**:
```python
import numpy as np

def select_best_skill(user_preference_vector: np.ndarray, 
                     candidate_skills: list) -> str:
    """
    Select skill with highest preference alignment using NumPy.
    
    Args:
        user_preference_vector: User's 16-dimensional preference vector
        candidate_skills: List of applicable skills with dimension vectors
    
    Returns:
        skill_id of best matching skill
    """
    best_skill_id = None
    best_score = -1
    
    max_distance = np.sqrt(len(user_preference_vector))
    
    for skill in candidate_skills:
        # Euclidean distance, normalized to [0, 1] alignment score
        distance = np.linalg.norm(user_preference_vector - skill.dimensions)
        alignment = 1.0 - (distance / max_distance)
        
        if alignment > best_score:
            best_score = alignment
            best_skill_id = skill.skill_id
    
    return best_skill_id
```

**Performance**: <1ms for 100 skills (negligible overhead)

**Scaling Note**: System is designed for <100 skills per user. Explicit dimensions scale better than embeddings.

### Natural Language Processing

#### 6. **Intent Classification & Context Analysis**

**Purpose**: Extract trigger context from conversations (intent, entities, topics).

**Model**: **REUSE EXISTING** - `xlm-roberta-base`
- Already configured in `core.yaml` at `modelservice.transformers.models.intent_classification`
- Already managed by `TransformersManager`
- Multilingual support (matches AICO's multilingual design)
- Use case: Classify user intent to determine appropriate skill category

**Entity Extraction**: **REUSE EXISTING** - `urchade/gliner_medium-v2.1`
- Already configured in `core.yaml` at `modelservice.transformers.models.entity_extraction`
- Already managed by `TransformersManager`
- Generalist entity extraction (can extract any entity type)
- Use case: Extract topics, subjects, and context from conversations

**Implementation**:
```python
from modelservice.core.transformers_manager import TransformersManager

# Use existing models
intent_model = transformers_manager.get_model("intent_classification")
entity_model = transformers_manager.get_model("entity_extraction")

def extract_context(text: str) -> dict:
    # Extract intent
    intent = intent_model.classify(text)
    
    # Extract entities (topics, subjects)
    entities = entity_model.extract(text, labels=["topic", "subject", "activity"])
    
    return {
        "intent": intent,
        "entities": entities,
        "time_of_day": get_time_of_day()
    }
```

#### 7. **Sentiment Analysis** (for Emotional Context)

**Purpose**: Detect user sentiment to inform skill selection.

**Model**: **REUSE EXISTING** - `nlptown/bert-base-multilingual-uncased-sentiment`
- Already configured in `core.yaml` at `modelservice.transformers.models.sentiment_multilingual`
- Already managed by `TransformersManager` (priority 1, required)
- Multilingual support
- Use case: Determine if user is frustrated, happy, neutral to select appropriate interaction style

**Alternative** (if more nuanced emotion detection needed):
- `cardiffnlp/twitter-roberta-base-sentiment-latest` (already in DEFAULT_MODELS as `sentiment_english`)
- `j-hartmann/emotion-english-distilroberta-base` (already in DEFAULT_MODELS as `emotion_analysis`)

**Implementation**:
```python
from modelservice.core.transformers_manager import TransformersManager

# Use existing sentiment model
sentiment_model = transformers_manager.get_model("sentiment_multilingual")

def detect_sentiment(text: str) -> str:
    result = sentiment_model(text)
    return result[0]['label']  # e.g., "positive", "negative", "neutral"
```

### Utilities & Supporting Libraries

#### 8. **Data Validation & Serialization**

**Library**: **REUSE EXISTING** - **Pydantic** (v2.0+)
- Already used throughout AICO for data validation
- Use case: Validate skill data, API payloads, database models
- Advantages: Type safety, automatic validation, JSON serialization

#### 9. **Numerical Computing**

**Libraries**: **REUSE EXISTING**
- **NumPy**: Already a dependency, use for array operations, vector math, confidence score updates
- **SciPy**: Already a dependency, use for cosine similarity, statistical functions

#### 10. **Logging & Monitoring**

**Infrastructure**: **REUSE EXISTING** - AICO's unified logging system
- Already configured in `core.yaml` at `logging`
- ZeroMQ message bus for log transport
- Use case: Track skill applications, feedback events, learning metrics
- Subsystem: Add `behavioral_memory` to logging configuration

**Implementation**:
```python
from shared.aico.core.logging import get_logger

logger = get_logger("backend", "behavioral_memory")
logger.info("Skill applied", extra={
    "skill_id": skill.skill_id,
    "user_id": user_id,
    "confidence": skill.confidence_score
})
```

### Frontend Integration

#### 11. **Flutter/Dart Libraries**

**Purpose**: Capture and send user feedback from the mobile/desktop UI.

**Frontend Requirements**:
- Use existing HTTP client (http/dio) to send feedback to `POST /api/v1/memory/feedback`
- Integrate thumbs up/down buttons into message UI components
- Maintain message_id and skill_id association for feedback submission

### Development & Testing

#### 12. **Testing Frameworks**

**Libraries**: **REUSE EXISTING**
- **pytest**: Already used for AICO backend tests
- **pytest-asyncio**: Already used for async endpoint tests
- **pytest-mock**: For mocking message bus and database interactions
- Use case: Unit tests for skill selection, preference updates, feedback processing

**Test Structure** (following AICO patterns):
```
tests/
├── unit/
│   ├── memory/
│   │   ├── test_skill_store.py
│   │   ├── test_preference_manager.py
│   │   └── test_confidence_updates.py
│   └── api/
│       └── test_memory_router.py
├── integration/
│   ├── test_feedback_flow.py
│   └── test_skill_selection.py
└── fixtures/
    ├── skills.py
    └── trajectories.py
```

**Example Tests** (see `tests/unit/memory/test_skill_store.py`):
```python
import pytest
from aico.ai.memory.procedural import Skill, update_skill_confidence

def test_positive_feedback_increases_confidence():
    skill = Skill(user_id="test", skill_name="concise", 
                  procedure_template="Be brief.", confidence_score=0.5)
    updated = update_skill_confidence(skill, reward=1, learning_rate=0.1)
    assert updated.confidence_score == 0.6

@pytest.mark.asyncio
async def test_feedback_endpoint(test_client, mock_bus_client):
    response = await test_client.post("/api/v1/memory/feedback",
        json={"message_id": "msg_123", "skill_id": "skill_456", "reward": 1})
    assert response.status_code == 200
    mock_bus_client.publish.assert_called_once()
```

### Configuration Management

#### 13. **Configuration**

**System**: **REUSE EXISTING** - Add to `config/defaults/core.yaml` under the `memory:` section

**Location**: After `memory.semantic.knowledge_graph` (around line 342), add:

```yaml
memory:
  # ... existing working and semantic config ...
  
  # Behavioral Learning - Adaptive interaction learning
  behavioral:
    enabled: true
    
    # Learning parameters
    learning_rate: 0.1  # How quickly confidence scores adjust to feedback
    exploration_rate: 0.1  # Probability of trying lower-confidence skills
    
    # Skill management
    max_skills_per_user: 100  # Maximum learned skills per user
    skill_selection_timeout_ms: 10  # Max time for skill selection
    min_confidence_threshold: 0.3  # Don't use skills below this confidence
    
    # Preference vectors (explicit dimensions, NOT embeddings)
    preference_vector_dim: 16  # Number of explicit style dimensions (optimal: 16)
    num_context_buckets: 100  # Context bucketing for contextual learning
    
    # Feedback classification (multilingual, uses embeddings)
    feedback_classifier:
      similarity_threshold: 0.6  # Minimum cosine similarity for category match
      embedding_model: "paraphrase-multilingual-mpnet-base-v2"  # Reuse existing model
      # Note: UI constraints (max chars, dropdown options) are defined client-side in Flutter app
    
    # Contextual bandit learning (Thompson Sampling)
    contextual_bandit:
      enabled: true
      algorithm: "thompson_sampling"  # Thompson Sampling for exploration/exploitation
      update_interval_hours: 24  # Run batch learning daily at 4 AM
      min_trajectories: 10  # Minimum trajectories needed for update
      prior_alpha: 1.0  # Beta distribution prior (successes)
      prior_beta: 1.0  # Beta distribution prior (failures)
      context_hash_buckets: 100  # Number of context buckets (matches num_context_buckets)
    
    # Trajectory logging for learning
    trajectory_logging:
      enabled: true
      retention_days: 90  # Archive after 90 days
      hard_delete_days: 365  # Delete after 1 year
      keep_feedback_indefinitely: true  # Never delete trajectories with feedback
    
    # Skill matching
    skill_matching:
      match_threshold: 0.5  # Minimum score to consider skill applicable
      use_explicit_dimensions: true  # Use explicit dimensions (NOT embeddings)
      max_candidates: 5  # Top N skills to consider
      distance_metric: "euclidean"  # Euclidean distance for explicit dimensions
    
    # Performance monitoring
    metrics:
      log_skill_selection: true  # Log every skill selection with timing
      log_feedback_events: true  # Log all user feedback
      log_confidence_changes: true  # Track confidence score evolution
      aggregate_interval_minutes: 60  # Aggregate metrics every hour
```

### Protocol Buffer Schemas

**New File**: `proto/aico_memory.proto` with messages:
- `FeedbackEvent`: user_id, message_id, skill_id, reward, reason, free_text, timestamp
- `SkillSelectionRequest`: user_id, conversation_id, message_text, context_tags, timestamp
- `SkillSelectionResponse`: request_id, skill_id, skill_name, procedure_template, confidence_score, preference_alignment, is_exploration, selection_time_ms
- `SkillApplicationEvent`: user_id, message_id, skill_id, skill_name, confidence_score, timestamp

**Topics**: `memory/procedural/{feedback,skill_request,skill_response,skill_applied}/v1`

### Complete Technology Stack Summary

**All components leverage existing AICO infrastructure:**

| Component | Technology | Status | Purpose |
|-----------|-----------|--------|---------|
| **Embeddings** | `paraphrase-multilingual-mpnet-base-v2` | ✅ Existing | Feedback classification ONLY |
| **Intent Classification** | `xlm-roberta-base` | ✅ Existing | Context extraction |
| **Entity Extraction** | `gliner_medium-v2.1` | ✅ Existing | Topic/subject detection |
| **Sentiment Analysis** | `bert-base-multilingual-uncased-sentiment` | ✅ Existing | Emotional context |
| **Database** | libSQL | ✅ Existing | Skill/preference storage |
| **Contextual Bandit** | Thompson Sampling (custom) | ➕ New | Statistical skill selection |
| **Preference Vectors** | Explicit dimensions (custom) | ➕ New | Context-aware style preferences |
| **Logging** | ZeroMQ message bus | ✅ Existing | Unified logging |
| **Config** | YAML | ✅ Existing | Configuration management |
| **Validation** | Pydantic v2 | ✅ Existing | Data validation |
| **Numerical** | NumPy | ✅ Existing | Vector operations |
| **Frontend** | Flutter/Dart | ✅ Existing | Feedback UI |
| **Testing** | pytest | ✅ Existing | Unit/integration tests |

### New Dependencies

**Only ONE new dependency required:**

**No new dependencies required** - all behavioral learning uses existing AICO infrastructure:
- NumPy for statistical computations and vector operations (already present)
- libSQL for skill storage (already present)
- Existing embedding models for feedback classification only (already present)

**Installation**:
```bash
# No additional packages needed - behavioral learning uses existing dependencies
uv pip install -e ".[backend]"

# Or install all optional dependencies
uv pip install -e ".[backend,modelservice,cli,test]"
```

**All dependencies are already present in AICO.**

### Resource Requirements

**Disk Space**:
- No additional models to download (all models already in use)
- Per-user skill storage: <1MB (target: 100 skills × ~10KB each)
- Trajectory logs: ~5-10MB per user per month

**Memory**:
- No additional runtime memory (reusing existing models)
- Thompson Sampling updates (offline): Minimal memory, <10MB (runs daily, not real-time)

**Compute**:
- Skill selection: <10ms (vector similarity lookup in ChromaDB)
- Context extraction: ~20-30ms (already happening for conversations)
- Feedback processing: <5ms (simple confidence update)
- Thompson Sampling updates: <1s per user, runs offline as scheduled task (not user-facing)

**All operations run locally on CPU; no GPU required.**

---

## Privacy & Security Considerations

**AICO's behavioral learning system follows strict privacy-by-design principles:**

### Local-First Architecture
- **All data stored locally**: Skills, preferences, and trajectories stored in encrypted libSQL database
- **No cloud dependencies**: System operates entirely on-device
- **Encrypted at rest**: SQLCipher encryption for all behavioral learning data
- **Secure key management**: Uses AICO's key derivation system (`aico.security.AICOKeyManager`)

### User Control & Transparency
- **Explicit opt-in**: Users must enable procedural learning (disabled by default)
- **Full visibility**: Users can view all learned skills and preferences via UI
- **Edit capabilities**: Users can modify or delete any learned skill
- **Explanation system**: UI shows why each skill was applied (confidence score, preference alignment)
- **Disable anytime**: Users can turn off procedural learning without data loss

### Data Governance & Compliance
- **No external sharing**: Data never leaves device, no telemetry
- **User export**: JSON format for full data portability
- **Audit logging**: All skill applications logged for review
- **Message bus security**: CurveZMQ encryption, topic isolation, access control
- **GDPR-ready**: Full access, modify, delete, export rights
- **Privacy-preserving**: Thompson Sampling uses aggregated success/failure counts, not raw messages

---

## Performance Metrics & Monitoring

The system logs comprehensive metrics to track learning effectiveness and system performance over time. All metrics are logged via AICO's unified logging system with `metric_type` tags for easy filtering and aggregation.

### Learning Effectiveness Metrics

**Logged on every feedback event** (`metric_type: "behavioral_memory_feedback"`):
```python
logger.info("Skill feedback received", extra={
    "user_id": user_id,
    "skill_id": skill_id,
    "skill_name": skill.skill_name,
    "reward": reward,  # 1, 0, or -1
    "reason": reason,  # Dropdown selection
    "old_confidence": old_confidence,
    "new_confidence": new_confidence,
    "confidence_delta": new_confidence - old_confidence,
    "total_usage": skill.usage_count,
    "positive_rate": skill.positive_feedback_count / skill.usage_count,
    "negative_rate": skill.negative_feedback_count / skill.usage_count,
    "has_free_text": bool(free_text),
    "metric_type": "behavioral_memory_feedback"
})
```

**Aggregated hourly** (`metric_type: "behavioral_memory_aggregate"`):
- **Skill Accuracy**: Percentage of skills receiving positive feedback (target: >70%)
- **User Satisfaction**: Average reward per user (target: >0.5)
- **Adaptation Speed**: Number of interactions to reach 70% positive rate for new users (target: <10)
- **Skill Retention**: Confidence score stability over time (low variance = good)

### System Performance Metrics

**Logged on every skill selection** (`metric_type: "behavioral_memory_selection"`):
```python
logger.info("Skill selected", extra={
    "user_id": user_id,
    "skill_id": selected_skill.skill_id,
    "skill_name": selected_skill.skill_name,
    "confidence_score": selected_skill.confidence_score,
    "preference_alignment": alignment_score,
    "selection_time_ms": selection_time_ms,  # Target: <10ms
    "context_extraction_time_ms": context_time_ms,  # Target: <30ms
    "total_candidates": len(candidate_skills),
    "exploration_mode": is_exploration,  # True if ε-greedy selected low-confidence skill
    "metric_type": "behavioral_memory_selection"
})
```

**Aggregated hourly** (`metric_type: "behavioral_memory_performance"`):
- **Response Time**: P50, P95, P99 skill selection latency (target: P95 <10ms)
- **Memory Usage**: Current skill storage per user (target: <1MB)
- **Processing Overhead**: Average skill selection time (target: <10ms)
- **Scalability**: Performance with increasing user count and skill library size

### Thompson Sampling Batch Update Metrics

**Logged after each batch update** (`metric_type: "behavioral_memory_thompson_sampling"`):
```python
logger.info("Thompson Sampling parameters updated", extra={
    "trajectories_analyzed": len(trajectories),
    "skills_updated": len(updated_skills),
    "avg_alpha_change": avg_alpha_change,
    "avg_beta_change": avg_beta_change,
    "update_duration_seconds": duration,
    "metric_type": "behavioral_memory_thompson_sampling"
})
```

### Monitoring Dashboard Queries

**Example queries** (filter by `metric_type` in logs):
- **Skill accuracy**: `AVG(CASE WHEN reward > 0 THEN 1.0 ELSE 0.0 END)` grouped by hour
- **Slow skills**: Skills with `AVG(selection_time_ms) > 10ms`
- **User adaptation**: Positive rate over time per user
- **Exploration effectiveness**: Compare confidence scores for explored vs. exploited skills

### Success Criteria

**Learning Effectiveness**:
- ✅ **Skill Accuracy**: >70% positive feedback rate across all skills
- ✅ **User Satisfaction**: Average reward >0.5 per user
- ✅ **Adaptation Speed**: New users reach 70% positive rate within 10 interactions
- ✅ **Skill Retention**: Confidence scores remain stable (variance <0.1) after 50 uses

**System Performance**:
- ✅ **Response Time**: P95 skill selection latency <10ms
- ✅ **Memory Usage**: <1MB storage per user (100 skills × 10KB)
- ✅ **Processing Overhead**: <30ms total (context extraction + skill selection)
- ✅ **Scalability**: Linear performance up to 1000 users, 100 skills each

---

## Appendix A: Implementation Specifications

### Consolidation Engine

**Idle Detection Criteria**:
```yaml
consolidation:
  idle_detection:
    cpu_threshold_percent: 20  # Trigger when CPU < 20%
    idle_duration_seconds: 300  # 5 minutes continuous idle
    check_interval_seconds: 60  # Check every minute
  schedule:
    daily_time: "02:00"  # Fallback: 2 AM local time
    timezone: "system"
```

**Replay Prioritization Algorithm** (based on Prioritized Experience Replay):
```python
# Priority = |importance| + recency_bonus + feedback_bonus
priority_i = abs(importance_score_i) + (1.0 / days_since_i) + (1.0 if has_feedback_i else 0.0)

# Efficient sampling using SumTree (O(log N) instead of O(N))
# SumTree stores priorities in binary tree structure
# Sampling: uniform random [0, total_priority], traverse tree in O(log N)
# Update: propagate priority changes up tree in O(log N)
# α = 0.6 (config: consolidation.priority_alpha)
```
- **Importance score**: Cosine similarity to recent queries (last 10 queries)
- **Recency bonus**: `1 / max(1, days_since_interaction)` (avoid division by zero)
- **Feedback bonus**: +1.0 if interaction has user feedback
- **Implementation**: Use SumTree data structure for O(log N) sampling

**Memory Reconsolidation Strategy** (with variant limits):
```python
# Confidence-weighted conflict resolution with variant limits
async def reconsolidate_fact(new_fact, existing_fact):
    """
    Integrate new fact with existing knowledge, preventing variant bloat.
    
    Strategy:
    - High confidence new fact: Update existing fact
    - Low confidence new fact: Store as variant (up to max limit)
    - Variant limit reached: Replace weakest variant
    """
    if new_fact.confidence > existing_fact.confidence:
        # New fact is more confident - update existing
        await update_fact(new_fact, mark_superseded=existing_fact)
    else:
        # New fact is less confident - store as variant
        variant_count = await get_variant_count(existing_fact.fact_id)
        
        if variant_count < 3:  # max_fact_variants from config
            # Store as new variant
            await store_variant(
                new_fact, 
                related_to=existing_fact, 
                temporal_link=True
            )
        else:
            # Variant limit reached - replace weakest variant
            weakest_variant = await get_weakest_variant(existing_fact.fact_id)
            
            if new_fact.confidence > weakest_variant.confidence:
                # New fact is stronger than weakest variant
                await replace_variant(weakest_variant.id, new_fact)
            else:
                # New fact is weaker - discard it
                logger.info(f"Discarded low-confidence variant for fact {existing_fact.fact_id}")
```

**Variant Cleanup** (scheduled weekly):
```python
async def cleanup_old_variants():
    """
    Remove low-confidence variants older than 90 days.
    Prevents accumulation of outdated alternative facts.
    """
    cutoff_date = datetime.now() - timedelta(days=90)
    
    await db.execute("""
        DELETE FROM semantic_facts
        WHERE is_variant = TRUE
        AND confidence < 0.3
        AND created_at < ?
    """, (cutoff_date,))
```

**Temporal Metadata Schema**:
```python
@dataclass
class TemporalMetadata:
    created_at: datetime
    last_updated: datetime
    last_accessed: datetime
    access_count: int
    confidence: float  # Decays: confidence *= (1 - decay_rate)^days
    version: int
    superseded_by: Optional[str] = None
```

**Storage Location**: Temporal metadata is stored as JSON in the `temporal_metadata` column of semantic memory tables (ChromaDB metadata + libSQL):

```sql
-- Add to semantic facts table in libSQL
ALTER TABLE semantic_facts ADD COLUMN temporal_metadata TEXT;  -- JSON

-- Example stored value:
{
  "created_at": "2025-01-15T10:30:00Z",
  "last_updated": "2025-01-20T14:22:00Z",
  "last_accessed": "2025-01-22T09:15:00Z",
  "access_count": 12,
  "confidence": 0.85,
  "version": 2,
  "superseded_by": null
}
```

**ChromaDB Integration**: Temporal metadata is also stored in ChromaDB document metadata for efficient temporal queries:
```python
chroma_collection.add(
    documents=[fact_text],
    metadatas=[{
        "user_id": user_id,
        "created_at": timestamp.isoformat(),
        "confidence": 0.9,
        "version": 1
    }]
)
```

**Configuration**:
```yaml
memory:
  consolidation:
    enabled: true
    idle_threshold_cpu_percent: 20
    idle_duration_seconds: 300
    schedule: "0 2 * * *"  # Cron format (2 AM daily)
    user_sharding_cycle_days: 7  # Round-robin: 1/7 of users per day
    replay_batch_size: 100
    max_duration_minutes: 60
    priority_alpha: 0.6
    max_concurrent_users: 4  # Semaphore limit
    
  temporal:
    enabled: true
    metadata_retention_days: 365
    evolution_tracking: true
    confidence_decay_rate: 0.001  # Per day without access
    max_fact_variants: 3  # Maximum variants per fact (prevents bloat)
    variant_cleanup_days: 90  # Delete low-confidence variants after 90 days
```

---

### Behavioral Learning Specifications

**Skill Trigger Matching**:
```python
def match_trigger(trigger_context: dict, current_context: dict) -> float:
    """
    Hybrid context matching for skill applicability.
    
    Note: User preferences are handled separately via preference vectors.
    This function only matches contextual factors (intent, time, topic).
    """
    score = 0.0
    
    # Exact match (40%): intent
    if trigger_context.get("intent") == current_context.get("intent"):
        score += 0.4
    
    # Contextual match (30%): time_of_day, sentiment
    if trigger_context.get("time_of_day") == current_context.get("time_of_day"):
        score += 0.15
    if trigger_context.get("sentiment") == current_context.get("sentiment"):
        score += 0.15
    
    # Embedding similarity (30%): topic/entities
    topic_sim = cosine_similarity(
        trigger_context["topic_embedding"],
        current_context["topic_embedding"]
    )
    score += 0.3 * topic_sim
    
    return score  # Range: [0.0, 1.0]
```

**Weight Distribution**:
- **40% Intent**: Primary signal (question, request, chat, etc.)
- **15% Time of Day**: Morning/afternoon/evening context
- **15% Sentiment**: User's emotional state (positive, negative, neutral)
- **30% Topic Similarity**: Semantic similarity of conversation topic

**User Preference Matching**: Handled separately via preference vector cosine similarity (see lines 1089-1094)

**Base Skills Definition** (`config/defaults/behavioral_skills.yaml`):
```yaml
base_skills:
  - skill_id: "concise_response"
    skill_name: "Concise Response"
    template: "Provide a brief, bullet-point answer. Maximum 3 points."
    trigger: {intent: ["question", "request"]}
    dimensions: [0.2, 0.5, 0.5, 0.5, 0.3, 0.7, 0.4, 0.5, 0.5, 0.5, 0.6, 0.5, 0.5, 0.5]  # 16 floats
    # [verbosity, formality, technical_depth, proactivity, emotional_expression, structure,
    #  explanation_depth, example_usage, question_asking, reassurance_level, directness,
    #  enthusiasm, patience, creativity, (2 reserved)]
    
  - skill_id: "detailed_explanation"
    skill_name: "Detailed Explanation"
    template: "Provide in-depth explanation with examples and context."
    trigger: {intent: ["question", "learning"]}
    dimensions: [0.9, 0.6, 0.7, 0.5, 0.4, 0.6, 0.8, 0.7, 0.6, 0.6, 0.6, 0.6, 0.7, 0.5]  # 16 floats
    # [verbosity, formality, technical_depth, proactivity, emotional_expression, structure,
    #  explanation_depth, example_usage, question_asking, reassurance_level, directness,
    #  enthusiasm, patience, creativity, (2 reserved)]
    
  # ... 8 more base skills, each with explicit dimension values
```

**Skill Dimension Assignment**:
- Each skill has explicit dimension values (16 floats in [0, 1] range)
- Dimensions encode the skill's style characteristics
- Example: "concise_response" has verbosity=0.2, "detailed_explanation" has verbosity=0.9
- These are manually defined for base skills, learned for user-created skills
- Last 2 dimensions reserved for future expansion

**Note**: Preference vectors are now context-aware explicit dimensions (see lines 786-810), not global embedding-based vectors.

**Confidence Score Update Formula** (Adaptive Exponential Moving Average):
```python
def update_confidence(current: float, reward: int, usage_count: int) -> float:
    """
    Adaptive EMA with reward mapped to [0, 1] range.
    Uses higher learning rate for new skills, lower for established skills.
    
    Args:
        current: Current confidence score
        reward: 1 (positive), -1 (negative), 0 (neutral - no update)
        usage_count: Number of times skill has been used
    
    Returns:
        Updated confidence score in range [0.2, 0.9]
    """
    if reward == 0:  # Neutral feedback - no update
        return current
    
    # Adaptive learning rate: faster for new skills, slower for established
    # New skills (< 10 uses): alpha = 0.3 (fast adaptation)
    # Established skills (>= 10 uses): alpha = 0.1 (stable learning)
    alpha = 0.3 if usage_count < 10 else 0.1
    
    # Map reward to target confidence: -1→0.2, 1→0.8
    target = 0.5 + (reward * 0.3)
    
    # EMA update: new = α * target + (1-α) * current
    new_confidence = alpha * target + (1 - alpha) * current
    
    # Clamp to [0.2, 0.9] range (0.2 min ensures skills remain discoverable)
    return max(0.2, min(0.9, new_confidence))
```

**Adaptive Learning Benefits**:
- **Fast initial adaptation**: New skills reach optimal confidence in ~5-7 feedback events (vs. ~22 with fixed alpha)
- **Stable refinement**: Established skills change slowly, preventing volatility
- **Smooth transition**: Gradual shift from exploration to exploitation

**Multi-User Skill Storage**:
```python
# Strategy: Base skills are user-agnostic templates
# User-specific confidence stored separately

skills_table:
  - skill_id: "concise_response" (base skill, shared template)
  - skill_id: "alice_custom_skill_1" (user-created)

user_skill_confidence_table:
  - (user_id="alice", skill_id="concise_response") → confidence: 0.8
  - (user_id="bob", skill_id="concise_response") → confidence: 0.3

# Base skill templates never change
# Only per-user confidence scores evolve
```

**Exploration Rate** (ε-greedy with adaptive decay):
- **Initial ε = 0.1**: 10% exploration, 90% exploitation
- **Adaptive decay**: `ε_t = max(0.05, 0.1 * 0.95^(feedback_count))` where `feedback_count` is number of feedback events received
- **Decay trigger**: Only decays when user provides feedback (not on total interactions)
- **Per-user tracking**: Each user has own exploration rate and feedback counter
- **Convergence**: Reaches 5% exploration after ~60 feedback events

**Rationale**:
- Decaying on feedback (not total interactions) ensures exploration continues until user actively guides the system
- Users who don't provide feedback maintain higher exploration rate
- 60 feedback events is realistic for active users over 2-3 weeks

**Implementation**:
```python
def get_exploration_rate(user_id: str) -> float:
    """Calculate current exploration rate for user."""
    feedback_count = get_user_feedback_count(user_id)
    epsilon = max(0.05, 0.1 * (0.95 ** feedback_count))
    return epsilon
```

---

### Feedback Processing Specifications

**Category Definitions**:
```python
FEEDBACK_CATEGORIES = {
    "too_verbose": [
        "too long", "too verbose", "too detailed", "too wordy", "too much text",
        "make it shorter", "be more concise", "brevity", "tldr", "summarize"
    ],
    "too_brief": [
        "too short", "too brief", "not enough detail", "more explanation",
        "elaborate", "expand", "needs context", "incomplete", "more info"
    ],
    "wrong_tone": [
        "too formal", "too casual", "wrong tone", "inappropriate style",
        "be more friendly", "be more professional", "tone down", "lighten up"
    ],
    "not_helpful": [
        "not helpful", "doesn't answer", "irrelevant", "off topic",
        "didn't help", "useless", "not what I asked", "wrong answer"
    ],
    "incorrect_info": [
        "incorrect", "wrong", "inaccurate", "false", "mistake",
        "error", "not true", "outdated", "misinformation"
    ]
}
```

**Similarity Threshold**: 0.6
- **Rationale**: Empirically validated for 85% accuracy in multilingual sentiment analysis
- **Trade-off**: Balance precision (avoid false positives) vs. recall (catch relevant feedback)

**Batch Processing Schedule**:
```yaml
consolidation:
  feedback_processing:
    schedule: "0 3 * * *"  # 3 AM daily (cron format)
    timezone: "system"
    min_feedback_count: 5
    max_processing_time_minutes: 30
```

---

### Data Model Specifications

**Complete Schemas**:
```sql
-- Skills table (user-agnostic templates)
CREATE TABLE skills (
    skill_id TEXT PRIMARY KEY,
    skill_name TEXT NOT NULL,
    skill_type TEXT NOT NULL,  -- 'base', 'user_created'
    trigger_context TEXT NOT NULL,  -- JSON: {intent: [...], time_of_day: ...}
    procedure_template TEXT NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_type (skill_type)
);

-- Feedback events table
CREATE TABLE feedback_events (
    event_id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    message_id TEXT NOT NULL,
    skill_id TEXT,
    reward INTEGER NOT NULL,  -- 1, 0, -1
    reason TEXT,  -- Dropdown selection
    free_text TEXT,  -- User's free text feedback
    classified_categories TEXT,  -- JSON: {"too_verbose": 0.85, ...}
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    processed BOOLEAN DEFAULT FALSE,
    INDEX idx_user_id (user_id),
    INDEX idx_skill_id (skill_id),
    INDEX idx_processed (processed)
);

-- Trajectories table (with retention policy)
CREATE TABLE trajectories (
    trajectory_id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    conversation_id TEXT NOT NULL,
    turn_number INTEGER NOT NULL,
    user_input TEXT NOT NULL,
    selected_skill_id TEXT,
    ai_response TEXT NOT NULL,
    feedback_reward INTEGER,  -- 1, 0, -1, NULL
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    archived BOOLEAN DEFAULT FALSE,  -- For soft deletion
    INDEX idx_user_feedback (user_id, feedback_reward),
    INDEX idx_timestamp (timestamp)  -- For retention cleanup
);

-- User-skill confidence mapping (separate from skills table)
CREATE TABLE user_skill_confidence (
    user_id TEXT NOT NULL,
    skill_id TEXT NOT NULL,
    confidence_score REAL DEFAULT 0.5,
    usage_count INTEGER DEFAULT 0,
    positive_count INTEGER DEFAULT 0,
    negative_count INTEGER DEFAULT 0,
    last_used_at DATETIME,
    PRIMARY KEY (user_id, skill_id),
    INDEX idx_confidence (user_id, confidence_score DESC)
);

-- Thompson Sampling context-skill statistics (contextual bandit)
CREATE TABLE context_skill_stats (
    user_id TEXT NOT NULL,
    context_bucket INTEGER NOT NULL,  -- Hash of (intent + sentiment + time_of_day) % 100
    skill_id TEXT NOT NULL,
    alpha REAL DEFAULT 1.0,  -- Beta distribution success parameter
    beta REAL DEFAULT 1.0,   -- Beta distribution failure parameter
    last_updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (user_id, context_bucket, skill_id),
    INDEX idx_user_context (user_id, context_bucket)
);

-- Context-aware preference vectors (explicit dimensions)
CREATE TABLE context_preference_vectors (
    user_id TEXT NOT NULL,
    context_bucket INTEGER NOT NULL,  -- Hash of (intent + sentiment + time_of_day) % 100
    dimensions TEXT NOT NULL,  -- JSON array: [0.5, 0.7, 0.3, ...] (16 floats)
    last_updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (user_id, context_bucket),
    INDEX idx_user (user_id)
);

-- Retention policy: Archive trajectories older than 90 days
-- Keep trajectories with feedback indefinitely
-- Scheduled cleanup task runs weekly
```

**Preference Vector Structure**:
```python
# Context-aware explicit preference dimensions (NOT embeddings)
# Stored as JSON array in context_preference_vectors table

# Example for user "alice" in context_bucket 42 (technical questions):
preference_vector = [
    0.2,  # verbosity (concise)
    0.8,  # formality (formal)
    0.9,  # technical_depth (very technical)
    0.5,  # proactivity (balanced)
    0.3,  # emotional_expression (neutral)
    0.7,  # structure (structured)
    0.6,  # explanation_depth (moderate detail)
    0.4,  # example_usage (some examples)
    0.5,  # question_asking (balanced)
    0.6,  # reassurance_level (supportive)
    0.7,  # directness (fairly direct)
    0.5,  # enthusiasm (balanced)
    0.6,  # patience (thorough)
    0.4,  # creativity (mostly conventional)
]  # 16 floats, each in [0.0, 1.0] range

# Initialization (cold start):
# New users: all dimensions = 0.5 (neutral)
# After first feedback: move toward/away from skill dimensions

# Update formula (gradient-based):
# direction = reward * learning_rate  # reward: +1 or -1
# pref_new = pref_old + direction * (skill_dims - pref_old)
# Clamp to [0.0, 1.0] range

# Preference matching:
# distance = euclidean_distance(user_pref_vector, skill_dimension_vector)
# score = 1.0 - (distance / max_distance)  # Normalized to [0, 1]
# Used as 30% weight in hybrid skill selection
```

**Trajectory Retention Policy**:
```python
# Retention rules:
# - Keep all trajectories with feedback (feedback_reward != NULL) indefinitely
# - Archive trajectories without feedback after 90 days
# - Hard delete archived trajectories after 365 days
# - Cleanup runs weekly via scheduled task

async def cleanup_trajectories():
    # Archive old trajectories without feedback
    await db.execute("""
        UPDATE trajectories 
        SET archived = TRUE
        WHERE feedback_reward IS NULL 
        AND timestamp < datetime('now', '-90 days')
        AND archived = FALSE
    """)
    
    # Delete very old archived trajectories
    await db.execute("""
        DELETE FROM trajectories
        WHERE archived = TRUE
        AND timestamp < datetime('now', '-365 days')
    """)
```

---

### Integration Specifications

**Message Bus Topics**:
```python
TOPICS = {
    "memory.consolidation.start": "Start consolidation job",
    "memory.consolidation.complete": "Consolidation finished",
    "memory.feedback.received": "User feedback event",
    "memory.feedback.processed": "Feedback classification complete",
    "memory.skill.selected": "Skill selected for response",
    "memory.skill.updated": "Skill confidence updated"
}
```

**API Error Responses** (`POST /api/v1/memory/feedback`):
```python
responses = {
    200: {"status": "success", "skill_updated": True, "new_confidence": 0.75},
    400: {"error": "invalid_reward", "message": "Reward must be -1, 0, or 1"},
    404: {"error": "skill_not_found", "message": "Skill ID does not exist"},
    422: {"error": "validation_error", "message": "Invalid request format"},
    500: {"error": "internal_error", "message": "Failed to update skill"}
}
```

**Skill Application Flow**:
```python
# In conversation_engine.py
async def generate_response(user_input: str, context: dict) -> str:
    # 1. Select skill
    skill = await skill_selector.select(user_input, context)
    
    # 2. Inject into system prompt
    system_prompt = f"{base_system_prompt}\n\n{skill.procedure_template}"
    
    # 3. Generate response
    response = await llm.generate(user_input, system_prompt, context)
    
    # 4. Log usage
    await log_skill_usage(skill.skill_id, user_input, response)
    
    return response
```

---

### Performance & Scaling

**Consolidation Parallelization with User Sharding**:
```python
# User sharding: round-robin 7-day cycle
async def schedule_consolidation():
    """
    Consolidate 1/7 of users each day using round-robin sharding.
    
    This prevents overwhelming the system with large user bases.
    Each user is consolidated once per week.
    """
    users = await get_active_users()
    day_of_week = datetime.now().weekday()  # 0 (Monday) to 6 (Sunday)
    
    # Assign users to days using modulo (ensures even distribution)
    users_today = [u for i, u in enumerate(users) if i % 7 == day_of_week]
    
    logger.info(f"Consolidating {len(users_today)} of {len(users)} users today")
    
    # Max 4 concurrent users to prevent resource exhaustion
    async with asyncio.Semaphore(4):
        await asyncio.gather(*[consolidate_user(u) for u in users_today])
```

**Memory Pressure Handling**:
```python
# LRU eviction: prioritize low-confidence skills regardless of type
if storage_size > max_storage:
    evict_candidates = db.query("""
        SELECT skill_id FROM skills 
        WHERE user_id = ?
        ORDER BY 
            CASE WHEN skill_type = 'base' THEN confidence_score * 1.5 
                 ELSE confidence_score END ASC,
            last_used_at ASC
        LIMIT 10
    """)
    # Base skills get 1.5x confidence boost (harder to evict)
    # But still evictable if confidence very low
    for skill_id in evict_candidates:
        await archive_skill(skill_id)
```

**GPU Usage**:
- **Default**: CPU-only operation (no GPU required)
- **Optional**: GPU provides 10x speedup (100ms → 10ms per embedding)
- **Config**: `modelservice.device: "cuda"` (if available) else `"cpu"`

**Additional Clarifications**:

1. **Skill Matching Threshold**: Skills with hybrid score ≥ 0.5 are considered applicable
2. **Base Skills Mutability**: Base skills are immutable templates; only user-created skills can be modified
3. **Trajectory Archival**: Archived = soft delete (still in DB, not queried); hard delete removes from DB
4. **User-Skill Confidence Init**: Rows created on first skill use with default confidence 0.5
5. **Importance Score**: Average cosine similarity to last 10 user queries
6. **Temporal Decay Application**: Applied during weekly graph evolution task (Sunday 3 AM)
7. **Concurrent Feedback**: Last-write-wins for confidence updates (acceptable for this use case)
8. **Embedding Timing**: 50-100ms is per-embedding; semantic query does 1 embedding + vector search
9. **Schedule Coordination**: Consolidation (2 AM), Feedback batch (4 AM) to avoid resource contention
10. **SumTree Usage**: Only used if replay buffer > 1000 items; simple weighted sampling for smaller buffers

---

## Appendix B: Foundational Research

The architecture described in this document is inspired by several key research papers in the fields of AI agency, reinforcement learning, and meta-learning.

- **Modular AI Architecture**:
  - [Behavioral Learning Is Not All You Need: Bridging Cognitive Gaps in LLM-Based Agents](https://arxiv.org/abs/2505.03434)
  - This paper advocates for augmenting LLMs with modular semantic and associative memory systems, which inspires our skill-based architecture.

- **Personalized Reinforcement Learning**:
  - [Personalizing Reinforcement Learning from Human Feedback with Variational Preference Learning](https://arxiv.org/abs/2408.10075)
  - This work provides the foundation for our multi-user personalization, using latent variables to model diverse user preferences.

- **Meta-Learning for Fast Adaptation**:
  - [Fast Context Adaptation via Meta-Learning (CAVIA)](https://arxiv.org/abs/1810.03642)
  - This paper's approach to partitioning model parameters informs our strategy for rapid adaptation to new users with minimal data.

- **Agent Self-Correction**:
  - [Agent Q: Advanced Reasoning and Learning for Autonomous AI Agents](https://arxiv.org/abs/2408.07199)
  - This research inspires our self-correction and exploration mechanism, particularly the use of statistical learning from successful and unsuccessful interactions.

- **Prioritized Experience Replay**:
  - [Prioritized Experience Replay (Schaul et al., 2015)](https://arxiv.org/abs/1511.05952)
  - Provides the foundation for our replay prioritization algorithm using proportional sampling based on importance scores.
