# WIP Security Refactor

## Purpose

This document defines the least-disruptive path to make AICO's security model fit a Docker/container-first runtime while preserving AICO's core principles:

- Zero-effort security
- Privacy-first design
- Defense in depth
- Zero trust
- Least privilege
- Local-first processing where possible
- Transparent, operationally useful security posture

The key shift is simple: **runtime security for containers must stop depending on host OS keyrings** and move to explicit, container-native secret sources with truthful posture reporting.

## Worklist

- [x] Audit all current secret-loading paths across `gateway`, `core`, `shared`, and `cli`
- [x] Define the runtime credential provider contract and source taxonomy
- [ ] Standardize Docker/Compose secret file names and mount paths
- [ ] Decide which secrets may be ephemeral in dev and which must fail loudly in production
- [ ] Separate asset classes in backend posture APIs
- [ ] Update Studio security UI to show source, persistence, and degraded reason consistently
- [x] Add bootstrap flow for first-time container deployments
- [ ] Add guided rotation and recovery workflows
- [ ] Add audit events for secret resolution, fallback, bootstrap, rotation, and degraded startup
- [x] Document deployment modes and recommended operator defaults

## Problem

Some of AICO's current documentation and runtime behavior still assume platform-native secure storage like macOS Keychain, Windows Credential Manager, or Linux Secret Service. That works for local CLI and some coupled desktop scenarios, but not for long-running Dockerized services.

This creates five problems:

- Runtime services inside containers cannot reliably access host keyrings
- Posture reporting becomes misleading because secret state depends on environment quirks
- Secret types use inconsistent source models
- Security metrics blur configuration, credential presence, transport state, and audit health
- Operations are more manual than they should be

## Current-state findings

### What exists today

- **Local bootstrap is CLI- and keyring-centric**
  - `aico config init` prepares config directories and templates
  - `aico security setup` creates the master password flow
  - `AICOKeyManager.setup_master_password()` derives the master key and stores it in the system keyring
  - `AICOKeyManager.has_stored_key()` is keyring-backed, and the durable master-key path remains centered on the system keyring

- **Runtime secret handling is already partially container-aware**
  - `AICOKeyManager.get_jwt_secret()` already prefers `CredentialProvider` before keyring
  - `shared/aico/data/postgres/connection.py` prefers `CredentialProvider().get("pg_password")` before keyring fallback
  - `docker/docker-compose.local.yml` already mounts secrets such as `pg_password` and `api_gateway_jwt_secret` into `/run/secrets`

- **Deploy/bootstrap is split-brain**
  - `cli/commands/deploy.py` supports headless bootstrap using `--master-password-file` or `AICO_MASTER_PASSWORD`
  - but `_authenticate_for_deploy()` still routes through `AICOKeyManager.authenticate()`, and durable master-key persistence remains keyring-based
  - deploy helpers also backfill credentials into keyring for CLI convenience, for example `_ensure_postgres_password_in_keyring()`

- **Database schema/bootstrap paths are still keyring-oriented**
  - `aico pg init` reads the Postgres password from keyring via `AICOKeyManager.get_database_password()`
  - local admin/bootstrap flows in deploy and pg tooling still assume keyring availability for repeated CLI operations

### The real end-to-end flow today

For local setup, the current authoritative path is:

1. `aico config init`
2. `aico security setup`
3. `AICOKeyManager.setup_master_password(password)`
4. master key stored in system keyring
5. JWT secret initialized
6. file-encryption derivation validated
7. transport-key derivation validation attempted by `security setup`, but the current key-derivation method raises a runtime error in the NATS-only architecture
8. `aico pg init` reads the Postgres password from keyring and applies schema

For headless deploy/bootstrap, the current path is different:

1. deploy command reads password from `--master-password-file` or `AICO_MASTER_PASSWORD`
2. `_authenticate_for_deploy()` calls `AICOKeyManager.authenticate()`
3. if the deploy path needs durable master-key setup, persistence still goes through the keyring-oriented master-key flow
4. deploy/bootstrap then ensures JWT secret exists
5. deploy helpers may generate or fetch database credentials
6. deploy helpers often sync those credentials back into keyring for CLI compatibility
7. runtime services then consume some credentials from `/run/secrets` or env, while CLI tooling still often expects keyring copies

### What is already working well

- Docker Compose already uses `/run/secrets` for important runtime secrets such as:
  - `pg_password`
  - `api_gateway_jwt_secret`
  - MinIO secrets
- `CredentialProvider` already implements a container-aware fallback chain:
  - env
  - `/run/secrets`
  - keyring in interactive local mode
- several runtime consumers already use `CredentialProvider` first:
  - gateway JWT setup through `get_jwt_secret()`
  - PostgreSQL connection pool/session factory

### Current architectural mismatches

- **The master key is still special**
  - JWT and database credentials already have container-aware resolution paths
  - the master key does not yet have an equivalent first-class runtime provider path
  - the current durable master-key model remains keyring-centric

- **CLI and runtime do not share one source of truth**
  - runtime services increasingly read from env/secrets
  - CLI bootstrap and maintenance flows still often write to and read from keyring
  - deploy commands bridge this by syncing credentials into keyring, which is a workaround rather than a clean model

- **`CredentialProvider` and docs are slightly inconsistent**
  - `CredentialProvider` resolves `AICO_<UPPERCASED_KEY_NAME>` and `/run/secrets/<key_name>`
  - the broader codebase and docs still mix provider-native names like `AICO_PG_PASSWORD` with additional aliases such as `AICO_POSTGRES_HOST` and raw secret-file names
  - this naming inconsistency increases operator confusion

- **Full deployment secret inventory is larger than the current mounted runtime set**
  - the current deployment/runtime surface requires secrets such as `pg_password`, `api_gateway_jwt_secret`, `minio_root_user`, `minio_root_password`, `artifact_store_access_key`, and `artifact_store_secret_key`
  - `docker-compose.local.yml` currently mounts only a subset of those into services
  - Grafana admin credentials are currently env-driven in Compose, not Docker-secret driven
  - master-password input and admin bootstrap passcode are deployment/bootstrap inputs, not currently modeled as canonical mounted runtime secrets

- **Database bootstrap is not fully container-native yet**
  - runtime Postgres connections can use secret files directly
  - but `aico pg init`, `aico pg status`, and related CLI commands still pull the password from keyring
  - this means local admin/bootstrap tooling is not yet aligned with container-native runtime resolution

- **Some posture/reporting paths still encode keyring assumptions**
  - `aico pg status` and `aico pg doctor` report credential availability based on keyring retrieval
  - those commands do not yet reflect the same source-aware runtime resolution model used by the shared Postgres connection layer

- **Transport setup messaging is ahead of implementation**
  - `security setup` still attempts transport-key validation and reports transport-encryption readiness
  - but transport-key derivation is not a cleanly settled runtime path in the current NATS-oriented architecture
  - posture and setup messaging should be aligned more closely with the actual transport implementation

### Refactor implications from the investigation

The implementation already contains the beginning of the right architecture:

- runtime credential resolution is moving toward env/secrets first
- Docker secrets are already wired into local container deployment
- non-interactive deploy helpers already exist

The missing step is to make this model authoritative end to end:

- define one runtime source of truth for all production-critical secrets
- stop requiring keyring-backed persistence for container runtime bootstrap
- make CLI commands able to operate against the same secret sources as runtime services
- reserve keyring for explicit local-only workflows
- normalize secret names, source reporting, and degraded/fallback behavior

### Recommended implementation order based on current code

1. Standardize secret names and source taxonomy across CLI, deploy, runtime, and docs
2. Extend the credential provider model to cover the root/master secret, not just JWT/database credentials
3. Refactor `aico pg` and related bootstrap tooling to use the same secret resolution chain as runtime services
4. Remove keyring as the implicit persistence layer for container bootstrap
5. Add explicit deployment-mode handling:
   - local interactive
   - container development
   - production container
6. Align security posture APIs and setup messaging with the actual runtime implementation

## Goals

- zero-effort setup and restart where safe
- one secret-resolution model for runtime and CLI
- truthful posture reporting
- low-risk migration

## Non-goals

- crypto redesign
- auth redesign
- mandatory external secret manager

## Target state

This section is **proposed design**, not current behavior.

### Runtime credential provider contract

Every runtime secret should have:

- one canonical secret name
- one canonical Docker secret file name
- one canonical environment variable
- one source classification
- one persistence policy
- one production policy when missing

Minimum provider contract:

- `value`
- `source`
- `is_persistent`
- `is_required`
- `is_degraded`
- `degraded_reason`

### Decisions

- separate local keyring workflows from container runtime workflows
- require every runtime secret to have a machine-detectable source
- prefer container-native sources first
- keep keyring only for explicit local mode
- separate posture from credential presence

### Secret classes

- runtime auth secrets
- data-at-rest root secrets
- transport identity material
- bootstrap and recovery material

The root encryption secret must not be treated like a JWT secret.

### Canonical runtime secret names

Use these canonical names for a full deployment:

- `pg_password`
- `api_gateway_jwt_secret`
- `grafana_admin_password`
- `minio_root_user`
- `minio_root_password`
- `artifact_store_access_key`
- `artifact_store_secret_key`
- `root_encryption_secret`

Canonical environment variables:

- `AICO_PG_PASSWORD`
- `AICO_API_GATEWAY_JWT_SECRET`
- `AICO_GRAFANA_PASSWORD`
- `AICO_MINIO_ROOT_USER`
- `AICO_MINIO_ROOT_PASSWORD`
- `AICO_ARTIFACT_STORE_ACCESS_KEY`
- `AICO_ARTIFACT_STORE_SECRET_KEY`
- `AICO_ROOT_ENCRYPTION_SECRET`

Canonical secret files:

- `/run/secrets/pg_password`
- `/run/secrets/api_gateway_jwt_secret`
- `/run/secrets/grafana_admin_password`
- `/run/secrets/minio_root_user`
- `/run/secrets/minio_root_password`
- `/run/secrets/artifact_store_access_key`
- `/run/secrets/artifact_store_secret_key`
- `/run/secrets/root_encryption_secret`

Older aliases may be supported temporarily, but posture should report the canonical name.

### Secret and input matrix

| Name | Class | Scope | Canonical source | Persistent in prod | Dev policy | Missing in prod | Rotation owner |
|---|---|---|---|---|---|---|---|
| `pg_password` | runtime auth secret | deployment | `/run/secrets/pg_password` | yes | may be generated for local/container dev | fail fast | deployment operator |
| `api_gateway_jwt_secret` | runtime auth secret | deployment | `/run/secrets/api_gateway_jwt_secret` | yes | may be generated for dev with degraded posture | fail fast | deployment operator |
| `grafana_admin_password` | runtime auth secret | deployment | `/run/secrets/grafana_admin_password` | yes | may be env/file-backed in dev until normalized | fail fast | deployment operator |
| `minio_root_user` | runtime auth secret | deployment | `/run/secrets/minio_root_user` | yes | may be generated for dev | fail fast | deployment operator |
| `minio_root_password` | runtime auth secret | deployment | `/run/secrets/minio_root_password` | yes | may be generated for dev | fail fast | deployment operator |
| `artifact_store_access_key` | runtime auth secret | deployment | `/run/secrets/artifact_store_access_key` | yes | may be generated for dev | fail fast | deployment operator |
| `artifact_store_secret_key` | runtime auth secret | deployment | `/run/secrets/artifact_store_secret_key` | yes | may be generated for dev | fail fast | deployment operator |
| `root_encryption_secret` | data-at-rest root secret | deployment | `/run/secrets/root_encryption_secret` | yes | dev generation allowed only for explicit local paths | fail fast | deployment operator |
| `master_password` | bootstrap/recovery input | deployment | `--master-password-file` or `AICO_MASTER_PASSWORD` | no, input only | allowed for headless dev/bootstrap | fail bootstrap | deployment operator |
| `admin_pin` | tenant identity bootstrap input | tenant | CLI/config input at bootstrap time | no, only stored as derived hash | required for first tenant bootstrap | fail bootstrap | tenant/deployment operator |
| tenant-scoped JWT | tenant session material | tenant | minted by gateway/session flow | yes, via auth/session store | normal runtime behavior | deny tenant access | auth/session subsystem |
| tenant-scoped refresh token | tenant session material | tenant | minted by gateway/session flow | yes, via auth/session store | normal runtime behavior | deny session renewal | auth/session subsystem |

Interpretation rules:

- deployment-scoped runtime secrets are shared by services inside one deployment and must not be duplicated per tenant by default
- tenant-scoped session material is isolated by `tenant_id` and should be partitioned in storage, cache, transport, and refresh logic
- bootstrap-only inputs are consumed during setup or recovery and are not the same thing as steady-state runtime secrets

### Deployment secret inventory

For clarity, split secrets into three groups:

- **Mounted runtime secrets already used in local Compose**
  - `pg_password`
  - `api_gateway_jwt_secret`
  - `minio_root_user`
  - `minio_root_password`
  - `artifact_store_access_key`
  - `artifact_store_secret_key`

- **Deployment/runtime credentials not yet normalized to Docker secrets**
  - `grafana_admin_password`

- **Bootstrap-only inputs**
  - `master_password` via `AICO_MASTER_PASSWORD` or `--master-password-file`
  - `admin_pin` / admin passcode for initial admin credential bootstrap

Target rule:

- runtime secrets should converge on canonical `/run/secrets/<name>` mounts
- bootstrap-only inputs should stay separate from steady-state runtime secrets

### Source taxonomy

Use only these source values:

- `docker_secret`
- `mounted_secret_file`
- `environment_variable`
- `external_provider`
- `local_keyring`
- `generated_ephemeral`

### Resolution model

For containerized services, the target resolution order is:

1. explicit mounted secret file
2. standard `/run/secrets/<name>`
3. external provider abstraction
4. environment variable
5. local keyring in explicit local mode
6. ephemeral generation only in dev/test

### Bootstrap and operations

Target operator experience:

- first startup detects whether required secrets exist
- dev may generate ephemeral secrets
- production requires one clear bootstrap action
- after bootstrap, restarts are unattended

### Tenancy-aware credential lifecycle

The credential model must treat **deployment** and **tenant** as different scopes.

- **Deployment-scoped credentials**
  - shared infrastructure/runtime secrets for one AICO deployment
  - examples: `pg_password`, `api_gateway_jwt_secret`, artifact-store credentials, `root_encryption_secret`
  - owned by the deployment operator
  - must not vary per tenant

- **Tenant-scoped identity/session material**
  - credentials or tokens that represent access within one tenant
  - examples: tenant-scoped JWTs, refresh tokens, admin bootstrap passcode hashes, future tenant session artifacts
  - must be isolated by `tenant_id`
  - must not be shared across tenants in storage, caches, or transport sessions

- **Bootstrap-only operator inputs**
  - one-time or occasional secrets used to initialize or recover a deployment
  - examples: `master_password`, recovery inputs, break-glass inputs
  - should not become steady-state runtime secrets unless explicitly persisted as deployment-scoped material

### Exact flow: initial setup

Target initial setup flow:

Authoritative bootstrap entrypoint:

- initial setup should be handled by `cli/commands/deploy.py` through the system-scope command:
  - `aico deploy system`
- this should be treated as the essential bootstrap command for zero-to-operational setup
- lower-level commands may still exist for advanced or repair workflows, but they should not be the primary first-run operator path

Target initial setup flow:

1. operator runs `aico config init`
2. operator runs `aico deploy system`
3. system selects or validates deployment mode:
   - local interactive
   - container development
   - production container
4. system resolves or creates **deployment-scoped** secrets
5. system bootstraps Postgres and shared infrastructure
6. system initializes deployment-level security state
7. system creates or verifies the initial tenant
8. system creates or verifies the initial tenant admin identity
9. system mints or enables tenant-scoped session issuance
10. system writes deploy/bootstrap state for safe re-runs

Rules:

- tenant creation must happen **after** deployment-scoped secrets exist
- tenant bootstrap must not create a separate per-tenant Postgres/JWT secret set by default
- tenant scope should be enforced through identity/session claims, not by duplicating deployment runtime secrets
- the initial admin passcode is tenant-scoped identity bootstrap data, not a runtime infrastructure secret
- `aico deploy system` should own orchestration of deployment bootstrap plus initial tenant/bootstrap identity setup
- current `deploy.py` already implements this **partially and mostly idempotently**:
  - `deploy_system()` calls component deploy commands with `nuke=False`
  - `_ensure_all_secrets()` reuses existing secret files and only generates missing ones
  - `_bootstrap_postgres()` is written as an idempotent ensure-flow for tenant, admin credential row, membership, and admin policy
  - deploy state is persisted and re-read from `runtime/deploy-state.yaml`
  - caveat: the current flow still contains keyring backfill/workaround behavior for CLI compatibility and some infrastructure coverage is broader than the intended OTEL/Prometheus-only target state

### Exact flow: steady-state runtime

At runtime:

1. services load deployment-scoped secrets from canonical sources
2. services start and operate without prompts
3. authenticated users obtain tenant-scoped sessions
4. JWT/session claims determine tenant scope
5. gateway/backend/message-bus layers enforce tenant isolation from those claims

Rules:

- Studio must not select tenant by raw headers alone
- tenant switching must mint/select tenant-scoped session state explicitly
- any client-side cached credentials or secure-session artifacts must be partitioned by `deployment + tenant`
- transport and message-bus scoping should carry `tenant_id` explicitly

### Exact flow: maintenance over time

Ongoing maintenance should separate **deployment operations** from **tenant operations**.

- **Deployment operations**
  - rotate deployment-scoped runtime secrets
  - rotate root encryption material
  - replace secret source backend
  - recover bootstrap state
  - verify posture and audit state

- **Tenant operations**
  - create/deactivate tenants
  - add/remove tenant memberships
  - mint tenant-scoped sessions
  - rotate tenant admin credentials
  - audit tenant-scoped admin actions

Rules:

- rotating a tenant admin credential must not require rotating deployment runtime secrets
- rotating a deployment runtime secret must not silently invalidate tenant boundaries
- operator workflows must make the scope explicit: `deployment` vs `tenant`

### Operator defaults

Recommended defaults:

- **Local interactive**
  - keyring allowed
  - file/secret sources preferred when present
  - ephemeral secrets allowed only for clearly marked dev paths

- **Container development**
  - `/run/secrets` or mounted files preferred
  - keyring disabled
  - limited ephemeral generation allowed with degraded posture

- **Production container**
  - persistent mounted secrets required
  - keyring disabled
  - missing required secrets fail fast
  - bootstrap-only inputs consumed once and scrubbed from process env where possible

### Workflow matrix

| Workflow | Scope | Inputs | Output/state change | Steady-state source after completion | Notes |
|---|---|---|---|---|---|
| first-time local interactive setup | deployment | operator password entry, optional dev defaults | local security/bootstrap state initialized | keyring or file-backed local sources | local-only convenience path |
| first-time container bootstrap | deployment | mounted runtime secrets plus `master_password` bootstrap input | deployment security state initialized, infra ready | mounted secret files | no keyring dependency |
| initial tenant bootstrap | tenant | `tenant_display_name`, `admin_full_name`, `admin_pin`, optional language | tenant row, membership, admin identity/bootstrap hash | tenant-scoped session issuance after auth | does not create separate infra secret set |
| service restart | deployment | none if required secrets already present | services restart unattended | same mounted/env source as before | must not prompt |
| tenant session minting | tenant | authenticated user context + selected tenant | tenant-scoped JWT + refresh token | auth/session store | explicit and auditable action |
| tenant switch | tenant | active deployment + target tenant | new tenant-scoped session and cache boundary | tenant-partitioned client/session state | no raw tenant-header trust as boundary |
| deployment secret rotation | deployment | replacement mounted secret or external provider update | runtime secret version changes | new mounted/env source | may require coordinated service restart |
| tenant admin credential rotation | tenant | authenticated admin action | updated tenant admin credential hash/session invalidation as needed | auth/session store | must not require infra secret rotation |
| recovery/bootstrap replay | deployment | deploy-state + bootstrap-only recovery inputs | re-establishes deployment bootstrap safely | canonical deployment source | idempotent, auditable |
| tenant maintenance | tenant | admin/operator action | tenant create/deactivate/membership updates | database + auth/session store | separate from deployment secret handling |

Workflow rules:

- every workflow must declare whether it operates at `deployment` or `tenant` scope
- deployment bootstrap and tenant bootstrap are separate phases, even if one command orchestrates both
- secret rotation, tenant switching, and recovery must emit explicit audit events with scope and source
- runtime services should only depend on steady-state sources, not on bootstrap-only inputs remaining present

Normal operations should not require:

- container keyring access
- password entry after restart
- inferring health from ambiguous `unknown` states

### Posture and audit

For each security control, expose at minimum:

- `configured_state`
- `effective_state`
- `credential_state`
- `credential_source`
- `persistence_state`
- `last_verified_at`
- `last_rotated_at`
- `degraded_reason`

Use explicit states like:

- `enabled` / `disabled`
- `present` / `missing`
- `degraded`
- `ephemeral` / `persistent`

Reserve `unknown` for telemetry failure only.

Audit at minimum:

- bootstrap secret creation
- secret source changes
- secret rotation
- failed secret resolution
- degraded or ephemeral startup
- admin-triggered security operations

## Migration path

1. fix posture semantics and keyring-based reporting assumptions
2. standardize one credential provider contract and source taxonomy
3. move CLI/bootstrap paths onto the same resolution chain as runtime
4. make Docker/file-backed secrets the default for containers
5. add bootstrap, rotation, recovery, and audit workflows

## Open decisions

- standard secret names and file paths
- deployment mode detection vs explicit config
- which secrets may be ephemeral in dev
- root-key rotation flow
- exact tenant session minting API and refresh lifecycle

## Summary

Keep local keyring support, but stop treating it as the container runtime default. Standardize runtime secret resolution around explicit secret sources, make posture truthful, and align CLI/bootstrap behavior with the same model.
