---
title: Phase 3 - Curiosity, Intrinsic Motivation & Hobbies
---

# Phase 3 – Curiosity, Intrinsic Motivation & Hobbies ✅

**Status:** Complete (December 9, 2025)

**Goal:** Give AICO **her own intrinsic drives** and hobbies that generate agent-self goals.

---

## Implementation

### Curiosity Engine (v1) ✅
- [x] Implement Curiosity Engine
  - Scans AMS, world model, and interaction history
  - Identifies gaps, anomalies, or under-explored topics
  - Location: `shared/aico/ai/curiosity/`
- [x] Define `IntrinsicSignal`/"curiosity opportunity" data structure
  - Basic scoring (heuristics + LLM prompts)
  - 4 curiosity types: knowledge_gap, novelty, self_performance, hobby_play
- [x] Feed curiosity-derived goal candidates into Goal System
  - Via `create_goal_from_curiosity_signal()`

### Hobbies & Agent-Self Goals ✅
- [x] Define curated set of hobby templates
  - Learning domains, conversational styles, organizing the 3D flat, internal research notebooks
  - 6 default hobby templates (learning, organizing, research categories)
- [x] Allow Curiosity Engine and Self-Reflection to instantiate and update hobby goals

### Lifecycle Integration ✅
- [x] Use Lifecycle & Daily Rhythm to allocate time for curiosity/hobbies
  - Idle spans, specific windows
- [x] Add lifecycle and agency-readiness flags
  - In `scheduled_tasks.config` for agency-related tasks
- [x] Implement lifecycle-aware deferral logic
  - Inside agency tasks (and later, centrally in scheduler if needed)
  - Respects idle/active state, quiet hours

---

## Achievements

**Implemented:**
- ✅ CuriosityEngine with 3 detectors
- ✅ IntrinsicSignal model with 4 curiosity types
- ✅ 6 default hobby templates
- ✅ Three-gate filtering system (Values/Ethics placeholder, Emotion/relationship, Resource)
- ✅ Personality-based scoring (openness, conscientiousness modifiers)
- ✅ Goal System integration
- ✅ Scheduled task: `curiosity_scan` (every 6 hours)
- ✅ Lifecycle-aware deferral
- ✅ Backend wiring in `lifecycle_manager.py`

---

## Exit Condition ✅

AICO regularly pursues self-generated curiosity and hobby goals, visibly distinct from direct user requests, within user-configurable bounds.

---

## Documentation

- [Curiosity Engine Component](agency-component-curiosity-engine.md)
- [Ontology Schemas](agency-ontology-schemas.md)

---

## Related Documentation

- [Phase 2: Memory & World Model](agency-phase-2-memory-world-model.md)
- [Phase 4: Values & Ethics](agency-phase-4-values-ethics.md)
- [Roadmap Overview](agency-roadmap-overview.md)
