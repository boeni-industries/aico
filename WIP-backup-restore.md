# WIP: Backup / Restore

## Scope
This document captures **repo-specific** findings for AICO’s backup/restore work, with a focus on **cross-database dependencies** between:

- PostgreSQL (primary system-of-record)
- ChromaDB (vector storage)
- LMDB (working memory)
- Telemetry (InfluxDB and/or OpenTelemetry → SQLite exporter)

Goal: define a restore order and the validations we must enforce to avoid orphaned data and silent corruption.

---

## What I looked at (code pointers)

- **ChromaDB semantic memory**
  - `shared/aico/ai/memory/semantic.py`
- **LMDB working memory**
  - `shared/aico/ai/memory/working.py`
  - `shared/aico/data/lmdb/__init__.py`
- **Knowledge Graph (hybrid: Postgres + ChromaDB)**
  - `shared/aico/ai/knowledge_graph/models.py`
  - `shared/aico/ai/knowledge_graph/storage.py`
- **DB admin / existing backup/restore scaffolding**
  - `backend/api/operations/database_admin.py`
  - `backend/services/backup/restore/chromadb.py`
  - `backend/services/backup/restore/lmdb.py`
- **Telemetry**
  - InfluxDB client: `shared/aico/data/influx/connection.py`
  - OTel storage exporter: `backend/core/otel_storage_adapter.py`

---

## Database overview (as implemented in this repo)

| Database | Type | Primary Purpose | Notes in this repo |
|----------|------|-----------------|--------------------|
| PostgreSQL | Relational | Users, conversations, goals, KG relational storage | Accessed via UoW + repositories; authoritative IDs live here |
| ChromaDB | Vector | Semantic memory segments, KG semantic search collections | Stores **metadata that includes Postgres-scoped IDs** (see below) |
| LMDB | Key-Value | Working memory (recent messages/session state) | Keys are **conversation-scoped**; values include `user_id` |
| InfluxDB | Time-Series | Telemetry/ops metrics/logging | Telemetry storage DB of choice |

Important: telemetry storage DB of choice is **InfluxDB**. There is no supported SQLite/libsql telemetry path.

---

# 1) PostgreSQL → ChromaDB dependencies

### Findings (confirmed)

- [x] **ChromaDB semantic memory stores PostgreSQL-scoped identifiers in metadata**
  - In `shared/aico/ai/memory/semantic.py`, `store_segment()` writes:
    - `user_id`
    - `conversation_id`
    - plus role/language/timestamp fields
  - This means ChromaDB items are **not standalone**: they depend on the same `user_id`/`conversation_id` universe as Postgres.

- [x] **Knowledge Graph is a dual-write system** (Postgres + ChromaDB)
  - `shared/aico/ai/knowledge_graph/storage.py` writes nodes/edges to Postgres first, then upserts into ChromaDB.
  - `shared/aico/ai/knowledge_graph/models.py` shows ChromaDB document format:
    - Node metadata includes: `user_id`, `label`, `canonical_id`, etc.
    - Edge metadata includes: `user_id`, `source_id`, `target_id`, etc.
  - Node/Edge IDs are UUID strings and are used across both stores.

### Implication

- Restoring ChromaDB without the matching Postgres dataset can create:
  - **Orphaned semantic segments** (metadata points to missing user/conversation)
  - **Orphaned KG vectors** (node/edge IDs absent in Postgres KG tables)

### Risk

- **High**: semantic search + KG semantic features will return IDs that can no longer be resolved, or worse, resolve to wrong entities if IDs collide across environments.

### Minimum restore constraints

- **Hard rule**: if restoring ChromaDB, require a compatible Postgres restore **first** (or as part of a coordinated backup set).

---

# 2) PostgreSQL → LMDB dependencies

### Findings (confirmed)

- [x] **LMDB working memory keys are based on `conversation_id`**
  - In `shared/aico/ai/memory/working.py`, `store_message()` uses:
    - key: `f"{conversation_id}:{timestamp.isoformat()}Z"`
  - Retrieval uses prefix scan: `prefix = f"{conversation_id}:"`.

- [x] **LMDB working memory values include Postgres-scoped identifiers**
  - The stored JSON payload preserves the original message dict.
  - `retrieve_user_history()` explicitly looks at `data.get('user_id')`.
  - The LMDB browser orphan check confirms the stored structure expects `user_id` / `userId` fields:
    - `backend/api/operations/lmdb_browser.py` → `find_orphaned_lmdb_entries()`

### Implication

- LMDB is effectively a cache of recent conversation state and is **not authoritative**, but it is tied to the Postgres identity space via `user_id` and `conversation_id`.

### Risk

- **Medium**: restoring LMDB without Postgres can yield stale/broken session context.

### Minimum restore constraints

- Prefer restoring Postgres before LMDB.
- If Postgres restore is done but LMDB is not restored, the system should treat working memory as empty (acceptable).
- If LMDB is restored but Postgres is not, the system should:
  - warn, and/or
  - provide a cleanup option that removes entries whose `user_id` does not exist in Postgres.

---

# 3) PostgreSQL → Telemetry dependencies (InfluxDB)

### Findings (confirmed)

- [x] InfluxDB exists as an integration point in this repo
  - `shared/aico/data/influx/connection.py` provides generic tags/fields API.
  - The client itself does **not enforce** any `user_id`/`conversation_id` tags; callers decide.

- [x] OpenTelemetry metrics are exported to InfluxDB
  - `backend/core/telemetry.py` installs `OTelInfluxExporter` via `PeriodicExportingMetricReader`.

### Implication

- Telemetry is not required for correctness, but it impacts observability and Studio UX.

### Risk

- **Low** for core operation.
- **Operational concern**: telemetry backup/restore should be optional and may be environment-specific.

### Minimum restore constraints

- Telemetry (InfluxDB) can be restored last, or skipped.

---

# 4) ChromaDB → PostgreSQL reverse dependencies

### Findings (partial)

- [ ] Need to confirm whether Postgres stores explicit references to ChromaDB document IDs.

Based on observed patterns:

- Semantic memory uses ChromaDB segment IDs (`segment_id`) that are not obviously stored in Postgres.
- Knowledge graph uses shared IDs and dual-write; Postgres is authoritative for node/edge existence.

### Hypothesis

- Reverse dependency is likely **low** (Postgres does not depend on ChromaDB to be consistent).

---

## Dependency matrix (repo-specific)

| Restore This | Without This | Risk Level | Impact (repo-specific) |
|--------------|--------------|------------|------------------------|
| ChromaDB (semantic memory + KG vectors) | PostgreSQL | High | Orphaned semantic segments and KG vectors; wrong/missing entity resolution |
| LMDB (working memory) | PostgreSQL | Medium | Stale session context; references to missing `user_id`/`conversation_id` |
| InfluxDB | PostgreSQL | Low | Metrics/logging lose context (if tags include IDs); core runtime ok |
| PostgreSQL | ChromaDB | Low | Semantic features degraded until Chroma restored; KG semantic search degraded |
| PostgreSQL | LMDB | Low | Working memory empty until LMDB refills naturally |

---

## Recommended restore order

1. **PostgreSQL**
2. **ChromaDB**
3. **LMDB**
4. **Telemetry** (InfluxDB; optional)

If we implement “backup sets”, restore all of them as a coordinated unit (but still apply the order above internally).

---

## Existing backup/restore scaffolding in repo

### What exists today

- `backend/api/operations/database_admin.py` includes:
  - Directory tar backups for:
    - ChromaDB path: `data/memory/semantic`
    - LMDB path: `data/memory/working`
  - Restore logic for those directories (`shutil.unpack_archive`) and a pre-restore copy.
  - PostgreSQL backup/restore is explicitly **not implemented** (raises 501).

### Gaps

- No coordinated backup-set manifest that pins **all stores** to the same point-in-time.
- No dependency validation before restore.
- No post-restore integrity checks.

---

## Backup/restore implementation requirements (derived from findings)

### Must enforce

- **Dependency validation**
  - Block restoring ChromaDB unless Postgres restore is complete and declared compatible.
  - Warn restoring LMDB alone; offer cleanup.

- **Backup set manifest**
  - Store backup-set metadata:
    - timestamps
    - Postgres schema version
    - Chroma collections present (semantic + kg_nodes + kg_edges)
    - LMDB named DBs present
    - telemetry stores included/skipped

- **Referential integrity checks**
  - ChromaDB semantic segments:
    - sample metadata includes `user_id` and `conversation_id` and must exist in Postgres.
  - KG vectors:
    - `kg_nodes` / `kg_edges` document IDs must exist in Postgres KG tables.
  - LMDB:
    - `user_id` must exist in Postgres; optionally verify `conversation_id` exists.

- **Orphan cleanup tools**
  - LMDB orphan finder already exists (`find_orphaned_lmdb_entries`).
  - Need a similar orphan finder for ChromaDB (segments and KG) by comparing metadata IDs vs Postgres.

---

## Open questions / follow-ups to close before implementation

1. **Postgres schema “source of truth”**
   - Identify the minimal set of tables whose IDs are referenced from Chroma/LMDB.

2. **ChromaDB collections & metadata**
   - Confirm collection names in runtime:
     - semantic memory collection name (`self._collection_name` in `semantic.py`)
     - KG collections: `kg_nodes`, `kg_edges`
   - Confirm whether semantic memory also stores `message_id` anywhere (currently not in `store_segment`).

3. **Telemetry strategy decision**
   - Confirm telemetry backup/restore scope: InfluxDB is the only supported telemetry DB.

---

## Status

- Dependency direction confirmed for:
  - Postgres → ChromaDB (semantic memory + KG vectors)
  - Postgres → LMDB
  - Telemetry is largely independent
- Remaining work:
  - confirm if any Postgres tables store Chroma IDs (reverse dependency)
  - finalize manifest format + required validations for restore API
