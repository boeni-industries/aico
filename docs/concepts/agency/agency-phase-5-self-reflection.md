---
title: Phase 5 - Self-Reflection & Behavioral Learning
---

# Phase 5 – Self-Reflection, Self-Model & Behavioural Learning ✅

**Status:** Complete

**Goal:** Enable AICO to **evaluate her own behaviour** and adapt policies and skills over time.

---

## Implementation

### Self-Reflection Engine (v1) ✅
- [x] Database schema v24
  - `agency_lessons`, `agency_self_model`, `agency_reflection_runs` tables
- [x] Pydantic models with full type safety
  - `Lesson`, `SelfModelEntry`, `ReflectionRun`
- [x] Persistence stores with CRUD operations
  - `LessonStore`, `SelfModelStore`, `ReflectionRunStore`
- [x] Core reflection engine
  - `SelfReflectionEngine` analyzing skill performance, goal patterns, user feedback
- [x] Lesson generation
  - Confidence scoring and metrics basis
- [x] Policy mode support
  - `observe_only` / `allow_amend` with full audit logging
- [x] Integration with `AgencyEngine`
  - Via convenience methods
- [x] Comprehensive test suite
  - 8 tests, all passing
- [x] Scheduled reflection jobs
  - `AgencyReflectionTask` runs during idle periods
- [x] LLM-based lesson generation
  - Fallback to statistical summaries
- [x] Contextual prompts
  - For skill, goal, and persona lessons
- [x] Graceful degradation when LLM unavailable

### Self-Model (v1) ✅
- [x] Performance tracking per skill/goal_type/entity
  - Success rates and metrics
- [x] Time-windowed analysis
  - Confidence scores based on sample size
- [x] Upsert operations for continuous performance updates
- [x] Query methods for retrieving latest performance data
- [x] Exposed to Planner
  - Via `get_skill_performance()` for skill selection
- [x] Exposed to Goal Arbiter
  - Via `get_goal_type_performance_context()` for scoring adjustments
- [x] Exposed to Curiosity Engine
  - Via `get_all_skill_performances()` for exploration decisions
- [x] Performance-based multipliers
  - Applied in arbiter scoring (0.9x-1.1x based on success rate)

### Behavioural Learning Hooks ✅
- [x] `LessonApplicationService`
  - For applying lessons to operational systems
- [x] Skill selection weight adjustments
  - Via dimension_vector metadata
- [x] Goal Arbiter weight adjustments
  - Via `agency_arbiter_adjustments` table
- [x] Goal Arbiter runtime integration
  - Cached adjustments (5min TTL)
- [x] Persona/style adjustments
  - Via PersonalityService automatic loading
- [x] PersonalityService queries active persona lessons
  - Applies to context
- [x] Policy rule suggestions
  - Logged for user approval
- [x] Full audit logging of all applied changes
- [x] Dry-run mode for testing
- [x] Confidence threshold enforcement

---

## Achievements

**Data:**
- 41 lessons generated
- 1,437 reflection runs completed
- 2,257 self-model entries tracked

**Integration:**
- Self-reflection engine generates lessons with LLM enhancement
- Scheduler runs automatic jobs
- Lesson applicator integrates with all systems (Skills, Arbiter, Personality)
- Self-model data informs decision-making across Planner, Arbiter, and Curiosity Engine

---

## Exit Condition ✅

AICO periodically updates how she behaves based on her own experience, in a traceable way, without changing the overall architecture.

---

## Related Documentation

- [Phase 4: Values & Ethics](agency-phase-4-values-ethics.md)
- [Phase 6: Advanced Integration](agency-phase-6-advanced-integration.md)
- [Roadmap Overview](agency-roadmap-overview.md)
