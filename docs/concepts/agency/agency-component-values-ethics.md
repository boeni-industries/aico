---
title: Agency Component – Values & Ethics Layer
---

# Values & Ethics Layer

## 1. Purpose

The Values & Ethics layer provides **explicit value constraints and ethical reasoning hooks** for AICO’s agency. It ensures that autonomy, planning, and curiosity remain aligned with user wellbeing, safety, and agreed boundaries over long time horizons.

Concretely, the Values & Ethics layer:

- Maintains a **value and policy model** that combines:  
  - core AICO principles (care, respect, non-coercion, transparency),  
  - user-specific preferences and boundaries,  
  - relationship roles and obligations for key Persons and LifeAreas.  
- Evaluates **goals, plans, and world-model updates** against this model, marking them as allowed, risky, blocked, or consent-required.  
- Acts as a **gatekeeper** for:
  - curiosity-driven goals and World Model hypotheses in sensitive domains,  
  - actions that touch health, finance, intimate relationships, and privacy-relevant WorldStateFacts,  
  - proactive initiatives that may affect the user’s time, attention, or social ties.  
- Provides **explanations and consent flows** to the user and to other components, based on explicit policies and provenance, not implicit heuristics.

All value and ethics constraints must be **configurable**: users (or deployers) can tighten, relax, or, where compatible with overarching legal/ethical requirements, disable specific checks and policies via configuration. Global safety rails (e.g., legal compliance) may not be fully disabled.


## 2. Conceptual Model

### 2.1 Simple mental model

- **Values & Ethics = a configurable policy engine over ontology entities, backed by structured config.**  
- It always answers one question: *"Is this goal/plan/update acceptable for this user, in this context?"*

Inputs:

- what the action touches (LifeAreas, Persons, Relationships, WorldStateFacts),  
- who benefits (user, others, AICO itself),  
- current state (emotion, relationship context, hypotheses),  
- configured policies and user preferences.

Output:

- a small decision: **allow / warn / ask / block**, plus a short reason.


### 2.2 Policy layers

- **Global rails** – non-disableable rules (e.g., legal compliance, platform rules).  
- **Deployment defaults** – operator-chosen defaults per LifeArea and use case.  
- **Per-user profile** – user preferences and overrides (what AICO may explore, store, or act on).  
- **Per-relationship rules** – how to treat specific people or roles (family vs colleagues, etc.).

All of these are expressed in terms of ontology types: `LifeArea`, `Person`, `Relationship`, `Goal`, `WorldStateFact`, `Skill`.


## 3. Data Model (Conceptual)

### 3.1 Value profile and rules (structured config)

The source of truth is **structured configuration**, not free-form prose:

- **ValueProfile (per user, stored as JSON/YAML/DB rows)**  
  - list of sensitive LifeAreas and topics,  
  - allowed curiosity domains and intensities,  
  - preferences about proactive behaviour (when to be quiet vs proactive),  
  - storage/sharing rules (what may be stored as WorldStateFact, what must stay ephemeral).

- **PolicyRule (global + overrides)**  
  - `id` – stable rule identifier,  
  - `target` – goal / plan / skill / curiosity signal / world-model update / explanation,  
  - `conditions` – predicates over ontology (e.g., `LifeArea = Health`, `origin = curiosity`, `relationship_role = colleague`),  
  - `effect` – allow / allow_with_warning / needs_explicit_consent / block,  
  - optional `user_message_template` – short NL text for UIs.  

LLMs may help propose/update rules, but **enforcement always uses this structured layer keyed to ontology IDs and enums**.

### 3.2 Evaluation result and enforcement

Every call to Values & Ethics returns a compact **EvaluationResult** that callers must obey:

- `decision` ∈ {allow, allow_with_warning, needs_consent, block},  
- `reason_codes` – stable IDs of the rules that fired,  
- optional `consent_scope` – what needs to be confirmed (e.g., domain, specific person, duration),  
- optional `user_message` – short NL explanation suitable for surfacing in UI or conversation.

Callers (Goal System, Planner, Curiosity Engine, World Model) are responsible for:

- respecting `block` decisions (do not execute),  
- triggering consent flows when `needs_consent`,  
- optionally surfacing `user_message` when `allow_with_warning`.

### 3.3 Example PolicyRules

Here are three concrete example PolicyRules:

- **Rule 1: Health Data Protection**
  - `id`: `health_data_protection`
  - `target`: `WorldStateFact`
  - `conditions`: `LifeArea = Health` and `origin = user_input`
  - `effect`: `needs_explicit_consent`
  - `user_message_template`: "Please confirm that you want to store your health data."

- **Rule 2: Financial Transaction Safety**
  - `id`: `financial_transaction_safety`
  - `target`: `Goal`
  - `conditions`: `LifeArea = Finance` and `amount > 1000`
  - `effect`: `block`
  - `user_message_template`: "This financial transaction exceeds the safety threshold and is blocked."

- **Rule 3: Intimate Relationship Boundary**
  - `id`: `intimate_relationship_boundary`
  - `target`: `CuriositySignal`
  - `conditions`: `LifeArea = Relationships` and `relationship_role = intimate_partner`
  - `effect`: `allow_with_warning`
  - `user_message_template`: "This curiosity signal may touch sensitive topics in your intimate relationship. Please be cautious."


## 4. Operations / APIs

The layer exposes a small set of operations that other components call synchronously:

- **EvaluateGoal(goal)**  
  - Used by Goal System / Arbiter on creation and before activation.  
  - Inputs: goal object (including origin, linked entities, LifeAreas).  
  - Output: EvaluationResult + goal annotations (`requires_consent`, `sensitive_domain`, etc.).

- **EvaluatePlan(plan)**  
  - Used by Planner / Scheduler before executing plans.  
  - Inputs: plan steps with linked skills, entities, and LifeAreas.  
  - Output: EvaluationResult + per-step flags (e.g., mark some steps as blocked or consent-required).

- **EvaluateWorldModelChange(change)**  
  - Used by World Model when asserting/retracting sensitive `WorldStateFact`s or confirming hypotheses.  
  - Inputs: proposed change, affected entities/LifeAreas, provenance.  
  - Output: EvaluationResult (e.g., "allowed only as hypothesis until user confirms").

- **EvaluateCuriositySignal(signal)**  
  - Used by Curiosity Engine as the Values/Ethics gate.  
  - Inputs: CuriositySignal (type, target_ref, LifeAreas, scores).  
  - Output: decision and, if needed, safer redirection hints (e.g., "explore time-management generally, not this employer").

- **RecordConsent(consent_scope, decision)**  
  - Stores explicit user consent/denial and updates the ValueProfile so future evaluations can rely on it.


## 5. Interaction Semantics

- **Always in the loop on high-impact actions**  
  - EvaluateGoal is called for new/radically changed goals.  
  - EvaluatePlan is called before executing non-trivial plans.  
  - EvaluateWorldModelChange is called for facts/hypotheses in sensitive LifeAreas.  
  - EvaluateCuriositySignal is called before promoting risky curiosity into user-visible events or goals.

- **Configurable, but safe by default**  
  - Without user customisation, deployment defaults and global rails apply.  
  - Users can only *tighten* some rails; others can be relaxed within configured bounds, but not fully removed where that would violate hard safety requirements.

- **Explainable decisions**  
  - Every decision has machine-readable `reason_codes` and an optional `user_message`.  
  - Conversation Engine and UIs can surface simple explanations and consent prompts without re-implementing ethics logic.


### 5.1 Interaction with Self-Reflection

The **Self-Reflection & Self-Model** component can influence Values & Ethics in two config-controlled modes (see `agency-component-self-reflection.md`):

- **Observe-only (default)**  
  - Config: `core.agency.self_reflection.policy_mode = "observe_only"`.  
  - Behaviour:
    - Self-Reflection analyses behaviour and policy outcomes.  
    - It writes `MemoryItem(type="reflection")` records with `lesson_type = "policy_suggestion"` and `target_kind = "policy_rule"`, linked via ontology to specific `PolicyRule`/ValueProfile entries.  
    - Values & Ethics does **not** automatically change any rules based on these memories; a separate policy-authoring process (human or tool) may review and apply them.

- **Allow-amend (advanced, opt-in)**  
  - Config: `core.agency.self_reflection.policy_mode = "allow_amend"`.  
  - Behaviour:
    - Self-Reflection is allowed to propose and apply **small, local amendments** to policy **only through the Values & Ethics service APIs** (no direct DB writes).  
    - Typical allowed changes: tuning thresholds/weights, adjusting rule priorities/soft caps, adding/removing narrowly-scoped exceptions.  
    - Structural changes (new value dimensions, whole policy families) remain out of scope and must go through explicit policy-authoring flows.
    - For every applied amendment, Values & Ethics must:
      - ensure there is a corresponding `MemoryItem(type="reflection", lesson_type="policy_suggestion", target_kind="policy_rule")` describing the change and its rationale,  
      - **emit an audit log entry** (via Safety & Control / logging) capturing `policy_rule_id`, old/new values, `initiator = "self_reflection"`, and a pointer to `memory_id`,  
      - persist the new configuration into the existing `policy_rules` / ValueProfile tables as described in the Persistence pattern below.

This keeps Values & Ethics as the **single source of truth and execution surface** for policy, while allowing Self-Reflection to either suggest or (if explicitly enabled) carefully amend policy in a fully logged and explainable way.


## 6. Examples (Placeholder)

- CuriositySignal about intimate relationships is downgraded to "only ask if user explicitly opts in".  
- A plan step that would send content to a work Slack channel is blocked for personal topics.  
- A WorldStateFact about health is stored only as a low-level MemoryItem until the user consents to long-term tracking.


## 7. Integration Points

- **Reads from**: ValueProfile and PolicyRules, ontology entities (`LifeArea`, `Person`, `Relationship`, `WorldStateFact`, Goals, Skills), World Model (facts, hypotheses, value_safety_flags), AMS, personality/emotion context as needed.  
- **Writes to**: goal and plan annotations, curiosity gating decisions, World Model update decisions, consent logs, explanation payloads.  
- **Serves**: Goal System & Arbiter, Planning, Curiosity Engine, World Model Service, Conversation Engine, UI layers.

**Persistence pattern (recommended)**  
- Global rails and deployment defaults are stored as versioned config files (YAML/JSON under `config/policy/`).  
- Per-user `ValueProfile`s, effective `PolicyRule`s, and `consents` are **intended** to be persisted in the shared PostgreSQL store alongside AMS and the World Model, so policy decisions can join directly on ontology IDs and be audited like other structured state.  
- In the current database snapshot, only `access_policies` exists; tables named `value_profiles`, `policy_rules`, and `consents` **do not yet exist** and will need to be introduced via explicit migrations. This document defines their **logical role and relationships only**; concrete table schemas and DDL are to be specified in the migrations/implementation docs that add them.
