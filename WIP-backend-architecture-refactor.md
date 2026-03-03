# WIP: Backend Architecture Refactor (Local-first + Cloud/Enterprise)

## Progress Checklist (tick-off)
- [x] Lock interfaces: freeze/version gateway↔core and core↔modelservice contracts; add contract tests
- [x] Introduce standalone Gateway service (authn/authz, rate limits, idempotency, WebSockets)
- [x] Publish frontend-independent External API Contract (OpenAPI + WebSocket spec + examples)
- [x] Centralize identity + scoping: make `tenant_id`/`user_id` mandatory end-to-end; enforce authz on every request/subscription
- [x] Postgres source of truth for conversations: add tables + catch-up API
- [x] Outbox fallback for durable publication: keep streaming chunks ephemeral; ensure final response notifications are eventually delivered
- [x] Enable JetStream for durable flows; keep streaming chunks ephemeral; add replay/recovery tests
- [x] **Migrate fully to NATS: remove ZMQ entirely without keeping any legacy or fallback code**
- [x] Replace LMDB working memory with Postgres (retention/TTL + indexes; cache only if proven)
- [x] Replace ChromaDB with Postgres + `pgvector` only (no dual-write); ChromaDB fully removed
- [x] Harden scheduler + workers: idempotent tasks, tenant-scoped, multi-replica safe (JetStream work-queue + Postgres idempotency + integration coverage + no-stall test harness)
- [x] Make backend stateless: verify all correctness-critical state is in Postgres/JetStream (strict fs_guard + outbox restart/idempotency + scheduler dedupe + reconnect catch-up + crash/restart failover)
- [x] Decommission legacy: remove ZMQ broker path, LMDB, ChromaDB (✅ All removed - using PostgreSQL + pgvector)
- [x] **Redesign credential management and system setup for fully dockerized architecture (✅ Docker Compose secrets system implemented: `docker/secrets/*` mounted to `/run/secrets/*`, CredentialProvider reads from secrets, `aico security secrets-show/secrets-sync` for admin access, `aico deploy` bootstraps from legacy .env)**
- [x] **Migrate runtime directory structure to docker-based environment (✅ Phase 1 complete: Removed host bind mount, scheduler uses `/run/aico/triggers` (tmpfs), CLI triggers via API, backward compatible during migration, zero data loss verified)**
- [x] **Clean up legacy native process architecture (remove start/stop service commands, process management)**
- [x] **Ensure all Docker components properly represented in CLI; remove legacy tech debt**
- [x] **Create `aico deploy` CLI command: zero-to-operational system installation (prod default, --dev flag for development)**
- [x] **Create `aico upgrade` CLI: Analyze and refactor to the current system reality with the architectural change to virtualized / docker containers (✅ Implemented: `aico upgrade status/check/run/rollback` with pre-flight checks, database backup, safe container updates, and rollback capability)**
- [x] **Update AICO-Studio to use the new architecture (✅ Completed: Removed all ChromaDB references, replaced with Postgres+pgvector, updated System Health to show 7 services with API Gateway/Core Services/Modelservice split, PostgreSQL details include vector indexes, backup UI updated, deleted obsolete ChromaDBBrowser components. Studio dev-server HMR WebSocket errors resolved without disabling websockets.)**
- [x] Observability: add OpenTelemetry Collector (OTLP ingest + tail sampling + spanmetrics)
- [x] Observability: add Tempo (+ Grafana Tempo datasource) for trace/span drilldown
- [x] Observability: propagate W3C trace context over NATS/JetStream headers (✅ Implemented: trace context injection in publish/request, extraction in subscribe, full end-to-end trace continuity across Gateway→Core→Modelservice)
- [x] Observability: correlate logs↔traces (inject `trace_id`/`span_id` into Loki logs; Grafana trace→logs links)
- [x] Observability: add Grafana dashboards for core golden paths (request→core→modelservice; NATS/JetStream; Postgres)
- [x] Observability: add third Grafana dashboard for span/trace visualization (high-UX, drill-down) and add direct links to the other two dashboards (same style)

## Gap-Driven Task List (from codebase comparison)

### Critical
- [x] Enforce hard Gateway/Core split (no monolith path; gateway must not start core domain services in-process).
- [x] **Implement gateway idempotency enforcement (✅ Implemented: `IdempotencyMiddleware` enforces `Idempotency-Key` on config/remediation/scheduler/admin mutations; persists request hash + response in `aico_core.idempotency_requests` table; returns cached responses for duplicate requests; tested with 5 rapid requests showing 3x faster cached responses)**
- [x] **Make conversation write-path Postgres-authoritative (✅ Implemented: `conversations` + `conversation_messages` tables are source of truth; `_persist_user_message()` writes user input before processing; `_persist_assistant_message()` writes AI response before NATS publish; processing aborts if persistence fails; NATS used only for transport/notification; HTTP catch-up reads from Postgres; idempotency via unique constraint on `(tenant_id, user_id, request_id, message_type)`)**
- [ ] Unify WebSocket architecture (single gateway WS termination; remove/merge duplicate WS stacks to avoid inconsistent auth/authz/catch-up).
- [ ] Tenant-scope NATS subjects (move from attributes-only to subject namespace `aico.<tenant_id>.…`; ensure publish/subscribe enforcement follows scoping).
- [ ] Enforce streaming durability policy (stream chunks ephemeral; ensure JetStream streams/outbox subjects cannot accidentally persist chunk traffic).
- [x] **Prove ZMQ removal repo-wide (✅ COMPLETE: Zero ZMQ code usage.

### High
- [ ] Align conversation schema and lifecycle with doc (ensure `conversations` table exists/used; implement status/title/updated_at and conversation lifecycle endpoints as needed).
- [ ] Standardize error envelope on all non-2xx responses (single `{error_code,message,request_id,details}` schema; remove ad-hoc responses).
- [ ] Normalize pagination contract to `limit`/`offset` + `items`/`total` for list endpoints (or explicitly update the contract).
- [ ] Implement real `turn_number` and ordering guarantees (no stubs; deterministic replay/catch-up ordering).
- [ ] Apply gateway-wide rate limiting consistently across REST (not only WS).

### Medium
- [ ] Migrate config namespaces toward documented `aico.*` keys (eliminate drift between doc and runtime config lookups).
- [ ] Encode a single authoritative durability matrix (map each flow to core NATS vs JetStream and enforce in code).
- [ ] Narrow outbox/JetStream stream subjects (avoid overly-broad `conversation.>` streams; publish only correctness-critical final events via outbox).
- [ ] Strengthen catch-up cursor semantics (add stable ordering/tiebreak; avoid timestamp-only edge cases).

### Low
- [ ] Remove remaining legacy/no-op/deprecated endpoints and startup stubs (e.g. deprecated conversation endpoints; no-op broker startup paths).
- [ ] Refine conversation WS subscription scoping (use tenant/user subjects instead of global topic + in-handler filtering).

## Make backend stateless (completed)

### Definition of done
- Every correctness-critical state is in **Postgres** and/or **NATS/JetStream**.
- Any service process can be restarted at any time with:
  - no data loss
  - no duplicate side effects
  - no stuck workflows

### State inventory (authoritative)

| Component | State | Source of truth | Restart / scale-out requirement |
|---|---|---|---|
| Gateway | auth sessions / tokens | Postgres | stateless beyond caches; multiple replicas safe |
| Gateway | WS subscriptions / fanout | in-memory | must be recoverable from client reconnect + HTTP catch-up |
| Core backend | conversations | Postgres | required for HTTP catch-up and replay |
| Core backend | durable notifications | JetStream / outbox→JetStream | eventual delivery; idempotent consumption |
| Core backend | scheduler tasks + execution history | Postgres | unique `(task_id, run_key)` prevents duplicates |
| Core backend | scheduler job queue | JetStream work-queue | pull-consumers; at-least-once; dedupe in Postgres |
| Modelservice | inference work-in-flight | JetStream / NATS request-reply | safe redelivery; no local checkpoints |
| All services | metrics / logs / traces | OTLP + Loki/Tempo/Prometheus | never required for correctness |

### Failover tests (must exist)

Progress:
- [x] Guardrails: strict `fs_guard` blocks runtime writes outside `AICO_DATA_DIR/{runtime,cache,logs,tmp,artifacts}` (backend + modelservice entrypoints)
- [x] Config persistence: runtime overrides persist under `AICO_DATA_DIR/runtime/runtime.yaml` (tested)
- [x] Durable outbox restart/idempotency: publisher can be re-run without duplicate publishes (tested)
- [x] Scheduler job execution idempotency: multi-consumer safe via Postgres run-key dedupe (tested)
- [x] True crash/restart failover test (process-level): stop producer/worker mid-flight and assert eventual consistency
- [x] Client reconnect catch-up: Postgres-backed cursor replay via `GET /conversation/messages/catchup` (tested)

1) Durable notification flow
- Start a request that produces a final durable notification.
- Kill the producing service before publish.
- Assert the outbox fallback eventually publishes and consumer receives exactly once (idempotent).

2) Scheduler job execution flow
- Publish the same job twice (or force redelivery).
- Run with 2 worker consumers.
- Assert only one execution row is created (idempotent) and job is ACKed.

3) Client reconnect catch-up
- Start streaming.
- Disconnect client mid-stream.
- Reconnect and validate HTTP catch-up returns the final persisted result.

### Guardrails (prevent regressions)
- No correctness-critical writes to local disk.
- Local disk allowed only for:
  - explicitly configured cache/temp directories
  - non-authoritative artifacts that can be recomputed
- Enforce `tenant_id`/`user_id` scoping in all persisted rows and NATS/JetStream subjects.

## Goals / Non-Goals
- **Goal**: Single codebase and single “final-stack” architecture that runs:
  - **Local-first/offline** on consumer hardware (single node, minimal footprint)
  - **Cloud/enterprise** (HA, horizontal scale, multi-tenant)
- **Goal**: Avoid duplicated logic and avoid mixing parallel messaging stacks (e.g. ZMQ *and* RabbitMQ).
- **Goal**: Split **edge gateway** from **core backend** for perimeter hardening, rate limiting, and load balancing.

## Current Reality (as implemented)
- **Backend**: FastAPI + embedded API Gateway layer + starts a message bus broker + runs core services in-process.
- **Modelservice**: separate process, message-bus only (no HTTP), handles LLM/embeddings/NER/TTS.
- **Message bus**: central broker semantics are required for:
  - pub/sub topics
  - request/reply (`correlation_id`, `reply_to`)
  - streaming (chunks/state)

## Key Decision
- **Standardize on NATS as the message bus**.
- **Use JetStream selectively** for durable streams (work queues, replay/audit, guaranteed delivery paths).
- Keep **Protobuf payloads** and **topic taxonomy** (map topics to NATS subjects).

## Target Runtime Topology
### Local-first (single node)
- 1x backend
- 1x modelservice
- 1x `nats-server` (JetStream optional/limited)
- DBs can remain “local Docker” (Postgres/Loki/Influx) as today.

### Cloud / Enterprise (multi-node)
- N backend replicas
- M modelservice replicas (scale independently)
- 3+ node NATS cluster (+ JetStream enabled)
- Managed Postgres; metrics/logs via standard OTel pipeline

## Runtime Data Location (Local + Docker)
- Separate **configuration** from **runtime data**.
- Preferred model:
  - **Config**: mounted read-only (or baked) into containers.
  - **Runtime data**: always goes to explicit volume mounts.
- Single source of truth for paths via environment variables:
  - `AICO_CONFIG_DIR`: configuration directory (YAML, keys, policy).
  - `AICO_DATA_DIR`: runtime data directory (uploads, caches, artifacts).
- Platform defaults:
  - Keep platform-specific default directories for non-container installs.
  - Treat them as defaults only (implementation detail) when `AICO_CONFIG_DIR` / `AICO_DATA_DIR` are not set.
- Docker convention:
  - `AICO_CONFIG_DIR` → bind mount (per-environment config repo/dir)
  - `AICO_DATA_DIR` → named volume or host path (persist across restarts)
- In cloud mode, avoid correctness-critical local files in app containers; persist via Postgres/NATS/managed stores.

## Service Boundaries (recommended)
- **Gateway (edge) service (required)**
  - Owns: HTTP/WebSocket termination, TLS, authn/authz enforcement, rate limiting, request validation, request shaping.
  - Owns: user-scoped realtime fanout to clients.
  - Does **not** own: persistence, conversation/memory business logic.
- **Backend (core) service**
  - Owns: persistence, conversation engine, memory/KG orchestration, domain services.
  - Publishes requests/events to NATS; consumes results/events.
- **Modelservice**
  - Stateless inference workers consuming model requests; publishes responses/stream chunks.
- **Broker (NATS)**
  - Separate deployable process (local: single node; cloud: cluster).
- **Edge ↔ Core interface**
  - Prefer one consistent internal interface (pick one):
    - NATS request/reply + streaming subjects
    - or internal HTTP/gRPC for commands + NATS for events/streams

## Messaging Conventions
- **Subjects**: preserve hierarchical naming (existing topics → NATS subjects).
- **Request/Reply**: standardize correlation + reply subjects.
- **Streaming**: stream chunks on dedicated subjects; optionally persist via JetStream when replay is needed.
- **AuthZ** (future): enforce subject-level permissions for tenant/user scoping.

### Scheduler scalability (JetStream + Postgres)
- **Current reality**: scheduler overlap prevention is primarily **per-process** (in-memory `running_tasks` + `max_concurrent_tasks`). In multi-replica deployments this can lead to **overlapping executions** and **load spikes**.
- **Decision (for scalable scheduler)**:
  - Use **JetStream** as a durable **work-queue** for scheduler jobs (e.g. `scheduler.jobs.*`).
  - Keep **Postgres** as the system of record (task definitions + execution history) and as an **idempotency/overlap guard**.
- **Pattern**:
  - Scheduler becomes a **job producer** (enqueue due runs to JetStream).
  - One or more worker replicas become **job consumers** (pull+ack; scale horizontally).
  - Worker uses Postgres to dedupe/avoid overlap (e.g. unique execution identifier per scheduled run); redeliveries are safe and simply `ACK` after detecting duplicates.
- **Backpressure / coalescing**:
  - Use JetStream consumer limits (e.g. `max_ack_pending`) and worker concurrency caps.
  - Coalesce misfires: if a task is already running, avoid enqueueing unbounded backlogs; allow "skip" or "coalesce to one pending" policies per task.

## Public API Specification (frontend-independent)

### Canonical contract
- **OpenAPI is canonical**: the public contract is the generated OpenAPI document + Swagger UI.
- **HTTP is mandatory**: every feature exposed to external frontends must be reachable over HTTP APIs documented in OpenAPI.
- **WebSocket is adjunct**: WS only for realtime delivery; it must always have an HTTP catch-up equivalent (see below).

### Base URL + versioning
- **Base path**: `/api/v1`
- **Breaking changes**: only in a new major path (`/api/v2`). No breaking changes inside the same major.

### Content types
- **Requests**: `Content-Type: application/json`
- **Responses**: `application/json` (binary payloads are referenced by URL and fetched separately).

### Authentication + identity
- **Auth**: `Authorization: Bearer <jwt>`
- **Identity claims (target)**: JWT contains `tenant_id` + `user_id` (and optional roles/permissions).
- **Authorization**:
  - Every request is authorized within caller’s `tenant_id`.
  - User-scoped resources require `user_id` ownership/membership checks.
  - Admin endpoints require admin role/permissions.

### Required headers
- **Tracing**: request may include `x-request-id`; server returns `x-request-id`.
- **Client identity (target)**: `x-client-id`, `x-session-id` (used for logging/rate limits).
- **Idempotency (target)**: `Idempotency-Key` on side-effecting endpoints (create/submit/transition).

### Error model (target)
- Non-2xx responses must return a consistent JSON envelope:
  - `error_code` (stable string)
  - `message` (human readable)
  - `request_id`
  - optional `details` (object)

### Pagination (target)
- List endpoints use `limit` + `offset`.
- Responses return `items` + `total` (and echo `limit`/`offset`).

### Realtime + catch-up rule
- WebSockets provide realtime notifications only.
- Clients must be able to fully reconstruct state after reconnect using HTTP:
  - conversations: fetch messages since cursor (`message_id`/timestamp)
  - interactions: list/detail endpoints (source of truth in Postgres)
  - scheduler: list executions + status endpoints

### Current API surface (v1 route groups)
- The backend currently mounts these route groups under `/api/v1/*`:
  - `health`, `echo`, `users`, `users-sessions`, `admin`, `logs`, `conversation`, `interactions`, `memory-album`, `kg`, `behavioral`, `emotion`, `tts`, `agency`, `system`, `operations`, `scheduler`, plus misc `memory`/`ams` routes.

### WebSocket endpoints (current)
- `GET /api/v1/conversation/ws`
- `GET /api/v1/scheduler/ws/events`

### Public-API readiness gaps (must close)
- **WebSocket authentication**: WS endpoints must authenticate (JWT/session) at handshake and enforce user/tenant scoping.
- **Identity normalization**: standardize on `tenant_id` + `user_id` naming in tokens, payloads, and DB.
- **OpenAPI hygiene**: ensure all endpoints have stable request/response models and avoid ad-hoc `dict` responses.
- **Idempotency enforcement**: gateway must enforce `Idempotency-Key` on all side-effecting endpoints and document retry semantics.
- **Error envelope**: replace mixed patterns (`{"success": false}` vs raw `detail`) with one documented schema.

## State / Storage Implications
- LMDB and local Chroma are not compatible with horizontal scaling and enterprise multi-tenancy.
- Use one storage *conceptual* architecture with different sizing/topology per environment (not different code paths).
- Recommended replacements:
  - **Working memory (LMDB replacement)**
    - Prefer **Postgres tables** for correctness + single source of truth.
    - Add **Redis** only as an optional cache/accelerator once there is evidence it is needed.
  - **Vector store (Chroma replacement; implemented)**
    - Prefer **Postgres + pgvector** for “single stack” local + cloud.
    - Cloud: managed Postgres + pgvector; Local: the same Postgres container with pgvector enabled.
- Rule: backend instances must be stateless; no correctness-critical state in local files.

## Postgres-first Policy
- Default stance: consolidate state into **Postgres** until there is strong evidence a specialized tool is required.
- Expected gains:
  - single operational surface (backup/restore, encryption, migrations)
  - easier multi-user / multi-tenant scoping (`tenant_id`, `user_id`, `conversation_id`)
  - stateless backend replicas become feasible
- Expected tradeoffs:
  - higher latency than LMDB for hot reads (mitigate with indexes + retention; cache only if proven necessary)
  - vector scale limits vs dedicated vector DBs (start with pgvector; swap behind an interface if ever needed)

## Multi-user Readiness (A + B)
- Must support both:
  - **A)** multi-account local deployments
  - **B)** enterprise multi-tenant deployments
- Required changes (high-level):
  - WebSocket auth is mandatory; user-scoped subscriptions.
  - Resource-level authorization beyond “auth only”.
  - Tenant/user scoping across message subjects and persistence.

## Tenancy Model (decision)
- **Decision**: start with **shared Postgres DB + shared schema** and enforce isolation via `tenant_id` + authz.
- **Definitions**:
  - **Deployment**: one installed/running AICO stack (ops boundary).
  - **Tenant**: top-level data + authorization boundary (org/workspace).
- **Enterprise installs**: typically a dedicated deployment with exactly **one tenant** (so `tenant_id` is constant, but still present).

### Data model rules
- All authoritative tables include **`tenant_id NOT NULL`**.
- Primary/unique keys are scoped by tenant where appropriate (e.g. `UNIQUE(tenant_id, conversation_id)`).
- Consider Postgres **Row Level Security (RLS)** later as a defense-in-depth option; do not require it to ship.

### Authn/Authz rules
- JWT/session identity includes `tenant_id` and `user_id`.
- Gateway enforces:
  - caller can only act within their `tenant_id`
  - subject-level publish/subscribe permissions (future: NATS subject ACLs)

### NATS subject scoping
- Subjects are tenant-scoped (examples):
  - `aico.<tenant_id>.conversation.*`
  - `aico.<tenant_id>.interaction.notifications.<user_id>`
- Keep `tenant_id` explicit even for local installs (single tenant) to avoid codepath divergence.

## Virtual Entity Model: Agents (decision)
- **Goal**: AICO can act as a stable, identifiable “virtual companion / virtual employee” with its own history and state.
- **Decision**: model a globally unique **Agent** (`agent_id`) plus per-tenant **membership/context**, with strict tenant boundaries.

### Identity and scope
- **Agent identity**: `agent_id` is globally unique (UUID). This is the “person”.
- **Tenant membership**: an agent participates in a tenant via `agent_memberships(tenant_id, agent_id, role, permissions, policy_flags)`.
- **Conversations**:
  - a conversation/thread has participants: users and agents.
  - each message has a single author: `actor_type` (user/agent/system) + `actor_id`.

### State and memory boundaries
- **Emotional/agency state**: **tenant-scoped** (decision 1B)
  - store state as `(tenant_id, agent_id, ...)` so “work self” and “private self” do not leak.
- **Learning policy**: **explicit-only by default** (decision 2B)
  - tenant agents learn only from:
    - explicitly enabled/training-marked conversations, and/or
    - designated tenant sources (docs/KB), and/or
    - explicit user consent signals.
- **Local/single-user override**: provide onboarding-friendly config that makes it trivial to enable “learn from all conversations” for private setups.

### Agent membership policy (decision)
- **Decision**: tenants control membership.
  - Default: membership requires tenant admin approval.
  - Optional: tenant can be configured “open” (auto-approve) for public communities.

## Configuration Structure (onboarding-friendly)
- **Goal**: config toggles must be self-explanatory, grouped, and suitable for onboarding prompts.

### Final config keys (full namespaces)
#### Conversation storage + delivery
- `aico.conversations.storage.driver` = `postgres`
- `aico.conversations.storage.persist_stream_chunks` = `false`
- `aico.conversations.delivery.require_idempotency_key` = `true`

#### Idempotency
- `aico.idempotency.http.header_name` = `Idempotency-Key`
- `aico.idempotency.enforcement.scope` = `tenant_user`  (meaning `(tenant_id, user_id, request_id)` must be unique)

#### Event publication reliability
- `aico.events.publication.mode` = `outbox`  (alternatives: `best_effort`)
- `aico.events.outbox.poll_interval_ms`
- `aico.events.outbox.batch_size`

#### Agents (virtual entity) + membership
- `aico.agents.identity.global_agent_id_enabled` = `true`
- `aico.agents.membership.approval.required` = `true`
- `aico.agents.membership.approval.mode` = `admin`  (alternatives: `open`)

#### Learning (two booleans only)
- `aico.learning.tenant.enabled` = `true`
- `aico.learning.user.enabled` = `true`

Semantics:
- If `aico.learning.tenant.enabled = false`: learning is disabled globally for the tenant (no memory/KG consolidation, no preference updates, no indexing).
- If `aico.learning.tenant.enabled = true` and `aico.learning.user.enabled = false`: disable user-specific learning for that user (their private companion state/memory does not evolve from new interactions).
- Precedence: tenant-level disable overrides user-level enable.

Wording (final):
- **What “learning” means in AICO**: writing **derived state** from interactions (memory consolidation, KG extraction/indexing, behavioral confidence updates, self-reflection/lesson application). It is **not** cloud LLM fine-tuning.
- **Tenant kill-switch** (`aico.learning.tenant.enabled`): “This workspace does not adapt. It may record conversations/feedback for product operation, but will not use them to update memory/KG/preferences/behavior.”
- **User kill-switch** (`aico.learning.user.enabled`): “Do not adapt based on *my* interactions. My messages/feedback may be stored as raw records, but must not change the agent’s memory/KG/preferences/behavior because of me.”
- **Public/enterprise agent expectation**: expose a user-facing control labelled **“Allow the agent to learn from me”** that maps to `aico.learning.user.enabled`, but only if tenant policy allows learning.

#### Onboarding presets (boolean-only)
- `aico.onboarding.private_companion.apply_defaults` = `false`
- `aico.onboarding.team_workspace.apply_defaults` = `false`
- `aico.onboarding.enterprise.apply_defaults` = `false`

## Migration Steps (incremental)
1) **Make the bus abstraction real**: harden `MessageBusClient` as the single API boundary.
2) **Add NATS transport** behind `MessageBusClient` (keep Protobuf + topic taxonomy).
3) **Run broker out-of-process**:
   - local: docker-compose service for NATS (optionally started by lifecycle tooling)
   - cloud: NATS cluster deployment
4) **Replace ZMQ broker usage** and remove ZMQ-specific assumptions from services.
5) **Introduce durable streams** (JetStream) only where needed (jobs/events/audit/replay).
6) **Split Gateway service** from Core backend:
   - gateway: edge concerns only
   - core: persistence + domain logic
7) **Replace LMDB working memory** with Postgres-backed working memory.
8) **Replace Chroma with Postgres + pgvector**.
9) **Make backend stateless** (all state in Postgres/Redis/NATS).

## Open Questions
- Which topics/flows must be **durable** (JetStream) vs **ephemeral** (core NATS)?
- Tenancy model details (org/project/user scoping) and required subject naming conventions.

## Durability (JetStream) vs Ephemeral (core NATS)
- **Reality check (today)**:
   - Postgres schema contains **AMS trajectories** (`ams_trajectories.user_input` / `ai_response`) and other derived memory tables, but **no canonical conversation message log** table.
   - Conversation “truth” is transitioning to **Postgres-backed conversation tables**; LMDB is not used for correctness-critical storage.
- **UX requirement**: clients must be able to **catch up** and reflect backend reality after reconnect/restart.

### Recommended durability matrix (target)
- **Conversation user input**: **JetStream durable**
  - Rationale: avoid loss when backend replicas restart; enables horizontal scaling.
- **Conversation AI response (final)**: **JetStream durable**
  - Rationale: required for deterministic client catch-up without relying on timing-sensitive pub/sub.
- **Streaming chunks**: **Ephemeral**
  - Rationale: delivery artifact; correctness is the final response.
- **State streaming / telemetry**: **Ephemeral**
  - Rationale: monitoring; replay not correctness-critical.
- **Background jobs dispatch (heavy lifting)**: **JetStream durable (work queue)**
  - Rationale: scalable workers; isolates heavy work from core service responsiveness.
- **Interaction notifications**: **Ephemeral by default**
  - Rationale: source of truth is Postgres (`interaction_requests`, `interaction_events`);
    gateway can catch up by querying DB.

### Catch-up strategy (target)
- **Clients**: treat WebSockets as realtime, but always support **resync** via:
  - durable streams (conversation input/final response), and/or
  - DB reads for entities that are authoritative in Postgres (interactions, task/execution status).

## Distributed Workers (heavy-lifting priority)
- Introduce a worker pool consuming from **JetStream work-queue streams** for:
  - memory consolidation
  - KG extraction / indexing
  - embedding generation (if not done inline with requests)
- Core backend publishes jobs with stable ids (`job_id`, `correlation_id`) and stores authoritative job state in Postgres.
- Workers:
  - ack on completion (at-least-once delivery + idempotent handlers)
  - persist results to Postgres (and publish optional completion events)

## Decision: Conversation catch-up uses Postgres (source of truth)
- **Decision**: conversation state (messages/turns) must be authoritative in **Postgres**, not reconstructed from JetStream.
- **Role of JetStream**:
  - durable transport for inputs/results (at-least-once), and
  - work queues for background jobs,
  - not the primary event store for long-term conversation history.

### Implications (target)
- Add a canonical Postgres schema for conversations (minimum):
  - `conversations` (id, user_id/tenant_id, created_at, updated_at, title, status)
  - `conversation_messages` (single table) (message_id, tenant_id, conversation_id, agent_id, actor_type, actor_id, content, metadata_json, created_at, correlation_id, request_id)
  - indexes for `(conversation_id, created_at)` and `(user_id, created_at)`.
- Gateway catch-up semantics:
  - WebSocket reconnect triggers DB read: “messages since `last_seen_message_id`/timestamp”.
- Delivery semantics:
  - assume **at-least-once** (NATS/JetStream) and implement **idempotency** using `message_id` / `idempotency_key`.
- Publish reliability:
  - for DB→bus consistency, prefer an **outbox pattern** (transactional insert to `outbox_events`, async publisher) for critical notifications.

### Message schema choice (decision)
- **Decision**: keep `conversation_messages` as a **single table** with `metadata_json` (JSONB) for tool calls, attachments references, model metadata.
- Split into additional tables only if there is proven need (analytics, very large payloads, attachment blobs).

### Idempotency (decision)
- **Decision**: idempotency is anchored at the **HTTP/gateway boundary**.
  - Client supplies `Idempotency-Key` (preferred) or gateway generates one.
  - Persist as `request_id` and enforce uniqueness (at least): `UNIQUE(tenant_id, user_id, request_id)`.
  - Propagate `request_id`/`correlation_id` through NATS messages and DB writes.

### Outbox usage (decision)
- **Why**: prevents inconsistencies where DB commit succeeds but publish fails (or vice versa).
- **Decision**: use **outbox** for correctness-critical state changes that must be observable to clients/services (e.g. conversation final response events).
