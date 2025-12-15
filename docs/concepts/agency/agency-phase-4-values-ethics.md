---
title: Phase 4 - Values, Ethics & Meta-Control
---

# Phase 4 – Goal Arbiter, Values/Ethics & Meta-Control ✅

**Status:** Complete (December 10, 2025)

**Goal:** Introduce a clear **decision layer** that balances user goals, curiosity, hobbies, and maintenance under constraints.

---

## Implementation

### Goal Arbiter & Meta-Control (v1) ✅
- [x] Implement Goal Arbiter
  - Collects goal candidates from user, Curiosity Engine, and system tasks
- [x] Define scoring/ranking function
  - Based on: priority, user configuration, personality, emotion, relationship vectors, and values
- [x] Maintain explicit "active intention set"
  - Publish to other components

### Values & Ethics Layer (v1) ✅
- [x] Implement Values & Ethics module
  - Configurable rule set plus optional LLM-based classifiers
- [x] Integrate as gate in front of goals/plans/skills
  - Block, require consent, annotate as risky
- [x] Make values/ethics constraints fully configurable
  - Tighten, relax, or disable where permissible
- [x] Design and migrate concrete schemas
  - `value_profiles`, `policy_rules`, `consents` tables
- [x] Implement Values & Ethics service API
  - Used by agency, Self-Reflection, and Safety & Control
- [x] Integrate Safety & Control configuration
  - Autonomy levels, consent requirements, quiet hours
  - Consistently enforced via Values & Ethics gate and `AgencyPlugin`

### Backend Integration ✅
- [x] Surface agency decisions in conversation logging
- [x] REST API endpoints for Flutter integration
  - `/api/v1/agency/*`
  - Encrypted database access with session support
  - Full test coverage with real database

---

## Achievements

- ✅ AgencyEngine integrates ValuesEthicsService and GoalArbiter
- ✅ Message bus integration working
- ✅ Configuration system complete with validation
- ✅ Database schemas migrated (v23: added agency_context to trajectories)
- ✅ Default policies installed and enforced
- ✅ Backend fully operational with all Phase 4 services running
- ✅ Comprehensive test suite: **120 tests passing** (including 12 new API endpoint tests)
- ✅ CLI commands implemented and tested (`aico agency`)
- ✅ Agency decisions logged to conversation trajectories

---

## Exit Condition ✅

AICO's behaviour is governed by an explicit meta-control layer backend.

---

## Related Documentation

- [Phase 3: Curiosity & Hobbies](agency-phase-3-curiosity-hobbies.md)
- [Phase 5: Self-Reflection](agency-phase-5-self-reflection.md)
- [Roadmap Overview](agency-roadmap-overview.md)
