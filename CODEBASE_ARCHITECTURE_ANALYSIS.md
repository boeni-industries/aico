# AICO Codebase Architecture Analysis
**Date:** 2026-01-13  
**Purpose:** PostgreSQL migration assessment  
**Scope:** Complete codebase (backend, shared, CLI, modelservice)

---

## Executive Summary

**Critical Findings:**
- **~2,900 raw SQL queries** across **149 files**
- **Zero abstraction layer** - direct SQL in business logic
- **SQLite-specific syntax** throughout (PRAGMA, datetime(), json_set())
- **No Repository/UoW/ORM patterns**
- **Severe architectural debt**
- **Performance workarounds** embedded everywhere

**Migration Complexity:** HIGH - Requires architectural refactoring, not just database swap.

---

## 1. SQL Query Distribution

| Module | Files | Queries | Pattern |
|--------|-------|---------|----------|
| shared/ai/agency | 25 | ~800 | Goals, plans, policies |
| shared/ai/knowledge_graph | 12 | ~300 | Nodes, edges, temporal |
| shared/ai/memory | 15 | ~250 | Working, episodic, semantic |
| shared/data | 8 | ~200 | Users, auth, sessions |
| backend/api | 45 | ~600 | REST endpoints |
| backend/scheduler | 8 | ~150 | Task storage |
| backend/services | 12 | ~200 | Conversation, emotion |
| cli/commands | 24 | ~400 | Admin operations |
| **TOTAL** | **149** | **~2,900** | Mixed |

**SQLite-Specific Syntax Requiring Conversion:**
- PRAGMA statements (key, journal_mode, busy_timeout, wal_autocheckpoint, cache_size)
- datetime() functions → NOW() or CURRENT_TIMESTAMP (150+ locations)
- json_set() → jsonb_set() (45+ locations)
- json_extract() → JSONB operators (30+ locations)
- AUTOINCREMENT → SERIAL/BIGSERIAL
- INSERT OR REPLACE/IGNORE → ON CONFLICT (80+ locations)

---

## 2. Architectural Anti-Patterns

**❌ ANTI-PATTERN 1: Raw SQL in Business Logic**
- SQL mixed directly in business logic (100+ locations)
- No query reusability, hard to test, difficult to migrate, no type safety

**❌ ANTI-PATTERN 2: Store Classes Are Just SQL Wrappers**
- 25+ "Store" classes that just execute raw SQL
- No abstraction value, tight coupling to database

**❌ ANTI-PATTERN 3: Dual-Write Without Transactions**
- LibSQL + ChromaDB writes without coordination
- No atomicity, potential inconsistency, no rollback

**❌ ANTI-PATTERN 4: Manual Row-to-Object Mapping**
- Brittle positional access (row[0], row[1]...) in 100+ locations
- Breaks if column order changes, repetitive boilerplate

**❌ ANTI-PATTERN 5: Query String Concatenation**
- SQL injection risks, unmaintainable

**Current Architecture:**
- API Layer → "Store" Classes → EncryptedLibSQLConnection → SQLite
- Missing: Repository pattern, Unit of Work, Query Builder, ORM, Connection pooling, Query caching, Migration framework

---

## 3. Performance Issues & Workarounds

**Database Lock Contention:**
- busy_timeout pragmas (10-30 seconds) - band-aids for SQLite's single-writer limitation

**Retry Logic Scattered:**
- Found in: metrics_collector.py, scheduler/storage.py, knowledge_graph/storage.py
- Problem: Retry logic should not be in business code

**Manual Async/Sync Bridging:**
- asyncio.to_thread() wrapper pattern in 50+ locations
- Error-prone and inefficient

---

## 4. Maintainability Issues

**Query Duplication:**
- User lookup: 12 files | Goal retrieval: 8 files | Session validation: 15 files
- Bug fixes require changes in multiple places

**No Query Testing:**
- Zero unit tests for SQL queries
- No performance testing or query plan analysis

**Schema Management:**
- 178 SQL statements in schema.py
- Manual migration tracking, no rollback, no versioning

---

## 5. Target Architecture (Modern Best Practices)

**Proposed Layers:**
1. **API Layer** - FastAPI route handlers, Pydantic schemas, dependency injection
2. **Service Layer** - Business logic, orchestrates repositories, transaction boundaries
3. **Repository Layer** - Data access, abstract interfaces (Protocol/ABC), concrete implementations
4. **Unit of Work** - Transaction management, atomic operations, rollback on failure
5. **Query Builder** - SQLAlchemy Core (recommended) or ORM or Pypika
6. **Connection Pool** - asyncpg (async) or psycopg3 (sync/async)
7. **PostgreSQL** - Multi-writer support, JSONB, CTEs, window functions

**Key Patterns:**
- Repository Pattern: Abstract interfaces with concrete PostgreSQL implementations
- Unit of Work: Transaction management across multiple repositories
- Query Builder: SQLAlchemy Core for type-safe, composable queries
- Connection Pooling: asyncpg or psycopg3 with 10-50 connections

---

## 6. Migration Strategy (DECIDED)

**✅ BIG BANG APPROACH (10 weeks):**
1. **Foundation (Week 1-2)** - Repository interfaces, SQLAlchemy Core tables, Unit of Work, asyncpg connection
2. **Core Modules (Week 3-4)** - User/Auth, Agency, Knowledge Graph repositories
3. **API Layer (Week 5)** - Update FastAPI endpoints, remove direct SQL, dependency injection
4. **Remaining (Week 6-7)** - Memory, Scheduler, Behavioral/AMS repositories, CLI commands
5. **Migration & Testing (Week 8-9)** - Data migration tool (LibSQL → Postgres), comprehensive testing
6. **Cutover (Week 10)** - Stop all services, migrate data, switch to Postgres, restart

**No Coexistence:** Single cutover event, no dual-database period

---

## 7. Technology Stack (DECIDED)

**Database Layer:** ✅ **SQLAlchemy Core + asyncpg**
- Query builder (not full ORM), lightweight, type-safe, async support, database-agnostic

**Connection Pooling:** asyncpg (10-50 connections)

**Migration Framework:** Alembic (auto-generate migrations, rollback support)

**Postgres Environment:** ✅ **Already containerized and ready** (schema installed)

---

## 8. Code Quality Improvements

**Remove Workarounds:**
- busy_timeout pragmas, retry logic, manual async/sync bridging, thread locks, WAL config

**Consolidate Queries:**
- Create query modules (e.g., AgencyQueries) for reusable query patterns

**Add Testing:**
- Unit tests for all repositories
- Query performance testing

---

## 9. Performance Optimizations

**Connection Pooling:** 10-20x throughput increase (single connection → pool)

**Postgres Features:** JSONB operators, CTEs, window functions, proper indexes

**Batch Operations:** Bulk inserts/updates instead of N individual queries

---

## 10. Risk Assessment

**High Risk:**
1. Query conversion errors (SQLite → Postgres syntax) - Mitigation: Comprehensive tests, gradual rollout
2. Performance regressions - Mitigation: Benchmark before/after, optimize hot paths
3. Data migration failures - Mitigation: Multiple backups, dry-run testing, rollback plan

**Medium Risk:**
1. Learning curve (new patterns) - Mitigation: Documentation, examples, pair programming
2. Integration issues (ChromaDB/LMDB) - Mitigation: Keep hybrid storage, thorough testing

---

## 11. Success Metrics

**Code Quality:** Zero raw SQL in business logic, 100% query coverage, type-safe queries, no duplication

**Performance:** <10ms query latency (p95), 1000+ concurrent users, zero "database locked" errors, 99.9% uptime

**Maintainability:** Single source of truth, easy to add queries, database-agnostic, comprehensive tests

---

## 12. Effort Estimate

| Phase | Duration | Person-Days |
|-------|----------|-------------|
| Architecture Design | 1 week | 5 |
| Foundation Layer | 2 weeks | 10 |
| Core Repositories | 2 weeks | 10 |
| API Migration | 1 week | 5 |
| Remaining Modules | 2 weeks | 10 |
| Data Migration Tool | 1 week | 5 |
| Testing & QA | 1 week | 5 |
| **TOTAL** | **10 weeks** | **50** |

**Team Size:** 2-3 developers

---

## 13. Implementation Plan (DECIDED)

**Immediate Actions:**
1. ✅ Stop adding raw SQL - require repository pattern for new queries
2. Create architecture spike - proof-of-concept for one module (User/Auth)
3. ✅ Postgres ready (containerized, schema installed)
4. Design repository interfaces - define contracts first

**Implementation:**
1. ✅ SQLAlchemy Core (query builder) - DECIDED
2. Repository pattern with Protocol interfaces
3. Unit of Work for transaction management
4. Comprehensive repository tests
5. Document patterns (ADRs)
6. Build data migration tool
7. Big Bang cutover (Week 10)

---

## Conclusion

AICO has **severe architectural debt** in data access:
- ❌ Unmaintainable (2,900+ queries to migrate)
- ❌ Untestable (no query isolation)
- ❌ Unscalable (SQLite limitations)
- ❌ Risky (no abstraction)

**This is not a database swap - it requires architectural refactoring.**

**✅ APPROVED PLAN:** 10-week Big Bang migration with SQLAlchemy Core, Repository pattern, Unit of Work. Postgres containerized and ready. Single cutover event in Week 10.
