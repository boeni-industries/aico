---
title: Agency Implementation Roadmap
---

# Agency Implementation Roadmap

This roadmap translates the conceptual agency design into an incremental implementation plan. 

- Each phase should yield a **testable, usable system**.
- Phases are cumulative: later work **extends** existing modules instead of replacing them.
- Items are written as checkable bullets (`[ ]`) so progress can be tracked.

## Phase 0 – Foundations & Enablement

Goal: Ensure the existing platform can host an always-on agency loop with clear extension points.

- [ ] **Conversation & Config Wiring**
  - [ ] Expose `enable_agency` feature flag and configuration options in `core.conversation` and related configs.
  - [ ] Define a minimal `AgencyEngine`/service interface and register it via `LifecycleManager` / `ai_registry`.
  - [ ] Integrate basic agency context hooks into `ConversationEngine` (e.g. pass active goals, agency state into prompts).

- [ ] **Persistence & Telemetry Prereqs**
  - [ ] Define core tables/collections (if needed) for goals, plans, agency logs, self-reflection notes.
  - [ ] Ensure logging and telemetry are rich enough to support evaluation and self-reflection (IDs, timestamps, outcomes).

## Phase 1 – Goal System & Planning Skeleton (First Testable Agent)

Goal: Move from stateless chatbot to a **goal- and plan-aware companion** with persistent intentions.

- [ ] **Goal & Intention System (core data structures)**
  - [ ] Implement `Goal` / `Intention` models (including origin: user, curiosity, hobby, system-maintenance).
  - [ ] Implement storage, retrieval, and lifecycle operations (create, activate, pause, complete, retire).
  - [ ] Add support for **agent-self goals and hobbies** as first-class objects.

- [ ] **Planning & Decomposition (v1)**
  - [ ] Implement a Planning component that converts goals into simple plans (linear or shallow branches).
  - [ ] Use templated LLM prompts plus hand-authored patterns for common plan shapes.
  - [ ] Store plans and steps with links back to goals and tools/skills.

- [ ] **Scheduler Integration (v1)**
  - [ ] Integrate plans with the existing Task Scheduler (schedule follow-ups, reminders, background tasks).
  - [ ] Respect quiet hours and basic user preferences.

- [ ] **Basic Proactive Behaviour**
  - [ ] Introduce simple proactive behaviours: follow-up messages, reminders based on open goals.
  - [ ] Make agency activity visible in conversation logs and, optionally, the 3D avatar (basic room/posture mapping).

> **Exit condition:** AICO keeps track of goals across sessions, can form simple multi-step plans, and can proactively act on them in a controlled way.

## Phase 2 – Memory, World Model & Relationship Integration

Goal: Ground goals and plans in **rich memory and world understanding**, not just recent turns.

- [ ] **AMS Integration (v1)**
  - [ ] Connect Goal System and Planning to AMS for retrieving context, preferences, and open loops.
  - [ ] Use AMS summaries and open-loop lists when (re)formulating goals and plans.

- [ ] **World Model & Knowledge/Property Graph (v1)**
  - [ ] Implement a `WorldModelService` API that wraps the existing KG + semantic memory.
  - [ ] Provide basic queries such as: entities around a user, projects, recurring contexts, uncertain/unknown areas.
  - [ ] Expose world model views to Planner and Curiosity Engine.

- [ ] **Social & Personality Hooks**
  - [ ] Wire Personality Simulation traits/values into goal creation and plan style.
  - [ ] Include relationship vectors from Social Relationship Modeling in goal selection (e.g. proactivity per user, topic boundaries).

> **Exit condition:** Goals and plans are meaningfully influenced by long-term memory, social context, and world structure; AICO feels more consistent and “aware” over time.

## Phase 3 – Curiosity, Intrinsic Motivation & Hobbies

Goal: Give AICO **her own intrinsic drives** and hobbies that generate agent-self goals.

- [ ] **Curiosity Engine (v1)**
  - [ ] Implement a Curiosity Engine that scans AMS, world model, and interaction history for gaps, anomalies, or under-explored topics.
  - [ ] Define an `IntrinsicSignal`/"curiosity opportunity" data structure with basic scoring (heuristics + LLM prompts).
  - [ ] Feed curiosity-derived goal candidates into the Goal System.

- [ ] **Hobbies & Agent-Self Goals**
  - [ ] Define a small, curated set of hobby templates (e.g. learning domains, conversational styles, organizing the 3D flat, internal research notebooks).
  - [ ] Allow Curiosity Engine and Self-Reflection to instantiate and update these hobby goals.
  - [ ] Ensure hobbies appear in AICOs visible behaviour (comments, embodiment, occasional sharing with the user).

- [ ] **Lifecycle Integration**
  - [ ] Use Lifecycle & Daily Rhythm to allocate time for curiosity/hobbies (idle spans, specific windows).
  - [ ] Represent curiosity/hobby work in the 3D flat (e.g., AICO at the desk reading, on the couch studying, reorganizing her room).

> **Exit condition:** AICO regularly pursues self-generated curiosity and hobby goals, visibly distinct from direct user requests, within user-configurable bounds.

## Phase 4 – Goal Arbiter, Values/Ethics & Meta-Control

Goal: Introduce a clear **decision layer** that balances user goals, curiosity, hobbies, and maintenance under constraints.

- [ ] **Goal Arbiter & Meta-Control (v1)**
  - [ ] Implement a Goal Arbiter that collects goal candidates from user, Curiosity Engine, and system tasks.
  - [ ] Define a scoring/ranking function based on: priority, user configuration, personality, emotion, relationship vectors, and values.
  - [ ] Maintain an explicit "active intention set" and publish it to other components.

- [ ] **Values & Ethics Layer (v1)**
  - [ ] Implement the Values & Ethics module with a configurable rule set plus optional LLM-based classifiers.
  - [ ] Integrate it as a gate in front of goals/plans/skills (block, require consent, annotate as risky).
  - [ ] Make values/ethics constraints fully configurable (tighten, relax, or disable where permissible).

- [ ] **Conversation & UX Integration**
  - [ ] Surface the active intention set and value/ethics decisions in explanations/tooltips/logs.
  - [ ] Allow users to inspect and adjust agency behaviour (e.g., tune curiosity strength, hobby intensity, initiative level).

> **Exit condition:** AICOs behaviour is governed by an explicit meta-control layer, and users can understand and influence why some goals are pursued and others are not.

## Phase 5 – Self-Reflection, Self-Model & Behavioural Learning

Goal: Enable AICO to **evaluate her own behaviour** and adapt policies and skills over time.

- [ ] **Self-Reflection Engine (v1)**
  - [ ] Implement scheduled reflection jobs (often during AMS "sleep" phases).
  - [ ] Define `Lesson` / self-reflection record structures based on logs, outcomes, and user feedback.
  - [ ] Use LLM prompts to derive simple behavioural lessons (what to do more/less of, timing, tone).

- [ ] **Self-Model (v1)**
  - [ ] Maintain a lightweight self-model summarizing recent performance per skill and per user.
  - [ ] Expose self-model information to Planner, Goal Arbiter, and Curiosity Engine.

- [ ] **Behavioural Learning Hooks**
  - [ ] Integrate lessons into existing or planned behavioural learning stores (e.g., skill metadata, preference weights).
  - [ ] Log changes in strategy so they can be audited and rolled back if needed.

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

- [ ] **Integration with Real-World Context (optional)**
  - [ ] Optionally connect agency state and embodiment with real devices/context (e.g., phone, calendar, home automation) under strict user control.

- [ ] **Refinement & Evaluation**
  - [ ] Define evaluation metrics and test scenarios for agency quality (usefulness, coherence, autonomy, user comfort).
  - [ ] Iterate on prompts, policies, and UX based on real usage data.

> **Exit condition:** AICO behaves as a coherent, self-motivated, relationship-centric companion whose inner life (goals, curiosities, hobbies, reflections) is legible through conversation and embodiment, with the full conceptual architecture implemented in practice.
