---
title: Agency Component – Scheduler & Resource Governance
---

# Scheduler & Resource Governance

## Status

- **Implemented (v1)**: backend scheduler service exists in `backend/scheduler/core.py` (`TaskScheduler`, `TaskRegistry`, `TaskExecutor`) with task discovery and cron-based scheduling.
- **Implemented (v1)**: task base types exist in `backend/scheduler/tasks/base.py` (`BaseTask`, `TaskContext`, `TaskResult`, `TaskStatus`, `TaskQueue`, `TaskPriority`, retry configuration).
- **Implemented (v1)**: resource monitoring exists via `backend/scheduler/resource_monitor.py` (`ResourceMonitor`, `ResourceSnapshot`).
- **Implemented (v1)**: scheduler admin API exists under `/api/v1/scheduler/*` (see `backend/api/scheduler/router.py`).
- **WIP**: end-to-end `EvaluateTaskReadiness` that combines Values & Ethics, Safety/Control, and a persisted LifecycleState; current readiness gating is primarily implemented inside individual tasks (e.g., `should_run()` checks).

## 1. Purpose

The Scheduler & Resource Governance component ensures AICO’s autonomy is **bounded and respectful** of system and user constraints by deciding **when and how much** work to run, once Values & Ethics and Safety & Control have said *what is allowed*.

It:

- turns high-level goals/plans into scheduled, observable tasks,  
- respects Lifecycle state, user preferences, and resource limits,  
- and makes sure background work never overwhelms the device or user experience.

## 2. Conceptual Model

- **Tasks & queues**  
  - All work (plan steps with Skills, AMS/World Model jobs, maintenance) is represented as Tasks grouped into logical queues (e.g., `user_facing`, `background_light`, `background_heavy`, `maintenance`).

  **Implementation note (v1):** queue types are represented as `TaskQueue` enum values in `backend/scheduler/tasks/base.py`. Enforcement of per-queue budgets/fairness is partially implemented and still evolving (**WIP**).

- **Resource governance**  
  - Each Task has a `resource_profile` and `runtime_context` describing expected CPU/memory/battery and sensitivity (foreground vs background).  
  - A Resource Monitor enforces per-queue and global budgets.

  **Implementation note (v1):** `ResourceMonitor` provides system snapshots and helpers (e.g., idle detection, defer heuristics). Full “budget enforcement” across queues is **WIP**.

- **Constraint integration**  
  - Scheduler only runs Tasks that are:
    - **allowed** by Values & Ethics (EvaluationResult),  
    - consistent with Safety & Control (AgencyMode, PauseState, capabilities),  
    - permitted by Lifecycle (e.g., heavy jobs mainly in SLEEP_LIKE),  
    - within resource budgets and user/device constraints.

  **WIP**: unified constraint integration across Values & Ethics, PauseState/capabilities, and Lifecycle as a single readiness function.

## 3. Data Model (Conceptual)

- **Task**  
  - `task_id`, `type` (plan_step_skill, ams_job, wm_job, maintenance, etc.),  
  - `origin` (user_request / curiosity / maintenance / system),  
  - `queue` (user_facing / background_light / background_heavy / maintenance),  
  - `plan_id` / `step_id` / `goal_id` (if applicable),  
  - `skill_id` / `tool_id` (for plan_step_skill tasks),  
  - `resource_profile` (estimated CPU/mem/battery, duration, IO intensity),  
  - `runtime_context` (foreground/background, network_required, power_required),  
  - `priority` (numeric or small enum),  
  - `status` (queued / running / completed / failed / deferred),  
  - `evaluation_result` (cached EvaluationResult from Values & Ethics),  
  - timestamps (created_at, started_at, completed_at, last_deferred_at),  
  - `defer_reason` (if deferred: lifecycle, resource, policy, pause_state, etc.).

**Implementation note (v1):** the scheduler persists scheduled task definitions (cron + config) in the database and maintains execution state in-memory; `TaskResult` already includes `defer_reason` and retry hints.

- **QueueConfig**  
  - per queue: `max_concurrent`, `max_cpu_share`, `max_battery_share`, `allowed_lifecycle_states`, etc.

Tasks and queue configs are stored in the shared PostgreSQL-backed task system, not in this doc’s component alone.

**WIP**: an explicit persisted `QueueConfig` model; current configuration is primarily code/config driven.

## 4. Operations & Behaviour

- **EnqueueTask(task_spec)**  
  - Called by Planner/Skills (for plan steps), AMS/World Model (for consolidation jobs), maintenance subsystems.  
  - Attaches `queue`, `resource_profile`, `runtime_context`, and caches an EvaluationResult (if available or easy to obtain).

- **EvaluateTaskReadiness(task)**  
  - Checks, for a given task:
    - `evaluation_result` from Values & Ethics (or calls evaluator if missing/stale),  
    - Safety & Control state (PauseState, CapabilityConfig),  
    - LifecycleState and `QueueConfig.allowed_lifecycle_states`,  
    - current resource usage vs queue/global budgets.  
  - Returns a decision: runnable now / defer with reason / discard.

  **Implementation note (v1):** readiness checks are partially implemented in:
  - task-specific gating (e.g., `should_run()` methods),
  - resource heuristics (see `ResourceMonitor`).
  A single canonical `EvaluateTaskReadiness` used by the scheduler dispatch loop is **WIP**.

- **DispatchLoop()**  
  - Periodically and on triggers (new tasks, state changes), select tasks per queue using:
    - priority and fairness strategies,  
    - EvaluateTaskReadiness results.  
  - Start runnable tasks, update status and timestamps.

- **HandleTaskCompletion(task, result)**  
  - Update status, record metrics, and notify upstream components (e.g., Planner, AMS).  
  - Optionally emit events for Self-Reflection or Curiosity (e.g., repeated failures).

## 5. Integration with Other Components

- **Planner, Skills & Tools**  
  - Planner / Skills create Tasks for plan steps bound to Skills/Tools (via InvokeSkill runners).  
  - Scheduler ensures these execute subject to policies, lifecycle, and resources.

- **Values & Ethics / Safety & Control**  
  - Scheduler never overrides allow/deny decisions; it:  
    - consults or caches EvaluationResult for tasks,  
    - respects PauseState and CapabilityConfig,  
    - contributes AuditEntries (e.g., for deferred or blocked executions).

- **Lifecycle**  
  - Uses LifecycleState (ACTIVE, FOCUSED_WORK, IDLE_LIGHT, SLEEP_LIKE, MAINTENANCE) and its flags to:
    - permit or deny execution in specific queues,  
    - bias priorities (e.g., favour wrap-up tasks before SLEEP_LIKE).  
  - Heavy queues (background_heavy, maintenance) are favoured in SLEEP_LIKE/MAINTENANCE.

- **Resource Monitor**  
  - Provides current CPU/mem/battery/network state and per-queue usage.  
  - Scheduler uses this to throttle, defer, or cancel tasks to keep within budgets.

- **Memory/AMS & World Model**  
  - Many AMS / WM jobs are scheduled as background tasks; Scheduler determines when they run given Lifecycle and resources.

## 6. Persistence & Metrics

- **Persistence**  
  - Tasks and their schedules/config are persisted in a task database (PostgreSQL) shared with other backend services.  
  - LifecycleState, AgencyMode, and PolicyRules live in their respective components but are read by Scheduler at decision time.

  **WIP**: persisted queue configuration + persisted task execution state beyond execution history tables.

- **Metrics**  
  - Metrics such as `scheduled_agency_tasks`, `agency_resource_usage`, and `tasks_run_vs_deferred_by_lifecycle` (see `agency-metrics.md`) are fed by Scheduler’s task and decision logs.  
  - Additional scheduler-specific metrics (queue lengths, average wait time, failure/defer reasons) are recommended for operational dashboards.

This design keeps Scheduler focused on **when and how** to run tasks under resource and lifecycle constraints, while relying on Values & Ethics and Safety & Control to determine **what** is permitted and how it is exposed to users.

## 7. Implementation Notes & Existing Scheduler Integration

- This component is implemented by **extending the existing `backend.scheduler` service** (`TaskScheduler`, `TaskExecutor`, and the scheduler repositories/service layer):  
  - The conceptual scheduled task maps to rows in the `scheduler_tasks` table, accessed via `SchedulerService` (`shared/aico/services/scheduler_service.py`) and repositories (`shared/aico/data/repositories/postgres/scheduler_tasks_repository.py`) using the UnitOfWork pattern.  
  - Agency-specific fields are stored in the task `config` payload (origin, queue, plan/step/goal IDs, skill/tool IDs, `resource_profile`, `runtime_context`, cached `evaluation_result`).  
  - The conceptual `DispatchLoop()` corresponds to `TaskScheduler._scheduler_loop()` / `_check_and_execute_tasks()`, extended with an `EvaluateTaskReadiness` check that consults Lifecycle, Values & Ethics, Safety & Control, and the Resource Monitor before calling `TaskExecutor.execute_task(...)`.
- There is **only one scheduler service and task database** in the system; agency does not introduce a second scheduler. It adds:
  - richer task metadata,  
  - readiness gating that combines policy, lifecycle, and resources,  
  - and metrics/logging that make agency-related scheduling decisions visible.

### 7.1 Required Scheduler Task Schema / Config Fields

The existing scheduler uses the `scheduler_tasks` table (see `shared/aico/data/postgres/schema.sql` and SQLAlchemy mappings in `shared/aico/data/tables.py`). Conceptually, it contains:

```sql
scheduler_tasks(
  task_id    TEXT PRIMARY KEY,
  task_class TEXT      NOT NULL,
  schedule   TEXT      NOT NULL,
  config     TEXT,               -- JSON payload (stored as text)
  enabled    BOOLEAN   DEFAULT TRUE,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
```

Agency integration requires that `config` (TEXT containing JSON) be able to hold at least the following fields for tasks created/managed by agency components:

```json
{
  "origin": "user_request | curiosity | maintenance | system",
  "queue": "user_facing | background_light | background_heavy | maintenance",

  "plan_id": "...",        // optional, link to Plan
  "step_id": "...",        // optional, link to PlanStep
  "goal_id": "...",        // optional, link to Goal

  "skill_id": "...",       // for plan_step_skill tasks
  "tool_id": "...",        // concrete tool/integration if applicable

  "resource_profile": {
    "cpu": "low|medium|high",          // or numeric estimate
    "mem": "low|medium|high",
    "battery": "low|medium|high",
    "duration_hint": "short|medium|long",
    "io_intensity": "low|medium|high"
  },

  "runtime_context": {
    "foreground": true,
    "network_required": true,
    "power_required": false
  },

  "priority": 0,   // small integer or enum mapping

  "evaluation_result": {
    "decision": "allow | needs_consent | block",
    "reason": "...",
    "policy_ids": ["..."]
  },

  "defer_reason": "lifecycle | resource | policy | pause_state | ..."  // when last deferred
}
```

No new table is introduced for agency; all fields above are stored in the existing `scheduler_tasks.config` JSON payload. Scheduler code parses/emits this JSON structure when working with agency-related tasks.
