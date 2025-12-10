---
title: Agency Implementation Roadmap
---

# Agency Implementation Roadmap

This roadmap translates the conceptual agency design into an incremental implementation plan. 

- Each phase should yield a **testable, usable system**.
- Phases are cumulative: later work **extends** existing modules instead of replacing them.
- Items are written as checkable bullets (`[ ]`) so progress can be tracked.
 - Implementation should follow the integration contracts defined in `agency-integration.md` for Conversation, Memory/AMS, Emotion, Scheduler, and Embodiment.

## Phase 0 – Foundations & Enablement

Goal: Ensure the existing platform can host an always-on agency loop with clear extension points.

- [x] **Localisation Prep & Conversation Language Signal**
  - [x] Add core language metadata columns to users, memories, KG nodes, and skills (see `SchemaVersion 19` in `shared/aico/data/schemas/core.py`).
  - [x] Implement unified per-user `primary_language` and per-conversation `conversation_language` signal, wired through ConversationEngine → MemoryManager → KG → Skills (see `WIP_full_localization.md`).

- [x] **Conversation & Config Wiring**
  - [x] Expose `enable_agency` feature flag and configuration options in `core.conversation` and related configs.
  - [x] Define a minimal `AgencyEngine`/service interface and register it via `LifecycleManager` / plugin registry.
  - [x] Integrate basic agency context hooks into `ConversationEngine` (Phase 0: call AgencyPlugin and log contract-shaped responses without changing behaviour).
  - [x] Implement `backend.services.agency_engine.AgencyPlugin.process` as a contract-compliant stub that returns structured, empty suggestions/goals.
  - [x] Wire `AgencyPlugin` into conversation flows behind `enable_agency` so it can be enabled safely when ready.

- [x] **Persistence & Telemetry Prereqs**
  - [x] Define core tables/collections for goals, plans, agency logs, self-reflection notes (`agency_goals`, `agency_plans`, `agency_events`, `agency_reflection_notes` in `SchemaVersion 19`).
  - [x] Ensure logging and telemetry are rich enough to support evaluation and self-reflection (agency_events captures IDs, timestamps, and structured payloads for future analysis).

## Phase 1 – Goal System & Planning Skeleton (First Testable Agent)

Goal: Move from stateless chatbot to a **goal- and plan-aware companion** with persistent intentions.

- [x] **Goal & Intention System (core data structures)**
  - [x] Implement `Goal` / `Intention` models (including origin: user, curiosity, hobby, system-maintenance).
  - [x] Implement storage, retrieval, and lifecycle operations (create, activate, pause, complete, retire).
  - [x] Add support for **agent-self goals and hobbies** as first-class objects.

- [x] **Planning & Decomposition (v1)**
  - [x] Implement a Planning component that converts goals into simple plans (linear or shallow branches).
  - [x] Use templated LLM prompts plus hand-authored patterns for common plan shapes.
  - [x] Store plans and steps with links back to goals and tools/skills.

- [x] **Scheduler Integration (v1)**
  - [x] Integrate plans with the existing Task Scheduler (schedule follow-ups, reminders, background tasks).
  - [x] Respect quiet hours and basic user preferences.
  - [x] Implement basic resource constraint checks in the scheduler (e.g., fill in `TaskExecutor._check_resource_constraints` for CPU/memory/battery/idle state).

- [x] **Basic Proactive Behaviour**
  - [x] Introduce simple proactive behaviours: follow-up messages, reminders based on open goals.
  - [x] Make agency activity visible in conversation logs and, optionally, the 3D avatar (basic room/posture mapping).

> **Exit condition:** AICO keeps track of goals across sessions, can form simple multi-step plans, and can proactively act on them in a controlled way.

## Phase 2 – Memory, World Model & Relationship Integration

Goal: Ground goals and plans in **rich memory and world understanding**, not just recent turns.

- [x] **AMS Integration (v1)** ✅ **Phase 2 Complete**
  - [x] Connect Goal System and Planning to AMS for retrieving context, preferences, and open loops.
  - [ ] Use AMS summaries and open-loop lists when (re)formulating goals and plans. *(Phase 4+ - placeholders exist)*
  - [ ] Track and implement AMS unified indexing and cross-tier lifecycle automation as described in `WIP_ams_future_improvements.md` (as a Phase 4+ optimisation).

- [x] **World Model & Knowledge/Property Graph (v1)** ✅ **Phase 2 Complete**
  - [x] Implement a `WorldModelService` API that wraps the existing KG + semantic memory.
  - [x] Provide basic queries such as: entities around a user, projects, recurring contexts, uncertain/unknown areas.
  - [x] Expose world model views to Planner and Curiosity Engine via AgencyEngine integration.

- [x] **Social & Personality Hooks** ✅ **Phase 2 Complete**
  - [x] Wire Personality Simulation traits/values into goal creation and plan style.
  - [x] Include relationship vectors from Social Relationship Modeling in goal selection (e.g. proactivity per user, topic boundaries).

> **Exit condition:** Goals and plans are meaningfully influenced by long-term memory, social context, and world structure; AICO feels more consistent and "aware" over time.

### ✅ Phase 2 Status: **COMPLETE** (December 9, 2025)

**Implemented:**
- ✅ WorldModelService with KG integration (`shared/aico/ai/world_model/`)
- ✅ PersonalityService with Big Five traits (`shared/aico/ai/personality/`)
- ✅ AgencyEngine Phase 2 methods: `create_goal_with_world_context()`, `create_goal_with_full_context()`
- ✅ Priority adjustment based on conscientiousness
- ✅ Proactivity calculation from relationship vectors
- ✅ Goal metadata enrichment with world context and personality
- ✅ Backend wiring in `lifecycle_manager.py`
- ✅ 54 comprehensive tests, 73% coverage
- ✅ Full backward compatibility with Phase 1

**Deferred to Phase 4+:**
- AMS summaries and open-loop lists (infrastructure in place, full implementation Phase 4+)
- Temporal pattern detection
- Uncertainty area identification

**Documentation:**
- See `docs/concepts/agency/phase2-integration-design.md` for architecture
- See `docs/concepts/agency/phase2-implementation-summary.md` for details

## Phase 3 – Curiosity, Intrinsic Motivation & Hobbies

Goal: Give AICO **her own intrinsic drives** and hobbies that generate agent-self goals.

- [x] **Curiosity Engine (v1)** ✅ **Phase 3 v1 Complete**
  - [x] Implement a Curiosity Engine that scans AMS, world model, and interaction history for gaps, anomalies, or under-explored topics.
  - [x] Define an `IntrinsicSignal`/"curiosity opportunity" data structure with basic scoring (heuristics + LLM prompts).
  - [x] Feed curiosity-derived goal candidates into the Goal System.

- [x] **Hobbies & Agent-Self Goals** ✅ **Phase 3 Complete**
  - [x] Define a small, curated set of hobby templates (e.g. learning domains, conversational styles, organizing the 3D flat, internal research notebooks).
  - [x] Allow Curiosity Engine and Self-Reflection to instantiate and update these hobby goals.

- [x] **Lifecycle Integration** ✅ **Phase 3 Complete**
  - [x] Use Lifecycle & Daily Rhythm to allocate time for curiosity/hobbies (idle spans, specific windows).
  - [x] Add lifecycle and agency-readiness flags into `scheduled_tasks.config` for agency-related tasks.
  - [x] Implement lifecycle-aware deferral logic inside agency tasks (and later, centrally in the scheduler if needed).

> **Exit condition:** AICO regularly pursues self-generated curiosity and hobby goals, visibly distinct from direct user requests, within user-configurable bounds.

### ✅ Phase 3 Status: **COMPLETE** (December 9, 2025)

**Implemented:**
- ✅ CuriosityEngine with 3 detectors (`shared/aico/ai/curiosity/`)
- ✅ IntrinsicSignal model with 4 curiosity types (knowledge_gap, novelty, self_performance, hobby_play)
- ✅ 6 default hobby templates (learning, organizing, research categories)
- ✅ Three-gate filtering system (Values/Ethics placeholder, Emotion/relationship, Resource)
- ✅ Personality-based scoring (openness, conscientiousness modifiers)
- ✅ Goal System integration via `create_goal_from_curiosity_signal()`
- ✅ Scheduled task: `curiosity_scan` (every 6 hours)
- ✅ Lifecycle-aware deferral (respects idle/active state, quiet hours)
- ✅ Backend wiring in `lifecycle_manager.py`

**Documentation:**
- See `agency-component-curiosity-engine.md` for full specification
- See `agency-ontology-schemas.md` for data models

## Phase 4 – Goal Arbiter, Values/Ethics & Meta-Control ✅ **COMPLETED**

Goal: Introduce a clear **decision layer** that balances user goals, curiosity, hobbies, and maintenance under constraints.

- [x] **Goal Arbiter & Meta-Control (v1)** ✅
  - [x] Implement a Goal Arbiter that collects goal candidates from user, Curiosity Engine, and system tasks.
  - [x] Define a scoring/ranking function based on: priority, user configuration, personality, emotion, relationship vectors, and values.
  - [x] Maintain an explicit "active intention set" and publish it to other components.
  - **Implementation:** `shared/aico/ai/agency/arbiter.py`
  - **Configuration:** `config/defaults/core.yaml` (`core.services.agency.arbiter.scoring_weights`)
  - **Database:** Schema v21 - `intention_set` table with status tracking
  - **Message Bus:** Publishes intention set updates to `agency/intention_set/updated` topic

- [x] **Values & Ethics Layer (v1)** ✅
  - [x] Implement the Values & Ethics module with a configurable rule set plus optional LLM-based classifiers.
  - [x] Integrate it as a gate in front of goals/plans/skills (block, require consent, annotate as risky).
  - [x] Make values/ethics constraints fully configurable (tighten, relax, or disable where permissible).
  - [x] Design and migrate concrete schemas for `value_profiles`, `policy_rules`, and `consents` tables.
  - [x] Implement a Values & Ethics service API used by agency, Self-Reflection, and Safety & Control for all policy decisions.
  - [x] Integrate Safety & Control configuration (autonomy levels, consent requirements, quiet hours) into the Values & Ethics gate and `AgencyPlugin`, so user controls are consistently enforced.
  - **Implementation:** `shared/aico/ai/agency/values_ethics.py`
  - **Default Policies:** `shared/aico/ai/agency/default_policies.py`
  - **Configuration:** `config/defaults/core.yaml` (`core.services.agency.values_ethics`)
  - **Database:** Schema v21 - `value_profiles`, `policy_rules`, `consents` tables
  - **Policy Modes:** enforce, warn, log

- [x] **Conversation & UX Integration** 
  - [x] Surface agency decisions in conversation logging
    - Agency context (intentions, ethics decisions) logged to `trajectories` table
    - Structured logging of agency decisions with conversation turns
    - Schema v23: Added `agency_context` column to trajectories
  - [x] API endpoints for Flutter integration
  - [ ] Surface the active intention set in UI explanations/tooltips
  - [ ] Allow users to inspect and adjust agency behaviour in Flutter UI
  - [x] CLI commands for policy management

**Status Update (Dec 10, 2025):**
- ✅ Core Phase 4 components fully implemented and operational
- ✅ AgencyEngine integrates ValuesEthicsService and GoalArbiter
- ✅ Message bus integration working
- ✅ Configuration system complete with validation
- ✅ Database schemas migrated (v23: added agency_context to trajectories)
- ✅ Default policies installed and enforced
- ✅ Backend fully operational with all Phase 4 services running
- ✅ Comprehensive test suite: 108 tests passing (99 original + 9 ethics gate tests)
- ✅ CLI commands implemented and tested (`aico agency`)
- ✅ Agency decisions logged to conversation trajectories
- ✅ REST API endpoints implemented (`/api/v1/agency/*`)
  - Intentions, curiosity, profile, policies, consents
  - Based on agency-metrics.md user-facing metrics
  - Encrypted database access with session support
- 🚧 Flutter UI integration pending
- 🚧 Surface intention set in conversation UI pending

> **Exit condition:** AICO's behaviour is governed by an explicit meta-control layer, and users can understand and influence why some goals are pursued and others are not.

## Phase 5 – Self-Reflection, Self-Model & Behavioural Learning

Goal: Enable AICO to **evaluate her own behaviour** and adapt policies and skills over time.

- [ ] **Self-Reflection Engine (v1)**
  - [ ] Implement scheduled reflection jobs (often during AMS "sleep" phases).
  - [ ] Define `Lesson` / self-reflection record structures based on logs, outcomes, and user feedback.
  - [ ] Use LLM prompts to derive simple behavioural lessons (what to do more/less of, timing, tone).
  - [ ] Wire `policy_suggestion` lessons (`target_kind = "policy_rule"`) into the Values & Ethics API, respecting `observe_only` / `allow_amend` modes with full audit logging (see `agency-component-self-reflection.md`).

- [ ] **Self-Model (v1)**
  - [ ] Maintain a lightweight self-model summarizing recent performance per skill and per user.
  - [ ] Expose self-model information to Planner, Goal Arbiter, and Curiosity Engine.

- [ ] **Behavioural Learning Hooks**
  - [ ] Integrate lessons into existing or planned behavioural learning stores (e.g., skill metadata, preference weights).
  - [ ] Log changes in strategy so they can be audited and rolled back if needed.
  - [ ] Standardise skill usage on `SkillStore` and the bandit selector for all agency-driven tools, extending skill metadata instead of adding new tables.

> **Exit condition:** AICO periodically updates how she behaves based on her own experience, in a traceable way, without changing the overall architecture.

## Phase 6 – Advanced Policies & World Model Sophistication

Goal: Upgrade internal decision-making and world modelling while keeping interfaces stable.

- [ ] **Curiosity & Intrinsic Motivation (advanced)**
  - [ ] Move from heuristic curiosity scoring to a more principled intrinsic reward model (e.g., prediction error, information gain, empowerment).
  - [ ] Track long-term returns from curiosity and hobby projects to refine what is worth exploring.

- [ ] **World Model Service (advanced)**
  - [ ] Enhance schema learning for user life situations, projects, and phases.
  - [ ] Add hypothesis generation and testing APIs (softly check possible changes or assumptions about the user).
  - [ ] Implement drift and contradiction detection with corresponding agency responses.

- [ ] **Goal Arbiter & Self-Reflection (advanced)**
  - [ ] Evolve from fixed scoring to adaptive/learned goal selection policies (e.g., bandits or RL on top of logged outcomes).
  - [ ] Allow Self-Reflection to adjust Arbiter and Planner parameters in a controlled, logged way.

> **Exit condition:** Internals of curiosity, world modelling, and goal selection are more principled and data-driven, while the external behaviour remains backward compatible and explainable.

## Phase 7 – Embodiment as Cognitive Substrate & Polishing

Goal: Use the 3D flat and embodiment not just for presentation, but as a **cognitive scaffold** and final polish.

- [ ] **Embodied Cognition Patterns**
  - [ ] Define internal tasks and routines that are always represented through spatial metaphors (desk work, reading on couch, organizing room).
  - [ ] Use environment layout and artefacts as memory cues and anchors for long-term projects and hobbies.
  - [ ] Represent curiosity/hobby work in the 3D flat (e.g., AICO at the desk reading, on the couch studying, reorganizing her room). *(Deferred from Phase 3)*

- [ ] **Conversation & UX Integration**
  - [ ] Ensure hobbies appear in AICO's visible behaviour (comments, embodiment, occasional sharing with the user). *(Deferred from Phase 3)*

- [ ] **Integration with Real-World Context (optional)**
  - [ ] Optionally connect agency state and embodiment with real devices/context (e.g., phone, calendar, home automation) under strict user control.

- [ ] **Refinement & Evaluation**
  - [ ] Define evaluation metrics and test scenarios for agency quality (usefulness, coherence, autonomy, user comfort).
  - [ ] Iterate on prompts, policies, and UX based on real usage data.

> **Exit condition:** AICO behaves as a coherent, self-motivated, relationship-centric companion whose inner life (goals, curiosities, hobbies, reflections) is legible through conversation and embodiment, with the full conceptual architecture implemented in practice.

## Implementation Completion Checklist (Cross-Phase)

These items ensure that early "basic" or placeholder implementations are fully evolved into the intended system by the time all phases are complete:

- [ ] **Planner maturity**: LLM-backed planning with robust templates and pattern selection, with fallbacks documented and tested.
- [ ] **Scheduler & resource management**: `_check_resource_constraints` and quiet-hours logic enforce real system limits and user preferences for all agency tasks.
- [ ] **Proactive behaviours**: Follow-ups/reminders move from simple checks to policy-aware, relationship- and values-informed behaviours.
- [ ] **Agency visibility & UX**: All internal agency components (goals, plans, intentions, curiosity, hobbies, reflections) are surfaced through consistent explanations, logs, and embodiment cues.
- [ ] **Mock/stub cleanup**: All temporary stubs, mocks, and "Phase 1 skeleton" code paths are either removed or clearly marked as legacy paths with replacement implementations in place.
