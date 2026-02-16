---
title: Agency Component – Skill & Tool Layer
---

# Skill & Tool Layer

## Status

- **Implemented (v1)**: in-process `SkillRegistry` / `Skill` base types exist in `shared/aico/ai/agency/skills/registry.py`.
- **Implemented (v1)**: skill matching exists via `SkillMatcher` in `shared/aico/ai/agency/skills/matcher.py` (multiple strategies).
- **Implemented (v1)**: skill invocation exists via `SkillInvoker` in `shared/aico/ai/agency/skill_invoker.py` and records executions (see `agency_skill_executions`).
- **Implemented (v1)**: in-process `ToolRegistry` exists in `shared/aico/ai/agency/tools/registry.py` and is bootstrapped via `shared/aico/ai/agency/bootstrap.py`.
- **WIP**: a persisted, ontology-backed skill catalog (skills as first-class World Model entities) and a scheduler-queued “skills run only via scheduler” execution path.

## 1. Purpose

The Skill & Tool Layer defines the **concrete, executable capabilities** AICO can use to act.

- **Ontology-backed** – **WIP**: skills/tools as first-class `Skill` entities in the shared ontology/World Model.
- **Policy-aware** – skills carry safety metadata (e.g., `safety_level`, `side_effect_tags`) and execution policy hints; end-to-end “every invocation is pre-gated by Values & Ethics + scheduler budgets” is **WIP**.
- **Schedulable** – **WIP**: executing plan steps by queueing explicit skill invocations in the backend scheduler.

It is the bridge between **goals/plans** and **actual actions** (conversation, memory operations, external APIs, automations).

This document focuses on the **current implementation model and flows**, and marks forward-looking parts as `**WIP**`.


## 2. Conceptual Model

### 2.1 Types of skills/tools

The layer organises capabilities into a small set of categories:

- **Conversation skills** – ask, reflect, summarise, challenge, encourage, teach, brainstorm.  
- **Memory skills** – store, recall, tag, consolidate, reinterpret experiences, query World Model views.  
- **Social skills** – check-ins, follow-ups, invitations, boundary-aware introductions.  
- **External tools** – APIs, local automations, file/system operations, third-party integrations.

**WIP:** mapping skills to ontology `Skill` nodes with:

- `skill_id`, `name`, `description`,  
- `input_schema_id`, `output_schema_id`,  
- `side_effect_tags` (e.g., touches_health_data, sends_external_message),  
- `safety_level` (used by Values & Ethics and Scheduler).

### 2.2 Full chain: from goal to tool

We follow a simple, hierarchical chain (in line with HTN-style and recent LLM planning/tool-use work):

1. **Goal & subgoals (Goal System)**  
   - High-level `Goal` nodes (themes/projects/tasks) are created and linked (`DERIVED_FROM`, `HAS_GOAL`) in the goal graph.  
   - Planner selects a concrete **target goal** to work on.

2. **Tasks / plan steps (Planner)**  
   - The Planner breaks the target goal into an ordered **plan**: a tree/sequence of **plan steps** (tasks) with clear preconditions and outcomes.  
   - Each plan step is linked to ontology entities (Persons, Activities, LifeAreas, WorldStateFacts) via the World Model.

3. **Skills (this layer)**  
   - For each executable plan step, the plan executor chooses a concrete `skill_id` from the `SkillRegistry`.
   - Inputs are passed as a typed dict and validated against `Skill.parameters`.

4. **Tools (implementation)**  
   - Many skills can be thin semantic wrappers around one or more concrete tools.
   - In code, tools are registered in a process-local `ToolRegistry` (see `shared/aico/ai/agency/tools/registry.py`).
   - A stable, end-to-end skill→tool mapping is partially implemented via `Skill.implementation_tools` (**WIP**: complete, enforced mapping and policy gating).

Before a skill executes, the runtime typically:

- validates inputs via the skill’s parameter definitions,
- executes via `SkillInvoker` with timeout + retry and records execution state.

**WIP**: canonical pre-execution gating that always invokes Values & Ethics and scheduler resource governance before running side-effectful skills.

**WIP**: enqueue skill invocations as scheduler tasks instead of executing inline in the plan executor.

### 2.3 Minimal contract per skill

Every skill/tool must define, at schema/config level:

- **Preconditions** – when it is valid to call it (required entities, LifeAreas, user state).  
- **Expected effects** – what it may change (WorldStateFacts, MemoryItems, external systems).  
- **Observables** – what signals/results are emitted back (success/failure, metrics, PerceptualEvents).  
- **Safety & ethics metadata** – side-effect tags, safety level, whether it ever leaves the device or calls third-party APIs.

This metadata is used by the Planner, Values & Ethics, World Model, and Scheduler to decide *whether* and *how* to use a given skill.

### 2.4 Skill registry and selection

Skill selection is **registry-driven**, not ad-hoc tool picking by the LLM:

- A `SkillRegistry` stores all available `Skill` implementations with their metadata (e.g., category, safety hints, side effects, capability tags).  
- For each **plan step**, the Planner/Skills layer:
  - builds a step spec (NL description + linked ontology entities + desired effect type),  
  - queries the registry for skills whose **preconditions and capabilities match** that spec,  
  - filters by safety level and deployment/user preferences,  
  - may use semantic similarity / fuzzy matching as part of `SkillMatcher` (**WIP**: strict allow-listing only; today the system supports multiple matching strategies).
- If a skill wraps multiple tools, the registry/skill config decides which concrete tool implementation to use based on context (e.g., LifeArea, relationship role, deployment config).

**Implementation note (v1):** registries are in-memory/process-local today. Bootstrapping of core tools happens in `shared/aico/ai/agency/bootstrap.py` (import-time registrations).

The Planner and Skill & Tool Layer therefore always pick skills/tools from a **finite, ontology-typed set** with known contracts, rather than letting the LLM free-form call arbitrary APIs.

### 2.5 Tool chaining and partial results

Tool chaining and partial results are handled in layers:

- At the **tool level**, a tool is just an implementation (function/HTTP call/etc.) returning a typed result + status (success/partial/failure) and optional PerceptualEvents/logs. Multiple tools can be sequenced **inside a single skill** (e.g., fetch → parse → summarise).
- At the **skill level**, a skill aggregates tool calls and returns a structured result: `status` (success/partial/failure), `outputs` (its promised data), and `observables` (PerceptualEvents, metrics, hints for World Model updates). If an internal tool fails, the skill decides whether to degrade gracefully (partial) or fail.
- At the **plan-step level**, the Planner treats each step’s expected effects as postconditions. Skill results mark these as satisfied/partial/failed, enabling backtracking, replanning, or fallbacks (e.g., insert an extra data-gathering step if preconditions weren’t fully met).
- At the **goal level**, outcomes from all relevant plan steps (plus user feedback) determine whether a goal/subgoal is progressed, completed, or needs adjustment.

All intermediate results are fed back into AMS/World Model as PerceptualEvents and `WorldStateFact`s, so future planning and Values & Ethics decisions can take past successes/failures into account.


## 3. Data Model (Conceptual)

### 3.1 Skill schema (ontology-level)

As defined in the ontology doc, a `Skill` node has at least:

- `skill_id` – stable identifier.  
- `name`, `description`.  
- `input_schema_id`, `output_schema_id` – JSON-schema-like IDs for request/response payloads.  
- `side_effect_tags` – e.g. `touches_health_data`, `sends_external_message`, `writes_files`.  
- `safety_level` – enum (low / medium / high / privileged).  
- `life_areas` – which LifeAreas it typically touches.  
- `implementation_ref` – pointer to one or more Tool definitions.

### 3.2 Tool schema (implementation-level)

Tools are concrete implementations referenced by `implementation_ref`:

- `tool_id` – stable identifier.  
- `backend` – `python`, `node`, `os_command`, `http`, etc.  
- `endpoint_or_entrypoint` – function name, command, or URL.  
- `runtime_context` – where it runs: `backend_service`, `local_client`, `third_party`.  
- `auth_profile` – which credentials/permission set it uses.  
- `resource_profile` – expected CPU/memory/latency class.  
- `allowed_env` – which deployments/environments may enable it.

Tools do **not** define their own free-form parameter lists; instead, they accept the **normalised input payload** defined by the `Skill`'s `input_schema_id`. Transport-specific details (e.g., how to map the payload into HTTP query/body fields or function arguments) live in the Tool runner configuration, not in the ontology.

**WIP**: persist `Skill.skill_id → [tool_id]` mappings alongside the World Model / ontology configuration.


## 4. Operations / APIs

### 4.1 Registration and lookup

**Implementation note (v1):** skills are registered in-process by constructing skill classes and calling `SkillRegistry.register(...)` (see `shared/aico/ai/agency/skills/registry.py`).

**Implementation note (v1):** tools are registered in-process in `ToolRegistry.register_tool(...)` (see `shared/aico/ai/agency/tools/registry.py`).

- **FindSkillsForStep(StepSpec)**  
  - Input: desired capabilities, LifeAreas, target entities, effect type.  
  - Output: ordered list of matching `Skill` candidates with metadata for Planner/LLM ranking.

### 4.2 Invocation

- **InvokeSkill(skill_id, input, context)**  
  - Called by the plan executor via `SkillInvoker.invoke_skill(...)` (`shared/aico/ai/agency/skill_invoker.py`).
  - Steps:
    - load `Skill` from `SkillRegistry`;
    - validate inputs;
    - execute with timeout + retry;
    - record the execution for reflection/learning loops.

  **WIP**: standardized tool-runner abstraction (python/http/zmq) with sandboxing and universal policy checks.

- **Tool runner APIs** (internal to infra)  
  - E.g. `RunPythonTool`, `RunHttpTool`, `RunOsCommand`, each responsible for sandboxing, timeouts, logging, and mapping raw results into typed outputs.


## 5. Interaction Semantics

### 5.1 Where tools execute

- **Backend services** – default for most tools (safe, auditable, same PostgreSQL/WM context).  
- **Local client** – optional, for device-local actions; requires explicit user permission and a secure bridge.  
- **Third-party APIs** – only via configured HTTP tools with explicit `auth_profile` and strong Value & Ethics checks.

The `runtime_context` and `auth_profile` fields determine how and where a tool is executed.

### 5.2 How chains behave at runtime

- LLMs **never call tools directly**; they propose plans/step specs.  
- Planner + Skill Registry choose Skills; Scheduler + Tool runners call Tools.  
- Partial results (from tools/skills) update WM/AMS and may trigger replanning; failures are surfaced as PerceptualEvents and metrics for debugging and learning.

### 5.3 Extensibility

- Adding a new tool: implement it behind a Tool runner, define a `ToolDefinition`, then wire it into one or more Skills via `implementation_ref`.  
- Adding a new skill: define a `Skill` with schemas, safety metadata, and mapping to existing or new tools; register it so Planner can discover it.  
- No planner code changes needed if new skills fit existing capability tags and schemas; the Skill Registry and ontology tags drive discovery.


## 6. MVP Skills and Tools (Non-exhaustive)

For the first usable version of AICO, we likely need at least:

- **Conversation skills/tools**  
  - `send_message_to_user` (via Conversation Engine).  
  - `summarise_conversation_segment` (LLM-backed).  
  - `ask_clarifying_question` (LLM-backed).

- **Memory & World Model skills/tools**  
  - `store_memory_item` (write to `user_memories` table).  
  - `query_relevant_memories` (search `user_memories` + AICO conversation initiations).  
  - `upsert_world_fact` (write to `kg_nodes`/`kg_edges` tables via WM APIs).

- **Social/relationship skills/tools**  
  - `schedule_check_in` (create a reminder/goal).  
  - `log_social_event` (write PerceptualEvent + MemoryItem + WM update).

- **Reflection / self-evaluation skills/tools**  
  - `generate_reflection` (LLM over recent logs/events).  
  - `propose_small_adjustments` (LLM suggestions turned into candidate goals).

- **Maintenance & self-healing skills/tools**  
  These are **shared between agency and the System Health UI**; the same skills that power
  user-facing “Fix” buttons in the Health tab are also available as agency skills for
  autonomous self-healing:
  - `run_connectivity_diagnostics` – orchestrates low-risk tests for gateway, DB, modelservice,
    and message bus connectivity, emitting PerceptualEvents and metrics.  
  - `reduce_db_disk_pressure` – runs a bounded, idempotent playbook such as archiving old
    conversations, cleaning transient data, and re-running disk checks.  
  - `stabilise_modelservice` – performs a safe sequence of checks and restarts for
    modelservice/LLM pipeline, within Values & Ethics and Scheduler policies.  
  - `rebalance_agency_load` – throttles or reschedules lower-priority agency work when
    resource scans show sustained overload.  
  - `re-evaluate_ai_behaviour_health` – triggers a focused agency/AMS/World Model check for
    goals, plan execution health, reflection cadence, and context/memory integrity.

From this component’s perspective, **maintenance/self-healing skills are not special** – they
follow the same ontology-backed, policy-aware, schedulable pattern as other skills. What
differs is how they are *used*:

- System Health checks in the frontend call backend endpoints that, under the hood, invoke
  these skills/tools as part of troubleshooting playbooks (e.g. “Archive old conversations”,
  “Run connection test & restart”).
- The agency layer treats degraded health or maintenance needs as **goals** (often
  `origin = system_maintenance`) and attaches plans whose executable steps use the very same
  maintenance skills.

This ensures a **single implementation path** for troubleshooting actions: whether a human
clicks a button in the Health tab or the agent acts autonomously, both go through the same
Skill & Tool Layer, Values & Ethics checks, and Scheduler, keeping behaviour auditable and DRY.

For verification and end-to-end testing, the backend may also provide an explicitly-configured
simulated issue mode that triggers a deterministic scan → remediate → verify plan using
explicit `skill_id`s (no fuzzy matching). This mode must be clearly marked as test-only and
disabled by default. See `agency-self-healing.md`.

All of these should be defined as `Skill`s with clear schemas and mapped to a small, well-audited
set of Tool implementations, so that adding more later follows the same pattern.
