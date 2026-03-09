---
description: Remove legacy local runtime path usage (macOS Application Support) and make frontend/studio fully independent
---

# Goal

Eliminate the legacy *host-local* runtime directory (historically `~/Library/Application Support/aico`, on this machine: `/Users/mbo/Library/Application Support/aico`) from the system entirely.

After the refactor, you must be able to delete that directory and have:

- Backend (gateway/core/modelservice) run in Docker **flawlessly**
- Flutter frontend run **independently** (deployable separately) and **not rely** on backend runtime paths
- AICO Studio run **independently** (deployable separately) and **not rely** on backend runtime paths

# Executive summary

## Execution checklist (tick as you go)

- [x] Fix backend macOS-hardcoded path usage in `backend/api/metrics/endpoints/system.py` (storage size calculation must use configured AICO data directory / docker volume root).
- [x] Enforce docker-only backend paths: require `AICO_DATA_DIR` (and/or related `AICO_*_DIR`) in container env; ensure no backend component writes to host user directories.
- [x] Make Flutter frontend independent: remove filesystem dependency on `core.yaml` under Application Support; replace with app-native config + runtime config (e.g. HTTP `/config.json`) and/or build-time `--dart-define`.
- [x] Remove retired LMDB working memory module and stale exports/docs (`shared/aico/ai/memory/working.py`, `shared/aico/ai/memory/__init__.py`).
- [x] Remove/rename remaining ChromaDB operational references (database admin, backups, scripts) if Chroma is fully retired.
- [x] Verify AICO Studio stays independent (`/config.json` and env only) and update docker deployment docs if needed.

## What is still “legacy”

There are two separate “legacy” themes that were historically conflated:

1. **Legacy storage backends** (LMDB, ChromaDB, etc.)
2. **Legacy runtime directory** on the host machine (`~/Library/Application Support/aico`)

Your new target architecture (fully dockerized) means:

- Backend components must use **container paths + docker volumes**, not macOS-specific user directories.
- Frontends must not read backend configuration or data from host runtime directories.

### Storage backends status (as observed in repo)

- **LMDB working memory**
  - `shared/aico/ai/memory/working.py` is explicitly marked **DEPRECATED** and raises at construction time.
  - `shared/aico/ai/memory/manager.py` enforces Postgres working memory (`core.memory.working.driver=postgres`).
  - **Conclusion**: LMDB working memory is retired, but **dead code + docs still exist**.

- **ChromaDB semantic memory**
  - The active semantic store in `shared/aico/ai/memory/semantic.py` is **Postgres/pgvector**.
  - However, there are still places (e.g. ops/admin endpoints, migration scripts) that assume a ChromaDB directory exists under the legacy runtime tree.
  - **Conclusion**: Chroma appears retired for runtime, but there are still **operational endpoints/scripts** that reference its legacy on-disk location.

- **Postgres / pgvector**
  - This is the primary storage for working + semantic memory in the shared memory manager.

- **Modelservice model caches**
  - `modelservice/handlers/tts_handler.py` uses `AICOPaths.get_cache_directory()` and sets `TTS_HOME` to that location.
  - In Docker, this must map to a **mounted cache volume** (or ephemeral cache, depending on preference).

## What is still calling into the legacy runtime path (directly or indirectly)

There are two ways code ends up using `~/Library/Application Support/aico`:

1. **Direct macOS path construction** (hardcoded `Path.home()/Library/Application Support/...`).
2. **Indirect path resolution** via `platformdirs.user_data_dir("aico", "boeni-industries")` or Flutter’s `getApplicationSupportDirectory()`.

### Backend: direct macOS hardcode (must be removed)

- `backend/api/metrics/endpoints/system.py`
  - Computes storage size by scanning:
    - `Path.home() / "Library" / "Application Support" / "aico" / "data"`
  - This is **macOS-only** and **host-local**.
  - In Docker, it’s wrong (and usually silently returns 0).

### Backend: indirect “Application Support” via shared path resolution

- `shared/aico/core/paths.py`
  - Default `AICOPaths.get_data_directory()` is `platformdirs.user_data_dir("aico", "boeni-industries")`.
  - On macOS, this resolves to `~/Library/Application Support/aico`.
  - Multiple backend components use `AICOPaths.get_data_directory()`, e.g.:
    - `backend/api/kg/router.py` (GQL templates)
    - `backend/core/nats_handlers.py` (GQL templates)
    - `backend/services/version_detector.py` (cache)
    - `backend/api/operations/backup_sets.py` (backup artifacts, semantic memory path)

This is not “wrong” on macOS-native runs, but it becomes “legacy” once the backend is *docker-only*.

### Modelservice: indirect cache directory

- `modelservice/handlers/tts_handler.py`
  - Uses `AICOPaths.get_cache_directory()`.
  - Without env overrides, this would resolve to `~/Library/Application Support/aico/cache` on macOS.
  - In Docker, it resolves to something like `/root/.local/share/...` unless you set `AICO_CACHE_DIR`/`AICO_DATA_DIR`.

### Flutter frontend: uses Application Support by design (must be decoupled from backend runtime)

- `frontend/lib/core/utils/aico_paths.dart`
  - Calls `getApplicationSupportDirectory()` and then builds:
    - `<appSupport>/boeni-industries/aico/...`
  - Reads backend-ish config from:
    - `<base>/config/defaults/core.yaml`

This makes the Flutter app **not independently deployable**, because it expects a backend runtime layout on disk.

### AICO Studio: already independent of host runtime dir

- `aico-studio/src/runtime/runtimeConfig.ts`
  - Loads `/config.json` at runtime, with env fallback.
  - No host runtime path dependencies were found.

# What “frontend fully independent” means (requirements)

For Flutter, “fully independent” should mean:

- No dependency on a shared host filesystem layout created by backend services.
- No need for `core.yaml` to exist under a shared runtime directory.
- All app configuration needed to run must come from:
  - build-time config (flavors / env / compile-time constants), and/or
  - a runtime **HTTP configuration endpoint** (served by gateway), and/or
  - bundled default config inside the app (assets).

It can still store its own local data (encrypted SQLite, offline queue, caches) using platform directories — that is normal for apps. The key is: **don’t couple frontend persistence to backend runtime layout**.

# Remediation plan (concrete steps)

## Phase A — Backend: remove macOS hardcodes and enforce container paths

1. **Remove** macOS-specific path scan in `backend/api/metrics/endpoints/system.py`.
   - Replace with scanning `AICOPaths.get_data_directory()` + configured subdir(s), or better: use configured env-based roots.

2. Ensure docker compose / container env sets these (single source of truth):
   - `AICO_DATA_DIR` (mandatory)
   - optionally `AICO_CACHE_DIR`, `AICO_LOGS_DIR`, `AICO_RUNTIME_DIR`, `AICO_MEMORY_DIR`

3. Update any endpoints that still assume Chroma directories exist (example below).
   - `backend/api/operations/database_admin.py` currently checks `AICOPaths.get_data_directory()/data/memory/semantic` and calls it “ChromaDB”.
   - If Chroma is retired, this should be removed or updated to the new storage reality.

## Phase B — Shared: delete retired LMDB working memory module and fix exports/docs

If your policy is **full cleanup with no backward compatibility**:

1. Delete `shared/aico/ai/memory/working.py` entirely (it is dead code and raises).
2. Update `shared/aico/ai/memory/__init__.py` to not export `WorkingMemoryStore`.
3. Update docs/comments that still claim:
   - Working memory = LMDB
   - Semantic memory stored in ChromaDB

## Phase C — Flutter: remove dependency on backend runtime layout

### Problem
`frontend/lib/core/utils/aico_paths.dart` currently:

- Derives a base directory under Application Support
- Reads `config/defaults/core.yaml` from disk under that base

This is a backend runtime assumption.

### Recommended solution (cleanest)

1. **Stop reading `core.yaml` from disk**.
2. Replace it with a Flutter-native config layer:
   - Built-in defaults (Dart constants or asset JSON)
   - Optional overrides via:
     - compile-time defines (`--dart-define`)
     - a gateway-served `/config.json` endpoint (similar to studio)

3. Keep local persistence (encrypted drift DB, offline queue, cache) under platform-appropriate app directories. That is not “legacy runtime”, it is normal client app storage.

### Deliverable
After this, Flutter can be deployed standalone (App Store / APK / etc.) with only an API base URL.

## Phase D — AICO Studio: confirm invariants

Studio already uses `/config.json` and environment variables.

Ensure:

- Docker deployment serves `/config.json` for Studio (or sets `REACT_APP_AICO_API_BASE_URL`).
- No references to host runtime directory exist.

# Open questions / decisions needed

1. **Do you want the backend to have zero dependency on platformdirs defaults?**
   - If yes, enforce `AICO_DATA_DIR` as mandatory at startup (fail fast if missing in docker).

2. **Is ChromaDB fully retired in runtime?**
   - If yes, remove remaining ops endpoints/scripts that treat it as active storage.

3. **What is the canonical runtime-config mechanism now?**
   - Backend: env + docker compose.
   - Studio: `/config.json`.
   - Flutter: decide between `--dart-define` vs gateway-served config.

# Concrete "can delete the runtime dir" checklist

You can delete `/Users/mbo/Library/Application Support/aico` once:

- Backend no longer writes/reads any data/config/logs there.
- Flutter no longer tries to read `core.yaml` from that tree.
- Studio does not rely on it (it currently doesn’t).

Minimum code changes required:

- Backend: remove macOS hardcode in `backend/api/metrics/endpoints/system.py`.
- Shared: remove LMDB working memory code + stale exports/docs.
- Flutter: replace disk-based `core.yaml` coupling with app-native + HTTP/env config.

