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
