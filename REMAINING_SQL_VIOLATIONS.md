# Remaining SQL Violations - Scheduler Tasks

## Status: 4 scheduler tasks still need UoW refactoring

These tasks use raw SQL and need to be refactored to use UoW/repositories:

### 1. kg_consolidation.py (HIGH COMPLEXITY)
**Lines:** 540-625 and more
**Issue:** Extensive raw SQL for node deduplication, edge updates, orphan cleanup
**Estimated effort:** 2-3 hours
**Recommendation:** This is a complex consolidation task that manipulates KG data directly. Consider:
- Using KG repositories for node/edge queries
- Batch operations via UoW
- May need new repository methods for complex operations

### 2. kg_consolidation_chromadb.py (LOW COMPLEXITY)
**Lines:** 31, 45
**Issue:** Simple SELECT queries for historical nodes/edges
**Fix:** Replace with `uow.kg_nodes.list(filters={'is_current': False})` and `uow.kg_edges.list(filters={'is_current': False})`
**Estimated effort:** 15 minutes

### 3. proactive_conversation.py (MEDIUM COMPLEXITY)
**Lines:** 101, 115, 233, 261
**Issue:** User queries, conversation initiation checks, INSERT operations
**Fix:** Use user_profiles repository and conversation repositories
**Estimated effort:** 1 hour

### 4. agency_arbiter.py (MEDIUM COMPLEXITY)
**Lines:** 190, 219
**Issue:** Goal queries for pending goals
**Fix:** Use `AgencyService` to get pending goals
**Estimated effort:** 30 minutes

### 5. agency_plan_executor.py (MEDIUM COMPLEXITY)
**Lines:** 242, 270
**Issue:** Plan execution queries
**Fix:** Use `AgencyService` for plan execution queries
**Estimated effort:** 30 minutes

## Completed Refactoring

✅ backend/api/ams/router_extensions.py - get_skill_overview(), get_memory_evolution()
✅ backend/api/kg/analytics.py - calculate_temporal_metrics(), calculate_centrality_metrics()
✅ backend/scheduler/tasks/ams_consolidation.py - user shard query
✅ backend/scheduler/tasks/ams_thompson_sampling.py - feedback events and stats updates

## Files Deleted

✅ backend/scheduler/storage.py (replaced by SchedulerService)
✅ backend/core/metrics_collector.py (not used, Influx only)

## Imports Cleaned

✅ backend/scheduler/core.py - Removed TaskStore import
✅ backend/api/operations/router.py - Removed sqlite3 import
