# AICO Database Architecture Refactor (Postgres + Timescale)

**Date:** 2026-01-09  
**Status:** Draft architecture for implementation  
**Goal:** Replace LibSQL/SQLite with a Postgres + Timescale architecture that works on a single local machine *and* scales to multi-system deployments, while preserving AICO's local-first, privacy-first guarantees.

---

## 1. Current Storage Overview & Problems

**Stores in use today**
- **LibSQL/SQLite (`aico.db`)** – Encrypted primary DB for:
  - Users, auth, sessions
  - Conversations and AMS data
  - Knowledge graph metadata
  - System logs (`system_logs`)
  - System events (`system_events`)
  - OTel metrics (`otel_model_inferences`, etc.)
- **ChromaDB** – Vector store for semantic memory and KG embeddings.
- **LMDB** – Working-memory cache for active conversations.

**Observed problems (already at single-user load):**
- Backend, modelservice, log consumer, and message-bus host all write to the **same SQLite file**.
- High-frequency writes (logs + OTel metrics) cause **database locked** errors and long stalls.
- Complex retry/busy-timeout workarounds spread across the codebase (`LibSQLConnection`, `OTelStorageExporter`, log consumer).
- Request handling can block on DB writes, causing timeouts and UI streaming failures.

Conclusion: **LibSQL/SQLite is no longer suitable as the central multi-writer store.** We need a different persistence architecture we can keep long-term.

---

## 2. Target Storage Architecture (to keep)

### 2.1 Primary OLTP: Postgres

- Replace LibSQL/SQLite with **PostgreSQL** as the single source of truth for:
  - Users, auth, sessions
  - Conversations/messages, AMS
  - Knowledge graph metadata
  - Scheduler/task data
- **Local single-machine path:**
  - Postgres data dir lives under:  
    `~/Library/Application Support/aico/data/postgres/`
  - This follows existing AICO data-folder patterns.
- **Multi-system / scale-out:**
  - Same schema, but `DATABASE_URL` can point to any Postgres instance:
    - Managed service (RDS/Aiven/Timescale Cloud),
    - Self-hosted VM,
    - Containerized deployment.

### 2.2 Telemetry: Timescale (metrics + logs)

- Use **TimescaleDB extension on Postgres** for all time-series telemetry:
  - OTel metrics from backend and modelservice.
  - System logs and event streams (currently written to `system_logs` / `system_events`).
- Implement **hypertables** with retention policies instead of writing to SQLite tables.
- OTel exporters (backend + modelservice) and the log consumer write **only** to Timescale hypertables, not to the OLTP tables.

**Readers:**
- **Studio** (React web app) - via backend API
- **Frontend** (Flutter mobile) - via backend API
- **CLI** - direct database access

**Write Patterns:**
| Component | Frequency | Volume | Critical Path |
|-----------|-----------|--------|---------------|
| Backend API | Per request | Low-Medium | ✅ Yes |
| Log Consumer | Continuous | High | ❌ No |
| OTel Exporter (Backend) | Every 5s | Medium | ❌ No |
| OTel Exporter (Modelservice) | Every 5s | High | ❌ No |
| Agency System | Per conversation | Low | ✅ Yes |
| Knowledge Graph | Per message | Medium | ✅ Yes |

**Concurrency Configuration:**
```python
# shared/aico/data/libsql/connection.py
PRAGMA busy_timeout = 10000  # 10 seconds (connection init)
PRAGMA busy_timeout = 30000  # 30 seconds (execute method)
PRAGMA journal_mode = WAL    # Write-Ahead Logging
PRAGMA synchronous = NORMAL  # Balanced durability/performance
PRAGMA wal_autocheckpoint = 1000
```

**Current Issues:**
- ❌ Multiple services writing simultaneously cause locks
- ❌ Busy timeout insufficient for high-volume writes
- ❌ WAL mode helps but doesn't eliminate serialization
- ❌ Metrics export (every 5s) creates predictable contention windows

#### 1.2 Database Schema (v46)

**Core Tables (High Write Frequency):**
- `system_logs` - Log entries from all services
- `otel_model_inferences` - Modelservice metrics (NEW - high frequency)
- `system_events` - Message bus events
- `conversation_messages` - Chat messages
- `ams_trajectories` - Agency trajectories
- `ams_behavioral_feedback` - User feedback

**Supporting Tables (Medium Write Frequency):**
- `user_profiles`, `auth_sessions`, `auth_user_credentials`
- `agency_goals`, `agency_plans`, `agency_intention_set`
- `kg_entities`, `kg_relationships`, `kg_entity_metadata`
- `semantic_memory_segments` (ChromaDB metadata)

**Low Write Frequency:**
- Configuration tables
- Schema migration history
- Static reference data

#### 1.3 Connection Management

**Pattern:** Singleton connection per service
```python
# Backend: backend/core/lifecycle_manager.py
db_connection = EncryptedLibSQLConnection(db_path, encryption_key)

# Modelservice: modelservice/main.py  
db_connection = EncryptedLibSQLConnection(db_path, encryption_key)

# CLI: Various commands
db_connection = EncryptedLibSQLConnection(db_path, encryption_key)
```

**Issues:**
- ✅ Each service has own connection (good)
- ❌ All connections write to same database file (bad)
- ❌ No connection pooling (not applicable for SQLite)
- ❌ No write queue or batching

#### 1.4 Transaction Patterns

**Explicit Transactions:**
```python
with db_connection.transaction():
    db_connection.execute("INSERT INTO ...")
    db_connection.execute("UPDATE ...")
```

**Auto-commit (Most Common):**
```python
db_connection.execute("INSERT INTO ...")
db_connection.commit()
```

**Issues:**
- ⚠️ Mix of transaction styles creates unpredictable lock duration
- ⚠️ Long transactions in agency system block other writes
- ⚠️ No batch write optimization for high-frequency operations

---

### 2. ChromaDB Usage

#### 2.1 Semantic Memory Store

**Location:** `~/Library/Application Support/aico/data/chroma/`

**Purpose:** Vector embeddings for conversation segments

**Writers:**
- **Backend** - Memory consolidation (episodic → semantic)
- **Backend** - Direct segment storage during conversation

**Readers:**
- **Backend** - Context retrieval for conversations
- **Studio** - ChromaDB browser (operations page)
- **CLI** - Chroma utilities, database admin

**Write Patterns:**
| Operation | Frequency | Volume |
|-----------|-----------|--------|
| Store segment | Per message | 1-3 segments |
| Batch consolidation | Periodic | 10-100 segments |
| Update metadata | Per message | 1-3 updates |

**Configuration:**
```python
# shared/aico/ai/memory/semantic.py
chroma_client = chromadb.PersistentClient(path=str(db_path))
collection = chroma_client.get_or_create_collection(
    name="conversation_segments",
    metadata={"hnsw:space": "cosine"}
)
```

**Current Status:**
- ✅ No concurrency issues (ChromaDB handles this well)
- ✅ Separate storage from main database
- ✅ Optimized for vector similarity search
- ⚠️ Metadata stored in ChromaDB, not LibSQL (some duplication)

#### 2.2 Knowledge Graph Storage

**Location:** Same ChromaDB instance, separate collections

**Collections:**
- `kg_entities` - Entity embeddings
- `kg_relationships` - Relationship embeddings

**Integration:**
- Entity/relationship metadata in LibSQL (`kg_entities`, `kg_relationships` tables)
- Vector embeddings in ChromaDB
- Hybrid queries combine both

**Issues:**
- ⚠️ Split storage requires coordinated writes (LibSQL + ChromaDB)
- ⚠️ No transaction support across both systems
- ⚠️ Potential for inconsistency if one write fails

---

### 3. LMDB Usage

#### 3.1 Working Memory Store

**Location:** `~/Library/Application Support/aico/data/lmdb/`

**Purpose:** High-speed ephemeral storage for active conversations

**Writers:**
- **Backend** - Conversation engine stores messages

**Readers:**
- **Backend** - Context assembly retrieves recent messages

**Write Patterns:**
| Operation | Frequency | Volume |
|-----------|-----------|--------|
| Store message | Per message | 1 message |
| Retrieve history | Per request | 10-50 messages |
| Cleanup expired | Periodic | Batch delete |

**Configuration:**
```python
# shared/aico/ai/memory/working.py
env = lmdb.open(str(db_path), max_dbs=len(named_dbs) + 1)
db = env.open_db(db_name.encode('utf-8'), create=True)
```

**Current Status:**
- ✅ Excellent performance for read-heavy workloads
- ✅ No concurrency issues
- ✅ Automatic memory-mapped file management
- ✅ TTL-based expiration (30 days default)
- ⚠️ Redundant with episodic memory in LibSQL

---

## Consumer Analysis

### 4.1 Backend (FastAPI)

**Database Operations:**
- **Read-heavy:** User profiles, conversations, agency data
- **Write-moderate:** Messages, logs, events, metrics
- **Critical path:** Message processing, agency decisions

**Concurrency:**
- Multiple API workers (uvicorn)
- Each worker shares same DB connection
- Async I/O but synchronous DB writes

**Issues:**
- ❌ DB writes block async event loop
- ❌ High-frequency log writes create contention
- ❌ Metrics export blocks request processing

### 4.2 Modelservice (ZMQ)

**Database Operations:**
- **Write-only:** OTel metrics (every 5 seconds)
- **High volume:** 80% of all metrics writes

**Concurrency:**
- Single-threaded ZMQ service
- Metrics buffered in memory, exported periodically

**Issues:**
- ❌ Metrics export fails with "database locked"
- ❌ Blocks modelservice processing during export
- ❌ Retry logic insufficient for high contention

### 4.3 CLI

**Database Operations:**
- **Read-heavy:** Query operations, admin tools
- **Write-occasional:** User management, database admin

**Concurrency:**
- Single-threaded, user-initiated
- Direct database access (no API)

**Issues:**
- ✅ No concurrency issues (user-initiated)
- ⚠️ Can conflict with backend/modelservice writes

### 4.4 Studio (React Web)

**Database Operations:**
- **Read-only:** All operations via backend API
- **No direct database access**

**Issues:**
- ✅ No direct database concerns
- ⚠️ Affected by backend performance issues

### 4.5 Frontend (Flutter Mobile)

**Database Operations:**
- **Read-only:** All operations via backend API
- **No direct database access**

**Issues:**
- ✅ No direct database concerns
- ⚠️ Affected by backend performance issues

---

## Root Cause Analysis

### 5.1 The Deadlock Mechanism

**Sequence of Events:**
```
T+0s:   Backend starts OTel export (locks aico.db)
T+0.1s: Modelservice tries OTel export (BLOCKED - waits for lock)
T+0.5s: User sends message → Backend processes
T+1s:   Backend tries to write message (BLOCKED - waiting for export to finish)
T+5s:   Modelservice timeout on lock acquisition
T+5.5s: Modelservice retries export (BLOCKED again)
T+10s:  Modelservice timeout again
T+15s:  Modelservice gives up, logs warning
T+15s:  Backend export finally completes
T+15.1s: Backend message write succeeds
T+15.2s: User receives response (15+ second delay)
```

**Why It Happens:**
1. SQLite allows only ONE writer at a time (even with WAL mode)
2. Backend OTel export takes 1-5 seconds (writing 10-50 metrics)
3. Modelservice OTel export tries to run simultaneously
4. Both exports run every 5 seconds (predictable collision)
5. During export, ALL database writes are blocked
6. Request processing stalls waiting for DB access

### 5.2 Compounding Factors

**Log Persistence:**
- Log consumer writes continuously to `system_logs` table
- Every log entry from backend, modelservice, CLI
- Adds additional write contention

**Agency System:**
- Long transactions for goal/plan updates
- Blocks other writes during trajectory storage
- Unpredictable lock duration

**Knowledge Graph:**
- Coordinated writes to LibSQL + ChromaDB
- If LibSQL locked, KG write fails
- Retry logic compounds contention

### 5.3 Why busy_timeout Doesn't Help

**Current Setting:** 5000ms (5 seconds)

**Problem:**
- Export takes 1-5 seconds to write metrics
- Modelservice waits 5 seconds for lock
- If backend export takes 6 seconds, modelservice times out
- Retry logic adds 500ms delay, tries again
- Second attempt also times out
- Total wait: 10+ seconds before giving up

**Increasing timeout doesn't solve:**
- Just delays the failure
- Blocks service processing longer
- Doesn't address root cause (single writer)

---

## Scalability Analysis

### 6.1 Current Limits

**Single User:**
- ✅ Works fine
- Occasional log/metrics contention
- No noticeable impact

**5-10 Users:**
- ⚠️ Intermittent slowdowns
- Metrics export failures increase
- Some request timeouts

**10-20 Users:**
- ❌ Frequent deadlocks
- Metrics export fails consistently
- User experience degraded
- System becomes unreliable

**20+ Users:**
- ❌ System unusable
- Constant database locks
- Requests timeout
- Services crash

### 6.2 Bottleneck Breakdown

**Write Throughput:**
- SQLite: ~10,000-50,000 inserts/sec (theoretical)
- AICO current: ~100-500 inserts/sec (actual)
- Bottleneck: Lock contention, not raw performance

**Lock Contention Windows:**
- OTel export: Every 5 seconds, 1-5 second duration
- Log writes: Continuous, 10-50ms per write
- Message writes: Per request, 50-200ms per message
- **Total contention: 30-50% of time**

**Scaling Math:**
```
10 users × 1 msg/min = 10 msg/min
  → 50-70 metrics/min
  → 12 export cycles/min × 1-5s = 12-60s of locks/min
  → 20-100% lock contention
```

### 6.3 Production Requirements

**Target Scale:**
- 100+ concurrent users
- 1000+ messages/hour
- 10,000+ metrics/hour
- 99.9% uptime

**Current Architecture:**
- ❌ Cannot support 100 users
- ❌ Cannot handle 1000 msg/hr reliably
- ❌ Cannot sustain 10k metrics/hr
- ❌ Uptime degraded under load

---

## Recommended Architecture

### 7.1 Immediate Fix (Phase 1: This Week)

**Separate Metrics Database**

**Goal:** Eliminate cross-service deadlock

**Implementation:**
1. Create `modelservice_metrics.db` for modelservice OTel exports
2. Keep `aico.db` for backend OTel exports
3. Update modelservice to use separate connection
4. No schema changes required

**Benefits:**
- ✅ Eliminates backend ↔ modelservice deadlock
- ✅ Each service writes independently
- ✅ Minimal code changes (1-2 hours)
- ✅ Immediate relief from current crisis

**Limitations:**
- ⚠️ Still SQLite single-writer per database
- ⚠️ Scales to ~10-20 users
- ⚠️ Log persistence still contends with backend

**Files to Change:**
```
modelservice/main.py - Use separate DB path
backend/api/system/metrics.py - Query both databases
studio/src/api/metrics.ts - Aggregate from both sources
```

### 7.2 Near-Term Fix (Phase 2: Next Sprint)

**Async Export + Separate Logs Database**

**Goal:** Remove blocking writes from critical path

**Implementation:**
1. Move OTel export to background thread (both services)
2. Create `system_logs.db` for log consumer
3. Batch metrics writes (30-second interval instead of 5s)
4. Implement write queue with graceful degradation

**Benefits:**
- ✅ Request processing never blocked by DB writes
- ✅ Log writes don't contend with application data
- ✅ Larger batches = fewer lock acquisitions
- ✅ Scales to 50-100 users

**Limitations:**
- ⚠️ Still SQLite limitations
- ⚠️ Increased memory usage (buffering)
- ⚠️ Metrics delayed by 30 seconds

**Implementation:**
```python
# Async export pattern
class AsyncOTelExporter:
    def __init__(self):
        self.queue = asyncio.Queue()
        self.worker = asyncio.create_task(self._export_worker())
    
    async def export(self, metrics):
        await self.queue.put(metrics)  # Non-blocking
    
    async def _export_worker(self):
        while True:
            batch = []
            # Collect metrics for 30 seconds
            deadline = time.time() + 30
            while time.time() < deadline:
                try:
                    metric = await asyncio.wait_for(
                        self.queue.get(), 
                        timeout=deadline - time.time()
                    )
                    batch.append(metric)
                except asyncio.TimeoutError:
                    break
            
            # Write batch to database
            if batch:
                await self._write_batch(batch)
```

### 7.3 Production Solution (Phase 3: Before Launch)

**Time-Series Database for Telemetry**

**Goal:** True production scalability

**Recommended:** InfluxDB (easiest) or TimescaleDB (PostgreSQL-based)

**Architecture:**
```
Application Data (LibSQL):
  - User profiles, auth, conversations
  - Agency goals, plans, intentions
  - Knowledge graph metadata
  
Telemetry Data (InfluxDB):
  - OTel metrics (all services)
  - System logs
  - Performance metrics
  - Usage analytics
  
Vector Data (ChromaDB):
  - Semantic memory embeddings
  - Knowledge graph embeddings
  
Working Memory (LMDB):
  - Active conversation cache
  - Session state
```

**Benefits:**
- ✅ Designed for high-frequency time-series writes
- ✅ Concurrent writes without locks
- ✅ Built-in aggregation, downsampling, retention
- ✅ Scales to 1000+ users
- ✅ Production-grade observability

**InfluxDB Advantages:**
- Single binary, no dependencies
- Native OTel support
- Excellent query language (Flux)
- Built-in dashboards
- Free tier sufficient for development

**Implementation Effort:**
- Setup: 2-4 hours
- OTel exporter swap: 1-2 hours
- Log consumer update: 2-4 hours
- Testing: 4-8 hours
- **Total: 1-2 days**

**OTel Exporter Change:**
```python
# Before (SQLite)
from backend.core.otel_storage_adapter import OTelStorageExporter
exporter = OTelStorageExporter(db_connection)

# After (InfluxDB)
from opentelemetry.exporter.influxdb import InfluxDBMetricsExporter
exporter = InfluxDBMetricsExporter(
    url="http://localhost:8086",
    token=influx_token,
    org="aico",
    bucket="metrics"
)
```

### 7.4 Alternative: PostgreSQL

**If you need ACID transactions + scalability:**

**Architecture:**
```
PostgreSQL:
  - All application data
  - Logs (with partitioning)
  - Metrics (with TimescaleDB extension)
  
ChromaDB:
  - Vector embeddings (unchanged)
  
LMDB:
  - Working memory cache (unchanged)
```

**Benefits:**
- ✅ True concurrent writes
- ✅ ACID transactions
- ✅ Rich query capabilities
- ✅ Mature ecosystem
- ✅ Scales to enterprise level

**Drawbacks:**
- ❌ Requires PostgreSQL server
- ❌ More complex deployment
- ❌ Higher resource usage
- ❌ Overkill for current scale

**Recommendation:** Only if you need ACID + scale beyond 1000 users

---

## Migration Strategy

### 8.1 Phase 1: Immediate (This Week)

**Separate Metrics Databases**

**Steps:**
1. Create `modelservice_metrics.db` path configuration
2. Update modelservice OTel initialization
3. Update metrics API to query both databases
4. Update Studio to aggregate metrics
5. Test with concurrent load

**Rollback Plan:**
- Keep old code path
- Feature flag for separate DB
- Can revert in minutes

**Success Criteria:**
- ✅ No "database locked" errors in modelservice
- ✅ Metrics export succeeds consistently
- ✅ Request processing not blocked
- ✅ System stable under normal load

### 8.2 Phase 2: Near-Term (Next Sprint)

**Async Export + Separate Logs**

**Steps:**
1. Implement async OTel export worker
2. Create `system_logs.db` for log consumer
3. Increase export interval to 30 seconds
4. Add write queue with overflow handling
5. Load testing with 20-50 simulated users

**Rollback Plan:**
- Feature flags for each component
- Can disable async export
- Can revert to single database

**Success Criteria:**
- ✅ No blocking writes in request path
- ✅ System handles 50 concurrent users
- ✅ Metrics delayed max 30 seconds
- ✅ Graceful degradation under extreme load

### 8.3 Phase 3: Production (Before Launch)

**Time-Series Database**

**Steps:**
1. Set up InfluxDB instance
2. Create OTel exporter configuration
3. Migrate log consumer to InfluxDB
4. Update metrics API to query InfluxDB
5. Update Studio dashboards
6. Parallel run for 1 week (dual write)
7. Cutover to InfluxDB primary
8. Remove SQLite metrics tables

**Rollback Plan:**
- Dual write during transition
- Can switch back to SQLite
- No data loss

**Success Criteria:**
- ✅ System handles 100+ concurrent users
- ✅ Metrics export never fails
- ✅ Sub-second query performance
- ✅ Production-ready observability

---

## Database-Specific Recommendations

### 9.1 LibSQL/SQLite

**Keep For:**
- ✅ User profiles, authentication
- ✅ Conversations, messages
- ✅ Agency system (goals, plans, intentions)
- ✅ Knowledge graph metadata
- ✅ Application configuration

**Remove:**
- ❌ System logs → Move to InfluxDB
- ❌ OTel metrics → Move to InfluxDB
- ❌ System events → Move to InfluxDB or separate DB

**Optimizations:**
```sql
-- Enable WAL mode (already done)
PRAGMA journal_mode = WAL;

-- Increase cache size for better performance
PRAGMA cache_size = -64000;  -- 64MB

-- Optimize for write performance
PRAGMA synchronous = NORMAL;
PRAGMA temp_store = MEMORY;

-- Auto-vacuum to prevent bloat
PRAGMA auto_vacuum = INCREMENTAL;
```

### 9.2 ChromaDB

**Keep For:**
- ✅ Semantic memory embeddings
- ✅ Knowledge graph embeddings
- ✅ Vector similarity search

**Current Status:**
- ✅ No changes needed
- ✅ Performs well
- ✅ Scales adequately

**Future Consideration:**
- If scale beyond 1M vectors, consider Qdrant or Weaviate
- Current ChromaDB sufficient for 100K-1M vectors

### 9.3 LMDB

**Keep For:**
- ✅ Working memory cache
- ✅ Active conversation state
- ✅ Session data

**Current Status:**
- ✅ Excellent performance
- ✅ No concurrency issues
- ✅ No changes needed

**Optimization:**
- Consider increasing map_size for growth
- Monitor disk usage with TTL cleanup

---

## Performance Targets

### 10.1 Current Performance

**Database Operations:**
- Read latency: 1-10ms (good)
- Write latency: 10-100ms (acceptable)
- Lock wait time: 0-5000ms (unacceptable)
- Export duration: 1-5s (too long)

**System Performance:**
- Request latency: 100-500ms (good)
- Request latency under load: 1-30s (unacceptable)
- Metrics export success: 60-80% (unacceptable)
- Log write success: 90-95% (acceptable)

### 10.2 Target Performance (Phase 3)

**Database Operations:**
- Read latency: <5ms
- Write latency: <10ms
- Lock wait time: <100ms
- Export duration: <500ms

**System Performance:**
- Request latency: <200ms (p95)
- Request latency under load: <500ms (p95)
- Metrics export success: >99.9%
- Log write success: >99.9%

**Scalability:**
- Concurrent users: 100+
- Messages/hour: 10,000+
- Metrics/hour: 100,000+
- Uptime: 99.9%

---

## Implementation Checklist

### Phase 1: Immediate (1-2 days)

- [ ] Create `modelservice_metrics.db` configuration
- [ ] Update modelservice OTel exporter initialization
- [ ] Update backend metrics API to query both databases
- [ ] Update Studio metrics aggregation
- [ ] Test concurrent load (backend + modelservice)
- [ ] Monitor for "database locked" errors
- [ ] Deploy to development environment
- [ ] Verify metrics collection working

### Phase 2: Near-Term (1 week)

- [ ] Implement async OTel export worker (backend)
- [ ] Implement async OTel export worker (modelservice)
- [ ] Create `system_logs.db` for log consumer
- [ ] Update log consumer to use separate database
- [ ] Increase export interval to 30 seconds
- [ ] Add write queue with overflow handling
- [ ] Load test with 20-50 simulated users
- [ ] Monitor memory usage (buffering)
- [ ] Deploy to staging environment
- [ ] Verify no blocking writes in request path

### Phase 3: Production (1-2 weeks)

- [ ] Set up InfluxDB instance (local + production)
- [ ] Create InfluxDB buckets (metrics, logs)
- [ ] Implement InfluxDB OTel exporter
- [ ] Update log consumer for InfluxDB
- [ ] Update metrics API to query InfluxDB
- [ ] Update Studio dashboards for InfluxDB
- [ ] Implement dual write (SQLite + InfluxDB)
- [ ] Parallel run for 1 week
- [ ] Verify data consistency
- [ ] Cutover to InfluxDB primary
- [ ] Remove SQLite metrics/logs tables
- [ ] Load test with 100+ simulated users
- [ ] Monitor production performance
- [ ] Document new architecture

---

## Risk Assessment

### High Risk

**Database Corruption:**
- Risk: Concurrent writes could corrupt SQLite database
- Mitigation: WAL mode, busy_timeout, backup strategy
- Status: ✅ Mitigated with current settings

**Data Loss:**
- Risk: Async export could lose metrics if service crashes
- Mitigation: Persistent queue, graceful shutdown
- Status: ⚠️ Needs implementation in Phase 2

**Migration Failure:**
- Risk: InfluxDB migration could fail or lose data
- Mitigation: Dual write, parallel run, rollback plan
- Status: ✅ Mitigated with phased approach

### Medium Risk

**Performance Regression:**
- Risk: Separate databases could slow down queries
- Mitigation: Benchmark before/after, optimize queries
- Status: ⚠️ Monitor during Phase 1

**Increased Complexity:**
- Risk: Multiple databases harder to manage
- Mitigation: Clear documentation, monitoring
- Status: ⚠️ Acceptable tradeoff for scalability

### Low Risk

**Deployment Complexity:**
- Risk: InfluxDB adds deployment dependency
- Mitigation: Docker compose, clear docs
- Status: ✅ Manageable

---

## Conclusion

**Current State:**
- ❌ System experiences deadlocks under normal load
- ❌ Cannot support more than 10-20 concurrent users
- ❌ Metrics and logs create unacceptable write contention
- ❌ User experience degraded (timeouts, failures)

**Recommended Path:**
1. **Phase 1 (Immediate):** Separate metrics databases - Eliminates deadlock, buys time
2. **Phase 2 (Near-term):** Async export + separate logs - Removes blocking writes, scales to 50-100 users
3. **Phase 3 (Production):** InfluxDB for telemetry - Production-grade scalability, 1000+ users

**Key Insight:**
SQLite is excellent for application data but fundamentally incompatible with high-frequency concurrent telemetry writes. The solution is not to fix SQLite, but to use the right tool for each job:
- **LibSQL:** Application data (ACID, relational)
- **InfluxDB:** Telemetry data (time-series, high-frequency)
- **ChromaDB:** Vector embeddings (similarity search)
- **LMDB:** Working memory (high-speed cache)

**Next Steps:**
1. Review and approve this architecture plan
2. Implement Phase 1 (separate metrics databases)
3. Test and verify deadlock resolution
4. Plan Phase 2 implementation
5. Evaluate InfluxDB for Phase 3

---

**Document Version:** 1.0  
**Last Updated:** 2026-01-09  
**Author:** Cascade AI Assistant  
**Status:** Ready for Review
