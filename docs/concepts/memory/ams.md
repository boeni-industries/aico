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

**Storage Footprint**: ~90KB per user (75% increase from 50KB baseline)
- Temporal metadata: ~10KB
- Knowledge graphs: ~15KB
- Consolidation buffers: ~12KB
- Behavioral patterns: ~8KB

**Performance**: 
- Context assembly: <50ms (multi-tier retrieval)
- Consolidation: 5-10 min/day per user (background)
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
- **Model**: `paraphrase-multilingual-MiniLM-L12-v2` (default)
- **Purpose**: Generate embeddings for semantic search
- **Memory**: ~500MB model size
- **Compute**: ~50-100ms per embedding (CPU), ~10-20ms (GPU)
- **Usage**: Every semantic query, fact storage, context retrieval

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

**6. RLHF Implementation** (Custom Lightweight)
- **Library**: Custom Python implementation in `behavioral/rlhf.py` (no external RL framework)
- **Algorithm**: Simplified DPO with direct feedback signals
- **Memory**: Minimal (~10-20MB)
- **Compute**: 5-10ms per feedback, 5-10 min batch refinement/day
- **Rationale**: 
  - Learning prompt template **selection**, not LLM weight updates
  - No neural network training required (confidence scores only)
  - Privacy-preserving, local-only processing
  - Sufficient for use case (guiding existing LLM vs. training new model)
- **Future Options**: TRL library for adapter fine-tuning (if needed)

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
- **Compute Time**: 5-15ms
  - Skill matching: 2-5ms (pattern matching)
  - Preference lookup: 1-3ms (libSQL)
  - Template application: 2-7ms (string operations)
- **Memory Impact**: Minimal (~5-10MB)
- **Frequency**: Every AI response generation

#### Background Operations (Non-Blocking)

**Memory Consolidation** (scheduled via AICO Scheduler)
- **Trigger**: System idle detection OR scheduled (e.g., "0 2 * * *" = 2 AM daily)
- **Components**: Experience replay + Semantic storage + Graph updates
- **Compute Time**: 5-10 minutes per user (estimated)
  - Experience selection: 30-60s (working memory scan)
  - Embedding generation: 2-5 min (batch processing)
  - Semantic storage: 1-2 min (ChromaDB batch insert)
  - Graph updates: 1-2 min (entity resolution + storage)
- **Memory Impact**: +200-400MB peak during consolidation
- **Frequency**: Once per day per user (configurable)
- **Parallelization**: Process users sequentially to limit resource usage

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
- **Trigger**: User feedback (immediate) + Batch refinement (daily)
- **Components**: RLHF processing + Skill confidence updates
- **Compute Time**: 
  - Per feedback: 5-10ms (immediate confidence update)
  - Batch refinement: 5-10 min/day (DPO template optimization)
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
# 1. Daily Memory Consolidation (2 AM, idle-aware)
{
    "task_id": "ams.consolidation.daily",
    "schedule": "0 2 * * *",  # 2 AM daily
    "enabled": True,
    "config": {
        "require_idle": True,
        "max_duration_minutes": 30,
        "users_per_batch": 5
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

**Scaling Considerations**:
- **10 users**: ~1GB total memory, <5 min consolidation/day
- **50 users**: ~3GB total memory, ~20 min consolidation/day
- **100 users**: ~5GB total memory, ~40 min consolidation/day
- **500 users**: ~20GB total memory, ~3 hours consolidation/day (needs optimization)

**For Large Deployments** (>100 users):
- Implement user sharding (consolidate different users on different days)
- Use GPU for embedding generation (10x speedup)
- Implement distributed consolidation (multiple workers)
- Add consolidation priority (active users first)

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

### 2. Meta-Learning for Rapid Adaptation

To quickly adapt to new users or changing preferences, AICO uses a meta-learning approach. It learns *how to learn* interaction styles, rather than starting from scratch with each user.

#### Conceptual Model

- **How it Works**: The model's parameters are split into two parts:
    1. **Shared Parameters**: Capture general principles of good interaction, trained across all users.
    2. **Context Parameters**: A small, user-specific set of parameters that are quickly updated based on a few interactions.
- **Benefit**: This allows for extremely fast personalization and reduces the amount of data needed to learn a new user's preferences.

#### Implementation Details

**User Preference Vectors** (`shared/aico/ai/memory/user_preferences.py`):
- Each user has a latent preference vector (16-32 dimensions) stored in the database
- Vector initialized with defaults and updated based on feedback patterns
- Encodes preferences: formality, verbosity, proactivity tolerance, emotional expression style

**Skill Matching Algorithm**:
- Retrieves user's preference vector
- Queries skills matching the current context
- Scores each skill: 70% confidence score + 30% preference alignment (cosine similarity)
- Returns highest scoring skill

### 3. Self-Correction and Exploration (Agent Q Model)

AICO actively refines its skills by learning from both its successes and failures.

#### Conceptual Model

- **Exploration**: Occasionally, AICO will try a slightly different interaction style and ask for feedback (e.g., "I usually use bullet points, but would a paragraph be better here?"). This is a form of active learning to discover better procedures.
- **Self-Critique**: When an interaction receives negative feedback, the system logs it as an "unsuccessful trajectory."
- **Preference Optimization**: Using an algorithm like Direct Preference Optimization (DPO), the system learns to prefer successful interaction patterns over unsuccessful ones. This explicitly teaches the model what *not* to do, leading to more robust and reliable behavior.

#### Implementation Details

**Exploration Strategy** (`shared/aico/ai/memory/exploration.py`):
- With probability ε (e.g., 0.1), select lower-confidence skills for exploration
- Explicitly request user feedback on new approaches
- Track exploration outcomes separately to measure learning effectiveness

**Trajectory Logging** (`backend/services/trajectory_logger.py`):
- Log each conversation turn: user input, selected skill, AI response, user feedback
- Store successful (positive feedback) and unsuccessful (negative feedback) trajectories
- Use trajectories for offline learning and skill refinement

**Preference Optimization** (Phase 3 implementation):
- Batch process analyzes trajectories periodically
- Uses DPO algorithm to update skill templates based on preference pairs
- Increases likelihood of preferred patterns, decreases dispreferred ones

---

## Data Model & Storage

### Database Schema (`shared/aico/data/schemas/behavioral.py`)

**Skills Table**:
- Primary key: skill_id
- Fields: user_id, skill_name, skill_type (base/learned/user_created), trigger_context (JSON), procedure_template, confidence_score (default 0.5), preference_profile (JSON latent vector), usage counters, timestamps
- Indices: user_id, confidence_score (descending)

**User Preferences Table**:
- Primary key: user_id
- Fields: preference_vector (JSON latent vector), learning_rate (default 0.1), exploration_rate (default 0.1), last_updated_timestamp

**Feedback Events Table**:
- Primary key: event_id
- Fields: user_id, message_id, skill_id, reward (-1/0/1), timestamp
- Indices: user_id, skill_id

### Python Data Classes (`shared/aico/ai/memory/behavioral.py`)

**Skill**: Pydantic model with skill_id, user_id, skill_name, skill_type, trigger_context, procedure_template, confidence_score, preference_profile, usage counters, timestamps

**UserPreferences**: Pydantic model with user_id, preference_vector, learning_rate, exploration_rate, last_updated_timestamp

**FeedbackEvent**: Pydantic model with event_id, user_id, message_id, skill_id, reward, timestamp

---

## Implementation Strategy

The behavioral learning system will be implemented as a complete, integrated solution with all components working together from the start. This approach ensures consistency and avoids technical debt from incremental builds.

### Core Implementation Components

**1. Data Layer**
- Database schema for `skills`, `user_preferences`, and `feedback_events` tables
- ChromaDB collection for skill embeddings (`behavioral_skills`)
- Python data classes (`Skill`, `UserPreferences`, `FeedbackEvent`)
- `SkillStore` class with CRUD operations and vector search integration

**2. Learning System**
- Real-time feedback processing via `POST /api/v1/memory/feedback` endpoint
- Confidence score updates using weighted learning
- User preference vector management with embedding-based updates
- Trajectory logging for successful/unsuccessful interactions

**3. Skill Selection Engine**
- Context extraction using existing NLP models (intent, entities, sentiment)
- Hybrid skill matching: confidence score + preference alignment
- ChromaDB vector search for similar skills
- Exploration strategy (ε-greedy) for discovering new patterns

**4. DPO Template Refinement Pipeline**
- Offline batch process (scheduled task, runs daily)
- Trajectory dataset preparation (preferred vs. dispreferred pairs)
- DPO-based template generation using TRL library
- Skill template updates in database (no model training)
- Performance metrics logging

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

**Weeks 1-2**: Database schema, SkillStore, ChromaDB collection, base skills  
**Weeks 3-4**: Feedback API, UI components, confidence updates, skill selection  
**Weeks 5-6**: Preference vectors, context extraction, trajectory logging  
**Weeks 7-8**: DPO pipeline, exploration strategy, metrics dashboard

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

#### 1. **Embedding Models** (for Preference Vector Similarity)

**Purpose**: Generate and compare user preference vectors for skill matching.

**Model**: **REUSE EXISTING** - `sentence-transformers/paraphrase-multilingual-mpnet-base-v2`
- Already configured in `core.yaml` at `modelservice.transformers.models.embeddings`
- Already managed by `TransformersManager` in modelservice
- 768 dimensions (same as semantic memory for consistency)
- Multilingual support
- Already loaded in memory for semantic memory operations

**Why Reuse**: This model is already running for semantic memory. Using the same model for preference vectors:
- Eliminates additional memory overhead (~500MB saved)
- Ensures consistency across memory systems
- Leverages existing model management infrastructure
- No additional downloads or configuration needed

**Implementation**:
```python
from modelservice.core.transformers_manager import TransformersManager

# Use existing TransformersManager instance
embeddings_model = transformers_manager.get_model("embeddings")
preference_embedding = embeddings_model.encode(user_preference_description)
```

#### 2. **Reinforcement Learning Framework**

**Purpose**: Implement RLHF feedback loops with DPO (Direct Preference Optimization).

**Library**: **TRL (Transformer Reinforcement Learning)** by Hugging Face
- Provides production-ready DPO implementation
- Use case: Refine prompt templates based on successful vs. unsuccessful trajectories
- Runs offline as scheduled task (daily)
- Library: `trl>=0.7.0` (add to `pyproject.toml` under `[project.optional-dependencies.backend]`)

**Clarification**: DPO refines **prompt templates** (not model weights). Analyzes feedback trajectories to generate improved templates. Runs offline daily, fully reversible, storage-efficient.

**Implementation** (`backend/scheduler/tasks/dpo_refinement.py`):
```python
"""
DPO Template Refinement Task

Scheduled task that refines behavioral learning skill templates using
Direct Preference Optimization (DPO) based on user feedback trajectories.

Follows AICO's message-driven architecture and privacy-by-design principles.
"""

from trl import DPOTrainer, DPOConfig
from transformers import AutoModelForCausalLM, AutoTokenizer
from aico.ai.memory.procedural import SkillStore, TrajectoryStore
from aico.core.logging import get_logger

logger = get_logger("backend", "scheduler.dpo_refinement")

async def refine_skill_templates():
    """
    Refine prompt templates using DPO based on user feedback trajectories.
    
    This task runs daily as a scheduled job. It analyzes recent user feedback
    to generate improved prompt templates that maximize user satisfaction.
    
    Privacy: All data is local and encrypted. No external API calls.
    """
    
    # Load trajectories from last 24 hours
    trajectory_store = TrajectoryStore()
    trajectories = await trajectory_store.get_recent_trajectories(hours=24)
    
    if len(trajectories) < 10:  # Need minimum data
        logger.info("Insufficient trajectories for DPO refinement")
        return
    
    # Prepare preference pairs
    preferred = [t for t in trajectories if t.feedback_reward > 0]
    dispreferred = [t for t in trajectories if t.feedback_reward < 0]
    
    # Use DPO to generate improved prompt templates
    # (This uses the model to analyze patterns, not to train it)
    improved_templates = await generate_improved_templates(
        preferred_examples=preferred,
        dispreferred_examples=dispreferred
    )
    
    # Update skill templates in database
    skill_store = SkillStore()
    for skill_id, new_template in improved_templates.items():
        await skill_store.update_skill_template(skill_id, new_template)
    
    logger.info(
        "DPO template refinement completed",
        extra={
            "trajectories_analyzed": len(trajectories),
            "templates_updated": len(improved_templates),
            "metric_type": "behavioral_memory_dpo"
        }
    )
```

#### 3. **Meta-Learning Framework**

**Purpose**: Implement rapid adaptation to new users with minimal data.

**Approach**: **Lightweight custom implementation** using existing infrastructure
- Store user-specific preference vectors (768-dim, matching embedding model)
- Use cosine similarity for preference alignment
- No separate neural network needed - leverage existing embedding space

**Why Lightweight**: Uses preference vectors (768-dim) + text templates instead of neural network training. Simple vector math, <10ms selection, interpretable, ~10-50KB per user.

**Implementation** (`aico/ai/memory/procedural/preferences.py`):
```python
"""
User Preference Management

Manages user-specific preference vectors in embedding space for rapid
adaptation and personalization. Part of AICO's behavioral learning system.

Follows AICO's privacy-by-design: all data stored locally and encrypted.
"""

import numpy as np
from scipy.spatial.distance import cosine
from aico.core.logging import get_logger

logger = get_logger("backend", "memory.procedural.preferences")

class UserPreferenceManager:
    """
    Manages user preference vectors for behavioral learning personalization.
    
    Preference vectors are stored in the same 768-dimensional space as the
    embedding model, enabling fast similarity-based skill matching.
    
    Attributes:
        embedding_dim: Dimension of preference vectors (must match embedding model)
    """
    
    def __init__(self, embedding_dim=768):
        self.embedding_dim = embedding_dim
        
    def initialize_user_preferences(self, user_id: str) -> np.ndarray:
        """Initialize with neutral preference vector."""
        return np.zeros(self.embedding_dim)
    
    def update_preferences(self, user_prefs: np.ndarray, 
                          skill_embedding: np.ndarray, 
                          reward: float, 
                          learning_rate: float = 0.1) -> np.ndarray:
        """Update user preferences based on feedback."""
        # Move preference vector toward/away from skill embedding
        update = learning_rate * reward * skill_embedding
        new_prefs = user_prefs + update
        # Normalize to unit vector
        return new_prefs / (np.linalg.norm(new_prefs) + 1e-8)
    
    def compute_preference_alignment(self, user_prefs: np.ndarray, 
                                     skill_embedding: np.ndarray) -> float:
        """Compute how well a skill aligns with user preferences."""
        return 1 - cosine(user_prefs, skill_embedding)
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

#### 5. **Vector Similarity Search**

**Purpose**: Fast nearest-neighbor search for skill matching.

**Library**: **REUSE EXISTING** - **ChromaDB**
- Already configured in `core.yaml` for semantic memory at `memory.semantic`
- Already running for conversation segment retrieval
- Use case: Store skill embeddings for fast similarity-based retrieval
- Advantages: Local-first, persistent, optimized for similarity search
- Library: `chromadb` (Python)

**Why Reuse**: ChromaDB is already managing conversation embeddings. We can add a new collection for skill embeddings:
- Reuses existing ChromaDB instance (no additional process)
- Consistent vector search across memory systems
- Optimized for similarity queries (faster than NumPy for >100 skills)
- Already integrated with the embedding model

**Implementation**:
```python
# Add new collection to existing ChromaDB instance
skill_collection = chroma_client.create_collection(
    name="behavioral_skills",
    embedding_function=embeddings_model,  # Reuse existing embedding model
    metadata={"hnsw:space": "cosine"}
)

# Query similar skills
results = skill_collection.query(
    query_texts=[user_preference_description],
    n_results=10,
    where={"user_id": user_id}
)
```

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
    
    # Preference vectors (must match embedding model dimensions)
    preference_vector_dim: 768  # Matches paraphrase-multilingual-mpnet-base-v2
    
    # Feedback processing (server-side)
    feedback:
      free_text_max_chars: 300  # Maximum length for free text feedback
      # Note: UI options (dropdown choices, button styles) are defined client-side in Flutter app
    
    # DPO template refinement (offline batch process)
    dpo:
      enabled: true
      batch_size: 4
      learning_rate: 5e-7
      beta: 0.1  # KL penalty coefficient
      max_length: 512
      training_interval_hours: 24  # Run template refinement daily
      min_trajectories: 10  # Minimum trajectories needed to run refinement
    
    # Trajectory logging for learning
    trajectory_logging:
      enabled: true
      max_trajectory_length: 20  # Number of turns to store per trajectory
      retention_days: 90  # Keep trajectories for 3 months
    
    # ChromaDB collection for skill embeddings
    chroma:
      collection_name: "behavioral_skills"  # Separate collection from conversation_segments
      distance_metric: "cosine"  # Same as semantic memory
    
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
| **Embeddings** | `paraphrase-multilingual-mpnet-base-v2` | ✅ Existing | Preference vectors, skill embeddings |
| **Intent Classification** | `xlm-roberta-base` | ✅ Existing | Context extraction |
| **Entity Extraction** | `gliner_medium-v2.1` | ✅ Existing | Topic/subject detection |
| **Sentiment Analysis** | `bert-base-multilingual-uncased-sentiment` | ✅ Existing | Emotional context |
| **Vector Store** | ChromaDB | ✅ Existing | Skill similarity search |
| **Database** | libSQL | ✅ Existing | Skill/preference storage |
| **RLHF/DPO** | TRL (Hugging Face) | ➕ New | Preference optimization |
| **Logging** | ZeroMQ message bus | ✅ Existing | Unified logging |
| **Config** | YAML | ✅ Existing | Configuration management |
| **Validation** | Pydantic v2 | ✅ Existing | Data validation |
| **Numerical** | NumPy, SciPy | ✅ Existing | Vector operations |
| **Frontend** | Flutter/Dart | ✅ Existing | Feedback UI |
| **Testing** | pytest | ✅ Existing | Unit/integration tests |

### New Dependencies

**Only ONE new dependency required:**

**Add to `pyproject.toml`** under `[project.optional-dependencies.backend]`:
```toml
[project.optional-dependencies]
backend = [
    "duckdb>=1.3.2",
    "fastapi>=0.116.1",
    "httpx>=0.28.1",
    "libsql==0.1.8",
    "pydantic>=2.11.7",
    "pyjwt>=2.10.1",
    "uvicorn>=0.35.0",
    "trl>=0.7.0",  # ADD THIS: Transformer Reinforcement Learning for DPO template refinement
]
```

**Installation with UV**:
```bash
# Install backend dependencies including behavioral learning
uv pip install -e ".[backend]"

# Or install all optional dependencies
uv pip install -e ".[backend,modelservice,cli,test]"
```

**All other dependencies are already present in AICO.**

### Resource Requirements

**Disk Space**:
- No additional models to download (all models already in use)
- Per-user skill storage: <1MB (target: 100 skills × ~10KB each)
- Trajectory logs: ~5-10MB per user per month

**Memory**:
- No additional runtime memory (reusing existing models)
- DPO training (offline): ~2-4GB during batch training (runs daily, not real-time)

**Compute**:
- Skill selection: <10ms (vector similarity lookup in ChromaDB)
- Context extraction: ~20-30ms (already happening for conversations)
- Feedback processing: <5ms (simple confidence update)
- DPO training: Runs offline as scheduled task (not user-facing)

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
- **Privacy-preserving**: DPO uses aggregated patterns, not raw messages

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

### DPO Template Refinement Metrics

**Logged after each batch refinement** (`metric_type: "behavioral_memory_dpo"`):
```python
logger.info("DPO template refinement completed", extra={
    "trajectories_analyzed": len(trajectories),
    "preferred_count": len(preferred),
    "dispreferred_count": len(dispreferred),
    "templates_updated": len(improved_templates),
    "avg_confidence_improvement": avg_improvement,
    "refinement_duration_seconds": duration,
    "metric_type": "behavioral_memory_dpo"
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

## Appendix: Foundational Research

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
  - This research inspires our self-correction and exploration mechanism, particularly the use of preference optimization (like DPO) to learn from both successful and unsuccessful interactions.
