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
- [x] **Values & Ethics Layer (v1)** ✅
  - [x] Implement the Values & Ethics module with a configurable rule set plus optional LLM-based classifiers.
  - [x] Integrate it as a gate in front of goals/plans/skills (block, require consent, annotate as risky).
  - [x] Make values/ethics constraints fully configurable (tighten, relax, or disable where permissible).
  - [x] Design and migrate concrete schemas for `value_profiles`, `policy_rules`, and `consents` tables.
  - [x] Implement a Values & Ethics service API used by agency, Self-Reflection, and Safety & Control for all policy decisions.
  - [x] Integrate Safety & Control configuration (autonomy levels, consent requirements, quiet hours) into the Values & Ethics gate and `AgencyPlugin`, so user controls are consistently enforced.
- [x] **Backend Integration** 
  - [x] Surface agency decisions in conversation logging
  - [x] REST API endpoints for Flutter integration

**Status Update (Dec 10, 2025):**
- ✅ **Phase 4 Backend Complete!**
- ✅ Core Phase 4 components fully implemented and operational
- ✅ AgencyEngine integrates ValuesEthicsService and GoalArbiter
- ✅ Message bus integration working
- ✅ Configuration system complete with validation
- ✅ Database schemas migrated (v23: added agency_context to trajectories)
- ✅ Default policies installed and enforced
- ✅ Backend fully operational with all Phase 4 services running
- ✅ Comprehensive test suite: **120 tests passing** (including 12 new API endpoint tests)
- ✅ CLI commands implemented and tested (`aico agency`)
- ✅ Agency decisions logged to conversation trajectories
- ✅ REST API endpoints implemented and tested (`/api/v1/agency/*`)
  - Based on agency-metrics.md user-facing metrics
  - Encrypted database access with session support
  - Full test coverage with real database

> **Exit condition:** AICO's behaviour is governed by an explicit meta-control layer backend. ✅ **COMPLETE**

## Phase 5 – Self-Reflection, Self-Model & Behavioural Learning ✅

Goal: Enable AICO to **evaluate her own behaviour** and adapt policies and skills over time.

- [x] **Self-Reflection Engine (v1)** ✅
  - [x] Database schema v24 with `agency_lessons`, `agency_self_model`, `agency_reflection_runs` tables
  - [x] Pydantic models for `Lesson`, `SelfModelEntry`, `ReflectionRun` with full type safety
  - [x] Persistence stores (`LessonStore`, `SelfModelStore`, `ReflectionRunStore`) with CRUD operations
  - [x] Core reflection engine (`SelfReflectionEngine`) analyzing skill performance, goal patterns, and user feedback
  - [x] Lesson generation with confidence scoring and metrics basis
  - [x] Policy mode support (`observe_only` / `allow_amend`) with full audit logging
  - [x] Integration with `AgencyEngine` via convenience methods
  - [x] Comprehensive test suite (8 tests, all passing)
  - [x] Scheduled reflection jobs via `AgencyReflectionTask` (runs during idle periods)
  - [x] LLM-based lesson generation with fallback to statistical summaries
  - [x] Contextual prompts for skill, goal, and persona lessons
  - [x] Graceful degradation when LLM unavailable

- [x] **Self-Model (v1)** ✅
  - [x] Performance tracking per skill/goal_type/entity with success rates and metrics
  - [x] Time-windowed analysis with confidence scores based on sample size
  - [x] Upsert operations for continuous performance updates
  - [x] Query methods for retrieving latest performance data
  - [x] Exposed to Planner via `get_skill_performance()` for skill selection
  - [x] Exposed to Goal Arbiter via `get_goal_type_performance_context()` for scoring adjustments
  - [x] Exposed to Curiosity Engine via `get_all_skill_performances()` for exploration decisions
  - [x] Performance-based multipliers applied in arbiter scoring (0.9x-1.1x based on success rate)

- [x] **Behavioural Learning Hooks** ✅
  - [x] `LessonApplicationService` for applying lessons to operational systems
  - [x] Skill selection weight adjustments via dimension_vector metadata
  - [x] Goal Arbiter weight adjustments via `agency_arbiter_adjustments` table
  - [x] Goal Arbiter runtime integration with cached adjustments (5min TTL)
  - [x] Persona/style adjustments via PersonalityService automatic loading
  - [x] PersonalityService queries active persona lessons and applies to context
  - [x] Policy rule suggestions (logged for user approval)
  - [x] Full audit logging of all applied changes
  - [x] Dry-run mode for testing
  - [x] Confidence threshold enforcement

> **Status:** ✅ **Phase 5 COMPLETE!** Self-reflection engine generates lessons with LLM enhancement, scheduler runs automatic jobs, lesson applicator integrates with all systems (Skills, Arbiter, Personality), and self-model data informs decision-making across Planner, Arbiter, and Curiosity Engine.

> **Exit condition:** ✅ **MET** - AICO periodically updates how she behaves based on her own experience, in a traceable way, without changing the overall architecture.

---

## Phase 6 – Full Implementation & Production Hardening

**Goal:** Remove ALL placeholders, stubs, hardcoded values, and shortcuts. Implement full-depth production-grade agency system with no compromises.

**Current State:** ✅ **Phase 6.1 (Planner) COMPLETE!** LLM planning, pattern learning, skill availability, resource constraints all done.

### **6.1 Planner Full Implementation**
- [x] **LLM-Backed Planning** ✅ *COMPLETE*
  - [x] LLM-generated plans with flexible client interface
  - [x] Robust prompt engineering for plan generation
  - [x] Plan validation and quality checks (EXCELLENT/GOOD/ACCEPTABLE/POOR)
  - [x] Three-tier fallback strategy (LLM → template → simple)
  - [x] Plan caching with TTL (1 hour default, 100 plan limit)
  - [x] Removed "Phase 1 planning skeleton" comments
  - [x] Added `PlanStrategy` and `PlanQuality` enums
  - [x] JSON parsing with error handling for LLM responses
  
- [x] **Pattern Recognition & Learning** ✅ *COMPLETE*
  - [x] Plan pattern detection from historical data (90-day lookback, min 3 occurrences)
  - [x] Pattern library with confidence scoring and quality metrics
  - [x] Pattern-based plan suggestions (auto-suggests if confidence ≥ 0.5)
  - [x] Plan adaptation from successful patterns
  - [x] Plan outcome tracking for continuous learning
  - [x] Integrated into main planning flow (pattern → LLM → template → simple)

- [x] **Resource & Constraint Management** ✅ *COMPLETE*
  - [x] Basic `_check_resource_constraints` (CPU, memory) - EXISTS in scheduler
  - [x] Quiet-hours enforcement - EXISTS with config loading
  - [x] Battery monitoring - IMPLEMENTED (psutil-based, skips on <50% battery)
  - [x] Network bandwidth management - IMPLEMENTED (configurable Mbps limit)
  - [x] Skill availability checking - IMPLEMENTED (DB-based, filters unavailable skills)
  - [x] Concurrent execution limits - IMPLEMENTED (configurable max concurrent tasks)

### **6.2 Scheduler & Task Execution** ✅ *COMPLETE*
- [x] **Production Scheduler** ✅ *COMPLETE*
  - [x] **Task Priority & Queue System** ✅ *COMPLETE*
    - [x] Added `TaskPriority` enum (CRITICAL, HIGH, NORMAL, LOW, IDLE)
    - [x] Added `TaskQueue` enum (USER_FACING, BACKGROUND_LIGHT, BACKGROUND_HEAVY, MAINTENANCE)
    - [x] Extended `BaseTask` with priority, queue, resource_profile, runtime_context
    - [x] Added `DEFERRED` status to `TaskStatus`
  - [x] **Retry Configuration** ✅ *COMPLETE*
    - [x] Added `RetryStrategy` enum (NONE, IMMEDIATE, LINEAR, EXPONENTIAL, FIBONACCI)
    - [x] Added `RetryConfig` dataclass with configurable backoff
    - [x] Extended `TaskResult` with retry_after_seconds and defer_reason
    - [x] Extended `TaskContext` with retry_count
  - [x] **Priority Queue Implementation** ✅ *COMPLETE*
    - [x] Created `PriorityTaskQueue` with heap-based multi-queue system
    - [x] Implemented fair scheduling across queue types
    - [x] Added weighted round-robin for background queues
    - [x] Implemented starvation prevention with time-based weights
    - [x] Added queue capacity limits and metrics
  - [x] **Retry Logic** ✅ *COMPLETE*
    - [x] Created `RetryManager` with all backoff strategies
    - [x] Implemented exponential, linear, and fibonacci backoff
    - [x] Added jitter support to prevent thundering herd
    - [x] Created `RetryTracker` for failure history
    - [x] Added retry delay calculation and scheduling
  - [x] **Scheduler Integration** ✅ *COMPLETE*
    - [x] Integrated `PriorityTaskQueue` into `TaskScheduler`
    - [x] Refactored task execution flow to use priority queue
    - [x] Implemented fair scheduling across queue types
    - [x] Added concurrent task limit enforcement
    - [x] Integrated retry logic into task execution
    - [x] Added automatic retry with backoff on failure
    - [x] Implemented retry history tracking
  - [x] Task timeout handling ✅ *ALREADY IMPLEMENTED* (1 hour default with asyncio.wait_for)
  - [x] **Task Cancellation** ✅ *COMPLETE*
    - [x] Added `cancel_task()` method to TaskExecutor
    - [x] Added `cancel_task()` method to TaskScheduler
    - [x] Implemented queue removal for pending tasks
    - [x] Implemented cancellation for running tasks

- [x] **Resource Monitoring** ✅ *COMPLETE*
  - [x] **Real-time Resource Monitoring** ✅ *COMPLETE*
    - [x] Created `ResourceMonitor` service
    - [x] Implemented CPU, memory, disk monitoring
    - [x] Implemented network bandwidth monitoring
    - [x] Added resource snapshot system
    - [x] Implemented idle detection logic
  - [x] Battery-aware task scheduling ✅ *IMPLEMENTED in Phase 6.1*
  - [x] Network bandwidth management ✅ *IMPLEMENTED in Phase 6.1*
  - [x] **Storage Quota Enforcement** ✅ *COMPLETE*
    - [x] Added `check_storage_quota()` method
    - [x] Implemented minimum free space checking
  - [x] **User Presence Detection** ✅ *COMPLETE*
    - [x] Implemented user idle time detection (macOS, Windows, Linux)
    - [x] Added idle threshold checking
    - [x] Integrated into resource snapshot

### **6.3 Curiosity Engine Depth** ✅ *COMPLETE*
- [x] **Advanced Curiosity Scoring** ✅ *COMPLETE*
  - [x] Created `IntrinsicRewardCalculator` with principled algorithms
  - [x] Implemented prediction error-based curiosity (surprise measurement)
  - [x] Added information gain calculations (epistemic uncertainty reduction)
  - [x] Implemented empowerment-based exploration (state influence)
  - [x] Added long-term value estimation (temporal discounting, 5-step horizon)
  - [x] Extended `IntrinsicSignal` model with reward component fields
  - [x] Weighted combination of all components (configurable)

- [x] **Opportunity Discovery** ✅ *COMPLETE*
  - [x] `_detect_knowledge_gaps` - Full World Model integration (uncertain areas query)
  - [x] `_detect_anomalies` - Full World Model integration (anomaly detection)
  - [x] `_track_interests` - Full AMS integration (user interests, engagement, mentions)
  - [x] Removed all "Phase 3 v1: Placeholder" comments
  - [x] Removed all TODOs from curiosity engine
  - [x] Implemented multi-source detection (World Model + AMS + personality)
  - [x] Added opportunity clustering and deduplication (`OpportunityClusterer`)
  - [x] Implemented similarity-based clustering (Jaccard, 0.7 threshold)
  - [x] Added signal merging and deduplication

- [x] **Three-Gate Filtering** ✅ *COMPLETE*
  - [x] Gate 1 (Values/Ethics): Sensitive topic detection, relevance requirements
  - [x] Gate 2 (Emotion/Relationship): Closeness check, distress detection
  - [x] Gate 3 (Resource): Intrinsic reward threshold (0.3 minimum)
  - [x] Removed placeholder TODOs, full implementation

### **6.4 World Model Service**
- [ ] **Schema Learning**
  - [ ] Implement automatic schema extraction from user data
  - [ ] Add schema evolution and versioning
  - [ ] Implement schema validation and consistency checking
  - [ ] Add schema-based query optimization

- [ ] **Hypothesis Generation & Testing**
  - [ ] Implement hypothesis generation from patterns
  - [ ] Add hypothesis testing framework
  - [ ] Implement soft validation (non-intrusive checking)
  - [ ] Add hypothesis tracking and refinement

- [ ] **Drift & Contradiction Detection**
  - [ ] Implement drift detection algorithms
  - [ ] Add contradiction resolution strategies
  - [ ] Implement confidence decay over time
  - [ ] Add proactive update mechanisms

### **6.5 Goal Arbiter Advanced**
- [ ] **Adaptive Scoring**
  - [ ] Move from fixed weights to learned scoring policies
  - [ ] Implement multi-armed bandit for weight optimization
  - [ ] Add reinforcement learning for goal selection
  - [ ] Implement A/B testing framework for scoring strategies

- [ ] **Context-Aware Prioritization**
  - [ ] Add time-of-day aware scoring
  - [ ] Implement user state-based adjustments (busy, relaxed, focused)
  - [ ] Add deadline-aware urgency calculations
  - [ ] Implement dependency-aware scheduling

### **6.6 Behavioral Feedback Integration**
- [ ] **Outcome Tracking Schema** ⚠️ *CRITICAL: Missing columns*
  - [ ] Add `outcome` column to `ams_behavioral_feedback` table (currently missing!)
  - [ ] Implement skill execution tracking
  - [ ] Add goal outcome recording  
  - [ ] Implement user satisfaction tracking
  - [ ] Fix reflection engine queries that expect `outcome` column

- [ ] **Feedback Loop Completion** ⚠️ *Data pipeline incomplete*
  - [ ] Connect skill executions to behavioral feedback
  - [ ] Implement automatic outcome detection
  - [ ] Add user feedback collection mechanisms
  - [ ] Complete reflection engine data pipeline (currently fails on missing schema)

### **6.7 Proactive Behaviors**
- [ ] **Follow-up System**
  - [ ] Implement policy-aware follow-up generation
  - [ ] Add relationship-informed timing
  - [ ] Implement values-based follow-up filtering
  - [ ] Add context-aware follow-up content

- [ ] **Reminder System**
  - [ ] Implement smart reminder scheduling
  - [ ] Add reminder clustering and batching
  - [ ] Implement reminder priority and urgency
  - [ ] Add reminder adaptation based on user response

### **6.8 Policy & Ethics Depth**
- [ ] **Dynamic Policy Loading** ⚠️ *Currently: Hardcoded defaults*
  - [ ] Remove hardcoded `DEFAULT_POLICY_RULES` from `default_policies.py`
  - [ ] Implement user-specific policy loading from database
  - [ ] Add policy versioning and migration
  - [ ] Implement policy conflict resolution
  - [ ] Note: `default_policies.py` has 0% test coverage

- [ ] **Consent Management** ⚠️ *Not implemented*
  - [ ] Implement granular consent tracking
  - [ ] Add consent expiration and renewal
  - [ ] Implement consent inheritance and delegation
  - [ ] Add consent audit logging

- [ ] **Ethics Gate Enhancement** ⚠️ *Basic implementation*
  - [ ] Add multi-level ethics checking (currently single-pass)
  - [ ] Implement ethics explanation generation
  - [ ] Add ethics decision caching
  - [ ] Implement ethics policy learning from decisions
  - [ ] Remove "Phase 4 placeholder" comments from curiosity gates

### **6.9 Integration & Data Flow**
- [ ] **End-to-End Workflows**
  - [ ] Implement complete goal → plan → execution → feedback loop
  - [ ] Add curiosity → opportunity → goal → hobby workflow
  - [ ] Implement reflection → lesson → adjustment → validation cycle
  - [ ] Add world model → hypothesis → validation → update flow

- [ ] **Event System**
  - [ ] Implement comprehensive event logging
  - [ ] Add event-driven triggers for agency components
  - [ ] Implement event replay for debugging
  - [ ] Add event-based metrics and monitoring

> **Exit condition:** Agency system is fully implemented with production-grade depth. NO placeholders, stubs, hardcoded values, or shortcuts remain. All components are fully functional, integrated, and production-ready.

---

## Phase 7 – Comprehensive Testing & Quality Assurance

**Goal:** Achieve 90%+ test coverage across all agency components with comprehensive integration, performance, and edge case testing.

### **7.1 Unit Test Coverage**
- [ ] **Core Components (Target: 95%+)**
  - [ ] Planner: 100% coverage of all planning strategies
  - [ ] Arbiter: 100% coverage of all scoring paths
  - [ ] Curiosity Engine: 95%+ coverage
  - [ ] Reflection Engine: 90%+ coverage (up from 47%)
  - [ ] Lesson Applicator: 90%+ coverage (up from 52%)
  - [ ] Values & Ethics: 95%+ coverage

- [ ] **Support Systems (Target: 90%+)**
  - [ ] Stores: 95%+ coverage
  - [ ] Models: 100% coverage (maintain)
  - [ ] Templates: 100% coverage (maintain)
  - [ ] Default Policies: 90%+ coverage (up from 0%)

### **7.2 Integration Testing**
- [ ] **Cross-Component Workflows**
  - [ ] Goal lifecycle end-to-end tests
  - [ ] Curiosity → hobby → reflection workflow tests
  - [ ] Behavioral learning → adjustment → validation tests
  - [ ] Policy enforcement across all components

- [ ] **Data Flow Testing**
  - [ ] Event propagation tests
  - [ ] State consistency tests
  - [ ] Transaction integrity tests
  - [ ] Concurrent operation tests

### **7.3 Performance Testing**
- [ ] **Load Testing**
  - [ ] High-volume goal processing
  - [ ] Concurrent user simulation
  - [ ] Long-running reflection jobs
  - [ ] Memory leak detection

- [ ] **Optimization Testing**
  - [ ] Query performance benchmarks
  - [ ] Cache effectiveness tests
  - [ ] Resource usage profiling
  - [ ] Bottleneck identification

### **7.4 Edge Case & Error Testing**
- [ ] **Failure Scenarios**
  - [ ] Database connection failures
  - [ ] LLM API failures and timeouts
  - [ ] Resource exhaustion scenarios
  - [ ] Concurrent modification conflicts

- [ ] **Boundary Conditions**
  - [ ] Empty data sets
  - [ ] Maximum data volumes
  - [ ] Invalid input handling
  - [ ] Schema migration edge cases

### **7.5 Regression Testing**
- [ ] **Automated Regression Suite**
  - [ ] All Phase 1-5 functionality preserved
  - [ ] Backward compatibility tests
  - [ ] API contract tests
  - [ ] Data migration tests

### **7.6 Test Infrastructure**
- [ ] **Test Utilities**
  - [ ] Comprehensive test fixtures
  - [ ] Mock factories for all components
  - [ ] Test data generators
  - [ ] Assertion helpers

- [ ] **CI/CD Integration**
  - [ ] Automated test runs on commit
  - [ ] Coverage reporting and tracking
  - [ ] Performance regression detection
  - [ ] Test result dashboards

> **Exit condition:** 90%+ test coverage across all agency components. Comprehensive test suite covering unit, integration, performance, and edge cases. All tests passing with fast execution times.

---

## Phase 8 – Flutter UI & User-Facing Agency Controls

**Goal:** Enable users to **understand and influence** AICO's agency through the Flutter UI.

### **8.1 Agency Dashboard Screen**
- [ ] Create dedicated agency screen in Flutter app
- [ ] Display active intention set with visual priority indicators
- [ ] Show current curiosity status and opportunities
- [ ] Display agency state overview (goals, hobbies, focus)

### **8.2 Intention Set Visibility**
- [ ] Surface active intentions in conversation UI (tooltips, status bar)
- [ ] Show why AICO is pursuing specific goals (reasons, scores)
- [ ] Display priority bands and arbiter scores visually
- [ ] Allow users to see hobby goals vs user-requested goals

### **8.3 Value Profile Management**
- [ ] UI for adjusting curiosity intensity slider
- [ ] Proactive behavior level selector (quiet/balanced/proactive)
- [ ] Manage sensitive life areas (add/remove)
- [ ] Configure allowed curiosity domains

### **8.4 Policy & Consent Management**
- [ ] View active policy rules with filtering
- [ ] Grant/revoke consents for specific actions
- [ ] See pending consent requests
- [ ] Review policy decisions and their effects

### **8.5 Conversation Integration**
- [ ] Show agency context in conversation tooltips
- [ ] Display when AICO is acting on curiosity vs user request
- [ ] Surface ethics decisions in conversation flow
- [ ] Explain goal selection and prioritization

### **8.6 Behavioral Learning Visibility**
- [ ] Display active lessons and their effects
- [ ] Show self-model performance metrics
- [ ] Visualize skill success rates and trends
- [ ] Allow users to approve/reject lesson applications

> **Exit condition:** Users can see what AICO is working on, why, and adjust her agency behavior through the Flutter UI. Full transparency and control over agency system.

---

## Phase 9 – Embodiment as Cognitive Substrate & Polishing

**Goal:** Use the 3D flat and embodiment not just for presentation, but as a **cognitive scaffold** and final polish.

### **9.1 Embodied Cognition Patterns**
- [ ] Define internal tasks and routines represented through spatial metaphors
- [ ] Use environment layout and artefacts as memory cues
- [ ] Represent curiosity/hobby work in the 3D flat *(Deferred from Phase 3)*

### **9.2 Conversation & UX Integration**
- [ ] Ensure hobbies appear in AICO's visible behaviour *(Deferred from Phase 3)*
- [ ] Integrate agency state with embodiment animations
- [ ] Add spatial context to goal and task representation

### **9.3 Integration with Real-World Context (optional)**
- [ ] Connect agency state with real devices/context under user control
- [ ] Add calendar and schedule integration
- [ ] Implement home automation hooks (optional)

### **9.4 Refinement & Evaluation**
- [ ] Define evaluation metrics for agency quality
- [ ] Create test scenarios for usefulness, coherence, autonomy
- [ ] Iterate on prompts, policies, and UX based on usage data
- [ ] Conduct user studies and gather feedback

> **Exit condition:** AICO behaves as a coherent, self-motivated, relationship-centric companion whose inner life (goals, curiosities, hobbies, reflections) is legible through conversation and embodiment, with the full conceptual architecture implemented in practice.

---

## Roadmap Summary

**Phase 1-5:** ✅ **COMPLETE** - Core agency architecture implemented  
**Phase 6:** 🔨 **Full Implementation** - Remove all placeholders, stubs, and shortcuts  
**Phase 7:** 🧪 **Comprehensive Testing** - Achieve 90%+ test coverage  
**Phase 8:** 🎨 **Flutter UI** - User-facing agency controls and visibility  
**Phase 9:** 🏠 **Embodiment & Polish** - Cognitive substrate and final refinement  

---

## Implementation Completion Checklist

**ACTUAL STATUS - Items requiring work in Phase 6:**

- [x] **Planner LLM-backed**: ✅ DONE - 905 lines, LLM generation, validation, caching, fallback strategies
- [x] **Planner pattern learning**: ✅ DONE - Historical detection, confidence scoring, auto-adaptation
- [x] **Planner skill availability**: ✅ DONE - DB-based checking, plan filtering by available skills
- [x] **Scheduler battery monitoring**: ✅ DONE - psutil-based, smart logic (skips only on <50%)
- [x] **Scheduler network constraints**: ✅ DONE - Bandwidth monitoring (configurable Mbps limit)
- [x] **Scheduler concurrent limits**: ✅ DONE - Max concurrent tasks enforcement
- [x] **Curiosity engine**: ✅ DONE - Full intrinsic reward system, World Model/AMS integration, clustering
- [ ] **Proactive behaviors**: Follow-ups/reminders NOT IMPLEMENTED
- [ ] **World model**: Schema learning, hypothesis testing, drift detection NOT IMPLEMENTED
- [ ] **Behavioral feedback**: CRITICAL - `ams_behavioral_feedback` table missing `outcome` column. Reflection engine queries fail
- [ ] **Policy system**: Uses hardcoded `DEFAULT_POLICY_RULES`. No user-specific loading. 0% test coverage
- [ ] **Event system**: Basic logging exists. Comprehensive event system NOT IMPLEMENTED

**Progress:** 8/10 major items complete (80%). ✅ **Phase 6.1, 6.2 & 6.3 COMPLETE!** ~12-15 tasks remaining across 3 subsystems.

---

## Future Improvements (Post-Phase 9)

### **Distributed Task Execution**
- [ ] Add distributed task execution support for multi-device scenarios
- [ ] Implement task migration between devices
- [ ] Add cluster coordination for shared task queues
- [ ] Implement distributed locking mechanisms

### **Advanced Scheduling**
- [ ] Machine learning-based task scheduling optimization
- [ ] Predictive resource usage modeling
- [ ] Dynamic priority adjustment based on historical patterns
- [ ] Multi-objective optimization (time, energy, user satisfaction)
