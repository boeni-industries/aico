---
title: Phase 8 - Agency CLI & Analysis
---

# Phase 8 – Agency CLI & Analysis ✅

**Status:** Complete

**Goal:** Provide a **CLI-first interface** for observing, analyzing, and validating the real-world behavior of the Agency system against the conceptual design.

**Current Status:** Core CLI commands and event instrumentation implemented. Comprehensive event logging system operational with 1,188+ events tracked.

---

## Metrics Collection & Exposure ✅

### Wire Metrics to Storage ✅
**Implemented:**
- Comprehensive event logging system
  - Tables: `agency_events`, `agency_events_log`, `event_metrics`
- Metrics tracked:
  - **Reflection:** lessons_generated, lessons_applied, reflection run timestamps (1,437 runs)
  - **Goals & Planning:** goal_lifecycle_events, plan execution tracking (108 goals, 108 plans, 3,710 executions)
  - **Skills & Curiosity:** skill_performance (486 skills, 48 executions tracked)
- Stored in queryable PostgreSQL tables with comprehensive indexing
- **Active data:** 382 agency_events, 224 agency_events_log, 582 event_metrics

### Event & Outcome Instrumentation ✅
**Implemented:**
- Comprehensive `EventSystem` in `workflows.py` (1,384 lines)
- Structured events emitted for all key workflows:
  - Goal creation/completion/lifecycle events
  - Reflection run start/end with lesson tracking
  - Lesson application with audit trail
  - Policy decisions and ethics gates
- Outcome labels attached (success/failure, severity levels)
- Event correlation via `workflow_trace_id` linking (52 workflow executions, 232 stages)
- Full integration with reflection runs and lessons

---

## Agency CLI Commands ✅

### Core Commands (13 implemented)

**`aico agency status`** ✅
- High-level agency state summary
- Shows active intentions, goal counts by status, top intention details
- Displays user profile (curiosity intensity, proactive level, sensitive areas)
- Arbiter score breakdown for top intention
- JSON output support for scripting

**`aico agency goals`** ✅
- List all goals with filtering
- Compact and detailed view modes
- Shows status, origin, priority, type, timestamps
- JSON output support

**`aico agency intentions`** ✅
- View active intention set
- Top-ranked goals with scores and priority bands
- Score breakdowns and status tracking
- Configurable limit (default 10)

**`aico agency plans`** ✅
- List and manage plans
- Filter by status and goal ID
- Shows plan lifecycle and timestamps

**`aico agency executions`** ✅
- View plan execution status
- Progress tracking (steps completed/total, percentage)
- Execution status and timing
- Filter by status

**`aico agency profile`** ✅
- View/edit user value profile
- Set curiosity intensity (0.0-1.0)
- Set proactive level (quiet/balanced/proactive)
- Manage sensitive life areas
- JSON output support

**`aico agency policies`** ✅
- List policy rules
- Filter by target type
- Shows effect, scope, priority
- JSON output support

**`aico agency consent`** ✅
- Grant/revoke consents

**`aico agency proactive`** ✅
- Manage proactive conversations

**`aico agency metrics`** ✅
- Comprehensive KPI dashboard
- Goal completion rates
- Plan success rates
- Reflection run statistics
- Lesson application rates
- Time window filtering (`--last 7d`, `--since <timestamp>`)
- JSON output support

**`aico agency reflection-history`** ✅
- Reflection run analysis
- Lessons generated per run
- Confidence scores
- Application status
- Time window filtering
- JSON output support

**`aico agency skill-performance`** ✅
- Skill execution success rates
- Success/failure counts
- Performance metrics
- Filter by skill name
- JSON output support

**`aico agency health`** ✅
- Diagnostic health checks
- Stale reflection run detection
- Lesson application rate monitoring
- Goal abandonment rate alerts
- Execution failure rate warnings
- Recent activity monitoring
- JSON output support

---

## Advanced Features ✅

### Time Window Filtering
- [x] `--last` parameter (e.g., `--last 7d`, `--last 30d`, `--last 1h`)
- [x] `--since` parameter (ISO timestamp)
- [x] Support for days (d), hours (h), weeks (w), minutes (m)

### Health Monitoring
- [x] Automated warnings for stale reflection runs (>7 days)
- [x] Abnormal lesson application rate detection (<20%)
- [x] High goal abandonment rate alerts (>30%)
- [x] High execution failure rate warnings (>20%)
- [x] Recent activity monitoring (24 hours)

### Engineering Analysis Workflows
- [x] Database schema & storage
- [x] Reflection effectiveness analysis
- [x] Skill performance correlation

---

## Implementation Details

**CLI Commands:** 1,633 lines in `cli/commands/agency.py` (+819 lines)

**Event System:** `shared/aico/ai/agency/workflows.py` (1,384 lines)

**Database Tables:**
- `agency_events` (382 records)
- `agency_events_log` (224 records)
- `event_metrics` (582 records)
- `workflow_executions` (52 records)
- `workflow_stages` (232 records)

---

## Exit Condition ✅

**COMPLETE** - CLI provides actionable, queryable views into agency behavior with advanced analytics and health monitoring.

**Achieved:**
- ✅ Inspect active intentions, goals, plans, and executions via CLI
- ✅ View user profiles, policies, and consents
- ✅ Access comprehensive event logs and metrics (1,188+ events)
- ✅ Export JSON for external analysis tools
- ✅ Comprehensive KPI dashboard with time window filtering
- ✅ Reflection run history and effectiveness analysis
- ✅ Skill performance tracking and success rates
- ✅ Automated health checks and anomaly detection
- ✅ Time-based filtering for all analytics commands

---

## Related Documentation

- [Phase 7: Testing & QA](agency-phase-7-testing-qa.md)
- [Phase 9: Lesson Management](agency-phase-9-lesson-management.md)
- [Current Status](agency-roadmap-status.md)
- [Roadmap Overview](agency-roadmap-overview.md)
- [Future Enhancements](agency-roadmap-overview.md#future-enhancements) - See Analytics & Observability section
