---
title: Agency Implementation Roadmap
---

# Agency Implementation Roadmap

> **Note:** This roadmap has been restructured for better readability. See individual phase documents for detailed implementation information.

This document provides a high-level overview of AICO's agency system implementation across 10 phases.

## Implementation Principles

- Each phase yields a **testable, usable system**
- Phases are cumulative: later work **extends** existing modules
- Implementation follows integration contracts in `agency-integration.md`

## Current Status

This roadmap is intentionally high-level. For the most up-to-date implementation status and metrics, use:

- `docs/concepts/agency/agency-roadmap-status.md`
- the CLI (`cli/commands/agency.py`, e.g. `aico agency status`, `aico agency metrics`, `aico agency health`)

[→ Detailed Current Status](agency-roadmap-status.md)

---

## Phase Overview

### Phase 0: Foundations & Enablement ✅
**Goal:** Platform readiness for always-on agency loop

**Status:** Complete

**Key Achievements:**
- Localization infrastructure
- Agency engine integration
- Core database tables

---

### Phase 1: Goal System & Planning ✅
**Goal:** Goal- and plan-aware companion with persistent intentions

**Status:** Complete

**Key Achievements:**
- Goal/Intention models and storage
- Planning component with LLM integration
- Scheduler integration with resource constraints

---

### Phase 2: Memory, World Model & Relationships ✅
**Goal:** Ground goals in rich memory and world understanding

**Status:** Complete (December 9, 2025)

**Key Achievements:**
- WorldModelService with KG integration
- PersonalityService with Big Five traits
- 54 comprehensive tests, 73% coverage

---

### Phase 3: Curiosity, Intrinsic Motivation & Hobbies ✅
**Goal:** Self-driven exploration and learning

**Status:** Complete (December 9, 2025)

**Key Achievements:**
- CuriosityEngine with 3 detectors
- 6 default hobby templates
- Three-gate filtering system

---

### Phase 4: Values, Ethics & Meta-Control ✅
**Goal:** Explicit meta-control layer for behavior governance

**Status:** Complete (December 10, 2025)

**Key Achievements:**
- ValuesEthicsService with policy rules
- GoalArbiter with adaptive scoring
- 120 tests passing, full backend integration

---

### Phase 5: Self-Reflection & Behavioral Learning ✅
**Goal:** Self-evaluation and adaptive policy/skill adjustments

**Status:** Complete

**Key Achievements:**
- SelfReflectionEngine with LLM enhancement
- LessonApplicationService
- 41 lessons, 1,437 reflection runs, 2,257 self-model entries

---

### Phase 6: Advanced Integration & Optimization ✅
**Goal:** Complete missing integrations and optimize performance

**Status:** Complete

**Key Achievements:**
- Adaptive arbiter with multi-armed bandits
- World model drift detection
- Hypothesis generation and testing

---

### Phase 7: Comprehensive Testing & QA ✅
**Goal:** 80%+ test coverage with comprehensive testing

**Status:** Complete

**Key Achievements:**
- 943 tests passing (+232 new tests)
- 80% overall coverage
- Skills database schema corrected
- 90.7% warning reduction (6,199 → 575)

---

### Phase 8: Agency CLI & Analysis ✅
**Goal:** CLI-first interface for observing and analyzing agency behavior

**Status:** Complete

**Key Achievements:**
- 13 CLI commands implemented (1,633 lines)
- Comprehensive event logging (1,188+ events)
- Advanced analytics with time window filtering
- Health monitoring and diagnostics
- Reflection run analysis
- Skill performance tracking

---

### Phase 9: Lesson Management CLI ✅
**Goal:** CLI tooling for lesson review and approval

**Status:** Complete (2025-12-15)

**Completed:**
- ✅ Lesson management CLI (5 commands)
- ✅ `aico agency lessons ls` - List and filter lessons
- ✅ `aico agency lessons show` - Detailed lesson view
- ✅ `aico agency lessons approve/reject` - Approval workflow
- ✅ `aico agency lessons stats` - Lesson statistics
- ✅ Full filtering support (status, confidence, time windows)
- ✅ JSON output and rich table formatting

---

### Phase 10: Web Dashboard & REST API 🔮
**Goal:** REST API and web dashboard for monitoring and administration

**Status:** Future

**Scope:**
- REST API endpoints for metrics and lessons
- Web dashboard with real-time visualization
- Metrics and analytics visualization
- Lesson management interface
- System health monitoring

---

### Phase 11: Flutter Frontend Integration 🔮
**Goal:** Integrate agency system into Flutter mobile/desktop app

**Status:** Future

**Scope:**
- Proactive message integration and notifications
- Intention set visibility in conversation UI
- Goal tracking and progress display
- Behavioral feedback and lesson review
- Agency settings and controls
- Real-time WebSocket updates
- Metrics and analytics visualization

---

## Future Enhancements

These items were deferred from completed phases and represent potential improvements for future development.

### Memory & AMS Integration
**From Phase 2:**
- [ ] Use AMS summaries and open-loop lists when (re)formulating goals and plans
- [ ] Temporal pattern detection
- [ ] Uncertainty area identification
- [ ] AMS unified indexing and cross-tier lifecycle automation

### Analytics & Observability
**From Phase 8:**
- [ ] Expected vs actual behavior reports
- [ ] Arbiter decisions vs goal outcomes correlation analysis
- [ ] Curiosity-driven goals analysis (creation vs completion vs rejection rates)
- [ ] CI/CD integration for behavioral regression detection

### Performance & Optimization
**Future Considerations:**
- [ ] Batch processing for plan executions
- [ ] Caching strategies for frequently accessed metrics
- [ ] Query optimization for large-scale deployments

---

## Related Documentation

- [Agency Architecture](agency-architecture.md)
- [Agency Integration Contracts](agency-integration.md)
- [Agency Metrics](agency-metrics.md)
- [Skills & Tools](agency-component-skills-tools.md)
- [Current Implementation Status](agency-roadmap-status.md)

---

## Quick Navigation

Last Updated: 2025-12-15
