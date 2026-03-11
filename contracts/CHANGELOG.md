# API Contract Changelog

This file tracks all changes to the frozen API contracts in `/contracts/`.

## Policy

### Allowed Changes (Non-Breaking)
- **Additive changes only**: new endpoints, new optional fields, new enum values
- **Bugfixes**: metadata corrections that don't change contract shape
- **Documentation**: improved descriptions, examples

### Breaking Changes (Require Version Bump)
- Removing or renaming endpoints/fields
- Changing field types or required/optional semantics
- Tightening validation that rejects previously valid payloads
- **Action required**: Create `/api/v2` (REST) or version proto package/service

### Update Workflow
1. Make your code changes
2. Regenerate contracts:
   - REST: `uv run python scripts/generate_openapi_public.py`
   - Proto: `cp -f proto/*.proto contracts/proto/`
3. Add entry to this CHANGELOG with rationale
4. Commit all changes together
5. CI will verify:
   - OpenAPI artifact matches generated spec
   - Proto changes are backward-compatible (buf breaking)
   - CHANGELOG was updated

---

## [Unreleased]

### 2026-03-11 - Contract Gate Split-Repo Alignment
- **CI Gates**: Updated contract workflows and helper scripts to run from the split-era `gateway/` package instead of the removed `backend/` directory.
- **WebSocket v1**: Refreshed frozen adapter metadata in `contracts/websocket/v1.json` to match the current gateway adapter path.
- **Compatibility**: Non-breaking contract/tooling alignment only; no request/response shape changes.

### 2026-03-05 - Scheduler Run Ledger Endpoints
- **Added (Scheduler)**: Run-ledger endpoints for deterministic planned-run accounting:
  - `GET /api/v1/scheduler/runs`
  - `GET /api/v1/scheduler/runs/{run_id}`
  - `GET /api/v1/scheduler/runs/stats`

### 2026-03-04 - Scheduler Executions Pagination + Ops Health Endpoints
- **Added (Scheduler)**: Cursor-paginated executions listing endpoint `GET /api/v1/scheduler/executions` (replaces bulk range payloads).
- **Added (Scheduler)**: Execution details endpoint `GET /api/v1/scheduler/executions/{execution_id}` for per-execution drilldown.
- **Added (Scheduler)**: Aggregated stats endpoint `GET /api/v1/scheduler/executions/stats` for time-bucketed dashboards.
- **Added (Health)**: Gateway readiness/liveness endpoints `GET /api/v1/health/ready` and `GET /api/v1/health/live`.
- **Removed**: Deprecated legacy/no-op endpoints (legacy conversation start and user pin/refresh stubs).

### 2026-02-24 - Add NATS Contract Snapshot
- **NATS v1**: Frozen internal NATS contract at `contracts/nats/v1.json` (subject mapping policy + request/reply patterns).
- **CI Gates**: Added NATS contract gate to verify the artifact matches the generated contract.

### 2026-02-24 - Add WebSocket Contract Snapshot
- **WebSocket v1**: Frozen WebSocket contract at `contracts/websocket/v1.json` (FastAPI WS endpoints + gateway websocket adapter message shapes).
- **CI Gates**: Added WebSocket contract gate to verify the artifact matches the generated contract.

### 2026-02-24 - Add Internal OpenAPI Snapshot
- **OpenAPI internal v1**: Frozen internal `/api/v1` REST contract at `contracts/openapi/internal-v1.json` (includes admin/system/operations/users-sessions).
- **CI Gates**: OpenAPI contract gate now verifies both public and internal OpenAPI artifacts.

### 2026-02-24 - Initial Contract Freeze
- **OpenAPI v1**: Frozen `/api/v1` REST contract at `contracts/openapi/v1.json`
- **Protobuf**: Frozen proto baseline at `contracts/proto/*.proto`
- **CI Gates**: Added strict breaking change detection for both REST and Protobuf
- **Policy**: Established Option 2 (strict but practical) - additive changes allowed via explicit contract update PR, breaking changes require version bump
