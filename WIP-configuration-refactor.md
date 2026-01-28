# WIP: Configuration Refactor (Domain-Based, Loud-Fail)

**Status:** ✅ **COMPLETED** (2026-01-28)  
**Last Updated:** 2026-01-28

## ✅ Completion Status

**All primary objectives achieved:**
- ✅ Domain split: 16 domain files created and migrated
- ✅ Code migration: 100+ files updated to new domains
- ✅ Schema validation: Implemented with JSON Schema Draft 7
- ✅ Legacy namespace guard: Strict fail-loud for `core.*` prefixes
- ✅ All schemas valid: 0 validation errors
- ✅ Environment configs: Updated to new domain structure
- ✅ Test coverage: Unit and integration tests created
- ✅ CI/CD: Schema validation script ready for pipeline

**Remaining (optional enhancements):**
- Schema improvements (more detailed validation rules)
- Additional test coverage for edge cases
- Documentation updates for end users

## Goal
Convert the current hybrid/monolithic configuration into a **clean, truly domain-based** configuration system with:

- **Single sources of truth** (no overlapping/duplicated config definitions across domains)
- **Strict / loud failure semantics** (missing required config keys must raise errors; no silent fallbacks)
- **Domain schemas for every domain** and validation enforced at startup / CLI
- **Removal of deprecated / unused config branches** (SQLite deprecated; DuckDB never used; anything else unused)

This is a **full refactor/migration**. No TODOs/placeholders should remain when complete.

## Current State (What’s Broken / Inconsistent)

### Domain loader is real, but content strategy isn’t
- `ConfigurationManager._load_default_configs()` loads each `config/defaults/*.yaml` into a top-level domain by filename stem.
  - `core.yaml` -> `core.*`
  - `security.yaml` -> `security.*`
  - `database.yaml` -> `database.*`
  - `service_auth.yaml` -> `service_auth.*`

### `core.yaml` is a mega-config
`config/defaults/core.yaml` currently includes many unrelated sections:
- `system`, `logging`, `message_bus`
- `api_gateway`, `modelservice`
- `scheduler`, `conversation`, `memory`, `agency`
- also contains `database` and (currently, re-added) `service_auth`

This makes `core` behave as a de-facto monolith, despite the loader being domain-based.

### Overlap / duplication hotspots (must be eliminated)
- **Service auth**
  - Exists in `core.yaml` under `core.service_auth.*` (re-added)
  - Exists in `service_auth.yaml` under `service_auth.*` (but user reverted shape to nested `services.defaults`, which does not match consumer expectations)
  - Consumer code reads `service_auth.defaults.*` and `service_auth.services.*`
  - Must pick ONE location and ONE schema.

- **Database naming confusion**
  - `core.yaml` contains `database:` for Postgres + Influx (“core database configuration”).
  - `database.yaml` contains SQLite-ish tuning + `chromadb` + `duckdb`.
  - With SQLite deprecated and DuckDB unused, `database.yaml` likely needs to be removed or repurposed.

## Target End State (Design)

## Namespace / Prefix Rules (MUST be consistent)

### Domain file rule
- Each `config/defaults/{domain}.yaml` defines the top-level config namespace `{domain}.*`.
- Therefore the YAML **must not repeat the domain name as a nested top-level key**.

Example:
- ✅ `config/defaults/system.yaml` contents start with `paths:`, `environment:`, etc. (read as `system.paths.*`, `system.environment`, ...)
- ❌ `config/defaults/system.yaml` starting with `system:` would create `system.system.*`

### Migration rule from the former mega-config
- Historically, many values lived in `core.yaml` and were accessed as `core.<section>.*`.
- After splitting, those keys move to dedicated domains:
  - `core.system.*` -> `system.*`
  - `core.logging.*` -> `logging.*`
  - `core.message_bus.*` -> `message_bus.*`
  - `core.api_gateway.*` -> `api_gateway.*`
  - `core.modelservice.*` -> `modelservice.*`
  - `core.memory.*` -> `memory.*`
  - `core.agency.*` -> `agency.*`
  - `core.scheduler.*` -> `scheduler.*`
  - `core.conversation.*` -> `conversation.*`

### Enforcement during migration
- During migration, any remaining reads to `core.*` must fail loudly with a guidance message.
- Final state: no `core.*` reads remain; no compatibility fallbacks remain.

### 1) “Core” becomes minimal (or renamed)
Decide one of:

- **Option A1 (preferred)**: Keep a small `core.yaml` for truly global primitives only.
  - `system.*`
  - config loader behavior / schema validation toggles
  - maybe `logging.*` if it is genuinely universal

- **Option A2**: Rename `core.yaml` to something honest like `platform.yaml` and split out the rest into dedicated domains.

Either way: avoid `core` becoming “everything”.

### 2) Dedicated domains with clear ownership
Proposed domain split (defaults files):

- `system.yaml`
  - environment
  - paths
  - global flags

- `logging.yaml`
  - levels, retention

- `message_bus.yaml`
  - broker ports/timeouts

- `api_gateway.yaml`
  - host/ports/protocols/auth config

- `modelservice.yaml`
  - ollama/transformers/tts

- `scheduler.yaml`
  - scheduler tuning

- `conversation.yaml`
  - conversation engine settings

- `memory.yaml`
  - working/semantic/AMS settings

- `agency.yaml`
  - agency planning/safety policies

- `security.yaml`
  - encryption, KDF, RBAC, transport security

- `service_auth.yaml`
  - service-to-service token defaults + permissions

- `telemetry.yaml`
  - instrumentation/exporters

- `datastores.yaml` (or `persistence.yaml`)
  - Postgres connection (host/port/db name/schema)
  - Influx connection (url/org/bucket/retention)
  - Chroma configuration if still used
  - Remove SQLite/DuckDB if truly unused

### 3) Loud-fail configuration semantics
Define strict rules:

- Any config that is required for startup must be retrieved using a **strict getter** that:
  - raises an exception if missing
  - includes domain/key path + known root keys in the error message

- Disallow silent fallbacks for required keys.
  - The only allowed fallback defaults are:
    - explicitly declared in the schema (`default`), and/or
    - used for non-critical optional features with clear naming.

## Required Code Changes (No placeholders)

### A) Implement strict config access
- Add a strict method on `ConfigurationManager`, e.g. `require(key: str) -> Any` (name TBD) that:
  - throws `ConfigurationError` if key missing
  - throws if value is empty dict for required section (optional rule)

- Update call sites to use strict access for required settings.
  - Replace `config.get("...", default)` for required keys.

### B) Remove current “silent fallback” behaviors
- `ConfigurationManager.get()` currently returns defaults silently and sometimes logs warnings/errors.
- Change behavior:
  - Either keep `get()` for optional reads only (no log spam),
  - and enforce `require()` for mandatory reads.

- Eliminate patterns like returning `{}` for missing section as “normal”.

### C) Enforce schema validation
- Create schemas for every domain under `config/schemas/*.schema.json`.
- On startup (backend/modelservice/cli), validate:
  - defaults
  - merged env/user/runtime config

- Ensure CLI `config validate` fails non-zero if any required domain schema missing or invalid.

### D) Refactor consumers to new domains
- Update all code that currently reads `core.*` keys to the new domain paths.
- Provide a temporary compatibility layer only during migration if absolutely necessary, but final result must have:
  - no duplicated keys
  - no “try both paths” logic remaining

## Required Config Migration Steps

### 1) Freeze current config inventory
- Build an inventory of all `config.get(...)` keys in `*.py`.
- Classify each key:
  - required vs optional
  - owning domain

### 2) Define final key paths + domains
- Decide exact dot paths for each config value (no ambiguity).
- Ensure no overlapping paths between domains.

### 3) Split defaults
- Create new defaults YAML files per domain.
- Move keys out of `core.yaml` into their domain file.

### 4) Update environment configs
- Update `config/environments/development.yaml` and `production.yaml` to match new domain structure.

### 5) Update user config + runtime config
- If user configs exist or runtime persisted config exists, provide a one-time migration:
  - read old
  - write new
  - validate

### 6) Remove deprecated configs
Given:
- SQLite deprecated (Postgres is the real store)
- DuckDB never used

Actions:
- Remove SQLite-related config branches and code paths.
- Remove DuckDB config and any integration remnants, unless it’s being adopted immediately.
- If ChromaDB still used, keep it but place under the correct domain (`memory` or `datastores`).

### 7) Delete or repurpose old files
- After migration, delete `config/defaults/core.yaml` (or reduce it to minimal system config) depending on chosen approach.
- Ensure only the new domain defaults remain.

## Specific Known Fixes (Do first)

### Service Auth single source of truth
- Decide: `service_auth.yaml` is authoritative.
- Ensure shape matches consumer:
  - `defaults:`
  - `services:`

- Remove any `service_auth:` from other domains.
- Add `service_auth.schema.json`.

## Test / Validation Work

- Add unit tests for `ConfigurationManager.require()` and schema validation.
- Add integration test that boots core components and asserts:
  - missing required keys -> hard failure
  - wrong types -> schema failure

- Add a CI check (or local script) that:
  - enumerates all domains
  - asserts each has a schema
  - validates defaults + environment configs

## Deliverables Checklist

- New domain YAML files in `config/defaults/`.
- Updated `config/environments/*.yaml`.
- Updated code: no stale key paths.
- New schemas for every domain.
- Strict config access implemented and adopted.
- Deprecated DB configs removed.
- Tests updated/added.
- No duplicated configuration values.
- No silent fallbacks for required configuration.
