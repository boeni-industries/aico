---
title: Agency Component – Control, Safety & Transparency
---

# Control, Safety & Transparency

## Status

- **Implemented (v1)**: Values/Ethics evaluation primitives exist (`ValuesEthicsService`, `PolicyEffect`, `EvaluationResult`) in `shared/aico/ai/agency/values_ethics.py`.
- **Implemented (v1)**: policy + consent REST endpoints exist in `backend/api/agency/router.py` (e.g., `GET /api/v1/agency/policies`, `POST /api/v1/agency/consent`, `GET /api/v1/agency/consent`).
- **Implemented (v1)**: Values & Ethics is enforced at key decision points (e.g., `AgencyEngine.create_goal_from_curiosity_signal(...)` evaluates curiosity signals before goal creation).
- **Implemented (v1)**: append-only, queryable audit-style tables exist for governance and debugging:
  - `agency_events_log` (see `shared/aico/data/postgres/schema.sql`), and
  - `ethics_gate_audit` (see `shared/aico/data/postgres/schema.sql`).
- **WIP**: user-facing AgencyMode / PauseState / CapabilityConfig as a unified UX-configurable system, and a single UX-oriented “audit log” view that joins agency events + ethics decisions into stable, user-facing explanation artifacts.

## 1. Purpose

The Control, Safety & Transparency component defines **how far** AICO’s agency can go and **how that power is exposed and governed** at the UX/infra level. It sits **on top of** the Values & Ethics / policy engine and World Model to:

- give users clear controls over autonomy and capabilities,  
- enforce permissions and modes,  
- provide audit trails of significant autonomous actions,  
- and answer "why did you do this / why didn’t you?" in human terms.

Values & Ethics decides *what is allowed*; this component decides *how that is configured, enforced at the edges, and surfaced to humans*.

## 2. Conceptual Model

Four core responsibilities:

- **User primacy & modes** – users can configure, pause, or reset agency; choose overall safety/initiative modes.
- **Permissions & capabilities** – manage whitelists/blacklists for tools, integrations, and action classes, implemented via the structured policy engine (`agency-component-values-ethics.md`).
- **Audit logging** – record autonomous actions, triggering goals/plans, EvaluationResult decisions, tools used, and key context.
- **Explainability** – generate human-understandable explanations based on ontology-backed provenance (PerceptualEvents, Goals, WorldStateFacts, policies).

**Implementation note (v1):** the system already logs structured agency events (e.g., curiosity signals blocked/needs consent) via the agency event store. A dedicated, UX-oriented “audit log” with stable schemas and explainability artifacts is **WIP**.

**Implementation note (v1):** the underlying persistence already includes `agency_events_log` and `ethics_gate_audit`, but the “audit log” described here is a product/UX concept that would sit on top of these raw logs.

## 3. Data Model (Conceptual)

- **AgencyMode**  
  - `mode` ∈ {cautious, balanced, experimental} (per-user, per-install).  
  - Maps to different default PolicyProfiles and resource/initiative caps.

- **CapabilityConfig**  
  - Per tool/integration/action-class:  
    - `capability_id`, `type` (tool, integration, action_class),  
    - `enabled` (boolean),  
    - `requires_explicit_consent` (boolean),  
    - optional `max_frequency` / quotas.  
  - Backed by PolicyRules in Values & Ethics; this is the UX-facing view.

- **PauseState**  
  - `is_paused` (boolean), `scope` (all/only_proactive/only_background), `since`, `reason`.

- **AuditEntry**  
  - `audit_id`, `timestamp`,  
  - `action_type` (goal_created, plan_executed, tool_invoked, policy_block, consent_request, etc.),  
  - `actor` (AICOAgent, component),  
  - `goal_id` / `plan_id` / `step_id` (if applicable),  
  - `tool_id` / `skill_id` (if applicable),  
  - `evaluation_result` (from Values & Ethics),  
  - `affected_entities` (Persons, LifeAreas, WorldStateFacts),  
  - `summary_text` (human-readable description).

- **ExplanationArtifact**  
  - produced on demand; not necessarily stored long term.  
  - contains: key provenance links (PerceptualEvent chain, policies, goals/plans, WM facts) and a short narrative.

## 4. Operations & Behaviour

- **SetAgencyMode(mode)**  
  - Updates AgencyMode; internally selects/updates the relevant ValueProfile / PolicyRules.  
  - May adjust Scheduler/Lifecycle caps (e.g., fewer proactive tasks in cautious mode).

  **WIP**: a first-class AgencyMode configuration surface; current implementation centers on policies + consents rather than a separate mode subsystem.

- **UpdateCapabilities(config_deltas)**  
  - Turn specific tools/integrations/action-classes on/off or toggle `requires_explicit_consent`.  
  - Writes through to Values & Ethics as structured PolicyRules.

  **WIP**: capability toggles as a dedicated subsystem; current implementation is policy-rule centric.

- **PauseAgency(scope, reason)** / **ResumeAgency()**  
  - Set PauseState and emit events to Scheduler/Goal Arbiter/Conversation so that:
    - proactive behaviour and/or background tasks are reduced or stopped,  
    - user-initiated requests may still be honoured within policy.

  **WIP**: pause/resume as an implemented, persisted control plane for agency execution.

- **RecordAuditEntry(event)**  
  - Called at key points in the Goal→Plan→Skill→Tool chain, especially when:
    - a non-trivial tool is invoked,  
    - a high-impact goal/plan is started or stopped,  
    - a policy decision blocks or modifies behaviour,  
    - explicit consent is requested/received.

  **Implementation note (v1):** similar telemetry is available as agency events; the dedicated `AuditEntry` model/table described below is **WIP**.

- **ExplainAction(action_ref)**  
  - Given a reference to an observed action (e.g., a proactive message, tool call, or blocked request), gather:
    - triggering PerceptualEvents,  
    - relevant Goals/Plans/Intention,  
    - EvaluationResult(s) from Values & Ethics,  
    - key WorldStateFacts / LifeAreas,  
    - involved policies or capability settings.  
  - Produce a short, human-oriented narrative that can be shown in UI or logs.

## 5. Integration with Other Components

- **Values & Ethics / Policy Engine**  
  - This component does **not** make independent allow/deny decisions; it configures and surfaces the policy engine:  
    - maps AgencyMode and UI toggles to PolicyRules/ValueProfiles,  
    - uses EvaluationResult for logging and explanations.

- **Goals & Arbiter**  
  - PauseState and AgencyMode influence Arbiter scoring and whether certain goal types can become active.  
  - High-level user controls (e.g., "no new hobbies") may be implemented as capabilities/policies that Arbiter must respect.

- **Planner & Skills/Tools**  
  - CapabilityConfig and EvaluationResult are checked before invoking Skills/Tools.  
  - Significant plan steps and tool calls yield AuditEntries and can be explained via ExplainAction.

- **Scheduler & Lifecycle**  
  - PauseState and AgencyMode can restrict what task queues are allowed to run, beyond normal Lifecycle rules.  
  - Maintenance/critical safety tasks may be whitelisted even when agency is paused.

- **World Model & Memory/AMS**  
  - AuditEntries and policy-relevant events can be stored as `MemoryItem`s and/or WM facts for long-term transparency and learning.

- **UI, Conversation & Embodiment**  
  - Conversation & UI expose controls (modes, permissions) and show explanations or audit summaries.  
  - Embodiment can reflect paused or constrained states visually.

## 6. Persistence & Metrics

- **Persistence**  
  - AgencyMode, PauseState, and CapabilityConfig are persisted in PostgreSQL config tables, aligned with Values & Ethics and Skill/Tool registries. **WIP**  
  - AuditEntries are stored append-only in a dedicated audit log table, with optional promotion into AMS/KG where needed. **WIP**  
  - No separate store for policies; those live in the Values & Ethics component.

- **Metrics & Visibility**  
  - Metrics such as `actions_blocked_by_policy`, `agency_initiated_messages`, and `safety_profile` in `agency-metrics.md` are fed by this component’s logging and configuration.  
  - Additional internal metrics (e.g., audit log volume, mode changes, pauses) can be surfaced for operators.

This design keeps the core policy logic inside Values & Ethics while providing a clear, inspectable, and user-controllable surface over AICO’s autonomy.
