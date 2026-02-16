---
title: Agency Integration
---

# Agency Integration

## 1. Purpose

This document describes how **agency** integrates with AICO’s existing systems:

- Conversation engine
- Memory and Adaptive Memory System (AMS)
- Emotion simulation
- Personality and social relationship modeling
- Scheduler and background tasks
- Modelservice
- 3D embodiment and living‑space

It builds on the conceptual specification in `agency.md` and the architecture view in `agency-architecture.md`, grounding them in the current codebase.

## 2. Core Runtime Loop (Today)

### 2.1 Conversation-Centered Flow

The current conversation‑driven flow is implemented primarily in:

- `backend/services/conversation_engine.py` – `ConversationEngine`
- `backend/services/modelservice_client.py` – ZMQ client to modelservice
- `shared/aico/ai/memory/manager.py` – `MemoryManager` and AMS
- `backend/services/emotion_engine.py` – `EmotionEngine`
- `backend/core/lifecycle_manager.py` – service registration and AI registry setup

The simplified loop for a user turn is:

1. **User input** arrives from API Gateway on `AICOTopics.CONVERSATION_USER_INPUT`.  
2. `ConversationEngine._handle_user_input()` unpacks a `ConversationMessage`, resolves `user_id` and `conversation_id`, and loads `UserContext`.  
3. `ConversationEngine._generate_response()` stores request metadata and calls `_get_memory_context()` if memory integration is enabled.  
4. `_get_memory_context()` uses the globally registered `MemoryManager` to assemble context and store the new message.  
5. `_generate_llm_response()` builds LLM messages (optional system prompt, recent context, current user message) and sends a chat request via the message bus to modelservice.  
6. Streaming responses from modelservice are forwarded back to the API Gateway for the frontend.

Emotion and personality integration are scaffolded but largely optional today; memory and modelservice are the primary active integrations. The conversation engine now also tracks a unified **conversation language signal**:

- `users.primary_language` (per-user preference, ISO/BCP-47) is loaded into `UserContext.conversation_language`.
- This `conversation_language` is propagated to memory (`MemoryManager.store_message(..., language=...)`), KG nodes (`kg_nodes.language`), and skill metadata (`skills.supported_languages`) so that future agency components can select prompts, skills, and content in the correct language.

**WIP**: the `kg_nodes.language` propagation described here is a target design; the current codebase already propagates language through `ConversationEngine` into `MemoryManager.store_message(..., language=...)` and stores `users.primary_language` in PostgreSQL, but KG language fields should be treated as in-progress until verified end-to-end.

### 2.2 Memory and AMS Integration

`MemoryManager` is created and registered by `BackendLifecycleManager._register_ai_processors()`:

- Receives the global config and a shared encrypted database connection.  
- Initializes:
  - **Working memory** (LMDB) for fast conversation history.  
  - **Semantic memory** (ChromaDB + PostgreSQL) when enabled.  
  - **Knowledge graph** (PropertyGraphStorage, MultiPassExtractor, EntityResolver, GraphFusion).  
  - **AMS components** (ConsolidationScheduler, IdleDetector, EvolutionTracker, behavioral learning scaffolding).

Key integration surfaces:

- `MemoryManager.assemble_context(user_id, current_message, conversation_id)`  
  - Returns `memory_context` (recent history, user facts, metadata) to the conversation engine.  
- `MemoryManager.store_message(user_id, conversation_id, text, role, language)`  
  - Called by the conversation engine for ongoing storage, and now records the **language** of each message across working and semantic memory tiers.

AMS consolidation is driven by the **Task Scheduler** via `backend/scheduler/tasks/ams_consolidation.py`, which pulls `memory_manager` from the AI registry and runs consolidation when enabled and idle.

### 2.3 Emotion Simulation

`EmotionEngine` is registered as a core service and started before the conversation engine:

- Maintains an internal emotional state (C‑CPM‑inspired multi‑stage appraisal).  
- Publishes state to the message bus on `AICOTopics.EMOTION_STATE_CURRENT`.  
- Persists state and history to encrypted PostgreSQL tables (`emotion_state`, `emotion_history`).

The conversation engine is currently wired to have access to the emotion engine via the service container, but most conditioning is still in early integration stages; nonetheless, the architecture assumes that agency will be able to query **current emotional state** and recent emotional history.

## 3. Agency as an Integrating Layer

Agency is designed to sit **above** and **between** these systems, not to replace them.

### 3.1 Over Conversation

The conversation engine already exposes:

- Feature flags: `enable_memory_integration`, `enable_emotion_integration`, `enable_personality_integration`, `enable_embodiment`, `enable_agency`.  
- A clear `_generate_response()` → `_generate_llm_response()` pipeline.

**Agency’s role** over conversation is to:

- Provide **goals and plans** that explain why a given response or initiative is being taken.  
- Influence **prompt construction** (via system/context prompts, skill selection, and planning templates).  
- Trigger **proactive messages** (ResponseMode.PROACTIVE) without direct user input, via topics like `AICOTopics.AI_AGENCY_PROACTIVE_TRIGGER` and conversation engine callbacks.

**WIP**: the concrete topic name in code is `AICOTopics.AI_AGENCY_PROACTIVE_TRIGGER` (see `shared/aico/core/topics.py`). End-to-end proactive initiation wiring (agency -> conversation) is still in early integration stages.

### 3.2 Over Memory, World Model and AMS

`MemoryManager`, the shared World Model Service, and AMS already implement:

- Long‑term storage and retrieval of facts, segments, and graph structure (PostgreSQL-backed KG + embeddings).  
- Background consolidation (sleep‑like phases) orchestrated by the scheduler.  
- Behavioral learning scaffolding (skill store, Thompson Sampling, preference manager) for skill‑based interaction.

**Agency’s role** over memory and world model is to:

- Treat AMS/WM as the **source of long‑term context, facts, hypotheses, and open loops** when forming goals.  
- Use behavioral learning outputs (skill success rates, user preferences) to select **which skills to apply** for a given goal.  
- Schedule consolidation and reflective tasks as part of AICO’s **sleep routine**, rather than as purely technical jobs.

### 3.3 Over Emotion, Personality, and Social

The emotion engine and personality simulation (see `personality-sim-architecture.md`) already provide:

- A continuously updated **emotional state** with valence/arousal and style parameters.  
- A **trait vector** and value system that constrain and explain behavior.

**Agency’s role** over these systems is to:

- Query emotion, personality, and relationship vectors to ensure goals and plans are **emotionally and socially coherent** (e.g., no hyper‑aggressive initiatives for a caring, calm persona, respect relationship roles).  
- Use emotional state to modulate **initiative timing** (e.g., avoid starting heavy topics during user distress unless explicitly requested).  
- Ensure long‑term goals respect the character’s **values and narrative arc** and feed the right signals into Values & Ethics and Curiosity gating.

### 3.3.1 Self-Reflection, Values & Ethics, and Policy Adaptation

At integration level, **Self-Reflection** and **Values & Ethics** form a closed loop:

- Self-Reflection periodically analyses behaviour, outcomes, and metrics (see `agency-component-self-reflection.md`).
- It records lessons as `MemoryItem(type="reflection")` in AMS/World Model, including `lesson_type`, `target_kind`, `target_id`, and a structured `proposed_change` diff.
- For policy-related lessons (`lesson_type = "policy_suggestion"`, `target_kind = "policy_rule"`), Values & Ethics consumes these memories in two modes:
  - `observe_only` (default): suggestions are **read-only** input for a human or dedicated policy-authoring flow.
  - `allow_amend` (opt-in): small, local amendments may be applied **via Values & Ethics APIs only**, which:
    - update the existing `policy_rules` / ValueProfile tables,
    - emit audit logs tied back to the originating reflection MemoryItem.

This keeps Values & Ethics as the single execution surface and store for policy, while allowing agency to gradually adapt within clear, audit-backed boundaries.

### 3.4 Over Scheduler and Background Tasks

The scheduler and AMS tasks already run:

- **Consolidation jobs** (nightly / idle) via `ams_consolidation.py`.  
- Other tasks (KG consolidation, trajectory cleanup, etc.).

**Agency’s role** is to:

- Align scheduler tasks with explicit goals and plans, rather than opaque jobs.  
- Introduce lifecycle-aware windows (sleep-like phases) where heavier jobs (AMS, World Model consolidation, curiosity exploration) can safely run.  
- Ensure that resource governance respects both technical constraints and user-configured autonomy levels.

Implementation-wise, this is realized by **extending the existing `backend.scheduler` service** (`TaskScheduler`, `TaskExecutor`, `TaskStore`) with agency-specific task metadata and readiness checks; there is a **single scheduler path** for all tasks in the system.

### 3.5 Over Embodiment

The embodiment architecture (see `embodiment.md`) defines the 3D avatar and living‑space. Agency extends this by:

- Mapping lifecycle and current plan step to **room and posture** (e.g., desk for work, couch for learning, bedroom for sleep).  
- Using spatial state as a **visible projection** of internal agency state (what AICO is doing when not actively chatting).  
- Ensuring spatial transitions (moving rooms) are consistent with goals and scheduler‑driven activity changes.

## 4. Proposed Integration Contracts

To keep the system coherent, each domain should expose a small, well‑defined contract to the agency layer.

### 4.1 Conversation Engine ↔ Agency

- **Agency → Conversation**  
  - `propose_proactive_message(user_id, goal_id, content, metadata)` → publishes to conversation engine (e.g., via `AI_AGENCY_PROACTIVE_TRIGGER` topic). **WIP**  
  - `decorate_prompt(request_id, agency_context)` → hook to add goal/plan/skill context into system prompt or message list.

- **Conversation → Agency**  
  - `on_user_turn(user_id, conversation_id, message, memory_context, emotion_state)` → agency observes each turn and updates goals/intentions.

### 4.2 Memory/AMS ↔ Agency

- **Agency → Memory**  
  - Request high‑level context: `assemble_context(...)` (already implemented).  
  - Store explicit commitments/decisions as **user‑visible memories** (Memory Album) and as internal facts.

- **Memory/AMS → Agency**  
  - Expose “open loops” and unresolved items (e.g., pending commitments, scenarios flagged for follow‑up).  
  - Provide APIs to query long‑term trends and preference shifts for goal formation.

### 4.3 Emotion, Personality, Social ↔ Agency

- **Agency → Emotion/Personality**  
  - Request current state and traits when selecting or vetoing goals.  
  - Optionally request “soft constraints” (e.g., maximum initiative level today).

- **Social Graph → Agency**  
  - Provide relationship vectors used to compute initiative level, topic suitability, and privacy rules for any agency‑driven action.

### 4.4 Scheduler & Resource Monitor ↔ Agency

- **Agency → Scheduler**  
  - Register planned tasks with priority, resource hints, and lifecycle alignment (e.g., night‑only tasks).

- **Scheduler/Monitor → Agency**  
  - Notify when tasks are completed, skipped, or throttled.  
  - Expose current resource budget to shape what agency may schedule.

### 4.5 Embodiment ↔ Agency

- **Agency → Embodiment**  
  - Publish high‑level activity state (`working`, `reading`, `sleeping`, `idle`, `cooking`, etc.).  
  - Embodiment system maps these to room/posture animations.

- **Embodiment → Agency (optional)**  
  - User interactions with the 3D space (e.g., tapping a room, moving AICO) can be fed back as signals that influence goals and plans.

## 5. Coherent Overall Picture

Putting it together:

- **Conversation** remains the primary interaction surface, but no longer the only driver; agency can initiate turns based on internal goals.  
- **Memory and AMS** provide the long‑term backbone that makes those goals stable and context‑aware.  
- **Emotion, personality, and social modeling** ensure that agency feels like a consistent character in relationship with the user, not a generic optimizer.  
- **Scheduler and resource monitor** operationalize bounded autonomy: agency proposes, scheduler enforces.  
- **Embodiment** turns agency state into a visible, spatial life simulation, so users can see AICO “living her life” even when not typing.

Future work should refine these contracts into concrete protobuf schemas and REST endpoints, but the integration structure above can already be implemented incrementally on top of the existing code.

## 6. Persistence & Migrations for Agency

Agency reuses existing PostgreSQL/Chroma/LMDB schemas.

- **Implemented (v1)**: `users.primary_language` exists in the PostgreSQL user profile schema and is used by `ConversationEngine` as the default `conversation_language`.
- **WIP**: the precise migration layering described below (a single `SchemaVersion 19` in `shared/aico/data/schemas/core.py`) does not match the current repository layout; treat the following as conceptual migration guidance rather than a verbatim code pointer.

The following migration block sketches the **agency-specific** Values & Ethics policy tables:

```python
N: SchemaVersion(
    version=N,
    name="Values & Ethics Policy Tables",
    description="Add value_profiles, policy_rules, and consents tables for the Values & Ethics subsystem",
    sql_statements=[
        # Per-user value / trait / priority profiles
        """CREATE TABLE IF NOT EXISTS value_profiles (
            uuid TEXT PRIMARY KEY,
            user_uuid TEXT NOT NULL,
            profile_type TEXT NOT NULL,              -- e.g. 'default', 'experimental'
            traits_json TEXT NOT NULL,               -- JSON blob with value/trait weights
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            is_active BOOLEAN DEFAULT TRUE,
            FOREIGN KEY (user_uuid) REFERENCES users(uuid) ON DELETE CASCADE
        )""",

        # Canonical policy rules
        """CREATE TABLE IF NOT EXISTS policy_rules (
            uuid TEXT PRIMARY KEY,
            user_uuid TEXT NOT NULL,                 -- owner / subject of the rule
            rule_type TEXT NOT NULL,                 -- classifier / hard_rule / consent_gate / rate_limit / etc.
            scope TEXT NOT NULL,                     -- goal / plan / skill / message / system
            target TEXT,                             -- optional target identifier (skill_id, goal_label, etc.)
            condition_json TEXT NOT NULL,            -- JSON condition structure
            action_json TEXT NOT NULL,               -- JSON action/effect structure
            status TEXT NOT NULL,                    -- draft / active / disabled / deprecated
            source TEXT NOT NULL,                    -- human / self_reflection / system_default
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_uuid) REFERENCES users(uuid) ON DELETE CASCADE
        )""",

        # Consents / preferences / revocations
        """CREATE TABLE IF NOT EXISTS consents (
            uuid TEXT PRIMARY KEY,
            user_uuid TEXT NOT NULL,
            subject TEXT NOT NULL,                   -- what the consent is about (feature, data_use, autonomy_level)
            scope TEXT NOT NULL,                     -- global / per_contact / per_context
            value TEXT NOT NULL,                     -- granted / denied / limited / pending
            metadata_json TEXT,                      -- extra structured info (limits, notes, etc.)
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_uuid) REFERENCES users(uuid) ON DELETE CASCADE
        )""",

        # Indexes
        "CREATE INDEX IF NOT EXISTS idx_value_profiles_user_active "
        "ON value_profiles(user_uuid, is_active)",

        "CREATE INDEX IF NOT EXISTS idx_policy_rules_user_status "
        "ON policy_rules(user_uuid, status)",

        "CREATE INDEX IF NOT EXISTS idx_policy_rules_scope_target "
        "ON policy_rules(scope, target)",

        "CREATE INDEX IF NOT EXISTS idx_consents_user_subject "
        "ON consents(user_uuid, subject)",

        "CREATE INDEX IF NOT EXISTS idx_consents_scope_value "
        "ON consents(scope, value)"
    ],
    rollback_statements=[
        "DROP INDEX IF EXISTS idx_consents_scope_value",
        "DROP INDEX IF EXISTS idx_consents_user_subject",
        "DROP INDEX IF EXISTS idx_policy_rules_scope_target",
        "DROP INDEX IF EXISTS idx_policy_rules_user_status",
        "DROP INDEX IF EXISTS idx_value_profiles_user_active",
        "DROP TABLE IF EXISTS consents",
        "DROP TABLE IF EXISTS policy_rules",
        "DROP TABLE IF EXISTS value_profiles"
    ]
),
```

Replace `N` with the next free schema version in `CORE_SCHEMA`. No other migrations are required for agency.

**WIP**: This section is intentionally conceptual and must be validated against the current migration system before being used as an implementation recipe.
