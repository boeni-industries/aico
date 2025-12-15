---
title: Phase 1 - Goal System & Planning
---

# Phase 1 – Goal System & Planning Skeleton ✅

**Status:** Complete

**Goal:** Move from stateless chatbot to a **goal- and plan-aware companion** with persistent intentions.

---

## Implementation

### Goal & Intention System ✅
- [x] Implement `Goal` / `Intention` models
  - Including origin: user, curiosity, hobby, system-maintenance
- [x] Implement storage, retrieval, and lifecycle operations
  - Create, activate, pause, complete, retire
- [x] Add support for **agent-self goals and hobbies** as first-class objects

### Planning & Decomposition (v1) ✅
- [x] Implement Planning component
  - Converts goals into simple plans (linear or shallow branches)
- [x] Use templated LLM prompts plus hand-authored patterns
  - Common plan shapes
- [x] Store plans and steps
  - Links back to goals and tools/skills

### Scheduler Integration (v1) ✅
- [x] Integrate plans with existing Task Scheduler
  - Schedule follow-ups, reminders, background tasks
- [x] Respect quiet hours and basic user preferences
- [x] Implement basic resource constraint checks
  - CPU/memory/battery/idle state in `TaskExecutor._check_resource_constraints`

### Basic Proactive Behaviour ✅
- [x] Introduce simple proactive behaviours
  - Follow-up messages, reminders based on open goals
- [x] Make agency activity visible
  - Conversation logs and 3D avatar (basic room/posture mapping)

---

## Exit Condition ✅

AICO keeps track of goals across sessions, can form simple multi-step plans, and can proactively act on them in a controlled way.

---

## Related Documentation

- [Phase 0: Foundations](agency-phase-0-foundations.md)
- [Phase 2: Memory & World Model](agency-phase-2-memory-world-model.md)
- [Roadmap Overview](agency-roadmap-overview.md)
