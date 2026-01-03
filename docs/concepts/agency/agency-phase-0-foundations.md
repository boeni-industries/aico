---
title: Phase 0 - Foundations & Enablement
---

# Phase 0 – Foundations & Enablement ✅

**Status:** Complete

**Goal:** Ensure the existing platform can host an always-on agency loop with clear extension points.

---

## Implementation

### Localisation Prep & Conversation Language Signal ✅
- [x] Add core language metadata columns to users, memories, KG nodes, and skills
  - See `SchemaVersion 19` in `shared/aico/data/schemas/core.py`
- [x] Implement unified per-user `primary_language` and per-conversation `conversation_language` signal
  - Wired through ConversationEngine → MemoryManager → KG → Skills
  - See `WIP_full_localization.md`

### Conversation & Config Wiring ✅
- [x] Expose `enable_agency` feature flag and configuration options
  - In `core.conversation` and related configs
- [x] Define minimal `AgencyEngine`/service interface
  - Register via `LifecycleManager` / plugin registry
- [x] Integrate basic agency context hooks into `ConversationEngine`
  - Phase 0: call AgencyPlugin and log contract-shaped responses without changing behaviour
- [x] Implement `backend.services.agency_engine.AgencyPlugin.process`
  - Contract-compliant stub returning structured, empty suggestions/goals
- [x] Wire `AgencyPlugin` into conversation flows
  - Behind `enable_agency` flag for safe enablement

### Persistence & Telemetry Prereqs ✅
- [x] Define core tables/collections
  - `agency_goals`, `agency_plans`, `agency_events`, `agency_reflection_notes`
  - See `SchemaVersion 19`
- [x] Ensure rich logging and telemetry
  - Support evaluation and self-reflection
  - `agency_events` captures IDs, timestamps, and structured payloads

---

## Exit Condition ✅

Platform ready to host always-on agency loop with:
- Feature flags for safe enablement
- Core database schema in place
- Logging infrastructure for telemetry
- Plugin architecture for agency integration

---

## Related Documentation

- [Phase 1: Goals & Planning](agency-phase-1-goals-planning.md)
- [Roadmap Overview](agency-roadmap-overview.md)
- [Current Status](agency-roadmap-status.md)
