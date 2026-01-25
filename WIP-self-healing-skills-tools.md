---
description: Implementation master spec for agency self-healing skills & tools
status: In Progress - Phase 1 (Manual Triggers)
last_updated: 2026-01-24
---

# WIP – Self-Healing Skills & Tools (Implementation Master Spec)

> **Status**: **Phase 1 Implementation In Progress** (Manual Frontend Triggers)
> 
> **Implementation Priority**: 
> 1. **Phase 1**: Manual frontend triggers (user-initiated remediation)
> 2. **Phase 2**: Agency autonomous self-healing
>
> This document is the **single source of truth** for concrete self-healing skills,
> tools, and their contracts. Conceptual and flow explanations live in:
>
> - `docs/concepts/agency/agency-self-healing.md`
> - `docs/concepts/agency/agency-component-skills-tools.md`

## Implementation Status Summary

**Overall Progress: ~35% Complete**

| Component | Status | Completion |
|-----------|--------|------------|
| Infrastructure (Registry, Invoker) | ✅ Complete | 100% |
| Diagnostic Skills | ✅ Complete | 87% (7/8) |
| Diagnostic Tools | ✅ Complete | 100% |
| **Remediation Tools** | 🚧 In Progress | 0% → Target: 100% |
| **Remediation Skills** | 🚧 In Progress | 0% → Target: 100% |
| **Manual Trigger Endpoints** | 🚧 In Progress | 0% → Target: 100% |
| **Frontend UI Components** | 🚧 In Progress | 0% → Target: 100% |
| Agency Self-Healing Loop | ⏳ Planned | 0% |
| Schema Registry | ⏳ Planned | 0% |
| Observables/Metrics | ⏳ Planned | 20% |

## 1. Scope & Goals

This spec defines the **concrete skills and tools** required for AICO's
self-healing and system-maintenance capabilities, aligned with the Agency and
System Health architecture.

### 1.1 Primary Goals

**Goal A: Manual Frontend Triggers (Phase 1 - IN PROGRESS)**
- Enable users to manually trigger remediation actions from AICO Studio Health UI
- Provide immediate actionable fixes for detected issues
- Build confidence in remediation skills before enabling automation
- Deliver immediate value to users

**Goal B: Agency Autonomous Self-Healing (Phase 2 - PLANNED)**
- Enable AICO to detect and fix issues autonomously
- Reduce manual intervention requirements
- Improve system reliability and uptime
- Learn from remediation patterns

### 1.2 Core Principles

- **Atomic, composable tools** that can be safely combined into higher-level
  skills (compound skills), avoiding duplicated logic.
- **Typed contracts** (input/output schemas) that make skills and tools easy to
  discover, validate, and orchestrate by both Agency and LLM-based components.
- **Cross-store awareness** – AICO currently uses **four main data stores**:
  - PostgreSQL (primary transactional state)
  - ChromaDB (semantic vector store)
  - InfluxDB (time-series metrics)
  - LMDB / RocksDB / similar (local key-value / working memory)
- **Self-healing alignment** with:
  - Agency Engine (goals, plans, intentions, arbiter)
  - Scheduler & Lifecycle
  - System Health UI (AICO Studio → System → Health)
  - AMS / World Model / metrics

This document is **implementation-oriented**: it defines registries, naming,
contracts, and the list of concrete skills/tools that need to exist.

Conceptual flows, motivation, and UX are documented in:

- `docs/concepts/agency/agency-self-healing.md`
- `docs/concepts/agency/agency-component-skills-tools.md`


## 2. Design Principles

### 2.1 Atomic but composable

- **Atomic tools** are the smallest executable units (e.g. “check PostgreSQL
  connectivity”, “measure disk usage”, “compact LMDB database”). They:
  - Perform exactly one bounded action.
  - Have well-defined inputs and outputs.
  - Are side-effect scoped and idempotent where possible.
- **Skills** are **semantic wrappers** that:
  - Compose one or more tools into a meaningful capability
    (e.g. `run_connectivity_diagnostics` uses multiple connectivity tools).
  - Are first-class ontology entities (`Skill` nodes).
  - Carry policy and safety metadata, and are the only things the Planner and
    Scheduler execute.
- **Compound skills** are allowed when they encode stable playbooks (e.g.
  “run DB disk-pressure remediation” as a multi-step sequence), but must reuse
  underlying atomic tools.

### 2.2 Registry-driven discovery (no ad-hoc tools)

- All tools and skills are registered in a **Skill & Tool Registry**.
- LLMs and Agency do not invent tools:
  - They query the registry for suitable skills by capability, tags, and
    schemas.
  - Internal execution always goes through `InvokeSkill` → Tool runners.

### 2.3 Typed contracts and schemas

- Every skill and tool has a **referenced schema** for `input` and `output`.
- Schemas are **JSON Schema–like** and live in a shared registry (e.g.
  `config/schemas/agency/*.json`), referenced by `*_schema_id` fields.
- Contracts are **versioned** (`v1`, `v2`, …) to allow non-breaking evolution.

### 2.4 Multi-store awareness

- Maintenance skills must respect the heterogeneity of storage:
  - PostgreSQL (transactions, migrations, archival, index health).
  - ChromaDB (collections, embeddings, metadata hygiene, compaction).
  - InfluxDB (shards, retention policies, time-series compaction).
  - LMDB / working-memory stores (map sizes, compaction, cleanup).
- Tools must be scoped to **one** backend at a time and labelled accordingly.

### 2.5 Safety, auditability, and observability

- Every skill/tool has:
  - `side_effect_tags` (e.g. `reads_metrics`, `modifies_storage`,
    `restarts_service`, `touches_sensitive_data`).
  - `safety_level` (`low`, `medium`, `high`, `privileged`).
  - **Observables**: metrics, PerceptualEvents, system logs.
- All executions are **logged and traceable** via Agency Event Log + metrics
  (OpenTelemetry → SQLite → System Health views).


## 3. Naming, Categorisation & Labels

### 3.1 Skill ID and Tool ID patterns

To support simple, reliable LLM usage and manual querying, we define a
consistent naming convention:

- **Skills** (ontology level):
  - Pattern: `maint.<domain>.<capability>[.variant]`
  - Examples:
    - `maint.connectivity.full_scan`
    - `maint.db.reduce_disk_pressure`
    - `maint.db.postgres.vacuum_analyze`
    - `maint.modelservice.stabilise`
    - `maint.agency.re_evaluate_behaviour_health`

- **Tools** (implementation level):
  - Pattern: `tool.<domain>.<backend>.<action>`
  - Examples:
    - `tool.connectivity.http.check_endpoint`
    - `tool.db.postgres.check_connectivity`
    - `tool.db.postgres.vacuum_analyze`
    - `tool.db.chroma.check_collection_health`
    - `tool.db.influx.check_retention_policies`
    - `tool.db.lmdb.compact_store`
    - `tool.modelservice.zmq.ping`
    - `tool.system.disk.measure_usage`

Domains should be **small, stable sets** such as:

- `connectivity`
- `db` (with `postgres`, `chroma`, `influx`, `lmdb` as `backend` segment)
- `modelservice`
- `message_bus`
- `system` (CPU, memory, disk, OS)
- `agency` (goals, plans, arbiter, AMS)
- `metrics` (InfluxDB / OTel views)


### 3.2 Tags and capability labels

Each skill/tool declares:

- `capability_tags`: short verbs/nouns:
  - e.g. `check_health`, `reduce_load`, `compact_store`, `archive_data`,
    `refresh_connection`.
- `resource_profile`: approximate cost class, e.g. `tiny`, `small`, `medium`,
  `large`, `heavy` (used by Scheduler and for LLM guidance).
- `risk_profile`: e.g. `read_only`, `low_impact`, `medium_impact`, `high_impact`.

These tags are critical for **LLM prompting** and Planner selection:
- “find low_impact skills that check modelservice health” → matches
  `capability_tags=['check_health']`, `risk_profile='read_only'`,
  `domain='modelservice'`.


## 4. Contract Model (Schemas & Runtime Contracts)

### 4.1 Schema IDs

- All skills/tools reference schema IDs:
  - `input_schema_id`: e.g. `schema.maint.connectivity.scan.v1`.
  - `output_schema_id`: e.g. `schema.maint.connectivity.scan_result.v1`.
- Schemas live in a shared folder, e.g. `config/schemas/agency/maint/*.json`.

#### Example: `schema.maint.connectivity.scan.v1`

```json
{
  "$id": "schema.maint.connectivity.scan.v1",
  "type": "object",
  "properties": {
    "targets": {
      "type": "array",
      "items": {
        "type": "string",
        "enum": [
          "gateway_http",
          "backend_api",
          "postgres",
          "chroma",
          "influx",
          "modelservice",
          "message_bus"
        ]
      },
      "description": "Optional subset of connectivity targets. If omitted, run all defaults."
    },
    "timeout_seconds": {
      "type": "number",
      "minimum": 1,
      "maximum": 300
    }
  },
  "additionalProperties": false
}
```

#### Example: `schema.maint.connectivity.scan_result.v1`

```json
{
  "$id": "schema.maint.connectivity.scan_result.v1",
  "type": "object",
  "properties": {
    "summary_status": {"type": "string", "enum": ["healthy", "degraded", "unhealthy"]},
    "checks": {
      "type": "object",
      "additionalProperties": {
        "type": "object",
        "properties": {
          "status": {"type": "string", "enum": ["ok", "warning", "error"]},
          "latency_ms": {"type": "number"},
          "error_message": {"type": "string"},
          "details": {"type": "object"}
        },
        "required": ["status"],
        "additionalProperties": false
      }
    },
    "observables": {
      "type": "object",
      "description": "Optional metrics and PerceptualEvent refs."
    }
  },
  "required": ["summary_status", "checks"],
  "additionalProperties": false
}
```

### 4.2 Runtime contract for skills

Each skill, when invoked via `InvokeSkill`, must adhere to:

```json
{
  "status": "success" | "partial" | "failure",
  "outputs": { /* as defined by output_schema_id */ },
  "observables": {
    "metrics": [/* metric points or references */],
    "events": [/* PerceptualEvent IDs or payloads */],
    "logs": [/* optional log correlation IDs */]
  }
}
```

- `status` is mandatory and used by Planner for backtracking/replanning.
- `observables` are optional but strongly encouraged.

### 4.3 Runtime contract for tools

Tools return a **tool-level result** that the Skill Layer wraps into the skill
result. Tools should not emit PerceptualEvents directly unless specifically
configured; they report raw data and errors.

```json
{
  "ok": true,
  "data": { /* backend-specific data */ },
  "error": null | {
    "code": "string",
    "message": "string"
  }
}
```


## 5. Core Skill Sets (Existing + Self-Healing)

This section lists both the **currently implemented agency skills** and the
**new maintenance/self-healing skills** required for this spec.

### 5.1 Existing Agency Skills (Today)

These skills already exist in `shared/aico/ai/agency/skills` and are wired into
the AgencyEngine via `SkillRegistry` and `SkillInvoker`.

- **analysis**
  - `AnalyzeConversationSkill` – Conversation and pattern analysis.

- **memory**
  - `SearchMemorySkill` – Memory search and retrieval.

- **knowledge**
  - `UpdateKnowledgeGraphSkill` – Knowledge graph management.

- **reflection**
  - `ReflectOnGoalSkill` – Goal and progress reflection.

- **communication**
  - `AskUserSkill` – Ask the user questions / clarifications.
  - `InitiateConversationSkill` – AICO-initiated user interaction / conversation start.


### 5.2 New Maintenance & Self-Healing Skills (Planned)

The following subsections define the **new** `maint.*` skills and supporting
tools to implement self-healing across connectivity, resources, and all four
datastores.

### 5.2.1 Connectivity & Routing

#### Skills

- **Skill** `maint.connectivity.full_scan`
  - Purpose: Run a comprehensive connectivity check for gateway, backend API,
    message bus, modelservice, and core databases.
  - Input schema: `schema.maint.connectivity.scan.v1`.
  - Output schema: `schema.maint.connectivity.scan_result.v1`.
  - Tools used:
    - `tool.connectivity.http.check_endpoint`
    - `tool.modelservice.zmq.ping`
    - `tool.db.postgres.check_connectivity`
    - `tool.db.chroma.check_connectivity`
    - `tool.db.influx.check_connectivity`
    - `tool.message_bus.curvezmq.check_connectivity`

- **Skill** `maint.connectivity.verify_component`
  - Purpose: Check connectivity for a **single named component**.
  - Input: `schema.maint.connectivity.verify_component.v1` (component ID,
    timeout, retries).
  - Output: `schema.maint.connectivity.verify_component_result.v1`.

#### Tools

- `tool.connectivity.http.check_endpoint`
  - Inputs: URL, method, expected status, timeout.
  - Outputs: latency, status, error.

- `tool.modelservice.zmq.ping`
  - Inputs: endpoint, timeout.
  - Outputs: round-trip time, version info.

- `tool.message_bus.curvezmq.check_connectivity`
  - Inputs: broker addresses, topic, timeout.
  - Outputs: ability to publish and receive a test message.

- `tool.db.postgres.check_connectivity`
  - Inputs: optional test query.
  - Outputs: success/failure, latency.

- `tool.db.chroma.check_connectivity`
- `tool.db.influx.check_connectivity`


### 5.2.2 System Resources (CPU, Memory, Disk)

#### Skills

- **Skill** `maint.system.scan_resources`
  - Purpose: Collect a snapshot of CPU, memory, and disk usage.
  - Input: `schema.maint.system.scan_resources.v1` (thresholds, scope).
  - Output: `schema.maint.system.scan_resources_result.v1` (per-resource
    statuses, metrics references).
  - Tools:
    - `tool.system.cpu.measure_load`
    - `tool.system.memory.measure_usage`
    - `tool.system.disk.measure_usage`

- **Skill** `maint.system.detect_pressure`
  - Purpose: Evaluate whether current resource usage warrants maintenance
    actions (e.g. throttling Agency, running disk cleanup).
  - Combines results from `maint.system.scan_resources` and relevant metrics in
    InfluxDB.

#### Tools

- `tool.system.cpu.measure_load`
- `tool.system.memory.measure_usage`
- `tool.system.disk.measure_usage`

Each tool returns scalar measurements + threshold comparisons.


### 5.2.3 PostgreSQL Maintenance

#### Skills

- **Skill** `maint.db.postgres.scan_health`
  - Checks: connectivity, slow queries (from InfluxDB / logs), index bloat
    (where affordable), connection pool saturation.

- **Skill** `maint.db.reduce_disk_pressure`
  - Uses atomic tools (archive, delete, vacuum) under strict bounds.
  - Steps could be split into sub-skills like
    `maint.db.postgres.archive_old_conversations`.

- **Skill** `maint.db.postgres.vacuum_and_analyze`
  - Controlled VACUUM/ANALYZE on selected tables.

#### Tools

- `tool.db.postgres.check_connectivity`
- `tool.db.postgres.get_table_sizes`
- `tool.db.postgres.archive_rows`
- `tool.db.postgres.delete_rows`
- `tool.db.postgres.vacuum_analyze`

Each tool operates on explicit table names and predicates to avoid "magic"
behaviour.


### 5.2.4 ChromaDB (Semantic Store) Maintenance

#### Skills

- **Skill** `maint.db.chroma.scan_collections`
  - Purpose: Enumerate collections, sizes, and basic health.

- **Skill** `maint.db.chroma.compact`
  - Purpose: Run compaction/gc on selected collections, optionally deleting
    orphaned or low-value embeddings.

#### Tools

- `tool.db.chroma.check_collection_health`
- `tool.db.chroma.get_collection_stats`
- `tool.db.chroma.delete_vectors`
- `tool.db.chroma.compact_store`


### 5.2.5 InfluxDB (Metrics) Maintenance

#### Skills

- **Skill** `maint.db.influx.scan_retention_policies`
- **Skill** `maint.db.influx.enforce_retention`

#### Tools

- `tool.db.influx.check_connectivity`
- `tool.db.influx.list_retention_policies`
- `tool.db.influx.apply_retention_policy`


### 5.2.6 LMDB / Working Memory Maintenance

#### Skills

- **Skill** `maint.db.lmdb.scan_health`
- **Skill** `maint.db.lmdb.compact_store`
- **Skill** `maint.db.lmdb.cleanup_obsolete_entries`

#### Tools

- `tool.db.lmdb.check_map_size`
- `tool.db.lmdb.compact`
- `tool.db.lmdb.delete_keys_by_prefix`


### 5.2.7 Modelservice & LLM Pipeline

#### Skills

- **Skill** `maint.modelservice.scan_health`
  - Uses connectivity tools, simple test completions/embeddings.

- **Skill** `maint.modelservice.stabilise`
  - If scan shows errors, attempts controlled recovery:
    - refresh connections, restart workers, clear internal caches.

#### Tools

- `tool.modelservice.zmq.ping`
- `tool.modelservice.request_test_completion`
- `tool.modelservice.request_test_embedding`
- `tool.modelservice.restart_workers` (if allowed and safe)


### 5.2.8 Agency & Behavioural Health

#### Skills

- **Skill** `maint.agency.re_evaluate_behaviour_health`
  - Aggregates metrics and AMS/World Model signals about:
    - stalled plans, open loops, reflection cadence, memory integrity.

- **Skill** `maint.agency.recover_stalled_plans`
  - Attempts to either replan, retire, or mark stale plans.

- **Skill** `maint.agency.rebalance_load`
  - Adjusts scheduler caps for maintenance vs user-facing work vs curiosity.

#### Tools

- `tool.agency.metrics.snapshot`
- `tool.agency.detect_stalled_plans`
- `tool.agency.update_scheduler_config`


## 6. Integration with Agency & System Health

This section summarises how the skills/tools are used in the **self-healing
loop** (detailed flows are in `agency-self-healing.md`).

1. **Health signals** from:
   - HealthCheckTask (backend scheduler),
   - metrics (InfluxDB / OTel),
   - modelservice health checks,
   - Agency metrics (AMS / World Model),
   are normalised into **PerceptualEvents**.

2. PerceptualEvents are transformed into **maintenance goals** with
   `origin = system_maintenance`, tagged by domain (`database`, `modelservice`,
   `agency`, etc.).

3. Planner attaches **plans** whose steps invoke skills such as
   `maint.connectivity.full_scan`, `maint.db.reduce_disk_pressure`,
   `maint.modelservice.stabilise`, `maint.agency.re_evaluate_behaviour_health`.

4. Scheduler executes skills via `InvokeSkill`, which dispatches to atomic
   tools while enforcing **Lifecycle** and resource limits.

5. Results update:
   - maintenance goals and execution records,
   - System Health status (via dedicated endpoints),
   - metrics (InfluxDB/OTel),
   - AMS / World Model (facts about system health and past repairs).


## 7. Implementation Roadmap

This section defines the **phased implementation plan** with manual triggers
implemented first, followed by autonomous self-healing.

### PHASE 1: Manual Frontend Triggers (CURRENT PHASE)

**Goal**: Enable users to manually trigger remediation actions from Health UI

#### 1.1 Foundation (COMPLETE ✅)
   - [x] Implement `SkillRegistry` and `ToolRegistry`
   - [x] Implement `SkillInvoker` with timeout and error handling
   - [x] Define `Skill` and `ToolDefinition` contracts
   - [x] Implement diagnostic skills (7/8 complete)
   - [x] Implement diagnostic tools (20+ tools)

#### 1.2 Remediation Tools (IN PROGRESS 🚧)
   - [ ] **PostgreSQL Tools**:
     - [ ] `tool.db.postgres.get_table_sizes` - Query table/index sizes
     - [ ] `tool.db.postgres.vacuum_analyze` - Run VACUUM ANALYZE
     - [ ] `tool.db.postgres.archive_rows` - Archive old data to separate table
     - [ ] `tool.db.postgres.delete_rows` - Delete rows with safety checks
   
   - [ ] **ChromaDB Tools**:
     - [ ] `tool.db.chroma.get_collection_stats` - Collection size/count
     - [ ] `tool.db.chroma.delete_vectors` - Delete vectors by filter
     - [ ] `tool.db.chroma.compact_store` - Trigger compaction
   
   - [ ] **InfluxDB Tools**:
     - [ ] `tool.db.influx.list_retention_policies` - List retention policies
     - [ ] `tool.db.influx.apply_retention_policy` - Apply/update retention
     - [ ] `tool.db.influx.drop_measurement` - Drop old measurements
   
   - [ ] **LMDB Tools**:
     - [ ] `tool.db.lmdb.check_map_size` - Check map size vs usage
     - [ ] `tool.db.lmdb.compact` - Compact database
     - [ ] `tool.db.lmdb.delete_keys_by_prefix` - Bulk delete by prefix
   
   - [ ] **Modelservice Tools**:
     - [ ] `tool.modelservice.restart_workers` - Restart worker processes
     - [ ] `tool.modelservice.clear_cache` - Clear internal caches
   
   - [ ] **Agency Tools**:
     - [ ] `tool.agency.retire_stalled_plans` - Mark plans as retired
     - [ ] `tool.agency.update_scheduler_config` - Adjust scheduler settings

#### 1.3 Remediation Skills (IN PROGRESS 🚧)
   - [ ] **Database Remediation**:
     - [ ] `maint.db.postgres.vacuum_and_analyze` - PostgreSQL maintenance
     - [ ] `maint.db.postgres.archive_old_data` - Archive old conversations/events
     - [ ] `maint.db.reduce_disk_pressure` - Comprehensive disk cleanup
     - [ ] `maint.db.chroma.compact` - ChromaDB compaction
     - [ ] `maint.db.lmdb.compact_store` - LMDB compaction
     - [ ] `maint.db.lmdb.cleanup_obsolete_entries` - LMDB cleanup
   
   - [ ] **Service Remediation**:
     - [ ] `maint.modelservice.stabilise` - Restart/recover modelservice
     - [ ] `maint.agency.recover_stalled_plans` - Fix stalled plans
     - [ ] `maint.agency.rebalance_load` - Adjust scheduler load
   
   - [ ] **System Remediation**:
     - [ ] `maint.system.clear_temp_files` - Clean temporary files
     - [ ] `maint.system.restart_component` - Restart specific component

#### 1.4 HTTP Endpoints for Manual Triggering (IN PROGRESS 🚧)
   - [ ] Create `/api/v1/system/health/remediate` router
   - [ ] Implement endpoints:
     - [ ] `POST /remediate/{skill_id}` - Trigger specific remediation skill
     - [ ] `GET /remediate/available` - List available remediation skills
     - [ ] `GET /remediate/history` - View remediation execution history
     - [ ] `POST /remediate/{skill_id}/dry-run` - Preview remediation effects
   - [ ] Add authentication and authorization checks
   - [ ] Implement execution tracking and logging
   - [ ] Add rate limiting for safety

#### 1.5 Frontend UI Components (IN PROGRESS 🚧)
   - [ ] **Health Tab Enhancements**:
     - [ ] Add "Remediate" button to each degraded/critical component
     - [ ] Show available remediation actions per component
     - [ ] Display remediation execution status (running/success/failed)
     - [ ] Show remediation history timeline
   
   - [ ] **Remediation Modal**:
     - [ ] Skill description and safety information
     - [ ] Parameter inputs (if skill requires configuration)
     - [ ] Dry-run preview option
     - [ ] Confirmation dialog with impact warning
     - [ ] Real-time execution progress
     - [ ] Success/failure feedback with logs
   
   - [ ] **Remediation History View**:
     - [ ] List of past remediation executions
     - [ ] Filter by skill, status, date
     - [ ] Detailed execution logs
     - [ ] Before/after metrics comparison

#### 1.6 Safety & Validation (IN PROGRESS 🚧)
   - [ ] Implement dry-run mode for all remediation skills
   - [ ] Add confirmation requirements for high-impact actions
   - [ ] Implement rollback mechanisms where possible
   - [ ] Add execution time limits and resource caps
   - [ ] Log all remediation actions to audit trail
   - [ ] Emit metrics for remediation success/failure rates

---

### PHASE 2: Agency Autonomous Self-Healing (PLANNED)

**Goal**: Enable AICO to detect and fix issues autonomously

#### 2.1 PerceptualEvent Emission (PLANNED ⏳)
   - [ ] Emit PerceptualEvents from health check skills
   - [ ] Define event schemas for different issue types
   - [ ] Wire events into Agency perception pipeline
   - [ ] Add event deduplication and aggregation

#### 2.2 Maintenance Goal Generation (PLANNED ⏳)
   - [ ] Create goal templates for common issues:
     - [ ] `goal.maintenance.database_pressure`
     - [ ] `goal.maintenance.service_degraded`
     - [ ] `goal.maintenance.resource_exhaustion`
   - [ ] Implement goal creation from PerceptualEvents
   - [ ] Add priority scoring for maintenance goals
   - [ ] Define goal success criteria

#### 2.3 Plan Templates (PLANNED ⏳)
   - [ ] Create plan templates for remediation workflows:
     - [ ] Database cleanup workflow (check → backup → clean → verify)
     - [ ] Service restart workflow (check → drain → restart → verify)
     - [ ] Resource pressure workflow (measure → identify → remediate → verify)
   - [ ] Implement plan template instantiation
   - [ ] Add plan step dependencies and rollback logic

#### 2.4 Arbiter Integration (PLANNED ⏳)
   - [ ] Add maintenance goal scoring to Arbiter
   - [ ] Implement priority balancing (user goals vs maintenance)
   - [ ] Add safety checks for autonomous execution
   - [ ] Define execution time windows (e.g., low-traffic periods)
   - [ ] Implement rate limiting for autonomous actions

#### 2.5 Scheduler Integration (PLANNED ⏳)
   - [ ] Add maintenance goal execution to scheduler
   - [ ] Implement resource caps for maintenance work
   - [ ] Add execution history tracking
   - [ ] Implement success/failure learning

#### 2.6 Observability & Learning (PLANNED ⏳)
   - [ ] Emit metrics for all remediation executions
   - [ ] Track success rates per skill
   - [ ] Implement pattern detection (recurring issues)
   - [ ] Add World Model integration (learn from fixes)
   - [ ] Create dashboards for autonomous healing activity

---

### PHASE 3: Advanced Features (FUTURE)

#### 3.1 Schema Registry (FUTURE 🔮)
   - [ ] Create JSON schema files for all skills
   - [ ] Implement schema validation in Skill Layer
   - [ ] Add schema versioning support
   - [ ] Generate documentation from schemas

#### 3.2 Predictive Maintenance (FUTURE 🔮)
   - [ ] Analyze metrics trends to predict issues
   - [ ] Trigger preventive maintenance before failures
   - [ ] Learn optimal maintenance schedules

#### 3.3 Multi-Instance Coordination (FUTURE 🔮)
   - [ ] Coordinate remediation across multiple AICO instances
   - [ ] Implement distributed locking for shared resources
   - [ ] Add cluster-wide health monitoring

---

## 8. Current Implementation Status (Detailed)

### ✅ COMPLETE

**Infrastructure:**
- SkillRegistry with category indexing and lookup
- ToolRegistry with domain/capability filtering  
- SkillInvoker with timeout and error handling
- Skill/Tool contract model (SkillResult, ToolDefinition)

**Diagnostic Skills (7/8):**
- `maint.connectivity.full_scan` ✅
- `maint.system.scan_resources` ✅
- `maint.modelservice.scan_health` ✅
- `maint.agency.re_evaluate_behaviour_health` ✅
- `maint.messagebus.check_health` ✅
- `maint.scheduler.check_health` ✅
- `maint.agency.cleanup_executions` ✅

**Diagnostic Tools (20+):**
- Connectivity: postgres, influx, chroma, lmdb, modelservice, ollama ✅
- Database health: postgres, chroma, influx, lmdb ✅
- System resources: cpu, memory, disk ✅
- Agency: metrics snapshot, stalled plan detection ✅
- Scheduler: status check, stuck task detection ✅
- Message bus: status check ✅

**Integration:**
- HealthService aggregates skill results ✅
- Health Router HTTP endpoints ✅
- Scheduler health check tasks ✅
- Frontend Health UI displays data ✅

### 🚧 IN PROGRESS (Phase 1)

**Remediation Tools:** 0% → Target: 100%
**Remediation Skills:** 0% → Target: 100%
**Manual Trigger Endpoints:** 0% → Target: 100%
**Frontend UI Components:** 0% → Target: 100%

### ⏳ PLANNED (Phase 2)

**Agency Self-Healing Loop:** 0%
**PerceptualEvent Emission:** 0%
**Maintenance Goal Generation:** 0%
**Plan Templates:** 0%
**Arbiter Integration:** 0%

### 🔮 FUTURE (Phase 3)

**Schema Registry:** 0%
**Predictive Maintenance:** 0%
**Multi-Instance Coordination:** 0%
