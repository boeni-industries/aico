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

- Reads from: logs/telemetry, AMS, emotion history, social relationship history.
- Writes to: behavioral learning store, policy/skill metadata, self-model summaries available to other components, and (optionally) Values & Ethics **policy authoring/amendment paths**.
- Collaborates with: Curiosity Engine (where to explore), Goal Arbiter (what to deprioritize or emphasize), Values & Ethics (alignment of behavior with declared values and, when allowed, small policy refinements).

## 4. Policy Interaction Modes

Self-Reflection interacts with Values & Ethics in **two modes**, controlled by configuration (e.g. `core.agency.self_reflection.policy_mode` in `core.yaml`):

- `observe_only` (default / safest)
  - Self-Reflection:
    - analyses behaviour against current policies,
    - writes **reflection MemoryItems** with `lesson_type = "policy_suggestion"`, describing potential improvements,
    - **does not** change any `PolicyRule` rows or ValueProfiles.
  - Values & Ethics (or a separate policy-authoring UI/process) may later review these memories and turn them into rule changes.

- `allow_amend` (config-gated, advanced)
  - When explicitly enabled, Self-Reflection may propose and apply **small, local amendments** to Values & Ethics **through the Values & Ethics service**, never by writing policy tables directly.
  - Typical allowed changes (subject to future refinement):
    - tuning numeric thresholds and weights inside existing rules,
    - adjusting rule priorities or soft caps,
    - adding narrowly-scoped allow/deny exceptions where the high-level value direction is unchanged.
  - Structural changes (e.g. adding entirely new value dimensions, deleting whole policy families) remain out of scope and must go through a separate policy-authoring path.

In both modes, every suggestion or amendment must be fully **auditable and explainable** (see Persistence below).

## 5. Persistence and Audit for Self-Reflection Outputs

Self-Reflection reuses the existing **Memory/AMS + World Model + Values & Ethics** persistence stack. It does not introduce new storage backends.

### 5.1 Reflection Lessons as Memory (Mapping to `user_memories`)

Self-Reflection does **not** require new tables or columns. It standardises how we use the existing `user_memories` schema:

```sql
CREATE TABLE "user_memories" (
  fact_id TEXT PRIMARY KEY,
  user_id TEXT NOT NULL,
  fact_type TEXT NOT NULL,
  category TEXT NOT NULL,
  confidence REAL NOT NULL,
  is_immutable BOOLEAN NOT NULL DEFAULT FALSE,
  valid_from TIMESTAMP NOT NULL,
  valid_until TIMESTAMP,
  content TEXT NOT NULL,
  entities_json TEXT,
  extraction_method TEXT NOT NULL,
  source_conversation_id TEXT NOT NULL,
  source_message_id TEXT,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  user_note TEXT,
  tags_json TEXT,
  is_favorite INTEGER DEFAULT 0,
  revisit_count INTEGER DEFAULT 0,
  last_revisited TIMESTAMP,
  emotional_tone TEXT,
  memory_type TEXT,
  content_type TEXT DEFAULT 'message',
  conversation_title TEXT,
  conversation_summary TEXT,
  turn_range TEXT,
  key_moments_json TEXT,
  temporal_metadata TEXT DEFAULT NULL,
  FOREIGN KEY (user_id) REFERENCES users(uuid) ON DELETE CASCADE
)
```

For **reflection lessons**, we adopt the following conventions:

- Each lesson is stored as a logical `MemoryItem` backed by a `user_memories` row:
  - `fact_id`: reflection ID (UUID).
  - `user_id`: owner of the lesson.
  - `fact_type`: set to `"reflection"`.
  - `category`: `"agency_behavior"` or `"policy"`.
  - `confidence`: numeric confidence in the lesson.
  - `valid_from` / `valid_until`: when this lesson is considered applicable.
  - `content`: human-readable `summary_text`.
  - `tags_json`: JSON array of tags.
  - `memory_type`: set to `"reflection"` to distinguish from other memories.
  - `content_type`: `"lesson"`.
  - `temporal_metadata`: JSON blob that encodes the **slots** we describe conceptually:
    - `lesson_type`: one of `"skill_tuning"`, `"planner_heuristic"`, `"curiosity_focus"`, `"persona_style"`, `"policy_suggestion"`.
    - `target_kind`: one of `"skill"`, `"planner_template"`, `"arbiter_weight"`, `"curiosity_policy"`, `"persona_trait"`, `"policy_rule"`.
    - `proposed_change`: structured diff with a stable mini-schema:
      - `change_type`: one of `"threshold_tweak"`, `"weight_tweak"`, `"exception_add"`, `"exception_remove"`, `"template_update"`.
      - `field`: the concrete config/parameter field being changed (for example `"risk_threshold"` or `"priority_weight"`).
      - `old`: previous value (typed as JSON).
      - `new`: new value (typed as JSON).
      - optional `notes`: short NL explanation for humans/tools.
    - `confidence`: numeric confidence in the lesson.
    - `scope`: one of `"this_user"`, `"global_default"`.
    - `status`: one of `"active"`, `"superseded"`, `"rejected"`.
    - `metrics_basis`: optional summary of the evidence window (time span, sample size, outcome counts).

### 5.1.1 Enumerated fields (canonical values)

The following fields in `temporal_metadata` and related structures MUST use these exact string values:

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

AMS/MemoryManager and the World Model can then project these rows into the KG as `MemoryItem` nodes with:

- `REFERENCES(MemoryItem, Skill|Goal|PolicyRule|PersonaTrait|CuriosityPolicy)` edges.
- `LEARNED_FROM(MemoryItem, PerceptualEvent)` edges for provenance.

No schema migration is needed for Self-Reflection itself; the work is in adopting these conventions in the existing `user_memories` table and corresponding KG projection logic.

### 5.2 Policy Amendments (When `policy_mode = allow_amend`)

When policy auto-amendment is enabled, Self-Reflection uses the **Values & Ethics service** to apply small changes to policy configuration, which is then persisted in the existing **policy tables** (e.g. ValueProfiles, PolicyRules) in the shared libSQL store.

For every applied amendment, the system must:

- **Create a reflection MemoryItem** with `lesson_type = "policy_suggestion"` and `target_kind = "policy_rule"`:
  - `slots.proposed_change` records the exact parameter diff (e.g. old/new threshold, weights, flags).
  - `slots.status = "active"` (or updated to `superseded/rejected` later).
- **Emit an audit log entry** via Safety & Control / logging layer, containing at minimum:
  - `timestamp`, `user_id`, `agent_id`.
  - `policy_rule_id` (or equivalent identifier), old vs. new values.
  - `initiator = "self_reflection"` and a pointer to the `memory_id` of the responsible reflection MemoryItem.
  - decision rationale summary (short text derived from the MemoryItem).
- **Persist the actual rule change** by calling Values & Ethics APIs, which in turn:
  - update the appropriate `PolicyRule` / ValueProfile rows in libSQL,
  - optionally project significant changes into the World Model as `WorldStateFact`s about AICO’s internal configuration, if needed for explainability.

This guarantees that:

- all Self-Reflection lessons (including policy-related ones) live in the same **AMS/MemoryItem** infrastructure, and
- any automatic policy amendments are **fully logged, auditable, and reversible**, without introducing new bespoke storage just for Self-Reflection.
