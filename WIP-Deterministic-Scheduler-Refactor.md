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
- [ ] Define run ledger schema + indexes + unique constraints (idempotency)
- [ ] Add repository/service primitives for runs (create/list/get/update transitions)
- [ ] Implement planner/reconciler (lookahead + backfill + missed detection)
- [ ] Add outbox (or equivalent) for run dispatch + publisher
- [ ] Update scheduler enqueue paths to always record run outcomes (suppressed/disabled/unknown task/etc.)
- [ ] Add API endpoints for run ledger (list/day view, detail, stats)
- [ ] Update Studio schedule view to optionally use planned runs (not only executions)
- [ ] Add minimal admin/CLI commands (inspect run, re-enqueue run, mark acknowledged)
- [ ] Add tests: idempotency, missed runs, concurrency claim, reconciliation correctness
