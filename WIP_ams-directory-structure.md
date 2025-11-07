# AMS Directory Structure

**Date:** 2025-11-07  
**Status:** Phase 1 Complete

## Complete Directory Tree

```
/shared/aico/ai/memory/
├── __init__.py                          # Main memory module (updated with AMS exports)
├── manager.py                           # Memory manager (existing, to be enhanced)
├── working.py                           # Working memory (existing, to be enhanced)
├── semantic.py                          # Semantic memory (existing, to be enhanced)
├── bm25.py                              # BM25 search (existing)
├── fusion.py                            # Result fusion (existing)
├── memory_album.py                      # Memory album (existing)
│
├── context/                             # Context assembly (existing, to be enhanced)
│   ├── __init__.py
│   ├── assembler.py                     # Context assembler (to add temporal ranking)
│   ├── graph_ranking.py                 # Graph-based ranking (existing)
│   ├── models.py                        # Data models (existing)
│   ├── retrievers.py                    # Retrievers (to add temporal queries)
│   └── scorers.py                       # Scorers (to add recency weighting)
│
├── temporal/                            # ✅ NEW - Temporal intelligence
│   ├── __init__.py                      # Module exports (43 lines)
│   ├── metadata.py                      # Temporal metadata structures (272 lines)
│   ├── evolution.py                     # Preference evolution tracking (311 lines)
│   └── queries.py                       # Temporal query support (327 lines)
│
├── consolidation/                       # ✅ NEW - Memory consolidation
│   ├── __init__.py                      # Module exports (47 lines)
│   ├── scheduler.py                     # Consolidation scheduling (298 lines)
│   ├── replay.py                        # Experience replay (378 lines)
│   ├── reconsolidation.py               # Memory reconsolidation (381 lines)
│   └── state.py                         # State tracking (293 lines)
│
├── behavioral/                          # ✅ NEW - Behavioral learning (structure only)
│   └── __init__.py                      # Module exports (68 lines)
│   # To be implemented in Phase 3:
│   # ├── skills.py                      # Skill library management
│   # ├── thompson_sampling.py           # Contextual bandit learning
│   # ├── preferences.py                 # Preference tracking
│   # ├── feedback_classifier.py         # Multilingual feedback classification
│   # ├── rlhf.py                        # RLHF integration
│   # └── templates.py                   # Prompt template management
│
└── unified/                             # ✅ NEW - Unified indexing (structure only)
    └── __init__.py                      # Module exports (39 lines)
    # To be implemented in Phase 4:
    # ├── index.py                        # Cross-layer indexing
    # ├── lifecycle.py                    # Memory lifecycle management
    # └── retrieval.py                    # Unified retrieval interface
```

## File Statistics

### Implemented Files (Phase 1)

| File | Lines | Purpose | Status |
|------|-------|---------|--------|
| **Temporal Module** | | | |
| `temporal/__init__.py` | 43 | Module exports | ✅ Complete |
| `temporal/metadata.py` | 272 | Temporal metadata structures | ✅ Complete |
| `temporal/evolution.py` | 311 | Preference evolution tracking | ✅ Complete |
| `temporal/queries.py` | 327 | Temporal query support | ✅ Complete |
| **Consolidation Module** | | | |
| `consolidation/__init__.py` | 47 | Module exports | ✅ Complete |
| `consolidation/scheduler.py` | 298 | Consolidation scheduling | ✅ Complete |
| `consolidation/replay.py` | 378 | Experience replay | ✅ Complete |
| `consolidation/reconsolidation.py` | 381 | Memory reconsolidation | ✅ Complete |
| `consolidation/state.py` | 293 | State tracking | ✅ Complete |
| **Module Structures** | | | |
| `behavioral/__init__.py` | 68 | Module exports | ✅ Structure |
| `unified/__init__.py` | 39 | Module exports | ✅ Structure |
| `__init__.py` (main) | 41 | Updated with AMS exports | ✅ Complete |
| **Total** | **2,498** | | |

### Existing Files (To Be Enhanced)

| File | Current Lines | Enhancement Needed | Priority |
|------|---------------|-------------------|----------|
| `working.py` | ~290 | Add temporal metadata storage | High |
| `semantic.py` | ~450 | Add temporal tracking | High |
| `context/assembler.py` | ~350 | Add temporal ranking | High |
| `context/retrievers.py` | ~200 | Add temporal queries | Medium |
| `context/scorers.py` | ~100 | Add recency weighting | Medium |
| `manager.py` | ~800 | Add consolidation integration | High |

## Module Responsibilities

### Temporal Module (`temporal/`)
**Purpose:** Temporal intelligence and preference evolution

**Components:**
- `metadata.py`: Temporal metadata structures (TemporalMetadata, EvolutionRecord, etc.)
- `evolution.py`: Preference evolution tracking and trend analysis
- `queries.py`: Time-aware query builders for SQL and ChromaDB

**Key Features:**
- Confidence decay over time
- Preference evolution tracking (16 dimensions)
- Trend detection (linear regression)
- Point-in-time queries
- Future preference prediction

### Consolidation Module (`consolidation/`)
**Purpose:** Brain-inspired memory consolidation

**Components:**
- `scheduler.py`: Idle detection and job scheduling
- `replay.py`: Prioritized experience replay
- `reconsolidation.py`: Conflict resolution and variant management
- `state.py`: State tracking and persistence

**Key Features:**
- 7-day user sharding (1/7 users per day)
- CPU-based idle detection (20% threshold)
- Prioritized sampling (importance + recency + feedback)
- Confidence-weighted conflict resolution
- Max 3 variants per fact with cleanup

### Behavioral Module (`behavioral/`)
**Purpose:** Skill-based interaction learning with RLHF

**Planned Components (Phase 3):**
- `skills.py`: Skill library and selector
- `thompson_sampling.py`: Contextual bandit learning
- `preferences.py`: Context-aware preference vectors (16 dims)
- `feedback_classifier.py`: Multilingual feedback classification
- `rlhf.py`: RLHF integration
- `templates.py`: Prompt template management

**Key Features (Planned):**
- 10-15 base skills (concise, detailed, technical, etc.)
- Thompson Sampling for exploration/exploitation
- 16 explicit preference dimensions per context
- Multilingual feedback classification (50+ languages)
- Thumbs up/down + optional text feedback

### Unified Module (`unified/`)
**Purpose:** Cross-layer memory indexing and retrieval

**Planned Components (Phase 4):**
- `index.py`: Unified indexing across L0/L1/L2
- `lifecycle.py`: Memory lifecycle management
- `retrieval.py`: Unified retrieval interface

**Key Features (Planned):**
- L0 (Raw): Unprocessed conversations
- L1 (Structured): Summaries, profiles, facts
- L2 (Parameterized): Behavioral models, skills
- Cross-layer queries
- Automatic tier transitions

## Integration Points

### With Existing Memory System
```python
# manager.py
from aico.ai.memory import temporal, consolidation

class MemoryManager:
    def __init__(self):
        self.temporal_tracker = temporal.EvolutionTracker()
        self.consolidation_scheduler = consolidation.ConsolidationScheduler()
```

### With Backend Scheduler
```python
# /backend/scheduler/tasks/ams_consolidation.py
from aico.ai.memory.consolidation import ConsolidationScheduler

class MemoryConsolidationTask(BaseTask):
    task_id = "ams.consolidation.daily"
    schedule = "0 2 * * *"  # 2 AM daily
```

### With Context Assembly
```python
# context/assembler.py
from aico.ai.memory.temporal import TemporalQueryBuilder

class ContextAssembler:
    def assemble_context(self, user_id, query):
        # Add temporal ranking
        temporal_query = TemporalQueryBuilder()
            .for_user(user_id)
            .last_n_days(30)
            .min_confidence(0.5)
            .build_chromadb_filter()
```

## Database Schema Additions

### Temporal Metadata (JSON columns)
```sql
-- Add to existing tables
ALTER TABLE semantic_facts ADD COLUMN temporal_metadata TEXT;  -- JSON
ALTER TABLE working_memory ADD COLUMN temporal_metadata TEXT;  -- JSON

-- Example temporal_metadata JSON:
{
  "created_at": "2025-11-07T18:00:00Z",
  "last_updated": "2025-11-07T18:30:00Z",
  "last_accessed": "2025-11-07T19:00:00Z",
  "access_count": 5,
  "confidence": 0.85,
  "version": 2,
  "superseded_by": null
}
```

### Consolidation State
```sql
CREATE TABLE consolidation_state (
    id TEXT PRIMARY KEY,
    state_json TEXT NOT NULL,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

### Behavioral Learning (Phase 3)
```sql
-- Skills table
CREATE TABLE skills (
    skill_id TEXT PRIMARY KEY,
    skill_name TEXT NOT NULL,
    skill_type TEXT NOT NULL,
    trigger_context TEXT NOT NULL,  -- JSON
    procedure_template TEXT NOT NULL,
    dimensions TEXT NOT NULL,  -- JSON: [0.5, 0.7, ...] (16 floats)
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- User-skill confidence
CREATE TABLE user_skill_confidence (
    user_id TEXT NOT NULL,
    skill_id TEXT NOT NULL,
    confidence_score REAL DEFAULT 0.5,
    usage_count INTEGER DEFAULT 0,
    positive_count INTEGER DEFAULT 0,
    negative_count INTEGER DEFAULT 0,
    last_used_at DATETIME,
    PRIMARY KEY (user_id, skill_id)
);

-- Context-skill statistics (Thompson Sampling)
CREATE TABLE context_skill_stats (
    user_id TEXT NOT NULL,
    context_bucket INTEGER NOT NULL,
    skill_id TEXT NOT NULL,
    alpha REAL DEFAULT 1.0,
    beta REAL DEFAULT 1.0,
    last_updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (user_id, context_bucket, skill_id)
);

-- Context-aware preference vectors
CREATE TABLE context_preference_vectors (
    user_id TEXT NOT NULL,
    context_bucket INTEGER NOT NULL,
    dimensions TEXT NOT NULL,  -- JSON: [0.5, 0.7, ...] (16 floats)
    last_updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (user_id, context_bucket)
);

-- Feedback events
CREATE TABLE feedback_events (
    event_id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    message_id TEXT NOT NULL,
    skill_id TEXT,
    reward INTEGER NOT NULL,
    reason TEXT,
    free_text TEXT,
    classified_categories TEXT,  -- JSON
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    processed BOOLEAN DEFAULT FALSE
);

-- Trajectories
CREATE TABLE trajectories (
    trajectory_id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    conversation_id TEXT NOT NULL,
    turn_number INTEGER NOT NULL,
    user_input TEXT NOT NULL,
    selected_skill_id TEXT,
    ai_response TEXT NOT NULL,
    feedback_reward INTEGER,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    archived BOOLEAN DEFAULT FALSE
);
```

## Configuration Additions

### To Add to `/config/defaults/core.yaml`

```yaml
memory:
  # ... existing working and semantic config ...
  
  # Temporal intelligence
  temporal:
    enabled: true
    metadata_retention_days: 365
    evolution_tracking: true
    confidence_decay_rate: 0.001  # Per day without access
    max_fact_variants: 3
    variant_cleanup_days: 90
  
  # Memory consolidation
  consolidation:
    enabled: true
    schedule: "0 2 * * *"  # 2 AM daily
    user_sharding_cycle_days: 7
    max_concurrent_users: 4
    max_duration_minutes: 60
    replay_batch_size: 100
    priority_alpha: 0.6
    idle_detection:
      cpu_threshold_percent: 20
      idle_duration_seconds: 300
      check_interval_seconds: 60
  
  # Behavioral learning (Phase 3)
  behavioral:
    enabled: true
    learning_rate: 0.1
    exploration_rate: 0.1
    max_skills_per_user: 100
    skill_selection_timeout_ms: 10
    min_confidence_threshold: 0.3
    preference_vector_dim: 16
    num_context_buckets: 100
    feedback_classifier:
      similarity_threshold: 0.6
      embedding_model: "paraphrase-multilingual-mpnet-base-v2"
    contextual_bandit:
      enabled: true
      algorithm: "thompson_sampling"
      update_interval_hours: 24
      min_trajectories: 10
      prior_alpha: 1.0
      prior_beta: 1.0
    trajectory_logging:
      enabled: true
      retention_days: 90
      hard_delete_days: 365
      keep_feedback_indefinitely: true
```

## Next Steps

1. **Write unit tests** for temporal and consolidation modules
2. **Enhance existing modules** with temporal support
3. **Update database schemas** with temporal columns
4. **Add configuration sections** to core.yaml
5. **Integration testing** with existing memory system
6. **Phase 3 implementation** (Behavioral Learning)
7. **Phase 4 implementation** (Unified Indexing)

---

**Status:** Foundation complete. Ready for integration and testing.
