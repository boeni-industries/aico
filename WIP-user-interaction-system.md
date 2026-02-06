---
description: Unified AICO → User interaction request system (approvals + questions + choices) with consumer + studio contracts
status: WIP
---

# WIP: AICO → User Interaction Request System

## Purpose
AICO needs a general-purpose, auditable, secure **interaction request** system for any AICO-initiated interaction that requires a user response.

This includes:

- Approvals / confirmations (explicit consent required before execution).
- Questions / clarifications (AskUserSkill, proactive prompts).
- Choices (multiple options, pick one).
- Acknowledgements (user confirms they saw something).

It must handle cases where:

- An action should be proposed automatically but must not execute without explicit user consent.
- An action should only be executed during off-hours.
- Elevated permissions are required (admin/operator flows).

## Goals
- One backend mechanism for *all* user interactions.
- A single state machine + audit trail.
- Idempotent and safe retries.
- Explicitly supports two frontend systems:
  - Client app (Flutter, `/frontend`)
  - AICO Studio (admin UI, `../aico-studio`)
- Backwards-compatible integration with existing proactive conversation initiation.

## Non-goals
- Implementing full UI.
- Designing the entire policy/risk engine (this system is the output target for policy decisions).

---

# Scope: Which skills create interaction requests?

## Skills that directly create user interactions
These skills already implement “AICO asks user / starts dialogue” semantics and should map to `interaction_type=question|dialogue`.

- `ask_user` (`AskUserSkill`)
  - Creates a persistent pending initiation and publishes `conversation/aico/initiate/v1`.
  - Expected answer types: `text`, `yes_no`, `choice`, `number`.

- `initiate_conversation` (`InitiateConversationSkill`)
  - Creates a proactive initiation and publishes `conversation/aico/initiate/v1`.
  - Expected answer type: `dialogue`.

## Skills that are not interactions but require user consent
These should map to `interaction_type=approval` when `execution_policy != auto`.

In the current codebase, this primarily applies to **remediation / service** skills with `safety_level != low` (default policy becomes `needs_user_consent`). Examples:

- `maint.modelservice.stabilise` (high safety)
- `maint.agency.recover_stalled_plans` (medium safety)
- Database maintenance skills (`vacuum`, `archive`, compaction) (medium safety)

Notes:

- The canonical signal is `Skill.execution_policy`.
- `IssueDetectionService` already gates autonomous execution based on `execution_policy`.

---

# Core Concepts

## Interaction Request
An **Interaction Request** represents an AICO-initiated interaction and the user’s response.

It contains:

- A human-facing summary (title, description, impact).
- An optional machine-executable payload (execute after approval).
- Constraints (expiry, off-hours window, required scopes/roles).
- Interaction-specific prompt/answer schema.

## Enforcement
Any consent gating must be enforced at **execution time**, not only at request creation time.

---

# Frontend Consumers

## Client app (Flutter, `/frontend`)
Responsibilities:

- Show user-scoped interaction inbox for the signed-in user.
- Render interactive prompts (approve/reject, answer question, choose option).
- Optionally render certain interaction requests as chat-thread messages.
- Show user-visible history (limited), without exposing sensitive cross-user data.

The client should generally not need to display the full raw audit payload; it should display a human-readable summary plus relevant timestamps and the current status.

## AICO Studio (Admin UI, `../aico-studio`)
Responsibilities:

- Cross-user visibility: list/filter interaction requests for *all* users.
- Detail view includes:
  - full current state
  - immutable execution payload (where applicable)
  - full `interaction_events` timeline (audit log)
- Operator intervention:
  - approve on behalf of user (when allowed)
  - cancel (emergency stop / stale proposal cleanup)

Studio must always show:

- who acted (user vs admin)
- when they acted
- the reason (mandatory for admin actions)

Studio must be able to show the full audit trail of any execution sequence that is gated by, or otherwise associated with, an interaction request. This includes end-to-end traceability across:

- the interaction request creation
- every decision (user/admin) and its metadata
- the resulting plan/skill execution attempts
- execution outcomes (success/failure) and failure details

---

# Data Model (Backend)

## Table: `interaction_requests`
Minimal recommended columns (names can be adapted to current schema conventions):

- `interaction_id` (uuid/string pk)
- `user_id`
- `created_at`, `updated_at`
- `status`
- `expires_at` (nullable)

### Classification / routing
- `category` (e.g. `self_healing`, `security`, `data_management`)
- `source` (e.g. `issue_detection`, `agency`, `manual_ui`)
- `severity` (optional)

### Human-facing content
- `title`
- `description`
- `impact` (optional)
- `proposed_by` (e.g. `system`, `agency`, `user:<id>`)

### Policy / constraints
- `execution_policy` (enum: `auto`, `needs_user_consent`, `off_hours_only`)
- `off_hours_window_json` (optional)
- `required_scopes_json` (optional)

### Optional executable payload (immutable once pending)
- `action_type` (e.g. `agency.plan.execute`, `agency.skill.invoke`)
- `action_payload_json`
- `idempotency_key` (optional)

### Interaction-specific payload
- `interaction_type` (enum: `approval`, `question`, `choice`, `ack`, `dialogue`)
- `prompt` (optional)
- `expected_answer_type` (optional: `text`, `yes_no`, `choice`, `number`, `dialogue`)
- `options_json` (optional)

### Resolution / audit
- `resolved_at` (nullable)
- `resolved_by` (nullable)
- `resolution_reason` (nullable)
- `decision_metadata_json` (nullable)

### Linkage to execution sequences (for Studio audit)
- `correlation_id` (optional) — stable trace id used across logs/events/execution
- `related_entity_type` (optional) — e.g. `goal`, `plan`, `plan_execution`, `skill_invocation`, `issue`
- `related_entity_id` (optional)

## Table: `interaction_events`
Append-only audit log.

- `event_id`
- `interaction_id` (fk)
- `created_at`
- `actor` (user id or `system` or `admin:<id>`)
- `event_type`
  - approval-style: `created`, `presented`, `approved`, `rejected`, `expired`, `cancelled`, `executing`, `executed`, `execution_failed`
  - question/choice-style: `created`, `presented`, `answered`, `dismissed`, `deferred`, `expired`, `cancelled`
- `details_json`

---

# State Machine

## Status values
Recommended:

- `pending`
- `approved` | `rejected` (approval-type)
- `answered` | `dismissed` | `deferred` (question/choice-type)
- `expired`
- `cancelled`
- optional execution states: `executing` → `executed` | `execution_failed`

Constraints:

- Once `pending`, `action_payload_json` must not change.

---

# Backend API Contract

## Consumer vs Studio access
Two frontend surfaces:

- **Consumer app**: user-scoped access (only `interaction_requests.user_id == current_user`).
- **Studio**: admin/operator access (cross-user) gated by explicit scopes.

## Consumer endpoints
- `GET /api/v1/interactions?status=pending&category=self_healing&limit=50`
- `GET /api/v1/interactions/{interaction_id}`
- `POST /api/v1/interactions/{interaction_id}/approve`
- `POST /api/v1/interactions/{interaction_id}/reject`
- `POST /api/v1/interactions/{interaction_id}/cancel`
- `POST /api/v1/interactions/{interaction_id}/answer`
- `POST /api/v1/interactions/{interaction_id}/execute` (optional)

## Studio (admin) endpoints
- `GET /api/v1/admin/interactions?...` (filters: `user_id`, `status`, `category`, `interaction_type`, `execution_policy`, `source`, `severity`, time ranges)
- `GET /api/v1/admin/interactions/{interaction_id}` (includes full timeline)
- `POST /api/v1/admin/interactions/{interaction_id}/approve` (on-behalf-of)
- `POST /api/v1/admin/interactions/{interaction_id}/cancel`

Admin endpoints must include `interaction_events` and should never omit the audit trail.

For Studio, the interaction detail view should also include enough linkage to render the complete execution trail (at minimum: `correlation_id` and/or `related_entity_*`).

---

# Eventing / Notifications

## Minimum viable
- Consumer polls `GET /api/v1/interactions?status=pending`

## Recommended
- WebSocket: `/api/v1/interactions/ws`
- Events:
  - `interaction.created`
  - `interaction.updated`
  - `interaction.resolved`

Studio can either use a separate admin WebSocket channel or poll admin list endpoints depending on operational/security constraints.

---

# Frontend Notes (Consumer app)

## UX
- A single “Inbox” for:
  - approvals
  - questions
  - choices

## Rendering guidance
- If `interaction_type in (question, dialogue)`:
  - Prefer chat-thread rendering *plus* inbox item.
- If `interaction_type == approval`:
  - Prefer modal/bottom-sheet + inbox item.
- Frontend can decide using:
  - `interaction_type`, `severity`, `execution_policy`, and an optional future `presentation_hint`.

---

# Frontend Notes (Studio)

- List and filter interactions across all users.
- Detail view shows:
  - current status
  - immutable payload
  - full `interaction_events` timeline
- Actions:
  - approve on behalf (when allowed)
  - cancel (emergency stop)

---

# Security

## Consumer
- Hard filter by `user_id`.

## Studio
- Separate scopes (examples):
  - `interactions:read:any`
  - `interactions:resolve:any`
  - `interactions:cancel:any`
  - `interactions:execute:any`
- All admin actions must write audit events including:
  - actor identity
  - `on_behalf_of`
  - reason

---

# Integration with existing Proactive Conversation / AskUser

Existing implementation:

- Skills:
  - `AskUserSkill` (`shared/aico/ai/agency/skills/communication/ask_user.py`)
  - `InitiateConversationSkill` (`shared/aico/ai/agency/skills/communication/initiate.py`)
- API:
  - `GET /api/v1/conversation/proactive/pending`
  - `POST /api/v1/conversation/proactive/respond`

Unification approach:

- Treat proactive initiations as `interaction_requests` with `interaction_type=question|dialogue`.
- User response resolves the interaction request.
- Keep publishing `conversation/aico/initiate/v1` for chat rendering.

Migration path:

1. Keep proactive endpoints stable.
2. Implement `interaction_requests` as canonical store.
3. Make proactive endpoints read/write through the interaction store.
4. Optionally deprecate duplicate initiation-specific storage.

---

# Conversation-first integration (text/voice) and guaranteed responses

## Objective
The primary user interaction channel is the normal user ↔ AICO conversation (text and/or voice). Interaction requests should integrate into that flow naturally while still ensuring that AICO receives the response it needs to progress a plan/goal/tool sequence.

## Principle: Interaction Request is the source of truth; conversation is a rendering
When AICO needs input/consent:

- The backend creates an `interaction_request` with `interaction_type` and prompt/constraints.
- The conversational UX (chat/voice) is the preferred rendering surface.
- The user's response must be recorded as a resolution event on the interaction request.

This allows:

- deterministic waiting/resume behavior for plans/tools
- cross-device completion
- full audit trails (Studio)

## Capturing responses from natural conversation
To integrate with normal conversation input:

- When an interaction is pending, the system should treat the next relevant user utterance as a candidate response.
- Response capture must be explicit (linked to `interaction_id`) and idempotent.

Recommended minimum backend behaviors:

- When publishing a conversation prompt, include `interaction_id` and `expected_answer_type`.
- When user sends a message, the backend checks for a pending required interaction and attempts to match/parse it as a response.
- If parsing fails, AICO asks again (same `interaction_id`), clarifying the expected answer.

## Guaranteeing progress (required vs optional interactions)
Some interactions are required for correctness (clarification, consent). Others are advisory.

The request should carry an explicit requirement level:

- required: plan/tool must not continue without resolution
- optional: missing response does not block plan/tool

If required:

- execution must pause and record a blocking state referencing `interaction_id`
- retries must re-use the same `interaction_id`
- escalation policy can be applied (e.g. notify again, remind later, Studio intervention)

## Effects on context, memory, emotion
Because prompts and responses happen inside the normal conversation:

- The prompt and the user's response should be appended to the conversation history.
- Memory extraction should treat the response like any other user message.
- Emotional state tracking should include:
  - the content of the prompt
  - the user's response and latency
  - dismissals/rejections

However, the interaction request resolution must remain authoritative even if later conversation turns diverge.

## Tool use integration (AskUser as a step)
When a tool/plan step uses `ask_user`:

- It should create or reference an `interaction_request` (question/choice).
- The step should block until the interaction is resolved (`answered`/`dismissed`/`deferred`) depending on requirement.
- The step should write execution events that link back via `interaction_id`/`correlation_id` so Studio can show the complete trace.

---

# End-to-end example: ask user for missing knowledge, then update knowledge graph

This example flow describes the expected end-to-end behavior (Client + Studio) when AICO needs a specific missing fact to progress an intention.

## Scenario
AICO knows the user's daughter's name but does not know her birthdate. It wants to learn it and persist it in the knowledge graph.

## Expected sequence

1. Agency identifies a missing fact
   - Agency observes a knowledge gap (e.g. KG node exists for the daughter but missing `birthdate`).
   - It creates a goal: "Learn daughter's birthdate".

2. Goal is elevated to an intention
   - The intention is actionable and should be tracked as a coherent execution thread.
   - A `correlation_id` is assigned for traceability.

3. Planner produces a plan
   - Plan has at least two key steps:
     - Step A: ask the user for the birthdate
     - Step B: update the knowledge graph

4. Step A executes via `ask_user`
   - Backend creates an `interaction_request`:
     - `interaction_type=question`
     - `expected_answer_type=text|number` (implementation-defined)
     - `prompt` explicitly includes daughter's name
     - `related_entity_type=goal|plan` and `related_entity_id=<id>`
     - `correlation_id=<same as intention/plan>`
     - requirement level is required (plan must not continue without the response)
   - Backend publishes a conversation prompt event including `interaction_id`.
   - Client renders it naturally in chat/voice and shows the inbox item.

5. User answers in the normal conversation (text/voice)
   - The response is captured and resolved against the same `interaction_id`.
   - The system records:
     - `interaction_events: answered`
     - the raw answer payload (as `details_json`)
     - resolution metadata (timestamps, client type)

6. Plan resumes automatically
   - Step A completes successfully with the parsed/validated birthdate.
   - Step B executes: update knowledge graph
   - KG update writes its own execution events and stores the fact so it is available for future retrieval.

7. Plan concludes
   - The plan reaches a terminal completed state.
   - Any completion summary references the same `correlation_id`.

## What AICO "knows" afterwards
Once Step B has succeeded, the daughter's birthdate must be retrievable via the knowledge system and usable by subsequent planning/conversation.

## What Studio must be able to show
For this single intention/plan, Studio must be able to show an end-to-end trace by `correlation_id`:

- the goal and intention metadata
- the plan and step list
- the `interaction_request` and full `interaction_events` timeline
- the plan execution timeline (including the pause/wait while pending)
- the knowledge graph update execution (success/failure)
- final plan completion state
