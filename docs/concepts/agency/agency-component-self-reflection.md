---
title: Agency Component – Self-Reflection & Self-Model
---

# Self-Reflection & Self-Model

## Status

- **Implemented (v1)**: reflection engine exists as `SelfReflectionEngine` in `shared/aico/ai/agency/reflection.py` and is invoked via `AgencyEngine.run_self_reflection(...)`.
- **Implemented (v1)**: scheduled execution exists as `AgencyReflectionTask` in `backend/scheduler/tasks/agency_reflection.py` (cron default `0 3 * * *`) with idle/battery gating.
- **Implemented (v1)**: persistence uses PostgreSQL tables in `shared/aico/data/postgres/schema.sql` (`agency_lessons`, `agency_self_model`, `agency_reflection_runs`) and SQLAlchemy mappings in `shared/aico/data/tables.py`.
- **Implemented (v1)**: transparency endpoints exist in `backend/api/agency/router.py` under `/api/v1/agency/reflection/*` (runs, lessons, self-model, skill performance, summary).
- **WIP**: projection of lessons into the Knowledge Graph / Memory/AMS as first-class entities (current system stores structured lessons in the agency tables and returns them via API).

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
- `agency_skill_executions` - Skill execution outcomes and timing
- `ams_behavioral_feedback` - Behavioral feedback signals (incl. user feedback/reward signals)
- `agency_goals` - Goal lifecycle and completion patterns
- `emotion_history` - Emotion history signals (when available)
- `user_relationships` - Relationship/social interaction signals
- `ethics_gate_audit` - Values & Ethics gate outcomes (for identifying repeated blocks/policy friction)

**Writes to:**
- `agency_lessons` - Behavioral lessons and change proposals (skill tuning, arbiter weights, curiosity intensity, policy threshold tweaks)
- `agency_self_model` - Aggregated performance summaries for tracked entities (e.g., skills, goal types)
- `agency_reflection_runs` - Audit trail of reflection job execution
- (When applied) Updates are performed via the lesson applicator (`shared/aico/ai/agency/lesson_applicator.py`) and stored in the corresponding tables (e.g., `agency_arbiter_adjustments`, user skill learning data, and ethics policy rules).

**Collaborates with:**
- `LessonApplicationService` - Applies lessons (implemented as `LessonApplicationService` in `shared/aico/ai/agency/lesson_applicator.py`)
- `ContextAssembler` - May surface lessons in runtime context assembly (**WIP**: consistent inclusion policies)
- Goal Arbiter - Can consume applied adjustments (e.g., via `agency_arbiter_adjustments`)
- Values & Ethics - In `allow_amend` mode, applies user-scoped policy tweaks by writing to ethics policy rules via UoW

## 4. Policy Interaction Modes

Self-Reflection interacts with Values & Ethics in **two modes**, controlled by configuration (see `agency.self_reflection.policy_mode`):

- `observe_only` (default / safest)
  - Self-Reflection:
    - Analyses behaviour against current policies
    - Creates lessons in `agency_lessons` with `lesson_type = "policy_suggestion"`, describing potential improvements
    - **Does not** change any `PolicyRule` rows or ValueProfiles
    - Lessons remain in `status = "active"` for review
  - Values & Ethics (or a separate policy-authoring UI/process) may later review these lessons and manually apply them as rule changes

- `allow_amend` (config-gated, advanced)
  - When explicitly enabled, Self-Reflection may propose and apply **small, local amendments** to Values & Ethics via the ethics policy repositories (UoW), creating user-scoped copies when needed.
  - Typical allowed changes (subject to future refinement):
    - tuning numeric thresholds and weights inside existing rules,
    - adjusting rule priorities or soft caps,
    - adding narrowly-scoped allow/deny exceptions where the high-level value direction is unchanged.
  - Structural changes (e.g. adding entirely new value dimensions, deleting whole policy families) remain out of scope and must go through a separate policy-authoring path.

In both modes, every suggestion or amendment must be fully **auditable and explainable** (see Persistence below).

## 5. Persistence and Audit for Self-Reflection Outputs

Self-Reflection uses **dedicated tables** for performance and clarity, separate from user-curated semantic memory. The authoritative schema lives in `shared/aico/data/postgres/schema.sql` (and SQLAlchemy mappings in `shared/aico/data/tables.py`).

### 5.1 Dedicated Reflection Tables

The implementation uses dedicated `agency_*` tables in PostgreSQL (see `schema.sql`):

#### 5.1.1 `agency_lessons`

Stores behavioral lessons generated from reflection analysis. See:

- `shared/aico/data/postgres/schema.sql` (`CREATE TABLE IF NOT EXISTS agency_lessons ...`)
- `shared/aico/data/agency/lesson_models.py` (Pydantic model)
- `shared/aico/data/repositories/postgres/lesson_repository.py` (CRUD + JSON field handling)

#### 5.1.2 `agency_self_model`

Stores aggregated performance summaries used by reflection and transparency endpoints. See `shared/aico/data/agency/reflection_models.py`.

#### 5.1.3 `agency_reflection_runs`

Stores an audit trail of reflection runs. It is written by `SelfReflectionEngine.run_reflection(...)`.

### 5.2 Enumerated Values

Enumerations and allowed values are defined in code (see `shared/aico/ai/agency/models.py` for `LessonType`, `LessonStatus`, `LessonScope`, and run status/type enums). Any textual values in the database should be treated as implementation-defined.

### 5.3 Data Sources for Reflection Analysis

The reflection engine analyzes performance data from dedicated behavioral tracking tables:

#### 5.3.1 Behavioral Feedback

**Purpose:** Tracks skill execution outcomes and performance metrics  
**Populated by:** `BehavioralFeedbackService` (automatic during skill execution)  
**Used for:** Skill performance analysis, success rate calculations

**Key fields:**
- `skill_id` - Which skill was executed
- `outcome` - success, failure, timeout, error, partial
- `reward` - Reward signal (-1, 0, 1)
- `execution_time_ms` - Performance timing
- `user_satisfaction` - Optional user satisfaction score

**Implementation note (v1):** the reflection engine analyzes both `ams_behavioral_feedback` and `agency_skill_executions`.
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

#### 5.3.3 User Feedback

**Purpose:** Tracks explicit user feedback and ratings (thumbs up/down)  
**Populated by:** feedback capture flows that write into the existing behavioral feedback tables (**WIP**: richer, structured free-text analysis).
  
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

When policy auto-amendment is enabled, Self-Reflection uses the **Values & Ethics service** to apply small changes to policy configuration, which is then persisted in the existing **policy tables** (e.g. ValueProfiles, PolicyRules) in the shared PostgreSQL store.

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
  - Update the appropriate `PolicyRule` / ValueProfile rows in PostgreSQL
  - Optionally project significant changes into the World Model as `WorldStateFact`s about AICO's internal configuration
  - Mark the lesson as applied: `UPDATE agency_lessons SET applied_at = NOW(), applied_by = 'values_ethics_service'`

This guarantees that:

- ✅ All Self-Reflection lessons (including policy-related ones) are stored in `agency_lessons` with full provenance
- ✅ Any automatic policy amendments are **fully logged, auditable, and reversible**
- ✅ Clear separation between lesson generation (reflection) and lesson application (values & ethics)
- ✅ Audit trail through `agency_reflection_runs` → `agency_lessons` → policy changes

## 6. Implementation Details

### 6.1 Core Components

**File:** `shared/aico/ai/agency/reflection.py`

**Main class:** `SelfReflectionEngine`

**Key methods:**
- `run_reflection()` - Main orchestrator for reflection runs
- `_analyze_skill_executions()` - Analyzes skill outcomes and execution characteristics
- `_analyze_goal_patterns()` - Analyzes goal completion patterns
- `_analyze_user_feedback()` - Analyzes user satisfaction
- `_analyze_curiosity_outcomes()` - Analyzes curiosity outcomes
- `_analyze_emotion_patterns()` - Analyzes emotion patterns
- `_analyze_social_patterns()` - Analyzes social patterns
- `_analyze_policy_patterns()` - Analyzes Values & Ethics gate patterns
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
      policy_mode: "observe_only"  # observe_only | allow_amend | disabled
      min_sample_size: 10
      confidence_threshold: 0.7
```

**Runtime note (v1):** scheduled runs are controlled separately by `agency.self_reflection.enabled` (see `backend/scheduler/tasks/agency_reflection.py`).

### 6.3 Typical Workflow

```
1. Scheduled Trigger (e.g., nightly at 3 AM via `AgencyReflectionTask`)
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
   - Query behavioral feedback sources (e.g., `ams_behavioral_feedback`)
   - Calculate satisfaction scores
   - Generate persona adjustment lessons
   ↓
7. Apply lessons (only if `policy_mode = allow_amend` and confidence >= threshold)
   - `LessonApplicationService.apply_lesson(...)`
   - Persist adjustments (arbiter adjustments / user skill learning data / ethics policy rules)
   - Mark the lesson as applied
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
