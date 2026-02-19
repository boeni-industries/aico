# WIP: Backend Architecture Refactor (Local-first + Cloud/Enterprise)

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

## State / Storage Implications
- LMDB and local Chroma are not compatible with horizontal scaling and enterprise multi-tenancy.
- Use one storage *conceptual* architecture with different sizing/topology per environment (not different code paths).
- Recommended replacements:
  - **Working memory (LMDB replacement)**
    - Prefer **Postgres tables** for correctness + single source of truth.
    - Add **Redis** only as an optional cache/accelerator once there is evidence it is needed.
  - **Vector store (Chroma replacement)**
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
8) **Replace Chroma** with pgvector (or a managed vector DB later, if needed).
9) **Make backend stateless** (all state in Postgres/Redis/NATS).

## Open Questions
- Which topics/flows must be **durable** (JetStream) vs **ephemeral** (core NATS)?
- Tenancy model details (org/project/user scoping) and required subject naming conventions.

## Durability (JetStream) vs Ephemeral (core NATS)
- **Reality check (today)**:
  - Postgres schema contains **AMS trajectories** (`ams_trajectories.user_input` / `ai_response`) and other derived memory tables, but **no canonical conversation message log** table.
  - So the closest thing to “conversation truth” is currently **LMDB working memory** (plus optional trajectory logging for behavioral learning).
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
