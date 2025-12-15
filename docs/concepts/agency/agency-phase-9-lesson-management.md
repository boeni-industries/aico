---
title: Phase 9 - Lesson Management CLI
---

# Phase 9 – Lesson Management CLI 🚧

**Status:** In Progress

**Goal:** Build CLI tooling for lesson review and approval, enabling users to guide AICO's learning process.

---

## Prerequisites ✅

**Completed in Phase 8:**
- ✅ Comprehensive event logging system operational
- ✅ Metrics data collection (1,188+ events tracked)
- ✅ 13 CLI commands for agency monitoring and analytics
- ✅ Advanced analytics: `metrics`, `reflection-history`, `skill-performance`, `health`
- ✅ Database tables: `agency_events`, `agency_events_log`, `event_metrics`
- ✅ Reflection data: 41 lessons, 1,437 reflection runs, 2,257 self-model entries

---

## Lesson Management CLI *PENDING*

**Goal:** Enable users to review and approve/reject lessons learned by AICO's reflection system.

### Core Commands
- [ ] `aico lessons list` - List all lessons with filtering
  - Filter by status (pending, approved, rejected, applied)
  - Filter by confidence score
  - Filter by time window
  - Sort by creation date, confidence, application count
  - JSON output support

- [ ] `aico lessons review <lesson_id>` - Detailed lesson view
  - Show lesson content and category
  - Display evidence and reasoning
  - Show confidence score and metadata
  - List application history
  - Show related reflection run

- [ ] `aico lessons approve <lesson_id>` - Approve lesson for application
  - Mark lesson as approved
  - Enable automatic application
  - Add approval timestamp and reason

- [ ] `aico lessons reject <lesson_id>` - Reject lesson
  - Mark lesson as rejected
  - Prevent future application
  - Add rejection timestamp and reason

- [ ] `aico lessons stats` - Lesson statistics
  - Total lessons by status
  - Approval/rejection rates
  - Application success rates
  - Confidence distribution

**Data Available:** 41 lessons in `agency_lessons` table ready for management

---

## Implementation Details

**Database Tables:**
- `agency_lessons` (41 records) - Lesson storage with status tracking
- `agency_reflection_runs` (1,437 records) - Source reflection runs
- `agency_self_model` (2,257 records) - Performance tracking

**CLI Location:** `/cli/commands/lessons.py` (new file)

**Integration Points:**
- Lesson approval updates `status` field in `agency_lessons`
- Approved lessons are automatically applied by `LessonApplicator`
- Rejected lessons are excluded from future application
- Statistics aggregate from lesson metadata and application history

---

## Exit Condition

Users can review, approve, and reject lessons learned by AICO through CLI commands. Complete transparency into the learning process with ability to guide and control lesson application.

---

## Current Progress

**Completed:**
- ✅ Phase 8: All metrics and analytics CLI commands
- ✅ 13 agency CLI commands operational
- ✅ Comprehensive event logging and data collection
- ✅ 41 lessons available for management

**Pending:**
- [ ] Lesson management CLI commands (5 commands)
- [ ] Lesson approval/rejection workflow
- [ ] Lesson statistics and reporting

**Next Steps:**
1. Create `/cli/commands/lessons.py` module
2. Implement `lessons list` command with filtering
3. Implement `lessons review` command for detailed view
4. Implement `lessons approve/reject` commands
5. Implement `lessons stats` for analytics
6. Add comprehensive tests for lesson management
7. Update CLI help and documentation

---

## Related Documentation

- [Phase 8: CLI & Analysis](agency-phase-8-cli-analysis.md) - Prerequisites
- [Phase 5: Self-Reflection](agency-phase-5-self-reflection.md) - Lesson generation
- [Current Status](agency-roadmap-status.md)
- [Roadmap Overview](agency-roadmap-overview.md)
- [Future Enhancements](agency-roadmap-overview.md#future-enhancements) - See UI & Tooling section
