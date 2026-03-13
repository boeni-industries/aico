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
- [x] Standardize Docker/Compose secret file names and mount paths
- [x] Decide which secrets may be ephemeral in dev and which must fail loudly in production
- [x] Separate asset classes in backend posture APIs
- [x] Update Studio security UI to show source, persistence, and degraded reason consistently
- [x] Add bootstrap flow for first-time container deployments
- [x] Add guided rotation and recovery workflows
- [x] Add audit events for secret resolution, fallback, bootstrap, rotation, and degraded startup
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
| `pg_password` | runtime auth secret | deployment | `/run/secrets/pg_password` | yes | current code auto-generates in `deploy.py` when missing | target: fail fast | deployment operator |
| `api_gateway_jwt_secret` | runtime auth secret | deployment | `/run/secrets/api_gateway_jwt_secret` | yes | current code auto-generates in `deploy.py` when missing | target: fail fast | deployment operator |
| `grafana_admin_password` | runtime auth secret | deployment | `/run/secrets/grafana_admin_password` | yes | current code auto-generates in `deploy.py` when missing | target: fail fast | deployment operator |
| `minio_root_user` | runtime auth secret | deployment | `/run/secrets/minio_root_user` | yes | current code auto-generates in `deploy.py` when missing | target: fail fast | deployment operator |
| `minio_root_password` | runtime auth secret | deployment | `/run/secrets/minio_root_password` | yes | current code auto-generates in `deploy.py` when missing | target: fail fast | deployment operator |
| `artifact_store_access_key` | runtime auth secret | deployment | `/run/secrets/artifact_store_access_key` | yes | current code auto-generates in `deploy.py` when missing | target: fail fast | deployment operator |
| `artifact_store_secret_key` | runtime auth secret | deployment | `/run/secrets/artifact_store_secret_key` | yes | current code auto-generates in `deploy.py` when missing | target: fail fast | deployment operator |
| `root_encryption_secret` | data-at-rest root secret | deployment | `/run/secrets/root_encryption_secret` | yes | not yet wired through current local Compose/deploy flow | target: fail fast | deployment operator |
| `master_password` | bootstrap/recovery input | deployment | `--master-password-file` or `AICO_MASTER_PASSWORD` | no, input only | allowed for headless dev/bootstrap | fail bootstrap | deployment operator |
| `admin_pin` | tenant identity bootstrap input | tenant | CLI/config input at bootstrap time | no, only stored as derived hash | required for first tenant bootstrap | fail bootstrap | tenant/deployment operator |
| tenant-scoped JWT | tenant session material | tenant | minted by gateway/session flow | yes, via auth/session store | normal runtime behavior | deny tenant access | auth/session subsystem |
| tenant-scoped refresh token | tenant session material | tenant | minted by gateway/session flow | yes, via auth/session store | normal runtime behavior | deny session renewal | auth/session subsystem |

Interpretation rules:

- deployment-scoped runtime secrets are shared by services inside one deployment and must not be duplicated per tenant by default
- tenant-scoped session material is isolated by `tenant_id` and should be partitioned in storage, cache, transport, and refresh logic
- bootstrap-only inputs are consumed during setup or recovery and are not the same thing as steady-state runtime secrets

### Current generation vs fail-fast reality

Current code behavior is narrower and less mode-aware than the target policy:

- `cli/commands/deploy.py::_ensure_all_secrets()` currently auto-generates missing local Compose secret files for:
  - `pg_password`
  - `api_gateway_jwt_secret`
  - `grafana_admin_password`
  - `minio_root_user`
  - `minio_root_password`
  - `artifact_store_access_key`
  - `artifact_store_secret_key`
- that generation path is not currently gated by an explicit deployment mode check such as "dev only" vs "production"
- `master_password` is different:
  - non-interactive deploy fails if no master key exists and neither `--master-password-file` nor `AICO_MASTER_PASSWORD` is provided
- some runtime consumers fail fast if secrets are absent at startup:
  - e.g. Postgres connection setup raises if `pg_password` cannot be resolved from provider or key manager
- `root_encryption_secret` is part of the target architecture, but is not yet part of the current local Compose secret generation path

Decision:

- **Allowed to be generated for local/container dev**
  - `pg_password`
  - `api_gateway_jwt_secret`
  - `grafana_admin_password`
  - `minio_root_user`
  - `minio_root_password`
  - `artifact_store_access_key`
  - `artifact_store_secret_key`

- **Must fail loudly in production if missing**
  - all steady-state runtime deployment secrets above
  - `root_encryption_secret`

- **Bootstrap-only failure conditions**
  - `master_password` missing during headless bootstrap
  - `admin_pin` missing when initial tenant admin bootstrap is required

Operational rule:

- local interactive and local container development may auto-generate the listed deployment-scoped runtime secrets
- production container/runtime startup must not generate steady-state secrets implicitly
- production bootstrap may consume bootstrap-only inputs, but steady-state runtime secrets must already exist in their canonical source before unattended restart
- `root_encryption_secret` is never a convenience-generated runtime secret in production

### Deployment secret inventory

For clarity, split secrets into three groups:

- **Mounted runtime secrets already used in local Compose**
  - `pg_password`
  - `api_gateway_jwt_secret`
  - `minio_root_user`
  - `minio_root_password`
  - `artifact_store_access_key`
  - `artifact_store_secret_key`
  - current Compose definitions live under `docker/secrets/<name>` and are mounted by Docker as `/run/secrets/<name>`
  - current service usage in `docker-compose.local.yml` is:
    - `postgres`, `postgres-shadow`: `pg_password` via `POSTGRES_PASSWORD_FILE=/run/secrets/pg_password`
    - `gateway`: `pg_password`, `api_gateway_jwt_secret`
    - `core`: `pg_password`, `artifact_store_access_key`, `artifact_store_secret_key`
    - `modelservice`: `pg_password`
    - `minio`: `minio_root_user`, `minio_root_password`
    - `minio-init`: `minio_root_user`, `minio_root_password`, `artifact_store_access_key`, `artifact_store_secret_key`

- **Deployment/runtime credentials not yet normalized to Docker secrets**
  - none in local Compose after Grafana normalization

- **Bootstrap-only inputs**
  - `master_password` via `AICO_MASTER_PASSWORD` or `--master-password-file`
  - `admin_pin` / admin passcode for initial admin credential bootstrap

Target rule:

- runtime secrets should converge on canonical `/run/secrets/<name>` mounts
- bootstrap-only inputs should stay separate from steady-state runtime secrets
- local Compose should declare every steady-state runtime secret in the top-level `secrets:` block with `file: ./secrets/<name>`
- deploy helpers should write those files under `docker/secrets/<name>` rather than relying on ad hoc env-only delivery for long-lived runtime credentials

### Current path standardization status

Today the codebase is close to one standard:

- **authoritative on-disk secret source for local Compose**
  - `docker/secrets/<name>`

- **authoritative in-container mount path**
  - `/run/secrets/<name>`

- **provider expectation**
  - `CredentialProvider().get("<name>")` reads `/run/secrets/<name>`

The remaining drift is concentrated in a few areas:

- some CLI/security helpers still sync `docker/secrets/*` into keyring for compatibility
- `deploy.py` still manages legacy Influx secret names that no longer fit the intended OTEL/Prometheus/Loki target direction

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

### Current rotation and recovery reality

Current implementation provides only partial rotation/recovery support:

- **Exists today**
  - gateway admin endpoint `POST /admin/security/keys/rotate`
    - rotates the API gateway JWT secret through `AICOKeyManager.rotate_jwt_secret("api_gateway")`
    - writes `security.key_rotation` and admin audit events
  - key rotation history endpoint:
    - `GET /admin/security/keys/history`
  - deploy replay baseline:
    - `aico deploy system` reuses deploy state and is mostly idempotent on rerun
  - master password change path:
    - `aico security passwd`

- **Partially present but not guided**
  - `AICOKeyManager.rotate_jwt_secret()` is keyring-oriented and not aligned with canonical mounted-secret rotation for containers
  - `deploy.py` can regenerate missing secret files, but that is not the same thing as an explicit audited rotation workflow
  - deploy-state reuse helps recovery, but there is no explicit recovery command contract yet

- **Missing or not implemented**
  - guided rotation for deployment-scoped mounted secrets such as:
    - `pg_password`
    - `grafana_admin_password`
    - `artifact_store_access_key`
    - `artifact_store_secret_key`
    - `root_encryption_secret`
  - coordinated service restart / cutover workflow for rotated mounted secrets
  - explicit recovery flow for restoring canonical secret files after host loss or operator error
  - guided tenant-admin credential recovery workflow
  - scheduler maintenance rotation is still placeholder/TODO for session and database keys

Decision:

- guided workflows must be defined separately for:
  - `deployment secret rotation`
  - `deployment bootstrap recovery`
  - `tenant admin credential rotation/recovery`
  - `JWT/session signing rotation`

- each workflow should declare:
  - `scope`
  - `required inputs`
  - `safe preconditions`
  - `state changes`
  - `restart requirements`
  - `audit events emitted`

- target operator path:
  - use `aico deploy system` for safe bootstrap replay / deployment recovery
  - use explicit rotation commands or admin actions for steady-state secret rotation
  - do not rely on "delete the secret and let it regenerate" as the production recovery model

### Guided rotation and recovery workflows

#### Deployment secret rotation

- **Scope**
  - deployment

- **Applies to**
  - `pg_password`
  - `grafana_admin_password`
  - `artifact_store_access_key`
  - `artifact_store_secret_key`
  - `root_encryption_secret`

- **Required inputs**
  - replacement secret material in canonical source
  - operator confirmation
  - maintenance window if restart is required

- **Safe preconditions**
  - replacement secret exists and passes validation
  - affected services are identified
  - rollback material is retained where appropriate

- **State changes**
  - canonical mounted secret changes
  - affected services restart or re-read configuration
  - posture reports new source/version state

- **Audit events**
  - rotation requested
  - rotation applied
  - restart/cutover completed
  - rollback applied if needed

#### Deployment bootstrap recovery

- **Scope**
  - deployment

- **Entry path**
  - `aico deploy system`

- **Required inputs**
  - canonical runtime secrets
  - bootstrap-only recovery inputs if deploy authentication is required
  - existing deploy-state if available

- **Safe preconditions**
  - operator intends replay/recovery, not destructive reset
  - `nuke`-style destructive paths are not used

- **State changes**
  - verifies or recreates missing deployment bootstrap state
  - reasserts tenant/admin bootstrap invariants without duplicating records
  - rewrites deploy-state when needed

- **Audit events**
  - recovery replay started
  - recovery replay completed
  - invariant mismatch detected

#### Tenant admin credential rotation or recovery

- **Scope**
  - tenant

- **Required inputs**
  - authenticated admin or explicit recovery authority
  - replacement admin credential / passcode input

- **Safe preconditions**
  - target tenant is explicit
  - deployment-scoped secrets remain unchanged

- **State changes**
  - updates tenant admin credential hash
  - invalidates tenant sessions if policy requires it

- **Audit events**
  - tenant admin credential change requested
  - tenant admin credential updated
  - session invalidation applied if relevant

#### JWT or session signing rotation

- **Scope**
  - deployment

- **Current implementation anchor**
  - `POST /admin/security/keys/rotate`

- **Required inputs**
  - explicit reason
  - operator confirmation

- **Safe preconditions**
  - operator understands session impact
  - replacement signing secret is persisted to canonical source in containerized deployments

- **State changes**
  - signing secret rotates
  - old/new key references are recorded where supported
  - session validation behavior changes according to cutover policy

- **Audit events**
  - `security.key_rotation`
  - admin audit entry for key rotation

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
- `last_checked_at`
- `audit_event_reference` when a state transition occurred

Use explicit states like:

- `enabled` / `disabled`
- `present` / `missing`
- `degraded`
- `ephemeral` / `persistent`

Reserve `unknown` for telemetry failure only.

### Current backend posture API mismatch

Current gateway admin posture APIs do not yet separate asset classes cleanly enough for the target model:

- `GET /admin/security/posture`
  - returns only four broad buckets:
    - `encryption`
    - `transport`
    - `authentication`
    - `audit`
  - this mixes different asset classes:
    - master-key / key-derivation state
    - database-at-rest posture
    - transport/message-bus posture
    - session/auth counters
    - audit pipeline state

- `GET /admin/security/keys`
  - reports a single `asset_name` / `asset_type`
  - currently labels the result as an API signing secret
  - but the data is assembled from both:
    - `AICOKeyManager.get_security_health_info()` for master-key metadata
    - `AICOKeyManager.get_jwt_secret("api_gateway")` for JWT secret presence
  - `source="credential_provider_or_keyring"` is also too coarse for the source taxonomy defined in this document

What is missing:

- a distinct asset class for **deployment runtime secrets**
  - e.g. `pg_password`, `api_gateway_jwt_secret`, `grafana_admin_password`, artifact-store credentials

- a distinct asset class for **master/root cryptographic material**
  - master key presence, age, Argon2id parameters, root encryption material

- a distinct asset class for **transport identity / transport encryption posture**
  - NATS / message-bus encryption status

- a distinct asset class for **bootstrap-only inputs**
  - whether bootstrap is awaiting `master_password` or `admin_pin`

- per-asset source reporting using the canonical taxonomy
  - `mounted_secret_file`
  - `environment_variable`
  - `local_keyring`
  - `external_provider`
  - `generated_ephemeral`

Decision:

- the backend posture surface should stop treating "security" as one flattened status blob
- posture responses should separate:
  - `runtime_secrets`
  - `root_crypto`
  - `transport_security`
  - `bootstrap_requirements`
  - `authentication_sessions`
  - `audit_pipeline`
- each reported asset should include:
  - `asset_name`
  - `asset_class`
  - `scope`
  - `source`
  - `persistent`
  - `status`
  - `degraded_reason`

Proposed target response shape:

```json
{
  "runtime_secrets": [
    {
      "asset_name": "api_gateway_jwt_secret",
      "asset_class": "runtime_secret",
      "scope": "deployment",
      "source": "mounted_secret_file",
      "persistent": true,
      "status": "present",
      "degraded_reason": null,
      "last_verified_at": "..."
    }
  ],
  "root_crypto": [
    {
      "asset_name": "root_encryption_secret",
      "asset_class": "root_crypto",
      "scope": "deployment",
      "source": "local_keyring",
      "persistent": true,
      "status": "degraded",
      "degraded_reason": "container_runtime_should_not_depend_on_keyring",
      "last_verified_at": "..."
    }
  ],
  "transport_security": [],
  "bootstrap_requirements": [],
  "authentication_sessions": {
    "status": "enabled"
  },
  "audit_pipeline": {
    "status": "enabled"
  }
}
```

Implementation note:

- this is a **target contract**, not current API behavior
- current backend schemas still expose:
  - `SecurityPostureResponse(encryption, transport, authentication, audit)`
  - `SecurityKeyInfoResponse(...)` as a flattened single-asset response
- the document is complete once this target contract is explicit and tied back to the current mismatch

### Current Studio security UI mismatch

Current Studio code is still coupled to the old backend posture shape:

- `src/api/adminSecurity.ts`
  - models `SecurityPostureResponse` as:
    - `encryption`
    - `transport`
    - `authentication`
    - `audit`
  - models `SecurityKeyInfoResponse` as one flattened key asset with a single `source`

- `SystemSecurityAuditTab.tsx`
  - renders overview cards directly from:
    - `securityPosture.encryption.status`
    - `securityPosture.transport.status`
    - `securityPosture.audit.status`
  - this means Studio currently cannot distinguish:
    - deployment runtime secret posture
    - root/master crypto posture
    - transport posture
    - bootstrap requirement state

- `SecurityManagementSection.tsx`
  - treats `keyInfo` as effectively one signing-secret asset
  - maps `source === "credential_provider_or_keyring"` to the display text:
    - `Loaded from runtime secret provider`
  - this loses the exact source class and cannot show:
    - mounted secret file vs environment variable vs keyring
    - persistent vs ephemeral
    - degraded reason

Decision:

- Studio should stop inferring nuanced security state from the current four-bucket summary alone
- Studio should render asset-oriented cards/tables from the same canonical asset classes defined for the backend posture API:
  - `runtime_secrets`
  - `root_crypto`
  - `transport_security`
  - `bootstrap_requirements`
  - `authentication_sessions`
  - `audit_pipeline`
- each rendered asset row/card should show:
  - `asset_name`
  - `source`
  - `persistent`
  - `status`
  - `degraded_reason`
  - `last_verified_at` when available

Minimum UI mapping contract:

- **Overview**
  - summary cards derived from aggregated asset classes, not hardcoded `encryption` / `transport` / `audit` buckets

- **Runtime secrets table**
  - rows for `pg_password`, `api_gateway_jwt_secret`, `grafana_admin_password`, artifact-store and MinIO credentials when exposed
  - exact source badge:
    - `mounted_secret_file`
    - `environment_variable`
    - `local_keyring`
    - `external_provider`
    - `generated_ephemeral`
  - persistence badge:
    - `persistent`
    - `ephemeral`
  - degraded-state callout when `status == "degraded"`

- **Root crypto section**
  - distinguish master/root crypto posture from JWT/session-signing posture
  - display KDF metadata separately from runtime-secret source metadata

- **Bootstrap requirements section**
  - show when deployment is blocked waiting for bootstrap-only inputs
  - do not present bootstrap-only inputs as steady-state runtime assets

- **Transport section**
  - show transport posture independently from secret presence
  - do not infer transport security from a JWT or master-key asset

Implementation note:

- this is a **target Studio contract**, not current Studio behavior
- current Studio still consumes:
  - `SecurityPostureResponse` with four coarse buckets
  - `SecurityKeyInfoResponse` as one flattened asset
- the document is complete once Studio requirements are explicit enough that a later implementation can follow them without inventing semantics

Audit at minimum:

- bootstrap secret creation
- secret source changes
- secret rotation
- failed secret resolution
- degraded or ephemeral startup
- admin-triggered security operations

### Current audit-event reality

Current code emits only part of the desired audit surface:

- **Exists today**
  - `security.key_rotation`
    - emitted by `POST /admin/security/keys/rotate`
  - `audit.admin`
    - emitted for admin-triggered key rotation actions through `_write_audit_event(...)`

- **Present only as logs, not structured audit events**
  - credential source selection inside `CredentialProvider`
  - keyring fallback warnings in `AICOKeyManager`
  - secret generation/import messages in `cli/commands/deploy.py`
  - missing-secret failures during runtime startup

- **Missing as explicit event topics**
  - bootstrap secret creation
  - bootstrap replay / recovery start and completion
  - secret source fallback
  - degraded startup because only ephemeral or non-canonical sources were available
  - failed canonical secret resolution

Decision:

- the event model should include at least these explicit topics:
  - `security.secret.resolved`
  - `security.secret.fallback_used`
  - `security.secret.missing`
  - `security.bootstrap.started`
  - `security.bootstrap.completed`
  - `security.bootstrap.replayed`
  - `security.startup.degraded`
  - `security.key_rotation`

- minimum event metadata should include:
  - `asset_name`
  - `asset_class`
  - `scope`
  - `source`
  - `persistent`
  - `status`
  - `degraded_reason`
  - `actor` when human-triggered
  - `correlation_id` for one bootstrap/rotation/recovery flow

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
