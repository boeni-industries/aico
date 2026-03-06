# WIP: Deterministic Scheduler Refactor

## Goal
Make scheduling **fully deterministic** and **fully observable** by persisting *planned runs* (not just executions).

## Non-goals (for Phase 1)
- Replacing the task execution runtime.
- Introducing Temporal or another external workflow engine.
- Solving all multi-step workflows (this is a scheduler/run-ledger foundation).

## Problem (current)
- We can’t always explain “why a job did not run” because we only persist executions, not the complete set of *expected/planned* runs.
- Many suppression/early-return paths never produce a durable record.

## Target design (Phase 1)
### 1) Durable run ledger (source of truth)
Add a new table `scheduler_run_ledger` representing one *planned occurrence* of a task.

Each run must have:
- Identity: `run_id` + stable `run_key` (derived from `task_id`, `tenant_id` (if any), `scheduled_for`).
- Timestamps: `scheduled_for`, `planned_at`, plus lifecycle timestamps.
- State machine: `planned -> enqueued -> running -> (completed | failed | skipped | suppressed | canceled)`.
- Explicit explanation fields for all non-success outcomes: `reason_code`, `reason_detail`.

### 2) Reconciler / planner loop
A deterministic planner ensures the ledger contains all runs for:
- `now - backfill_window` to `now + lookahead_window`

It must:
- Create missing planned runs idempotently.
- Mark overdue runs as `missed` (after a grace period) with a reason.

### 3) Atomic dispatch (recommended: outbox)
When a run transitions to `enqueued`, dispatch must be reliable and traceable.

Recommended pattern:
- DB transaction updates run state + inserts outbox message.
- Separate publisher sends outbox to JetStream/NATS (idempotent publish).

### 4) Executor claim is idempotent
Workers claim by `run_id` (or `run_key`) with atomic state transition:
- only one worker can move `enqueued -> running`.

## Invariants
- Every task occurrence that “should have happened” is represented by exactly one ledger record.
- Every terminal state is explainable (has a reason when not `completed`).
- Reconciliation can always rebuild current truth from DB state (no hidden in-memory-only facts).

## Observability surfaces
- API + Studio can show per-day planned vs executed vs missed.
- “Why didn’t it run?” becomes a DB query, not guesswork.
- State streaming can emit run lifecycle events (planned/enqueued/running/terminal).

## Progress checklist
- [x] Define run ledger schema + indexes + unique constraints (idempotency)
  - ✅ `scheduler_run_ledger` table with `id`, `task_id`, `run_key`, `tenant_id`, `scheduled_for`, `planned_at`, `state`, lifecycle timestamps
  - ✅ Unique constraints: `uq_scheduler_run_ledger_idempotency_single_tenant` (task_id, scheduled_for)
  - ✅ Unique constraints: `uq_scheduler_run_ledger_idempotency_multi_tenant` (task_id, tenant_id, scheduled_for)
  - ✅ Indexes: task_id, scheduled_for, state, (state, scheduled_for)
- [x] Add repository/service primitives for runs (create/list/get/update transitions)
  - ✅ `PostgresSchedulerRunLedgerRepository` with full CRUD operations
  - ✅ `create()`, `create_if_absent()`, `get_by_id()`, `update()`, `delete()`, `list()`, `count()`
  - ✅ `mark_enqueued()`, `mark_missed_before()`, `mark_suppressed()`, `stats_in_range()`, `cleanup_old_runs()`
  - ✅ `SchedulerService` wraps repository with business logic
- [x] Implement planner/reconciler (lookahead + backfill + missed detection)
  - ✅ `_reconcile_planned_runs()` in `TaskScheduler.core.py` (lines 1067-1139)
  - ✅ Configurable `lookahead_seconds` (default: 6 hours), `backfill_seconds` (default: 2 hours)
  - ✅ Configurable `missed_grace_seconds` (default: 10 minutes)
  - ✅ Creates missing planned runs idempotently via `create_if_absent()`
  - ✅ Marks overdue runs as `missed` with `mark_missed_before()`
- [x] Add outbox (or equivalent) for run dispatch + publisher
  - ✅ `outbox_events` table with `event_id`, `tenant_id`, `subject`, `payload_bytes`, `status`, `attempts`
  - ✅ Atomic dispatch: DB transaction updates run state + inserts outbox event (lines 1275-1315)
  - ✅ Inline publish attempt + fallback to outbox publisher on failure
  - ✅ `OutboxEvent` model and repository with `enqueue()`, `mark_sent()` operations
- [x] Update scheduler enqueue paths to always record run outcomes (suppressed/disabled/unknown task/etc.)
  - ✅ `_mark_suppressed()` helper records suppression reasons (OUTBOX_PERSIST_FAILED, etc.)
  - ✅ `mark_enqueued()` called on successful dispatch (line 1299-1310)
  - ✅ Run ledger tracks all outcomes: planned → enqueued → running → (completed | failed | skipped | suppressed | missed)
- [x] Add API endpoints for run ledger (list/day view, detail, stats)
  - ✅ `GET /api/v1/scheduler/runs` - List planned runs with filters (time range, task_id, state, tenant_id)
  - ✅ `GET /api/v1/scheduler/runs/stats` - Run stats aggregated by time buckets (hour/day/week)
  - ✅ `GET /api/v1/scheduler/runs/{run_id}` - Get single run details by numeric ID
  - ✅ `POST /api/v1/scheduler/tasks/{task_id}/trigger` - Manually trigger task (JWT authenticated)
- [ ] Update Studio schedule view to optionally use planned runs (not only executions)
- [x] Add minimal admin/CLI commands (inspect run, re-enqueue run, mark acknowledged)
  - ✅ `aico scheduler trigger <task_id>` - Manually trigger task (JWT authenticated)
  - ✅ `aico scheduler history <task_id>` - View execution history
  - ✅ `aico scheduler show <task_id>` - Show task details
  - ✅ `aico scheduler ls` - List all scheduled tasks
  - ✅ `aico scheduler status` - Show scheduler status
  - ✅ `aico scheduler cleanup` - Clean up old execution history
- [ ] Add tests: idempotency, missed runs, concurrency claim, reconciliation correctness
