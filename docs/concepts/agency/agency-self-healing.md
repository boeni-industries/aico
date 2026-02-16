---
title: Agency Self-Healing & System Health Integration
---

# Agency Self-Healing & System Health Integration

## Status

- **Implemented (v1)**: system health endpoints exist for Studio/system integration (see `backend/api/system/health/router.py`).
- **Implemented (v1)**: basic service/process health endpoints exist (see `backend/api/health/router.py`, including `GET /api/health` and `GET /api/health/detailed`).
- **Implemented (v1)**: automated issue detection is scheduled via `system.health.issue_detection` (see `backend/scheduler/tasks/issue_detection.py`).
- **Implemented (v1)**: issue detection uses maintenance skills from the Skill layer (see `aico.ai.agency.skills.maintenance.*`).
- **WIP**: normalizing all health signals into persisted `PerceptualEvent` objects and using them as the canonical trigger for maintenance goal creation.

## 1. Purpose

This document specifies how **Agency** implements self-healing behaviour that is
**aligned with the System Health UI** in AICO Studio.

Goals:

- Use the **same maintenance actions** for:
  - user-driven troubleshooting from the **System → Health** tab, and
  - autonomous **self-healing** driven by Agency.
- Make self-healing **transparent, auditable, and bounded** by Values & Ethics,
  Scheduler, and Lifecycle.
- Keep remediation logic **DRY**: implement maintenance actions once as
  ontology-backed skills/tools; both frontend and Agency call into them.

This document is the main **conceptual reference** for self-healing behaviour in
backend services and Agency components. The **implementation master spec** for
the concrete skills, tools, and contracts used here is:

- `WIP-self-healing-skills-tools.md` (project root)

Related docs:

- `agency-component-goals-intentions.md`
- `agency-component-skills-tools.md`
- `agency-component-lifecycle.md`
- `agency-component-memory-ams.md`
- `agency-component-self-reflection.md`
- `agency-metrics.md`
- `/aico-studio/docs/system-design.md` (System → Health tab, Health Checks bar)


## 2. Conceptual Overview

At a high level, self-healing follows this loop:

1. **Health signal**  
   - A backend health check, metric, or anomaly detector reports a degraded
     condition (infra or agency-level).
2. **Maintenance goal**  
   - Agency represents this as a **system-maintenance goal** in the goal graph.
3. **Plan & skills**  
   - Planner attaches a **remediation plan** whose executable steps use
     maintenance skills/tools defined in the Skill & Tool Layer.
4. **Execution via Scheduler**  
   - Scheduler executes the skills, respecting Lifecycle and resource budgets.
5. **Verification & feedback**  
   - Health checks are re-run; outcomes update metrics and goals; the frontend
     Health tab shows the results.

The **System Health UI** and **Agency** are two *clients* of the same
maintenance skills:

- The Health tab exposes **explicit troubleshooting buttons**.
- Agency uses the same skills as part of its **background maintenance plans**.


## 3. Entities and Signals

### 3.1 Health signals

Self-healing is triggered by **health signals** from infrastructure and
agency-level components. Examples (spanning AICO's multi-store architecture of PostgreSQL, ChromaDB,
InfluxDB, and LMDB/working-memory stores):

- `GET /api/health` and `GET /api/health/detailed` responses (CPU, memory, disk,
  Modelservice, Ollama, message bus).
- System Health endpoints for Studio workflows (see `backend/api/system/health/router.py`), e.g.:
  - `GET /api/system/health/health`
  - `GET /api/system/health/health/issues`
  - `POST /api/system/health/health/check/connectivity`
  - `POST /api/system/health/health/check/resources`
  - `POST /api/system/health/health/check/models`
  - `POST /api/system/health/health/check/ai-behaviour`
- Modelservice health handler signals (ZMQ health checks).
- Operations telemetry (latency, error rates).
- Agency metrics (see `agency-metrics.md`):
  - `plan_execution_success_rate` per goal type.
  - `curiosity_goals_active` and `curiosity_goal_outcomes`.
  - `open_loops_count`, `last_consolidation_time`.
  - `lifecycle_phase`, `scheduled_agency_tasks`, etc.

All such conditions are conceptually normalised into **PerceptualEvents** with a suitable
`percept_type` (**WIP**: persisted PerceptualEvent ingestion as a canonical trigger):

- `SystemMaintenanceEvent` (e.g., DB disk pressure, memory index fragmentation).
- `RiskOrOpportunityEvent` (e.g., critical component unhealthy).
- `PatternEvent` (e.g., recurring plan failures).

These events are produced by health/check components and are consumed by the
Goal & Intention System (**WIP**: a single canonical `ProposeGoalFromPercept` integration surface; some paths currently create maintenance goals more directly).

### 3.2 Maintenance goals

Health-related goals are modelled as **maintenance goals** in the goal graph
(see `agency-component-goals-intentions.md`):

- `origin = system_maintenance` (sometimes `curiosity` or `agent_self` when
  optimisations are exploratory).
- `tags` typically include `infra`, `maintenance`, `self_healing`, and
  component-specific tags such as `database`, `modelservice`, `agency`,
  `world_model`.

Examples:

-- `g_reduce_db_disk_pressure` – "Reduce DB disk usage below 70%", combining
  PostgreSQL archival, ChromaDB/InfluxDB retention, and LMDB compaction skills
  as defined in `WIP-self-healing-skills-tools.md`.
- `g_restore_modelservice_connectivity` – "Restore healthy modelservice
  responses".
- `g_recover_stalled_plans` – "Identify and repair stalled plan executions".
- `g_repair_ai_behaviour_health` – "Restore healthy AI behaviour:
  active goals, non-stalled plans, recent reflections, sane context".

Whether a maintenance goal becomes an **active intention** depends on:

- Goal Arbiter scoring and caps on active maintenance intentions.
- Lifecycle state (prefer SLEEP_LIKE/MAINTENANCE for heavy work).
- Values & Ethics policies (some actions may require consent or be
  user-trigger-only).


## 4. Shared Maintenance Skills & Tools

Maintenance actions are implemented as **skills** in the Skill & Tool Layer
(see `agency-component-skills-tools.md`) and **reused** by both Agency and the
System Health UI.

### 4.1 Principle: single implementation path

For each troubleshooting action exposed in the Health tab, there must be a
corresponding **Skill** (ontology-level) and Tool implementation (code-level):

- Health tab button → hits a backend endpoint → calls **Skill** via a thin
  service layer.
- Agency plan step → Scheduler executes **Skill** → same underlying Tool(s).

This keeps remediation logic **DRY** and guarantees that human-triggered and
self-triggered repairs behave identically, pass through the same guardrails,
and generate the same telemetry.

### 4.2 Example maintenance skills

Non-exhaustive examples that correspond to current and planned Health tab
playbooks:

- `run_connectivity_diagnostics`
  - Checks connectivity for gateway, DB, modelservice, message bus.  
  - Emits PerceptualEvents with detailed component results and metrics.

- `reduce_db_disk_pressure`
  - Invokes a bounded sequence such as:  
    - identify archival candidates (old conversations/logs),  
    - archive or delete within configured policies,  
    - re-check disk usage.  
  - Exposes parameters for **safe bounds** (max GB per run, time windows).

- `stabilise_modelservice`
  - Runs health checks, triggers safe restarts or pool refreshes where allowed,
    and revalidates inference health.

- `rebalance_agency_load`
  - Adjusts Scheduler priorities, pauses low-priority agency tasks, or reduces
    curiosity-driven load when resource scans show sustained overload.

- `re-evaluate_ai_behaviour_health`
  - Combines agency metrics and AMS/World Model queries to evaluate:
    - `active_intentions` and `open_loops_count`,
    - stalled plans or repeated plan failures,
    - reflection cadence and lesson application,
    - context/memory integrity signals.
  - Emits PerceptualEvents that can create or update AI-behaviour issues in the
    System Health tab.

Each of these is defined as a `Skill` with:

- clear `input_schema_id` / `output_schema_id`,
- `side_effect_tags` (e.g. `modifies_storage`, `restarts_service`),
- `safety_level` (often `high` or `privileged`),
- mapping to one or more Tool implementations that operate in backend services
  only.


## 5. End-to-End Flows

### 5.1 User-initiated troubleshooting (via Health tab)

1. User opens **System → Health** in AICO Studio.  
   The Health Checks bar shows bundles (Connectivity, Resources, Models &
   Pipeline, AI Behaviour), each with badges indicating recent results.
2. User clicks a bundle button (e.g. **Connectivity Scan**) to run all checks,
   or expands the dropdown and clicks a specific test row.
3. Frontend calls a backend endpoint (e.g. `POST /api/system/health/run` with
   `check_group=connectivity` or `check_id=conn_gateway`).
4. Backend endpoint:
   - Validates request and user permissions.
   - Invokes the appropriate **maintenance skills** (`run_connectivity_diagnostics`,
     etc.) via the Skill & Tool Layer.
   - Logs results as PerceptualEvents, metrics, and System Health entries.
5. Health tab updates:
   - Bundle badges and per-test status pills.
   - Active Issues Playbook cards (e.g. "Modelservice not available").

From Agency’s perspective, this is equivalent to a **user-triggered
maintenance plan** with a single step, executed immediately.

### 5.2 Agency-initiated self-healing

1. A health signal (infra or agency-level) is detected:
   - e.g. disk usage > threshold, repeated modelservice failures, stalled
     execution plans, missing active goals during recent activity.
2. A maintenance goal is created/updated.
   - Conceptually this can be driven by a `PerceptualEvent` (`SystemMaintenanceEvent`, `RiskOrOpportunityEvent`).
   - Current backend wiring also supports direct creation of maintenance goals by system services (e.g. Issue Detection) as an implementation shortcut.
4. Goal Arbiter may activate the goal as an intention, subject to:
   - Values & Ethics policies (some actions require consent).  
   - Lifecycle state (heavy actions deferred to SLEEP_LIKE / MAINTENANCE).  
   - Caps on concurrent maintenance goals.
5. Planner attaches a **remediation plan** using the same skills as the Health
   tab playbook.
   - For Issue Detection–driven self-healing, the plan is intentionally deterministic:
     - scan → remediate → verify, where each step has an explicit `maint.*` `skill_id`.
6. Scheduler executes these steps over time (or immediately for bounded E2E testing), honouring:
   - Lifecycle & resource budgets (see `agency-component-lifecycle.md`).  
   - Values & Ethics decisions for each skill invocation.
7. Results are fed back as:
   - updates to the maintenance goal and its plan/execution records,  
   - PerceptualEvents for System Health,  
   - metrics for `agency-metrics.md`, and
   - potential lessons in `agency_lessons` via Self-Reflection.
8. Frontend Health tab:
   - When loaded, calls backend health endpoints that now reflect Agency’s
     recent actions.  
   - Issue cards may show that actions were **auto-attempted** by Agency
     (e.g. "AICO already ran connection diagnostics and stabilisation").

### 5.3 Mixed-initiative

Self-healing is intentionally **mixed-initiative**:

- Agency may **suggest** a remediation path but require a user click to run
  high-impact skills (e.g. "Restart database", "Delete large archives").
- Health tab surfaces both **current status** and **what Agency has
  already tried**.
- Some skills are **user-trigger-only**, enforced via Values & Ethics and
  skill metadata.


### 5.4 Manual and test triggers (for verification)

Self-healing must work for real issues, but it is useful to have a deterministic
end-to-end trigger for testing and demos.

The backend uses the Scheduler task:

- `system.health.issue_detection`

to run detection and (optionally) create maintenance goals and run the agency
loop.

Manual trigger via CLI:

```bash
uv run aico scheduler trigger system.health.issue_detection
```

Inspect outcomes via Scheduler history and agency inspection commands.


## 6. Guardrails & Safety

Self-healing must remain within the same guardrails as any other agency
behaviour.

### 6.1 Values & Ethics

- Maintenance skills have explicit `side_effect_tags` and `safety_level`.  
- Values & Ethics policy rules can:
  - restrict which skills may run autonomously vs user-trigger-only,  
  - impose rate limits or time windows,  
  - require explicit consent for certain actions.

### 6.2 Scheduler, Lifecycle, and Resource Monitor

- Heavy maintenance tasks should only run in **SLEEP_LIKE** or
  **MAINTENANCE** states unless the user explicitly requests otherwise.  
- Scheduler and Resource Monitor enforce CPU/memory limits and prioritise
  user-facing tasks over background self-healing.

### 6.3 Transparency and Explainability

- Every maintenance goal and skill invocation should be:
  - logged as PerceptualEvents and goal history entries,  
  - explainable via `GetGoalDetailsWithHistory`,  
  - optionally surfaced in UI as part of "what AICO is working on".
- Self-healing actions that materially affect user data must have clear,
  human-readable summaries and provenance.


## 7. Metrics and Observability

Self-healing is evaluated via existing and new metrics (see
`agency-metrics.md`):

- `plan_execution_success_rate` for maintenance goals.  
- counts of maintenance goals created/active/completed/dropped.  
- time-to-repair for common issues (e.g. modelservice outages, disk pressure).  
- rate of user-triggered vs agency-triggered maintenance actions.  
- correlation between self-healing events and overall System Health status.

Self-Reflection (`agency-component-self-reflection.md`) can use these metrics to
propose lessons, e.g.:

- prefer lighter-weight repairs before heavy ones,  
- avoid repeating ineffective remediation steps,  
- adjust when to auto-run vs suggest to the user.


## 7.1 Configuration (backend)

Self-healing is controlled by `system.self_healing.*` configuration keys.

Key flags:

- `system.self_healing.enabled`
- `system.self_healing.run_immediately`
- `system.self_healing.allow_side_effects`
- `system.self_healing.max_steps_per_goal`

Deterministic simulated issue injection for end-to-end tests (explicitly
disabled by default):

- `system.self_healing.simulation.enabled`
- `system.self_healing.simulation.issue_id`
- `system.self_healing.simulation.persist_issue`


## 8. Implementation Notes & Checklist

This section provides a concrete checklist for implementing self-healing.

### 8.1 Backend services

- [ ] Identify existing troubleshooting actions used in the System Health tab
      (DB cleanup, connectivity tests, restarts, etc.).
- [ ] Extract them into **Skill & Tool Layer** primitives with:
      - ontology `Skill` definitions,  
      - Tool implementations,  
      - safety/resource metadata.
- [ ] Expose thin HTTP or message-bus endpoints that call these skills for the
      Health tab UI.

### 8.2 Agency integration

- [ ] For each major health condition, define a **maintenance goal type** with
      `origin = system_maintenance` and appropriate tags.  
- [ ] Ensure health signals emit PerceptualEvents that map cleanly into these
      goal types via `ProposeGoalFromPercept`.
- [ ] For deterministic E2E tests, support an explicitly-configured simulated
      issue injection that exercises the full loop: goal → intention → plan →
      execution → verify.
- [ ] Define **plan templates** that use the maintenance skills for each
      maintenance goal.
- [ ] Integrate with Scheduler and Lifecycle so heavy plans run in safe
      windows.
- [ ] Wire results back into metrics and System Health endpoints.

### 8.3 Frontend linkage

- [ ] Align Health tab check groups and detailed tests with the backend
      maintenance skills and PerceptualEvent types.  
- [ ] For each playbook button, call the backend endpoint that invokes the
      corresponding skill(s).  
- [ ] Display when Agency has already attempted a remediation and surface
      remaining manual options.

Once this document is implemented, AICO’s agency will be able to use the same
well-audited tools as the System Health UI to detect, repair, and explain
self-healing actions, while respecting all existing architecture and safety
constraints.
