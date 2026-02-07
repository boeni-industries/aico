---
description: Unified AICO → User interaction request system (approvals + questions + choices) with consumer + studio contracts
status: WIP
---

# User Interaction Request System (Implementation Specification)

## Purpose
This document specifies a complete, implementation-ready, end-to-end interaction system that unifies:

- **Approvals / confirmations** (consent gating for side effects)
- **Questions / clarifications** (blocking plan steps until information is provided)
- **Choices** (structured selection)
- **Acknowledgements** (user confirms they saw something)
- **Dialogue initiations** (proactive or intention-driven conversation prompts)

The system is the authoritative backend mechanism that allows AICO to safely progress goals and plans that depend on user input, while providing:

- deterministic pause/resume semantics
- full auditability for AICO Studio
- natural integration into conversation (text/voice)

## Goals
- One canonical persistence model for user interactions across all subsystems.
- One state machine with strict invariants and idempotent transitions.
- Runtime enforcement: no consent-gated execution without an approved interaction.
- Complete admin observability: Studio can render the full trace end-to-end.

## Non-goals
- Designing a policy/risk engine. This system is the *sink* for those decisions.

---

# Actors and Frontends

## Client app (Flutter, `/frontend`)
- User-scoped: a user can only see/act on their own interaction requests.
- Primary UX surface is the normal conversation (text/voice). Interaction requests also appear in an “Inbox”.

## AICO Studio (Admin UI, `../aico-studio`)
- Cross-user admin: can list/filter/inspect interactions for all users.
- Must always be able to show complete, end-to-end audit trails.
- Operator actions are always audited and require an explicit reason.

---

# Core Principles and Invariants

## Fail loudly (never silently)
- All invalid transitions must raise explicit errors.
- All parsing failures of user responses must produce explicit warnings and a re-prompt.

## Privacy & security
- Never log sensitive user content in plaintext logs.
- Store user-provided content only in the encrypted database.

## Deterministic idempotency
- Every interaction creation and every state transition is idempotent.
- Retries must never create duplicate pending requests.

## Execution gating is enforced at runtime
If a plan/skill execution requires user consent or a user answer:

- execution pauses and cannot proceed without a resolved interaction
- resuming uses the interaction’s canonical resolution payload

---

# Data Model (PostgreSQL)

The database schema below is the authoritative contract.

## Enums
```sql
CREATE TYPE aico_core.interaction_type AS ENUM (
  'approval',
  'question',
  'choice',
  'ack',
  'dialogue'
);

CREATE TYPE aico_core.interaction_status AS ENUM (
  'pending',
  'approved',
  'rejected',
  'answered',
  'dismissed',
  'deferred',
  'expired',
  'cancelled'
);

CREATE TYPE aico_core.interaction_requirement AS ENUM (
  'required',
  'optional'
);

CREATE TYPE aico_core.execution_policy AS ENUM (
  'auto',
  'needs_user_consent',
  'off_hours_only'
);

CREATE TYPE aico_core.interaction_event_type AS ENUM (
  'created',
  'presented',
  'approved',
  'rejected',
  'answered',
  'dismissed',
  'deferred',
  'expired',
  'cancelled',
  'execution_linked'
);
```

## Table: `interaction_requests`
```sql
CREATE TABLE aico_core.interaction_requests (
  interaction_id UUID PRIMARY KEY,

  user_id UUID NOT NULL,

  created_at TIMESTAMPTZ NOT NULL,
  updated_at TIMESTAMPTZ NOT NULL,
  expires_at TIMESTAMPTZ NULL,

  status aico_core.interaction_status NOT NULL,
  interaction_type aico_core.interaction_type NOT NULL,
  requirement aico_core.interaction_requirement NOT NULL,

  category TEXT NOT NULL,
  source TEXT NOT NULL,
  severity TEXT NULL,

  title TEXT NOT NULL,
  description TEXT NOT NULL,
  impact TEXT NULL,
  prompt TEXT NULL,

  expected_answer_type TEXT NULL,
  options_json JSONB NULL,

  execution_policy aico_core.execution_policy NOT NULL,
  off_hours_window_json JSONB NULL,
  required_scopes_json JSONB NULL,

  action_type TEXT NULL,
  action_payload_json JSONB NULL,
  idempotency_key TEXT NULL,

  correlation_id UUID NOT NULL,
  related_entity_type TEXT NULL,
  related_entity_id TEXT NULL,

  resolved_at TIMESTAMPTZ NULL,
  resolved_by TEXT NULL,
  resolution_reason TEXT NULL,
  decision_metadata_json JSONB NULL
);

CREATE UNIQUE INDEX interaction_requests_user_id_idempotency
  ON aico_core.interaction_requests (user_id, idempotency_key)
  WHERE idempotency_key IS NOT NULL;

CREATE INDEX interaction_requests_user_id_status
  ON aico_core.interaction_requests (user_id, status, created_at DESC);

CREATE INDEX interaction_requests_correlation
  ON aico_core.interaction_requests (correlation_id, created_at DESC);

CREATE INDEX interaction_requests_category_status
  ON aico_core.interaction_requests (category, status, created_at DESC);
```

Hard invariants:

- If `status='pending'`, then `resolved_at` and `resolved_by` must be NULL.
- If `action_type` is not NULL, `action_payload_json` must be non-NULL and immutable once pending.
- `correlation_id` is mandatory and must be stable across the full execution chain.

### JSON field schemas

`off_hours_window_json` schema:
```json
{
  "timezone": "Europe/Zurich",
  "start_local_time": "22:00",
  "end_local_time": "06:00",
  "days_of_week": [1, 2, 3, 4, 5, 6, 7]
}
```

Rules:

- `timezone` must be an IANA timezone string.
- `start_local_time` and `end_local_time` are 24h `HH:MM`.
- If `end_local_time` is earlier than `start_local_time`, the window crosses midnight.
- `days_of_week` is ISO-8601 weekday numbers (1=Monday .. 7=Sunday).

`required_scopes_json` schema:
```json
["interactions:resolve:any"]
```

`options_json` schema (for `interaction_type='choice'` and `expected_answer_type='choice'`):
```json
{
  "selection": "single",
  "options": [
    {"id": "allow", "label": "Allow", "description": "Proceed with the proposed action"},
    {"id": "deny", "label": "Deny", "description": "Do not proceed"}
  ]
}
```

Rules:

- `selection` is `single` or `multi`.
- Each option `id` must be unique.

`decision_metadata_json` schema (stored, not logged):
```json
{
  "client": "flutter",
  "client_version": "x.y.z",
  "device": {"platform": "ios"},
  "received_at": "2026-02-06T22:00:00Z"
}
```

## Table: `interaction_events`
```sql
CREATE TABLE aico_core.interaction_events (
  event_id UUID PRIMARY KEY,
  interaction_id UUID NOT NULL REFERENCES aico_core.interaction_requests(interaction_id) ON DELETE CASCADE,

  created_at TIMESTAMPTZ NOT NULL,
  actor TEXT NOT NULL,
  event_type aico_core.interaction_event_type NOT NULL,

  details_json JSONB NULL
);

CREATE INDEX interaction_events_interaction_id
  ON aico_core.interaction_events (interaction_id, created_at ASC);
```

---

# Backend Services

## InteractionService (authoritative domain logic)
Responsibilities:

- Create interaction requests with idempotency.
- Perform transitions (approve/reject/answer/dismiss/defer/cancel/expire).
- Validate transitions and invariants.
- Emit `interaction_events` for every mutation.
- Expose query methods for Client and Studio.

Transition rules:

- `pending` → `approved` | `rejected` | `answered` | `dismissed` | `deferred` | `expired` | `cancelled`
- Any non-`pending` status is terminal.
- `expires_at` in the past makes the request terminal `expired`.

Idempotency:

- `InteractionService.create_interaction_request(...)` uses `(user_id, idempotency_key)` unique index.
- `approve/reject/answer` are idempotent: if already in target terminal state, return the current record.

## InteractionNotifier (delivery)
Responsibilities:

- Publish a bus event whenever an interaction is created/updated.
- For conversation-first UX, publish an AICO-initiated message event that includes `interaction_id`.

Bus topics:

- `interaction/created/v1`
- `interaction/updated/v1`
- `interaction/resolved/v1`

The `interaction/resolved/v1` payload must include `interaction_id` in metadata.

---

# Agency Integration (pause/resume on interaction)

## Step execution contract
Plan steps that require user input/consent must be representable as:

- a step that *creates* an interaction request, and then
- a step that *waits* for resolution and returns the resolved payload to the plan context

## Executor behavior (hard requirement)
When executing a step that depends on an interaction:

- If there is no existing pending interaction for the step’s idempotency key, create one.
- Mark the execution as blocked with a stable reference: `blocked_on_interaction_id`.
- Do not proceed to subsequent steps.
- When the interaction resolves, resume execution deterministically using the recorded resolution.

This requires persistence of the block linkage in the plan execution/step execution tables.

## Persistence requirements for pause/resume
The execution layer must persist both:

- the fact that a plan execution is blocked
- the identity of the interaction it is blocked on

The plan execution persistence model must include the following fields at the **plan execution** level:

- `blocked_on_interaction_id` (UUID, nullable)
- `blocked_reason` (TEXT, nullable; values include `awaiting_user_answer`, `awaiting_user_consent`)
- `blocked_at` (TIMESTAMPTZ, nullable)

Additionally, the **step execution** record for the blocking step must include:

- `interaction_id` (UUID, nullable)
- `interaction_idempotency_key` (TEXT, nullable)

Hard runtime rules:

- If `blocked_on_interaction_id` is set, `execute_next_step(...)` must not execute any further steps and must return a deterministic “blocked” signal.
- When the interaction resolves, the executor must atomically:
  - clear `blocked_on_interaction_id`
  - record the resolution payload into the execution context
  - mark the blocking step as `success` or `failure` based on validation

## Correlation and audit
Every:

- interaction request
- plan execution
- step execution
- side-effecting skill invocation

must carry the same `correlation_id`.

---

# HTTP API (Client)

All endpoints require authentication.

## List
`GET /api/v1/interactions`

Query params:

- `status` (repeatable)
- `interaction_type` (repeatable)
- `category` (repeatable)
- `created_after`, `created_before`
- `limit` (default 50, max 200)
- `cursor` (opaque)

Returns: list of interaction summaries.

Response item schema:
```json
{
  "interaction_id": "uuid",
  "status": "pending",
  "interaction_type": "question",
  "requirement": "required",
  "category": "knowledge",
  "severity": "info",
  "title": "Question required",
  "description": "AICO needs this information to continue the current plan.",
  "prompt": "What is your daughter's birthdate?",
  "expected_answer_type": "date",
  "expires_at": null,
  "created_at": "2026-02-06T22:00:00Z",
  "updated_at": "2026-02-06T22:00:00Z",
  "correlation_id": "uuid",
  "related_entity_type": "goal",
  "related_entity_id": "goal_123"
}
```

## Detail
`GET /api/v1/interactions/{interaction_id}`

Returns:

- full interaction request
- full `interaction_events` timeline

Detail response schema:
```json
{
  "interaction": {"interaction_id": "uuid", "status": "pending", "interaction_type": "question"},
  "events": [
    {"event_id": "uuid", "created_at": "2026-02-06T22:00:00Z", "actor": "system", "event_type": "created", "details": null},
    {"event_id": "uuid", "created_at": "2026-02-06T22:01:30Z", "actor": "user:<id>", "event_type": "answered", "details": {"answer": "1999-12-31"}}
  ]
}
```

## Resolve (approval)
`POST /api/v1/interactions/{interaction_id}/approve`
`POST /api/v1/interactions/{interaction_id}/reject`

Body:

- `reason` (string, optional)
- `client_metadata` (object)

## Resolve (question/choice/ack)
`POST /api/v1/interactions/{interaction_id}/answer`

Body:

- `answer_type` (string)
- `answer` (json)
- `client_metadata` (object)

Validation:

- answer parsing must validate against `expected_answer_type` and `options_json`.
- invalid answers return 400 and a warning log entry.

Answer contract:

- `answer_type` must match `interaction.expected_answer_type`.
- Supported `expected_answer_type` values are:
  - `text`
  - `yes_no` (answer must be boolean)
  - `choice` (answer must be `{ "selected": ["opt_1"] }` and validated against `options_json`)
  - `number` (answer must be numeric)
  - `date` (answer must be ISO-8601 `YYYY-MM-DD`)

If validation fails:

- response status code is 400
- backend logs a warning with `interaction_id` and a non-sensitive error message
- interaction remains `pending`

## Cancel
`POST /api/v1/interactions/{interaction_id}/cancel`

---

# HTTP API (Studio / Admin)

All endpoints require admin authentication + scopes.

## Scopes
- `interactions:read:any`
- `interactions:resolve:any`
- `interactions:cancel:any`

## List
`GET /api/v1/admin/interactions`

Query params:

- `user_id`
- `status`
- `interaction_type`
- `category`
- `execution_policy`
- `source`
- `severity`
- time range filters
- pagination

## Detail
`GET /api/v1/admin/interactions/{interaction_id}`

Returns:

- full interaction record
- full event timeline
- correlation linkage fields

Admin detail must always include the full event timeline.

## Resolve / Cancel
`POST /api/v1/admin/interactions/{interaction_id}/approve`
`POST /api/v1/admin/interactions/{interaction_id}/reject`
`POST /api/v1/admin/interactions/{interaction_id}/cancel`

Body:

- `reason` (string, required)
- `on_behalf_of` (uuid, required)

Admin actions must always create an `interaction_event` with actor `admin:<id>`.

---

# Realtime delivery

## WebSocket transport (authoritative)
The current codebase already uses a dedicated WebSocket transport implemented by the API Gateway (`backend/api_gateway/adapters/websocket_adapter.py`) running on a separate port.

Canonical connection URL:

- `ws://<host>:8772/ws`

Client protocol:

- Client sends `{ "type": "auth", ... }` to authenticate.
- Client subscribes via `{ "type": "subscribe", "topic": "interaction.notifications.<user_uuid>" }`.
- Server pushes broadcasts in the form:
```json
{
  "type": "broadcast",
  "topic": "interaction.notifications.<user_uuid>",
  "data": {
    "type": "interaction.updated",
    "interaction_id": "uuid",
    "status": "pending",
    "interaction_type": "question",
    "timestamp": "2026-02-06T22:00:00Z"
  }
}
```

This transport must be reused for the interaction system. The FastAPI in-process WebSocket endpoints are not the canonical delivery mechanism and must not be used for interaction notifications.

## Interaction notification topics
The system must publish message-bus events that the WebSocket adapter forwards.

Message bus topics:

- `interaction.notifications.<user_uuid>`

The WebSocket adapter must subscribe to `interaction.notifications.*` and forward events to authenticated user connections.

## WebSocket (Studio)
Studio uses the same WebSocket transport and subscribes to admin topics.

Canonical admin subscription:

- `{ "type": "subscribe", "topic": "interaction.notifications.admin" }`

Admin events must include `correlation_id` and `user_id` so Studio can route and render cross-user timelines.

Broadcast payload schema (`data`):
```json
{
  "type": "interaction.updated",
  "interaction_id": "uuid",
  "user_id": "uuid",
  "status": "pending",
  "interaction_type": "question",
  "category": "knowledge",
  "severity": "info",
  "correlation_id": "uuid",
  "timestamp": "2026-02-06T22:00:00Z"
}
```

Admin subscriptions must be authorized by scopes. If unauthorized, the server must close the connection with an explicit error message.

---

# Legacy reuse and cleanup (mandatory)

The codebase must not contain or expose any legacy proactive initiation subsystem. The only supported mechanism is the interaction request system.

## What must be reused

- The API Gateway WebSocket transport and subscription model:
  - client subscribes to `interaction.notifications.<user_uuid>`
  - server forwards from message bus topic `interaction.notifications.<user_uuid>`

## What must be replaced

### Skill implementations

- `AskUserSkill` (`shared/aico/ai/agency/skills/communication/ask_user.py`)
  - must stop writing legacy proactive initiation records
  - must create `interaction_request` with:
    - `interaction_type='question'`
    - `requirement='required'`
    - `expected_answer_type` from inputs
    - stable `idempotency_key`
    - `correlation_id` from execution context
  - must publish to message bus:
    - `interaction.notifications.<user_uuid>` (for inbox + gating)

- `InitiateConversationSkill` (`shared/aico/ai/agency/skills/communication/initiate.py`)
  - must stop writing legacy proactive initiation records
  - must create `interaction_request` with `interaction_type='dialogue'` (typically `requirement='optional'`)

### Backend HTTP endpoints

Remove the legacy proactive endpoints and replace with interaction endpoints:

- Delete:
  - `backend/api/conversation/proactive.py`
  - any router inclusion that exposes:
    - `GET /api/v1/conversation/proactive/pending`
    - `POST /api/v1/conversation/proactive/respond`
    - `GET /api/v1/conversation/proactive/history`

- Implement:
  - `GET /api/v1/interactions`
  - `GET /api/v1/interactions/{interaction_id}`
  - `POST /api/v1/interactions/{interaction_id}/answer`
  - `POST /api/v1/interactions/{interaction_id}/approve|reject|cancel`
  - `GET /api/v1/admin/interactions` and admin detail/resolve/cancel endpoints

### Backend persistence / repositories

- Delete any legacy persistence layers and schema entries related to proactive initiation tracking.

- Introduce new repositories and UoW accessors:
  - `interaction_requests`
  - `interaction_events`

### Scheduler tasks

- Replace `backend/scheduler/tasks/proactive_conversation.py` to create `interaction_request` records instead of any legacy initiation records.
- Replace message bus publication:
  - publish `interaction.notifications.<user_uuid>`

### API Gateway WebSocket forwarding

- Extend `backend/api_gateway/adapters/websocket_adapter.py`:
  - subscribe to `interaction.notifications.*`
  - forward to:
    - per-user `interaction.notifications.<user_uuid>` subscriptions
    - admin `interaction.notifications.admin` subscriptions (authorized)

## Frontend changes (Flutter)

The Flutter app must:

- Use the interaction HTTP endpoints (`/interactions`) for inbox + resolution.
- Subscribe to `interaction.notifications.<user_uuid>`.
- Handle broadcast `data.type` values:
  - `interaction.created`
  - `interaction.updated`
  - `interaction.resolved`

The proactive UI components can remain, but their data model must be replaced from `InitiationModel` to an `InteractionModel` backed by the new API.

---

# Frontend Behavior

## Client (Flutter)
- Must render the prompt in conversation and must ensure a required interaction is answered.
- If the user tries to continue chatting without resolving a required pending interaction, the UI must keep the interaction visible and allow resolution.
- Resolution must call the interaction endpoints, not ad-hoc endpoints.

UI correctness requirements:

- If there is a `required` pending interaction, the client must keep it prominently resolvable.
- The client must never “fake-resolve” locally; it must always persist resolution via the API.

## Studio
- Must provide:
  - cross-user list with filters
  - interaction detail with full timeline
  - correlation view: jump from interaction to the associated goal/plan/execution view

Audit requirements:

- Studio must be able to query and render timelines sorted by `correlation_id`.
- Studio must show plan execution pause/resume points and the interaction that caused the pause.

---

# Error codes and logging requirements

All APIs must be explicit about failures.

Status codes:

- 400: invalid input or invalid answer payload
- 401: unauthenticated
- 403: authenticated but not allowed (user accessing another user; missing admin scopes)
- 404: interaction not found
- 409: invalid state transition (e.g. trying to approve an already answered interaction)
- 410: interaction expired (terminal)
- 422: semantic validation error (e.g. choice option not in allowed set)
- 500: unexpected error

Logging rules:

- `prompt` and user answers must be logged only at DEBUG level.
- At INFO/WARN/ERROR level, never log `prompt` or user answers in plaintext.
- Always log:
  - `interaction_id`
  - `correlation_id`
  - transition intent and outcome
  - non-sensitive failure reason

---

# End-to-end example (knowledge gap → ask → KG update)

1. Agency identifies missing fact and creates a goal.
2. Goal becomes an intention with a new `correlation_id`.
3. Planner generates a plan with:
   - Step A: ask the user for the missing fact
   - Step B: update the knowledge graph
4. Step A creates `interaction_request` (required, `interaction_type=question`, idempotency key derived from intention + fact type).
5. Client renders prompt via normal conversation; user answers.
6. Backend records `answered` event; executor resumes.
7. Step B updates KG and completes plan.
8. Studio can render the full chain by `correlation_id`, including:
   - interaction events
   - execution timeline
   - KG update success
