---
title: Agency Component – Self-Reflection & Self-Model
---

# Self-Reflection & Self-Model

## 1. Purpose

Self-Reflection gives AICO a **model of itself over time**: what it tried, how it behaved, what worked, and what should change. It runs periodically (often during Lifecycle SLEEP_LIKE phases or low-activity windows) to:

- analyse past behaviour and outcomes across conversations, tasks, and emotional episodes,  
- extract **lessons and patterns** ("this strategy works well", "this tends to fail or annoy"),  
- propose **small, explainable adaptations** to:
  - goal/plan selection heuristics,  
  - skill/strategy preferences,  
  - curiosity focus,  
  - personality/style parameters,
- and record these lessons as memories so other components can inspect and rely on them.

It is intentionally conservative: Self-Reflection adjusts **parameters and preferences**, not core values or safety policies (those remain owned by Values & Ethics).

## 2. Responsibilities (Conceptual)

- Maintain a **self-model** of capabilities, limits, and recent behavior patterns.
- Periodically run **reflection tasks** (often during sleep-like phases) over:
  - actions taken and their outcomes,
  - user feedback and emotional trajectories,
  - goal completion/drop patterns and World Model hypotheses/conflicts,
  - agency metrics (see `agency-metrics.md`, e.g., curiosity outcomes, conflicts resolved, blocked actions).
- Extract **lessons and adjustments** (e.g., "speak less during high-stress episodes", "check in earlier when pattern X appears").
- Feed these lessons back into: skill selection metadata, planning templates, Goal Arbiter weights, curiosity focus, personality/expression parameters, and (optionally, if enabled) **policy rule suggestions or amendments** for Values & Ethics.

## 3. Integration Points

**Reads from:**
- `ams_behavioral_feedback` - Skill execution outcomes and performance metrics
- `agency_goals` - Goal lifecycle and completion patterns (including curiosity-driven goals)
- `feedback_events` - User satisfaction ratings and feedback
- `emotion_history` - User emotional trajectories (valence, arousal, stress patterns)
- `user_relationships` - Social relationship data (closeness, interaction frequency)

**Writes to:**
- `agency_lessons` - Behavioral lessons and improvement suggestions
- `agency_self_model` - Performance tracking for skills and goal types
- `agency_reflection_runs` - Audit trail of reflection job execution
- Knowledge Graph - Self-model facts and lesson provenance edges
- Memory/AMS - Lessons as queryable MemoryItems
- (When applied) Skill metadata, planner templates, arbiter weights, persona configuration

**Collaborates with:**
- `LessonApplicationService` - Applies lessons to system configuration
- `LessonMemoryProjector` - Projects lessons to Memory/AMS and Knowledge Graph
- `BehavioralFeedbackService` - Consumes performance data
- `WorldModelService` - Links lessons to hypotheses, queries self-assessment
- `ContextAssembler` - Provides lessons to conversation context
- Goal Arbiter - Adjusts goal prioritization based on lessons
- Values & Ethics - Policy suggestions (observe_only mode) or amendments (allow_amend mode)

## 4. Policy Interaction Modes

Self-Reflection interacts with Values & Ethics in **two modes**, controlled by configuration (e.g. `core.agency.self_reflection.policy_mode` in `core.yaml`):

- `observe_only` (default / safest)
  - Self-Reflection:
    - Analyses behaviour against current policies
    - Creates lessons in `agency_lessons` with `lesson_type = "policy_suggestion"`, describing potential improvements
    - **Does not** change any `PolicyRule` rows or ValueProfiles
    - Lessons remain in `status = "active"` for review
  - Values & Ethics (or a separate policy-authoring UI/process) may later review these lessons and manually apply them as rule changes

- `allow_amend` (config-gated, advanced)
  - When explicitly enabled, Self-Reflection may propose and apply **small, local amendments** to Values & Ethics **through the Values & Ethics service**, never by writing policy tables directly.
  - Typical allowed changes (subject to future refinement):
    - tuning numeric thresholds and weights inside existing rules,
    - adjusting rule priorities or soft caps,
    - adding narrowly-scoped allow/deny exceptions where the high-level value direction is unchanged.
  - Structural changes (e.g. adding entirely new value dimensions, deleting whole policy families) remain out of scope and must go through a separate policy-authoring path.

In both modes, every suggestion or amendment must be fully **auditable and explainable** (see Persistence below).

## 5. Persistence and Audit for Self-Reflection Outputs

Self-Reflection uses **dedicated tables** for performance and clarity, separate from the user-curated `user_memories` table. This design choice prioritizes query performance, type safety, and clear separation between user semantic memories and system performance metrics.

### 5.1 Dedicated Reflection Tables

The implementation uses three dedicated tables in the `agency` schema (see Schema Version 24 in `core.py`):

#### 5.1.1 `agency_lessons` Table

Stores behavioral lessons generated from self-reflection analysis:

```sql
CREATE TABLE IF NOT EXISTS agency_lessons (
    lesson_id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    
    -- Lesson classification
    lesson_type TEXT NOT NULL,  -- skill_tuning, planner_heuristic, curiosity_focus, persona_style, policy_suggestion
    target_kind TEXT NOT NULL,  -- skill, planner_template, arbiter_weight, curiosity_policy, persona_trait, policy_rule
    target_id TEXT,             -- ID of the target entity (skill_id, policy_rule_id, etc.)
    
    -- Human-readable summary
    summary_text TEXT NOT NULL,
    
    -- Structured change proposal (JSON)
    proposed_change TEXT NOT NULL,  -- JSON: {change_type, field, old, new, notes}
    
    -- Evidence and confidence
    confidence REAL NOT NULL,       -- 0.0 to 1.0
    metrics_basis TEXT,             -- JSON: {time_span, sample_size, outcome_counts, etc.}
    
    -- Scope and status
    scope TEXT NOT NULL,            -- this_user, global_default
    status TEXT NOT NULL,           -- active, superseded, rejected
    superseded_by TEXT,             -- lesson_id that replaced this one
    
    -- Application tracking
    applied_at TIMESTAMP,           -- When the lesson was applied
    applied_by TEXT,                -- Component that applied it
    
    -- Provenance
    source_reflection_run_id TEXT,
    evidence_window_start TIMESTAMP,
    evidence_window_end TIMESTAMP,
    
    -- Links to related entities
    related_goal_ids TEXT,         -- JSON array
    related_trajectory_ids TEXT,   -- JSON array
    related_event_ids TEXT,        -- JSON array
    
    -- Audit trail
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (user_id) REFERENCES users(uuid) ON DELETE CASCADE,
    FOREIGN KEY (superseded_by) REFERENCES agency_lessons(lesson_id) ON DELETE SET NULL
)
```

#### 5.1.2 `agency_self_model` Table

Tracks performance metrics for skills, goal types, and interaction patterns:

```sql
CREATE TABLE IF NOT EXISTS agency_self_model (
    model_id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    
    -- What this tracks
    entity_type TEXT NOT NULL,     -- skill, goal_type, interaction_pattern
    entity_id TEXT NOT NULL,       -- Specific skill_id, goal type name, etc.
    
    -- Performance metrics (JSON)
    performance_summary TEXT NOT NULL,  -- JSON: {success_rate, avg_duration, user_satisfaction, etc.}
    
    -- Temporal scope
    window_start TIMESTAMP NOT NULL,
    window_end TIMESTAMP NOT NULL,
    sample_size INTEGER NOT NULL,
    
    -- Confidence and freshness
    confidence REAL NOT NULL,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Metadata
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (user_id) REFERENCES users(uuid) ON DELETE CASCADE,
    UNIQUE(user_id, entity_type, entity_id, window_start)
)
```

#### 5.1.3 `agency_reflection_runs` Table

Audit trail for reflection job execution:

```sql
CREATE TABLE IF NOT EXISTS agency_reflection_runs (
    run_id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    
    -- Run metadata
    run_type TEXT NOT NULL,        -- scheduled, triggered, manual
    trigger_reason TEXT,           -- sleep_phase, goal_completion, user_request, etc.
    
    -- Analysis scope
    analysis_window_start TIMESTAMP NOT NULL,
    analysis_window_end TIMESTAMP NOT NULL,
    
    -- Results
    lessons_generated INTEGER DEFAULT 0,
    lessons_applied INTEGER DEFAULT 0,
    
    -- Timing
    started_at TIMESTAMP NOT NULL,
    completed_at TIMESTAMP,
    duration_seconds REAL,
    
    -- Status
    status TEXT NOT NULL,          -- running, completed, failed
    error_message TEXT,
    
    -- Metadata
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (user_id) REFERENCES users(uuid) ON DELETE CASCADE
)
```

### 5.2 Enumerated Field Values

The following fields use these exact string values:

- `lesson_type`
  - `"skill_tuning"`
  - `"planner_heuristic"`
  - `"curiosity_focus"`
  - `"persona_style"`
  - `"policy_suggestion"`

- `target_kind`
  - `"skill"`
  - `"planner_template"`
  - `"arbiter_weight"`
  - `"curiosity_policy"`
  - `"persona_trait"`
  - `"policy_rule"`

- `proposed_change.change_type`
  - `"threshold_tweak"`
  - `"weight_tweak"`
  - `"exception_add"`
  - `"exception_remove"`
  - `"template_update"`

- `scope`
  - `"this_user"`
  - `"global_default"`

- `status`
  - `"active"`
  - `"superseded"`
  - `"rejected"`

### 5.3 Data Sources for Reflection Analysis

The reflection engine analyzes performance data from dedicated behavioral tracking tables:

#### 5.3.1 `ams_behavioral_feedback` Table

**Purpose:** Tracks skill execution outcomes and performance metrics  
**Populated by:** `BehavioralFeedbackService` (automatic during skill execution)  
**Used for:** Skill performance analysis, success rate calculations

**Key fields:**
- `skill_id` - Which skill was executed
- `outcome` - success, failure, timeout, error, partial
- `reward` - Reward signal (-1, 0, 1)
- `execution_time_ms` - Performance timing
- `user_satisfaction` - Optional user satisfaction score

**Analysis:** `_analyze_skill_performance()` queries this table to:
- Calculate success rates per skill
- Identify poorly performing skills (< 50% success)
- Generate lessons to adjust skill selection weights
- Update self-model performance tracking

#### 5.3.2 `agency_goals` Table

**Purpose:** Tracks goal lifecycle and completion patterns  
**Populated by:** Goal management system  
**Used for:** Goal pattern analysis, completion/retirement rates

**Analysis:** `_analyze_goal_patterns()` queries this table to:
- Calculate completion rates per goal type
- Identify frequently retired goal types (> 50% retirement)
- Generate lessons to adjust goal arbiter weights
- Optimize goal prioritization

#### 5.3.3 `ams_behavioral_feedback` Table (User Feedback)

**Purpose:** Tracks explicit user feedback and ratings (thumbs up/down)  
**Populated by:** User feedback system via `/api/v1/behavioral/feedback`  
**Used for:** Immediate skill confidence updates and persona/style adjustments

**Key fields:**
- `feedback_id` - Unique feedback event ID
- `reward` - User rating: 1 (thumbs up), -1 (thumbs down), 0 (neutral)
- `reason` - Optional dropdown category (e.g., "incorrect_info", "wrong_tone")
- `free_text` - Optional user-provided detailed feedback (max 300 chars)
- `skill_id` - Which skill was used (if known)

**Current Usage:**
- `reason` field is analyzed for pattern detection
- Immediate skill confidence updates via `SkillStore.update_confidence()`

**TODO - Future Enhancement:**
- **LLM-based analysis of `free_text` field** for nuanced lesson generation
- Extract specific improvement suggestions from user's detailed feedback
- Generate more targeted persona/style adjustment lessons
- Correlate free text patterns with skill performance metrics

### 5.4 Separation from User Memories

**Important:** The `user_memories` table serves a **different purpose**:

| `user_memories` | Reflection Tables |
|----------------|-------------------|
| **User-curated semantic facts** | **System performance metrics** |
| "My cat is named Whiskers" | "web_search succeeded 45/50 times" |
| "I prefer dark mode" | "goal_type 'learning' retired 60%" |
| User explicitly saves | Automatically captured |
| Permanent memories | Historical performance data |
| Memory Album / KG | Behavioral learning |

This separation ensures:
- ✅ Clean data model (semantic vs. quantitative)
- ✅ Optimized queries (no JSON parsing overhead)
- ✅ Type safety (proper column types)
- ✅ Clear ownership (user vs. system data)

### 5.5 Future Integration with Knowledge Graph

While reflection data currently lives in dedicated tables, future enhancements may include:
- Projection layer to expose lessons to Knowledge Graph
- Integration with AMS for cross-component visibility
- Links between lessons and World Model hypotheses
- Provenance tracking through KG relationships

### 5.6 Policy Amendments (When `policy_mode = allow_amend`)

When policy auto-amendment is enabled, Self-Reflection uses the **Values & Ethics service** to apply small changes to policy configuration, which is then persisted in the existing **policy tables** (e.g. ValueProfiles, PolicyRules) in the shared libSQL store.

For every applied amendment, the system must:

- **Create a lesson** in `agency_lessons` with `lesson_type = "policy_suggestion"` and `target_kind = "policy_rule"`:
  - `proposed_change` records the exact parameter diff (e.g. old/new threshold, weights, flags)
  - `status = "active"` (or updated to `"superseded"`/`"rejected"` later)
  - `source_reflection_run_id` links to the reflection run that generated it
  - `evidence_window_start`/`end` track the analysis period
  
- **Emit an audit log entry** via Safety & Control / logging layer, containing at minimum:
  - `timestamp`, `user_id`, `lesson_id`
  - `policy_rule_id` (or equivalent identifier), old vs. new values
  - `initiator = "self_reflection"` and reference to the `lesson_id`
  - Decision rationale summary (from `summary_text`)
  
- **Persist the actual rule change** by calling Values & Ethics APIs, which in turn:
  - Update the appropriate `PolicyRule` / ValueProfile rows in libSQL
  - Optionally project significant changes into the World Model as `WorldStateFact`s about AICO's internal configuration
  - Mark the lesson as applied: `UPDATE agency_lessons SET applied_at = NOW(), applied_by = 'values_ethics_service'`

This guarantees that:

- ✅ All Self-Reflection lessons (including policy-related ones) are stored in `agency_lessons` with full provenance
- ✅ Any automatic policy amendments are **fully logged, auditable, and reversible**
- ✅ Clear separation between lesson generation (reflection) and lesson application (values & ethics)
- ✅ Audit trail through `agency_reflection_runs` → `agency_lessons` → policy changes

## 6. Implementation Details

### 6.1 Core Components

**File:** `/shared/aico/ai/agency/reflection.py`

**Main class:** `SelfReflectionEngine`

**Key methods:**
- `run_reflection()` - Main orchestrator for reflection runs
- `_analyze_skill_performance()` - Analyzes skill success rates
- `_analyze_goal_patterns()` - Analyzes goal completion patterns
- `_analyze_user_feedback()` - Analyzes user satisfaction
- `get_active_lessons()` - Retrieves active lessons for a user
- `get_self_model()` - Retrieves performance model for an entity

**Storage classes:**
- `LessonStore` - Manages `agency_lessons` table
- `SelfModelStore` - Manages `agency_self_model` table
- `ReflectionRunStore` - Manages `agency_reflection_runs` table

**Application:**
- `LessonApplicationService` - Applies lessons to system configuration

### 6.2 Configuration

```yaml
core:
  agency:
    self_reflection:
      policy_mode: "observe_only"  # or "allow_amend"
      min_sample_size: 10           # Minimum data points before generating lessons
      confidence_threshold: 0.7     # Minimum confidence to apply lessons
```

### 6.3 Typical Workflow

```
1. Scheduled Trigger (e.g., nightly at 3 AM)
   ↓
2. run_reflection(user_id, run_type=SCHEDULED)
   ↓
3. Create reflection run record (status: RUNNING)
   ↓
4. Analyze skill performance (7-day window)
   - Query ams_behavioral_feedback
   - Calculate success rates
   - Generate lessons for poor performers
   - Update agency_self_model
   ↓
5. Analyze goal patterns (7-day window)
   - Query agency_goals
   - Calculate completion/retirement rates
   - Generate lessons for problematic patterns
   ↓
6. Analyze user feedback (7-day window)
   - Query feedback_events
   - Calculate satisfaction scores
   - Generate persona adjustment lessons
   ↓
7. Apply lessons (confidence >= 0.7)
   - LessonApplicationService.apply_lesson()
   - Update system configuration
   - Mark lessons as applied
   ↓
8. Complete reflection run
   - Update status: COMPLETED
   - Record lessons_generated, lessons_applied
   - Calculate duration
```

## 7. Design Rationale

### 7.1 Why Dedicated Tables Instead of user_memories?

**Decision:** Use dedicated `agency_*` tables instead of storing lessons in `user_memories`

**Rationale:**

1. **Performance:** Direct column access vs. JSON parsing in `temporal_metadata`
2. **Type Safety:** Proper SQL types vs. JSON blobs
3. **Indexing:** Specific indexes for lesson queries vs. generic memory indexes
4. **Clarity:** Self-documenting schema vs. convention-based JSON structure
5. **Separation of Concerns:** Performance metrics vs. semantic facts
6. **Query Simplicity:** Standard SQL vs. JSON extraction functions

**Trade-offs:**
- ❌ Not integrated with Memory/AMS system (yet)
- ❌ Not projected into Knowledge Graph (yet)
- ✅ Better performance and maintainability
- ✅ Clearer data model

**Future:** Integration layer can be added to expose lessons to AMS/KG without changing storage model.

### 7.2 Why Separate from user_memories?

**user_memories is for:**
- User-curated semantic facts
- Personal information and preferences
- Conversational memories
- User-visible Memory Album

**agency_lessons is for:**
- System performance metrics
- Behavioral learning
- Automatic optimization
- Internal system state

**These are fundamentally different data types with different lifecycles, access patterns, and purposes.**
