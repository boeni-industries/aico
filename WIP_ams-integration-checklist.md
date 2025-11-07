# AMS Integration Checklist

**Date:** 2025-11-07  
**Phase:** 1 - Temporal Foundation  
**Status:** Implementation Complete, Integration Pending

---

## ✅ Completed Tasks

### Phase 1: Core Implementation

- [x] **Temporal Module** (`/shared/aico/ai/memory/temporal/`)
  - [x] `metadata.py` - Temporal metadata structures (272 lines)
  - [x] `evolution.py` - Preference evolution tracking (311 lines)
  - [x] `queries.py` - Temporal query support (327 lines)
  - [x] `__init__.py` - Module exports

- [x] **Consolidation Module** (`/shared/aico/ai/memory/consolidation/`)
  - [x] `scheduler.py` - Idle detection & scheduling (298 lines)
  - [x] `replay.py` - Experience replay (378 lines)
  - [x] `reconsolidation.py` - Memory reconsolidation (381 lines)
  - [x] `state.py` - State tracking (293 lines)
  - [x] `__init__.py` - Module exports

- [x] **Module Structures**
  - [x] `behavioral/__init__.py` - Phase 3 structure
  - [x] `unified/__init__.py` - Phase 4 structure
  - [x] Main `__init__.py` updated with AMS exports

- [x] **Enhanced Existing Modules**
  - [x] `working.py` - Added temporal metadata support
  - [x] Main memory `__init__.py` - Added AMS module imports

- [x] **Configuration**
  - [x] Added `memory.temporal.*` section to `core.yaml`
  - [x] Added `memory.consolidation.*` section to `core.yaml`
  - [x] Added `memory.behavioral.*` section (disabled, Phase 3)

- [x] **Documentation**
  - [x] `WIP_ams-phase1-progress.md` - Progress tracking
  - [x] `WIP_ams-implementation-summary.md` - Complete summary
  - [x] `WIP_ams-directory-structure.md` - Directory guide
  - [x] `WIP_ams-database-migrations.md` - Migration guide
  - [x] `WIP_ams-integration-checklist.md` - This document

---

## 🔄 Pending Integration Tasks

### 1. Database Migrations

- [ ] **Run Migration 001**: Add temporal_metadata column to semantic_facts
  ```bash
  # Option 1: Using AICO CLI (when implemented)
  aico db migrate
  
  # Option 2: Manual SQL
  sqlite3 ~/.local/share/aico/data/aico.db < migrations/001_temporal_metadata.sql
  ```

- [ ] **Run Migration 002**: Create consolidation_state table
  ```bash
  sqlite3 ~/.local/share/aico/data/aico.db < migrations/002_consolidation_state.sql
  ```

- [ ] **Verify Migrations**
  ```sql
  -- Check temporal_metadata column
  PRAGMA table_info(semantic_facts);
  
  -- Check consolidation_state table
  SELECT name FROM sqlite_master WHERE type='table' AND name='consolidation_state';
  ```

### 2. Enhance Remaining Modules

- [ ] **semantic.py** - Add temporal tracking
  - [ ] Import `TemporalMetadata` from temporal module
  - [ ] Add temporal metadata to stored facts
  - [ ] Update confidence decay on retrieval
  - [ ] Add temporal queries support
  - **Estimated**: ~100 lines of changes

- [ ] **context/assembler.py** - Add temporal ranking
  - [ ] Import temporal query builders
  - [ ] Add recency weighting to relevance scores
  - [ ] Implement temporal-aware context assembly
  - **Estimated**: ~80 lines of changes

- [ ] **context/retrievers.py** - Add temporal queries
  - [ ] Use `TemporalQueryBuilder` for time-range queries
  - [ ] Add point-in-time query support
  - [ ] Filter by confidence decay
  - **Estimated**: ~60 lines of changes

- [ ] **context/scorers.py** - Add recency weighting
  - [ ] Implement recency decay function
  - [ ] Add temporal bonus to relevance scores
  - [ ] Balance recency vs. relevance
  - **Estimated**: ~40 lines of changes

### 3. Memory Manager Integration

- [ ] **manager.py** - Integrate AMS components
  - [ ] Import consolidation scheduler
  - [ ] Import temporal tracker
  - [ ] Add consolidation scheduling method
  - [ ] Add temporal evolution tracking
  - [ ] Coordinate consolidation with existing memory operations
  - **Estimated**: ~150 lines of changes

### 4. Backend Scheduler Integration

- [ ] **Create Consolidation Task** (`/backend/scheduler/tasks/ams_consolidation.py`)
  - [ ] Implement `MemoryConsolidationTask` class
  - [ ] Use `ConsolidationScheduler` from consolidation module
  - [ ] Handle idle detection
  - [ ] Process user sharding (1/7 users per day)
  - [ ] Log consolidation results
  - **Estimated**: ~200 lines new file

- [ ] **Register Task** in scheduler
  - [ ] Add task to scheduler configuration
  - [ ] Set schedule: "0 2 * * *" (2 AM daily)
  - [ ] Enable idle detection
  - [ ] Configure max duration (60 min)

### 5. Testing & Verification

**Note:** Skipping unit/integration test files as per user request. Testing to be tackled separately.

- [ ] **Manual Verification**
  - [ ] Verify temporal metadata is stored in working memory
  - [ ] Verify temporal metadata is stored in semantic memory
  - [ ] Check consolidation state tracking
  - [ ] Monitor consolidation job execution
  - [ ] Verify idle detection works correctly

- [ ] **Performance Testing**
  - [ ] Measure context assembly latency with temporal ranking
  - [ ] Measure consolidation throughput (users/hour)
  - [ ] Monitor memory overhead
  - [ ] Check database query performance with temporal indexes

### 6. Monitoring & Observability

- [ ] **Add Metrics**
  - [ ] Consolidation job duration
  - [ ] Experiences processed per user
  - [ ] Temporal query performance
  - [ ] Confidence decay statistics

- [ ] **Add Logging**
  - [ ] Consolidation start/complete events
  - [ ] Temporal metadata updates
  - [ ] Evolution tracking events
  - [ ] Error conditions and recovery

### 7. Documentation Updates

- [ ] **Update README.md**
  - [ ] Add AMS overview section
  - [ ] Document new configuration options
  - [ ] Add consolidation scheduling info

- [ ] **Update Architecture Docs**
  - [ ] Add AMS architecture diagrams
  - [ ] Document temporal intelligence
  - [ ] Explain consolidation process

- [ ] **Create User Guide**
  - [ ] How to enable/disable AMS features
  - [ ] Configuration tuning guide
  - [ ] Troubleshooting common issues

---

## 📋 Integration Order (Recommended)

### Week 1: Database & Core Enhancements

1. **Day 1-2**: Run database migrations
   - Execute Migration 001 (temporal_metadata)
   - Execute Migration 002 (consolidation_state)
   - Verify migrations successful
   - Backfill temporal metadata for existing facts (optional)

2. **Day 3-4**: Enhance semantic.py
   - Add temporal metadata to fact storage
   - Implement confidence decay
   - Add temporal query support
   - Test with existing semantic memory operations

3. **Day 5**: Enhance context modules
   - Update assembler.py with temporal ranking
   - Update retrievers.py with temporal queries
   - Update scorers.py with recency weighting
   - Test context assembly with temporal features

### Week 2: Manager & Scheduler Integration

4. **Day 1-2**: Update memory manager
   - Integrate consolidation scheduler
   - Add temporal evolution tracking
   - Coordinate with existing memory operations
   - Test manager initialization

5. **Day 3-4**: Backend scheduler integration
   - Create MemoryConsolidationTask
   - Register with backend scheduler
   - Configure cron schedule (2 AM daily)
   - Test idle detection

6. **Day 5**: End-to-end testing
   - Run full consolidation cycle
   - Verify user sharding (1/7 per day)
   - Check state persistence
   - Monitor performance

### Week 3: Monitoring & Documentation

7. **Day 1-2**: Add monitoring
   - Implement metrics collection
   - Add structured logging
   - Create monitoring dashboard queries
   - Test alerting

8. **Day 3-5**: Documentation
   - Update README and architecture docs
   - Create user guide
   - Document troubleshooting
   - Review and polish all docs

---

## 🔍 Verification Checklist

### Temporal Metadata

- [ ] Working memory stores temporal metadata
- [ ] Semantic memory stores temporal metadata
- [ ] Temporal queries work correctly
- [ ] Confidence decay applies correctly
- [ ] Access counts increment on retrieval

### Memory Consolidation

- [ ] Idle detection triggers correctly
- [ ] User sharding works (1/7 per day)
- [ ] Experience replay prioritizes correctly
- [ ] Reconsolidation resolves conflicts
- [ ] State persists across restarts
- [ ] Consolidation completes within time limit

### Configuration

- [ ] All AMS config sections present in core.yaml
- [ ] Temporal features can be enabled/disabled
- [ ] Consolidation schedule is configurable
- [ ] Idle detection thresholds are tunable

### Performance

- [ ] Context assembly: <50ms with temporal ranking
- [ ] Consolidation: 5-10 min/user
- [ ] Temporal queries: <5ms overhead
- [ ] Memory overhead: <100KB per user
- [ ] No performance regression in existing features

---

## 🚨 Known Issues & Limitations

### Current Limitations

1. **No Unit Tests**: Testing framework to be set up separately
2. **No Integration Tests**: End-to-end testing manual for now
3. **Semantic.py Not Enhanced**: Temporal support pending
4. **Context Assembly Not Enhanced**: Temporal ranking pending
5. **Manager Not Integrated**: Consolidation coordination pending
6. **Scheduler Task Not Created**: Backend integration pending

### Future Work (Phase 2+)

1. **Phase 2**: Complete consolidation engine integration
2. **Phase 3**: Implement behavioral learning system
3. **Phase 4**: Implement unified indexing
4. **Testing**: Comprehensive test suite
5. **Optimization**: Performance tuning based on real usage

---

## 📞 Support & Troubleshooting

### Common Issues

**Issue**: Temporal metadata not appearing in stored messages

**Solution**: 
1. Check if enhanced `working.py` is being used
2. Verify `TemporalMetadata` import is working
3. Check logs for errors during storage

**Issue**: Consolidation not running

**Solution**:
1. Check if consolidation is enabled in config
2. Verify scheduler task is registered
3. Check if system meets idle threshold
4. Review consolidation logs for errors

**Issue**: Database migration fails

**Solution**:
1. Check if column already exists (safe to skip)
2. Verify database file permissions
3. Backup database before retrying
4. Check SQLite version compatibility

### Debug Commands

```bash
# Check AMS module imports
python -c "from aico.ai.memory import temporal, consolidation; print('✅ Imports OK')"

# Check configuration
aico config get memory.temporal.enabled
aico config get memory.consolidation.enabled

# Check database schema
sqlite3 ~/.local/share/aico/data/aico.db "PRAGMA table_info(semantic_facts);"

# Check consolidation state
sqlite3 ~/.local/share/aico/data/aico.db "SELECT * FROM consolidation_state;"

# Monitor consolidation
tail -f ~/.local/share/aico/logs/backend.log | grep consolidation
```

---

## 📊 Success Metrics

### Phase 1 Success Criteria

- [x] All temporal and consolidation modules implemented
- [x] Configuration sections added
- [x] Database migration guide created
- [ ] Database migrations executed successfully
- [ ] Temporal metadata stored in working memory
- [ ] Temporal metadata stored in semantic memory
- [ ] Consolidation runs successfully (manual test)
- [ ] State persists across restarts
- [ ] No performance regression

### Performance Targets

- [ ] Context assembly: <50ms (with temporal ranking)
- [ ] Consolidation: 5-10 min/user
- [ ] Temporal queries: <5ms overhead
- [ ] Memory overhead: <100KB per user
- [ ] Idle detection: <1 min latency

### Quality Targets

- [x] Code follows AICO guidelines (KISS, DRY, modularity)
- [x] All modules <400 lines
- [x] Comprehensive docstrings
- [x] Type hints throughout
- [ ] No errors in production logs
- [ ] Graceful error handling

---

## 🎯 Next Actions

### Immediate (This Week)

1. **Run database migrations** (Migration 001 & 002)
2. **Enhance semantic.py** with temporal support
3. **Test temporal metadata** storage and retrieval
4. **Verify configuration** is loaded correctly

### Short-term (Next 2 Weeks)

1. **Enhance context assembly** with temporal ranking
2. **Integrate memory manager** with consolidation
3. **Create scheduler task** for consolidation
4. **End-to-end testing** of consolidation cycle

### Medium-term (Next Month)

1. **Phase 2 completion**: Full consolidation integration
2. **Monitoring setup**: Metrics and dashboards
3. **Documentation**: User guides and troubleshooting
4. **Performance tuning**: Optimize based on usage

### Long-term (Next Quarter)

1. **Phase 3**: Behavioral learning implementation
2. **Phase 4**: Unified indexing implementation
3. **Testing framework**: Comprehensive test suite
4. **Production deployment**: Roll out to users

---

**Status:** Phase 1 implementation complete. Ready for integration and testing.

**Last Updated:** 2025-11-07  
**Next Review:** After database migrations and semantic.py enhancement
