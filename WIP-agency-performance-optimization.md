# Agency Performance Optimization - Work In Progress

**Context**: Curiosity scan task timing out (167 minutes) with only 1 active non-technical user.
**Root Cause**: Unbounded sequential processing with excessive database/LLM calls in tight loops.
**Target**: <2 minutes for 10+ users, <30 seconds for single user.

---

## Critical Issues (Blocking Production)

### 1. Curiosity Scan Timeout Protection ✅ COMPLETED
- [x] Add per-user timeout wrapper (60s max per user) - **DONE**
- [x] Add batch size limit (max 5 users per run) - **DONE**
- [x] Add operation-level timeouts (30s per goal creation) - **DONE**
- [ ] Add early exit if approaching task deadline
- [ ] Add circuit breaker for degraded service detection

### 2. Single-User Performance (CRITICAL - 1 user taking >167 min) ✅ COMPLETED
- [x] Profile curiosity scan for single user to identify exact bottleneck - **DONE**
- [x] Add detailed timing logs per operation (scan, ethics, embeddings, DB) - **DONE**
- [x] Add timeout to each sub-operation (not just task-level) - **DONE**
- [ ] Identify which specific call is hanging/retrying - **READY FOR TESTING**

**Implementation Details**:
- Added comprehensive timing instrumentation for all operations
- Per-user timeout: 60s (task will skip user if exceeded)
- Per-goal timeout: 30s (prevents single goal from blocking)
- Batch limit: 5 users max per run
- Performance metrics tracked: config_load, scan_opportunities, goal_creation (total/avg/max)
- Logs show duration for each operation and identify slow users (>30s)

---

## Database Performance

### 3. Ethics Evaluation Optimization
- [ ] Batch ethics evaluations (single UoW for all signals per user)
- [ ] Cache ethics policies in memory (load once per task run)
- [ ] Add query optimization: index on `(user_id, origin, title, status)`
- [ ] Lazy load user profiles (only when needed)

### 4. Goal Duplicate Checking
- [ ] Optimize duplicate goal lookups (currently 3 DB queries per signal)
- [ ] Add caching for recent goal titles per user
- [ ] Consider bloom filter for "definitely not duplicate" fast path

### 5. Connection Pool Health
- [ ] Verify asyncpg pool not exhausted during concurrent queries
- [ ] Add connection pool metrics/monitoring
- [ ] Tune pool size if needed

---

## Modelservice Performance

### 6. Embedding Generation
- [ ] Implement batch embedding generation (array of prompts → single request)
- [ ] Add embedding cache by content hash (avoid regenerating duplicates)
- [ ] Reduce embedding timeout from 60s to 10s for curiosity context
- [ ] Add fallback: skip embeddings if modelservice slow, use string matching

### 7. Modelservice Circuit Breaker
- [ ] Detect modelservice degradation (consecutive timeouts)
- [ ] Skip embedding generation if circuit open
- [ ] Add metrics for modelservice call duration

---

## Personality Service

### 8. Personality Context Caching
- [ ] Load personality context once per user (not once per signal)
- [ ] Implement async prefetch for all users before processing loop
- [ ] Add lazy evaluation (only call if needed for scoring/gates)

---

## World Model Integration (Placeholders)

### 9. Implement `detect_anomalies()`
- [ ] Query KG for contradictions using PropertyGraphStorage
- [ ] Implement temporal anomaly detection
- [ ] Add inconsistency detection across facts
- [ ] **Blocked by**: KG query capabilities

### 10. Implement `query_uncertain_areas()`
- [ ] Integrate with hypothesis manager
- [ ] Query AMS summaries for sparse topics
- [ ] Identify high prediction error areas
- [ ] **Blocked by**: Hypothesis manager implementation

### 11. World Model Query Optimization
- [ ] Batch queries (single KG query per user for all data)
- [ ] Add result caching (5 minute TTL for low-churn data)
- [ ] Implement incremental updates instead of full scans

---

## Architecture Improvements

### 12. Parallel User Processing
- [ ] Implement `asyncio.gather()` for parallel user processing
- [ ] Process 5 users concurrently instead of sequentially
- [ ] Add semaphore to limit concurrency (prevent resource exhaustion)

### 13. Progressive Batching
- [ ] Process 5 users, commit, repeat (not all-or-nothing)
- [ ] Add checkpoint/resume capability for long runs
- [ ] Return partial results if timeout approaching

### 14. Background Task Queue (Future)
- [ ] Move curiosity scan to background worker (Celery/RQ)
- [ ] Implement async job queue for user processing
- [ ] Add job status tracking and retry logic
- [ ] **Blocked by**: Background worker infrastructure

### 15. Incremental Goal Creation
- [ ] Create goals as discovered (don't wait for all users)
- [ ] Stream results instead of batch return
- [ ] Add event emission for real-time monitoring

---

## Monitoring & Observability

### 16. Detailed Performance Metrics
- [ ] Add per-user timing logs (identify slow users)
- [ ] Track time spent in: ethics, embeddings, DB, personality
- [ ] Add percentile metrics (p50, p95, p99)
- [ ] Create Grafana dashboard for curiosity scan performance

### 17. Alerting
- [ ] Alert if any user takes >30s to process
- [ ] Alert if task approaches timeout (>4 minutes)
- [ ] Alert on modelservice degradation
- [ ] Alert on database connection pool exhaustion

### 18. Graceful Degradation
- [ ] Return partial results if timeout approaching
- [ ] Skip optional operations (embeddings) under time pressure
- [ ] Add degraded mode flag in task result

---

## Code Quality

### 19. Refactoring
- [ ] Extract user processor to separate method
- [ ] Add dependency injection (avoid global state in loops)
- [ ] Add comprehensive type hints
- [ ] Split curiosity_scan.py into smaller modules

### 20. Testing
- [ ] Add unit tests for timeout behavior
- [ ] Add tests for batch processing
- [ ] Add tests for fallback modes
- [ ] Add integration tests with mocked services

---

## Performance Targets

| Metric | Current | Target | Stretch Goal |
|--------|---------|--------|--------------|
| Single user | >167 min | <30s | <10s |
| 10 users | N/A | <5 min | <2 min |
| 100 users | N/A | <30 min | <15 min |
| Task timeout rate | 100% | <1% | 0% |
| Modelservice calls per user | ~10 | ~2 | 1 |
| DB queries per user | ~30+ | <10 | <5 |

---

## Investigation Tasks

### Immediate (Before Any Optimization)
- [ ] **Profile single-user curiosity scan** - identify exact bottleneck
- [ ] Add debug logging to measure each operation duration
- [ ] Check if issue is modelservice timeout, DB lock, or LLM hang
- [ ] Verify no infinite retry loops in any service

### Root Cause Analysis
- [ ] Why does 1 user take 167 minutes?
- [ ] Is it waiting on a single blocking call?
- [ ] Is it retrying failed operations indefinitely?
- [ ] Are there any deadlocks or race conditions?

---

## Priority Order

1. **P0 - Critical**: Investigation + Single-user profiling (#2, Investigation tasks)
2. **P0 - Critical**: Timeout protection (#1)
3. **P1 - High**: Database optimization (#3, #4)
4. **P1 - High**: Modelservice optimization (#6, #7)
5. **P2 - Medium**: Personality caching (#8)
6. **P2 - Medium**: Parallel processing (#12)
7. **P3 - Low**: World Model implementation (#9, #10, #11)
8. **P3 - Low**: Background queue (#14)

---

## Notes

- **Single user taking 167 min is abnormal** - suggests blocking call or infinite retry
- Focus on profiling before optimization to avoid premature optimization
- World Model placeholders are not the bottleneck (return empty lists fast)
- Likely culprits: modelservice timeout cascade, database lock contention, or ethics evaluation
- Need to add operation-level timeouts, not just task-level timeout

---

**Last Updated**: 2026-02-05 10:50 UTC+01:00
**Status**: P0 tasks completed - Ready for testing
**Owner**: TBD

## Recent Changes

### 2026-02-05 10:50 - P0 Critical Tasks Completed
- ✅ Implemented comprehensive performance profiling
- ✅ Added per-user timeout wrapper (60s)
- ✅ Added per-goal timeout (30s)
- ✅ Added batch size limit (5 users max)
- ✅ Added detailed timing logs for all operations
- 📊 Next: Test with single user to identify actual bottleneck
