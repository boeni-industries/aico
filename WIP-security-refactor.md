# WIP Security Refactor

## Purpose

This document is the **implementation spec** for refactoring AICO security toward a container-first runtime model.

Core rule:

- runtime services in containers must not depend on host OS keyrings as their default secret source

What this doc keeps:

- current-state facts that constrain implementation
- the target runtime/API/UI contracts
- rollout decisions
- the actual implementation backlog

What this doc intentionally omits:

- exhaustive narrative
- repeated justification
- duplicate workflow prose

## Goals

- one secret-resolution model for runtime and CLI
- truthful security posture reporting
- container-native steady-state operation
- low-risk rollout with explicit degraded states

## Non-goals

- crypto redesign
- auth redesign
- mandatory external secret manager

## Current-state facts that matter

### Secret resolution

- `CredentialProvider` currently resolves in this order:
  - environment variable `AICO_<KEY>`
  - `/run/secrets/<key>`
  - system keyring in interactive local mode

- some runtime consumers already use provider-first resolution:
  - JWT secret retrieval
  - Postgres runtime credential retrieval

### Current architectural mismatches

- master/root secret handling is still keyring-centric
- CLI/bootstrap and runtime do not yet share one authoritative source model
- `aico pg` and related CLI/database flows still assume keyring access in places
- secret names and aliases are not fully normalized
- posture reporting is coarser than the real asset model
- rotation/recovery support exists only partially

### Deploy/bootstrap reality

- `aico deploy system` is the authoritative bootstrap/replay entrypoint
- current reruns are **mostly idempotent**, not strict no-op idempotent
- `_ensure_all_secrets()` currently reuses existing files, may import legacy values, and otherwise generates missing secrets
- current deploy behavior is therefore still more dev-friendly than strict prod fail-fast

### Current API/UI reality

- backend posture still exposes coarse buckets:
  - `encryption`
  - `transport`
  - `authentication`
  - `audit`

- `GET /admin/security/keys` currently flattens multiple concerns into one key asset

- Studio still consumes the old coarse posture shape and flattened key response

### Current audit-event reality

- structured events that exist today:
  - `security.key_rotation`
  - `audit.admin`

- secret resolution, fallback, bootstrap replay, and degraded startup are mostly logs or missing as structured events

## Target decisions

### Source policy

- keep keyring support for explicit local interactive workflows only
- prefer container-native sources first
- every runtime secret must have machine-detectable source metadata
- posture must distinguish:
  - configured vs effective
  - persistent vs ephemeral
  - healthy vs degraded

### Deployment modes

- **Local interactive**
  - keyring allowed
  - file/env sources preferred when available

- **Container development**
  - mounted files or env preferred
  - keyring disabled
  - limited explicit degraded/ephemeral behavior allowed

- **Production container**
  - persistent steady-state secrets required
  - keyring disabled
  - missing required secrets fail loudly

### Scope model

- deployment-scoped operations and tenant-scoped operations must remain distinct
- rotating tenant credentials must not imply deployment secret rotation
- bootstrap-only inputs must not be modeled as steady-state runtime assets

## Canonical secret model

### Runtime secrets

- `pg_password`
- `api_gateway_jwt_secret`
- `grafana_admin_password`
- `minio_root_user`
- `minio_root_password`
- `artifact_store_access_key`
- `artifact_store_secret_key`
- `root_encryption_secret`

### Bootstrap-only inputs

- `master_password`
- `admin_pin`

### Canonical environment variables

- `AICO_PG_PASSWORD`
- `AICO_API_GATEWAY_JWT_SECRET`
- `AICO_GRAFANA_PASSWORD`
- `AICO_MINIO_ROOT_USER`
- `AICO_MINIO_ROOT_PASSWORD`
- `AICO_ARTIFACT_STORE_ACCESS_KEY`
- `AICO_ARTIFACT_STORE_SECRET_KEY`
- `AICO_ROOT_ENCRYPTION_SECRET`

### Canonical mounted secret paths

- `/run/secrets/pg_password`
- `/run/secrets/api_gateway_jwt_secret`
- `/run/secrets/grafana_admin_password`
- `/run/secrets/minio_root_user`
- `/run/secrets/minio_root_password`
- `/run/secrets/artifact_store_access_key`
- `/run/secrets/artifact_store_secret_key`
- `/run/secrets/root_encryption_secret`

## Target contracts

### Credential provider contract

Each resolved secret should expose:

- `value`
- `source`
- `persistent`
- `required`
- `degraded`
- `degraded_reason`

Allowed source taxonomy:

- `mounted_secret_file`
- `environment_variable`
- `local_keyring`
- `external_provider`
- `generated_ephemeral`

### Backend posture contract

Target posture shape:

```json
{
  "runtime_secrets": [],
  "root_crypto": [],
  "transport_security": [],
  "bootstrap_requirements": [],
  "authentication_sessions": {},
  "audit_pipeline": {}
}
```

Each reported asset should include:

- `asset_name`
- `asset_class`
- `scope`
- `source`
- `persistent`
- `status`
- `degraded_reason`
- `last_verified_at`

### Studio contract

Studio should render the same asset-oriented model as the backend posture contract.

Minimum UI requirements:

- overview derived from asset classes, not hardcoded coarse buckets
- runtime secret rows/cards show:
  - `asset_name`
  - `source`
  - `persistent`
  - `status`
  - `degraded_reason`
- root crypto rendered separately from JWT/session-signing posture
- bootstrap requirements rendered separately from steady-state runtime assets
- transport posture rendered separately from secret presence

### Audit-event contract

Target event topics:

- `security.secret.resolved`
- `security.secret.fallback_used`
- `security.secret.missing`
- `security.bootstrap.started`
- `security.bootstrap.completed`
- `security.bootstrap.replayed`
- `security.startup.degraded`
- `security.key_rotation`

Minimum metadata:

- `asset_name`
- `asset_class`
- `scope`
- `source`
- `persistent`
- `status`
- `degraded_reason`
- `actor` when human-triggered
- `correlation_id`

## Operator workflow rules

- `aico deploy system` remains the authoritative deployment bootstrap/replay entrypoint
- normal service restart must not require operator password entry
- production recovery must not rely on deleting secrets and letting them regenerate
- rotation and recovery must be explicit, auditable workflows

## Implementation backlog

### Phase 1: backend posture and truthfulness

- [ ] Replace coarse posture schemas in `gateway/api/admin/schemas.py`
- [ ] Refactor `GET /admin/security/posture` in `gateway/api/admin/router.py`
- [ ] Refactor `GET /admin/security/keys` so it no longer mixes root-key and JWT concerns

### Phase 2: secret resolution alignment

- [ ] Extend `shared/aico/security/credential_provider.py` to return structured metadata
- [ ] Normalize runtime consumers onto canonical secret names and sources
- [ ] Implement container-appropriate handling for `root_encryption_secret`
- [ ] Align `aico pg` and related CLI/database flows with runtime resolution

### Phase 3: deploy/bootstrap/recovery alignment

- [ ] Refactor `cli/commands/deploy.py` around canonical steady-state secret sources
- [ ] Preserve bootstrap replay via `aico deploy system`
- [ ] Add explicit production fail-fast behavior for missing required secrets
- [ ] Standardize Compose/runtime secret names and aliases

### Phase 4: audit events and degraded startup

- [ ] Add structured secret lifecycle and startup events
- [ ] Emit consistent security event metadata
- [ ] Preserve and extend current `security.key_rotation` and `audit.admin` behavior

### Phase 5: Studio migration

- [ ] Update `aico-studio/src/api/adminSecurity.ts`
- [ ] Refactor `SystemSecurityAuditTab.tsx`
- [ ] Refactor `SecurityManagementSection.tsx`
- [ ] Update any other Studio views coupled to the coarse posture shape

### Phase 6: rollout and verification

- [ ] Decide compatibility strategy for old vs new posture responses
- [ ] Verify dev vs prod behavior end-to-end
- [ ] Test bootstrap, restart, replay/recovery, and rotation workflows end-to-end
- [ ] Re-audit code against this document after implementation lands

## Open decisions

- whether backend supports old and new posture response shapes temporarily
- exact rollout path for root-key rotation
- exact tenant session minting/refresh lifecycle details

## Summary

Keep local keyring support, but stop treating it as the runtime default for containers. Standardize secret resolution, make posture asset-oriented and truthful, align CLI/bootstrap with runtime behavior, and implement explicit audit/rotation/recovery paths.
