# AICO

---
> [!IMPORTANT]
> IMPORTANT NOTICE: AICO  is now hosted on Gitoro. You find the repository at:
> - **Gitoro**: https://gitoro.com/boeni-industries/aico
> 
> - AICO will continue to be avaiable open source with the same license. We are just moving our repositories to Europe.
---




AICO is an **open-source, local-first AI companion stack**. It’s built for long-lived relationships, and it’s designed so your data stays under your control.

At its core, AICO is a system with memory, emotion simulation, and agency. The goal is a companion that can hold continuity over time, take initiative, and still stay inspectable and operable.

## Links

- **Discord**: https://discord.gg/4tGyGtbCPt
- **Homepage**: https://boeni.industries/aico
- **Docs**: https://boeni-industries.github.io/aico/welcome/

## Commercial offerings

The AICO core in this repository is open source and fully usable on its own.

For teams and organizations, we offer **Pro** and **Enterprise** editions that add capabilities around operating AICO at scale (deployment support, administration, observability, and advanced workflows). A key part of that offering is a **Studio** application for developers and operators: a UI for inspecting and controlling the running system (agency state, scheduler activity, logs/telemetry, configuration, and operational tooling).

We also provide consultancy and custom development for Pro/Enterprise users. To get in touch: https://boeni.industries/aico

Open-source contributors are welcome: improvements to the core, CLI, and architecture are upstream-first and directly shape what everyone builds on.

## Use cases

AICO is a good fit when you want a conversational system that can sustain continuity (memory), behave credibly over time (emotion simulation), and follow through (agency + scheduler) while remaining inspectable.

Examples that match AICO particularly well:

- **Personal companion with continuity**
  - Long-running conversations that build on remembered context and relationship state

- **Coaching / reflective practice**
  - Structured check-ins, journaling-style conversations, goal support, and progress follow-up driven by agency and scheduled prompts

- **Therapy-adjacent support tooling (non-clinical)**
  - Mood and interaction-state tracking, conversational support, and user-controlled memory (for applications that complement human care rather than replace it)

- **Caregiving and assisted living support**
  - Companionship plus operator visibility: summaries, behavioural signals, and a state/history you can inspect (emotion history, scheduler history, logs)

- **Training and simulation**
  - Believable role-play partners that keep context, maintain a consistent stance, and can be instrumented and replayed for iteration

- **Customer success / account companion (business)**
  - A long-lived “account context” that remembers constraints, stakeholders, and prior decisions; with operable workflows and clear auditability

- **Internal ops copilot (business)**
  - A local-first assistant embedded into internal systems, where you need strong debugging surfaces (CLI, logs, telemetry) and controllable automation (scheduler)

- **Companion-as-a-platform**
  - Build your own client experience on top of the gateway API (REST + WebSocket), while reusing AICO’s memory, agency, and model runtime services

## Architecture (high level)

```text
Clients (Flutter, your own UI, automation)
  | REST / WebSocket
  v
API Gateway (FastAPI)
  |\
  | \-> Subsystems: conversation, memory, emotion, agency, scheduler,
  |               interactions, knowledge graph
  |\
  | \-> Storage: LMDB, ChromaDB, PostgreSQL (when configured)
  |
  | ZeroMQ + protobuf (internal bus)
  v
modelservice
  - Ollama (LLM runtime)
  - Transformers (NLP helpers)
  - TTS engines

Observability
  - Logs: Loki
  - Metrics/telemetry: InfluxDB (Pro/Enterprise)
```

Details:

- **Transformers (NLP helpers)**
  - Entity extraction (GLiNER): `urchade/gliner_medium-v2.1`
  - Sentence embeddings: `sentence-transformers/paraphrase-multilingual-mpnet-base-v2`
  - Intent classification (NLI): `joeddav/xlm-roberta-large-xnli`
  - Sentiment/emotion classifiers (e.g. multilingual BERT sentiment)

## What AICO can do today

You can run AICO locally (including the LLM) and offline (unless you give it access to the internet) to have ongoing conversations that build on memory and context, and you can inspect what the system is doing (and why) through the CLI.

AICO ships with a multi-platform Flutter client that connects to the gateway for chat, streaming responses, and interaction prompts. If you’re building your own experience, you can integrate your own frontend (or automation) against the backend components via REST + WebSocket.

Beyond chat, AICO is built to be operable and inspectable. You can inspect and manage memory stores, query and analyze the knowledge graph, explore what skills/tools are registered, review scheduler history, and use logs + time-series telemetry to understand behaviour and performance.

### Conversation, memory, and knowledge

AICO supports conversational interactions backed by a human-like multi-layer memory system. Working memory keeps short-term conversation context, semantic memory provides retrieval, and a knowledge graph can extract and query entities and relationships. For user-curated recall, AICO also exposes a **Memory Album** API for saving and managing meaningful moments.

Working memory is designed for speed and recency: it stores active conversation context in **LMDB** with TTL-based expiry. Semantic memory stores conversation segments in **ChromaDB**, and retrieval uses hybrid ranking (semantic similarity + keyword relevance) so you can get both “meaning” matches and concrete keyword hits.

On top of this, the knowledge graph can extract and manage entities/relationships and supports richer inspection and analysis (stats, traversal, temporal history, and graph insights). The Memory Album complements this by letting users explicitly curate “keep this” moments, along with notes/tags and revisit metadata.

These subsystems are not “hidden behind the model”: you can inspect them directly.

- CLI: `aico lmdb ...`, `aico chroma ...`, `aico kg ...`
- API: Memory Album (`/api/v1/memory-album/...`)

### Emotion simulation

AICO includes an emotion simulation loop (C-CPM-inspired appraisal) that runs on conversation turns. It appraises incoming user input and incorporates sentiment analysis (requested from the modelservice) to produce a compact emotional state, then publishes it so other components can react (for example: conditioning response style and coordinating expression).

The engine is built around a 4-stage appraisal flow (relevance → goal impact → coping capability → social appropriateness) with explicit safety hooks (e.g. crisis indicators). It also models **emotional inertia** so state evolves smoothly across turns instead of snapping instantly.

Emotional state is persisted and logged over time. That gives you a time-series you can inspect to understand longer arcs and sustained periods (what you might think of as “episodes”), and to correlate state changes with specific conversation moments.

The system tracks:

- A **subjective feeling** label (e.g. calm, curious, warm concern)
- **Mood dimensions** (valence/arousal/intensity)
- **Expression parameters** that can shape interaction style (warmth, directness, formality, engagement, closeness, care focus)

It’s designed to be operable and inspectable:

- CLI: `aico emotion status`, `aico emotion history`, `aico emotion stats`, `aico emotion export`, `aico emotion reset`
- API: `/api/v1/emotion/current` and `/api/v1/emotion/history` (with filters like time ranges and feeling)

Note: there is scaffolding to integrate explicit user emotion detection signals; when enabled, those signals can feed into appraisal.

### Agency and proactive behavior

The agency system is structured (and inspectable) rather than being a black box. In AICO, agency is expressed as **goals** that compete and get prioritized, **intentions** that represent what the system is currently committing to, and **plans** that break work into executable steps.

Agency is designed to be proactive. When the stack is running, scheduled tasks can scan for follow-ups (e.g. checking in on inactive goals) and trigger proactive actions while you’re offline. Proactive actions are surfaced as events and interaction requests so they remain reviewable.

Execution is grounded in two registries:

- **Skills**: higher-level capabilities the agent can select and run (e.g. conversation analysis, memory search, knowledge graph updates, maintenance/remediation workflows).
- **Tools**: concrete, invokable operations with explicit inputs/outputs and safety metadata (e.g. database checks, service health probes, remediation actions).

Agency is also constrained and instrumented: AICO includes a values/ethics layer with policies and user consent surfaces, and it logs events so you can review what happened and how decisions were made.

This layer is observable and operable:

- CLI: `aico agency ...`, `aico skills ...`, `aico tools ...`
- API: `/api/v1/agency/...` (intentions, goals, plans/steps, executions, policies/consent, reflections, lessons, and skill performance)

### Interaction requests

When AICO needs explicit user input (choices, approvals, structured prompts), it can produce interaction requests that flow end-to-end through storage, message bus, and WebSocket notifications.

### Speech

Text-to-speech is provided via the modelservice, with multiple configurable engines (including **XTTS v2**, **Piper**, and **Kokoro**).

### Security and privacy

AICO is designed around local-first operation. Secrets and keys are managed via the system keyring, the internal message bus transport is encrypted, and API endpoints use JWT authentication.

For operational visibility, the stack includes log tooling (Loki) and optional time-series telemetry (InfluxDB in Pro/Enterprise). The CLI exposes commands to query those signals while you iterate.

## How you use AICO

The recommended workflow is CLI-first: you start/stop services, check health, and inspect subsystems from the CLI. For interactive use you talk to the gateway (directly via HTTP/WebSocket, or through the Flutter client). For automation you call the REST API.

## The CLI (a first-class tool)

The AICO CLI is a diagnostic and operations interface for the stack. It’s built around Rich tables and a command surface that mirrors AICO subsystems.

It can:

- Start/stop services and verify health (`gateway`, `modelservice`)
- Inspect internal state (agency, emotion, scheduler, memory stores, knowledge graph)
- Manage security and credentials (master password, keyring-backed secrets, roles)
- Query logs and telemetry (Loki + InfluxDB)
- Provision dev infrastructure (Postgres/InfluxDB) with derived credentials (`deploy`)
- Test and monitor the internal message bus (`bus`)

Command groups you’ll use a lot:

- **Core ops**: `aico gateway ...`, `aico modelservice ...`, `aico scheduler ...`
- **Agency runtime**: `aico agency ...`, `aico skills ...`, `aico tools ...`
- **Memory & knowledge**: `aico lmdb ...`, `aico chroma ...`, `aico kg ...`
- **Security & config**: `aico security ...`, `aico config ...`
- **Observability**: `aico logs ...`, `aico influx ...`

Examples:

```bash
# Get oriented
uv run aico --help

# Service lifecycle + health
uv run aico gateway start --dev
uv run aico modelservice start
uv run aico gateway status
uv run aico modelservice status

# Inspect what the agent can actually do
uv run aico skills ls
uv run aico tools ls

# Investigate behaviour and state
uv run aico emotion status
uv run aico scheduler ls
uv run aico scheduler history
uv run aico kg status
uv run aico lmdb status

# Operational visibility
uv run aico logs tail --service backend --level info
uv run aico influx status
```

Common entry points:

- `aico gateway ...` for the API gateway
- `aico modelservice ...` for model runtime (Ollama + NLP helpers + TTS)
- `aico agency ...` for inspecting the agentic layer
- `aico scheduler ...` for scheduled tasks and execution history
- `aico skills ...` to list/inspect/run agency skills
- `aico tools ...` to list/inspect/run agency tools
- `aico interactions ...` for interaction requests
- `aico logs ...` and `aico influx ...` for operational debugging and telemetry

If you want to get value quickly, treat AICO like a running system: start services, verify health, then explore what’s registered and available (skills/tools) before you dive into code.

### Operations from the CLI (examples)

```bash
# Service health
uv run aico gateway status
uv run aico modelservice status

# Agency: inspect and observe
uv run aico agency status --user system_user
uv run aico agency goals --user system_user
uv run aico agency plans --user system_user

# Skills & tools: discover and run
uv run aico skills ls
uv run aico tools ls

# Scheduler: list tasks and view execution history
uv run aico scheduler ls
uv run aico scheduler history
uv run aico scheduler trigger maintenance.health_check

# Logs & telemetry
uv run aico logs tail
uv run aico influx status
```

## Quickstart (development)

Prereqs:

- Python **3.13+**
- `uv` installed

Install dependencies:

```bash
cd cli
uv sync --frozen
```

Start the backend (API Gateway) via the CLI:

```bash
uv run aico gateway start --dev
```

Start modelservice (Ollama + NLP + TTS via ZMQ) via the CLI:

```bash
uv run aico modelservice start
```

Optional: verify services are up:

```bash
uv run aico gateway status
uv run aico modelservice status
```

Direct Python entrypoints (debug/dev only):

```bash
uv run python backend/main.py
uv run python modelservice/main.py
```

Use the CLI:

```bash
uv run aico --help
uv run aico gateway status
uv run aico agency status --user <uuid>
```

## Deployment notes

- **Services**: the stack is split into an API Gateway and a separate modelservice. Most interactive features assume both are running.
- **Storage**: working memory and semantic memory are stored locally (LMDB + ChromaDB). The gateway also uses PostgreSQL-backed subsystems (e.g. scheduler and agency state) when configured.
- **Observability**: logs can be queried via Loki. Metrics/telemetry can be stored in InfluxDB in Pro/Enterprise deployments.
- **Offline**: AICO can run fully offline; network access is only used when you configure external integrations.

## Scheduler (background automation)

AICO includes a task scheduler to run background maintenance and system workflows. Tasks are managed as first-class entities (create/update/enable/disable/trigger) and have execution history, results, and error reporting.

Use `aico scheduler ...` to list tasks, trigger runs, and inspect history.

## How AICO works (high level)

AICO is split into services and libraries so that components can evolve independently.

- The **API Gateway** (FastAPI) provides REST endpoints for conversations, memory, agency, knowledge graph, scheduler, logs, metrics, TTS, and more.
- The **modelservice** handles model-facing work over the internal message bus: Ollama integration, transformers-based NLP helpers, and TTS.
- A shared Python library (`shared/`, `aico.*`) provides common abstractions for data, security, messaging, and AI subsystems.

Internally the system is message-driven (ZeroMQ + protobuf). Storage is composed of multiple stores suited to different access patterns (working memory, vector search, and relationship knowledge).

## Security model (at a glance)

- **Auth**: API endpoints use JWT authentication.
- **Secrets**: keys and secrets are managed via the system keyring.
- **Transport**: internal message bus transport is encrypted.

## Planned / in progress

The repository contains both production-ready subsystems and work that is still evolving.
For the high-level direction, see `docs/roadmap/`.

- **Embodiment**
  - Avatar/3D presence and richer multimodal UI experiences

- **Multimodal understanding**
  - Vision and voice inputs (e.g. scene understanding, richer emotion signals)

- **Federated / multi-device**
  - Encrypted device-to-device sync and roaming

- **Community & plugins**
  - More first-party plugins and a safer plugin distribution story

## Repository layout

- `backend/` FastAPI API gateway + services
- `modelservice/` ZMQ model runtime (Ollama, transformers, TTS)
- `shared/` shared Python library (`aico.*` namespace)
- `cli/` Typer/Rich CLI
- `frontend/` Flutter client
- `proto/` protobuf contracts
- `config/` default configs and Modelfiles
- `docs/` MkDocs documentation

## Contributing

- Developer guide: `docs/guides/developer/getting-started.md`
- Guidelines: `docs/guides/developer/guidelines.md`

## License

Core (this repository): MIT (see `LICENSE`).
