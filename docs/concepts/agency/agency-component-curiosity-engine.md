---
title: Agency Component – Curiosity Engine
---

# Curiosity Engine

## 1. Purpose

The Curiosity Engine provides **intrinsic motivation** for AICO. It detects gaps, anomalies, and under‑explored regions in AICO’s world model and relationship with the user, and turns them into **self‑generated, agent‑self and curiosity‑origin goals**.

It is responsible for:

- Maintaining a stream of **CuriositySignalEvent** PerceptualEvents (see `agency-ontology-schemas.md`).  
- Proposing **hobby and self‑development activities** (`Hobby` entities, agent‑self goals) that remain aligned with user wellbeing and values.  
- Doing so under explicit **safety, values, and resource constraints** enforced by the Values & Ethics component and Scheduler/Resource Monitor, as described in `agency-component-values-ethics.md`, `agency-component-scheduler-governance.md`, and the Personality/Values/Emotion and Core Infrastructure sections of `agency-architecture.md`.

## 2. Conceptual Model

This section describes how curiosity behaves in practice: what kinds of curiosity AICO has, when they fire, and how they are gated by values and resources before becoming goals.

### 2.1 Core Concepts

- **CuriositySignal**  
  Internal numerical signal that “this is worth exploring”. It always has at least:
  - a **target** (entity, topic, hobby, skill, relationship, behaviour pattern),  
  - a **curiosity_type** (see fixed set below), and  
  - scores for novelty, uncertainty, user relevance, and estimated cost.

- **Curiosity types** (implemented as an enum `curiosity_type`):
  - `knowledge_gap` – AICO knows that it does not know enough about something important (high uncertainty, high user relevance).  
  - `novelty` – AICO detects under‑explored but potentially meaningful areas (low visit count, moderate relevance).  
  - `self_performance` – AICO wants to improve in areas where its own behaviour is weak or repetitive.  
  - `hobby_play` – agent‑self interest in hobbies that are safe and emotionally beneficial, not strictly task‑driven.

- **CuriositySignalEvent (PerceptualEvent subtype)**  
  A PerceptualEvent with `percept_type = CuriositySignalEvent` that encodes a *concrete* curiosity opportunity (e.g., “creative writing is an under‑explored hobby domain with high potential value”), as defined in `agency-ontology-schemas.md`.

- **CuriosityPolicy**  
  A set of rules and learned heuristics that decide **which CuriositySignals are turned into events and goals**, and at what intensity, after passing through Values/Ethics and resource gates.


### 2.2 Sources and Triggers

The Curiosity Engine may **observe the full stream of PerceptualEvents** plus internal metrics and world‑model state, but only events that match specific patterns are allowed to become CuriositySignals. This avoids flooding the system with noise, respects safety/consent, and keeps curiosity within resource budgets.

CuriositySignals are produced by specialised detectors that watch for:

- **World Model & AMS**  
  - High prediction error or instability about key entities or relationships.  
  - Sparse or missing facts in areas that matter for active goals or long‑term themes.  
  - Under‑represented topics in memory given their apparent importance for the user.

- **User behaviour**  
  - Repeated mentions of interests (e.g., music, writing, fitness) that are weakly supported by existing goals and plans.  
  - Behavioural patterns suggesting latent needs (e.g., stress spikes around work, but few restorative hobbies).

- **Self‑performance**  
  - Metrics indicating poor or monotonous performance (e.g., many “so‑so” conversations in a topic, weak plan success rates).  
  - Repeated use of generic strategies where more tailored approaches could exist.

- **Social/relationship context**  
  - Opportunities to better understand the user’s relationships, values, or life structure that have been only superficially explored.

Each detector emits candidate CuriositySignals into an internal pool; they are then scored and filtered by the CuriosityPolicy.


### 2.3 Gating by Values, Emotion, and Resources

Curiosity must always remain **second‑class to user wellbeing, consent, and resources**. Before a CuriositySignal becomes a CuriositySignalEvent (and later a goal), it passes three gates:

- **Values/Ethics gate**  
  - Rejects or down‑weights signals in sensitive domains (e.g., health, finance, intimate relationships) unless explicitly allowed.  
  - Enforces user preferences (e.g., topics AICO should not probe without being asked).  
  - Ensures that curiosity proposals do not push AICO towards manipulative or coercive behaviour.

- **Emotion and relationship gate**  
  - Uses current EmotionState and relationship context to decide *when* exploration is appropriate (e.g., avoid introducing new hobby experiments when the user is in acute distress, favour supportive/restorative activities instead).  
  - Can boost signals that are likely to improve emotional wellbeing (e.g., light, shared hobbies during stable periods).

- **Resource gate**  
  - Consults Scheduler/Resource Monitor to ensure that curiosity does not exceed background budgets (CPU, tokens, user attention).  
  - May downgrade or defer signals when many user‑origin or safety‑critical goals are active.

Only CuriositySignals that pass these gates with sufficient combined score are turned into CuriositySignalEvents.


### 2.4 From Signals to Goals and Hobbies

For selected signals, the Curiosity Engine:

- Creates a `CuriositySignalEvent` capturing the opportunity (type, topic, scores, NL summary, candidate goals).  
- Lets the **Goal & Intention System** interpret the event via `ProposeGoalFromPercept` to create or update:
  - **Agent‑self / curiosity goals** (`origin = agent_self | curiosity`), and  
  - **Hobby‑linked projects** using ontology relations such as `FOCUSES_ON_HOBBY` and `IS_AGENT_SELF_GOAL`.
- Relies on the Goal Arbiter and Values/Ethics to decide which of these become **active intentions** and with what priority relative to user‑origin and maintenance goals.


## 3. Data Model

This section specifies the main data structures that the Curiosity Engine must read or produce, at a language‑agnostic level. Detailed schemas for entities like `Hobby` and `PerceptualEvent` live in `agency-ontology-schemas.md`.

### 3.1 CuriositySignal Representation

- Minimal conceptual fields:
  - `signal_id` – stable identifier.  
  - `source_component` – e.g., `world_model`, `ams`, `metrics_aggregator`.  
  - `topic_tags` – ontology tags for what the signal is about (domains, hobbies, skills).  
  - `novelty_score` – how novel/unexplored this area is.  
  - `uncertainty_score` – epistemic uncertainty or disagreement.  
  - `user_relevance_score` – estimated impact on user’s long‑term wellbeing/relationship.  
  - `cost_estimate` – rough resource/time estimate for investigating.

### 3.2 CuriositySignalEvent (PerceptualEvent View)

The Curiosity Engine turns selected CuriositySignals into PerceptualEvents with `percept_type = CuriositySignalEvent` and fields such as:

- `percept_id`, `timestamp`, `source_component = curiosity_engine`.  
- `summary_text` – natural‑language explanation of the curiosity opportunity.  
- `topic_tags`, `opportunity_score`, `novelty_score`, `user_relevance_score`.  
- Optional `candidate_goal_summaries`, `candidate_goal_horizon`, `candidate_origin = curiosity | agent_self`.

### 3.3 Curiosity-Linked Goal Metadata

Curiosity‑driven goals should be clearly identifiable in the Goal & Intention System by:

- Tags such as `hobby`, `exploration`, or specific domain tags.  
- Ontology relations like `FOCUSES_ON_HOBBY(Goal, Hobby)` and `IS_AGENT_SELF_GOAL(Goal)` where applicable.


## 4. Operations / APIs

This section describes the Curiosity Engine’s behaviours as operations with inputs, preconditions, and effects. It does not prescribe transport/serialisation.

### 4.1 Signal Ingestion and Scoring

- **IngestCuriositySignals**  
  - *Input*: streams of candidate signals from AMS, World Model, metrics, logs, and PerceptualEvents.  
  - *Effect*: maintain an internal pool of CuriositySignals, each annotated with `curiosity_type`, target, novelty/uncertainty/relevance/cost scores, and provenance (which detectors and PerceptualEvents contributed).

- **ScoreCuriosityOpportunities**  
  - *Input*: current pool of CuriositySignals, Emotion/Personality/Values context, resource budgets.  
  - *Effect*: apply the CuriosityPolicy and the three gates from Section 2.3 (Values/Ethics, Emotion/relationship, Resources) to compute a *combined curiosity score* per signal and classify them into bands such as {promote to event now, keep for later, discard}.

### 4.2 Event Emission

- **EmitCuriositySignalEvents**  
  - *Input*: CuriositySignals classified as “promote to event now”.  
  - *Preconditions*: Signals have passed Values/Ethics, Emotion, and Resource gates with sufficient combined score.  
  - *Effect*: create one or more `CuriositySignalEvent` PerceptualEvents (as per `agency-ontology-schemas.md`), including `curiosity_type`, scores, and candidate goal hints, and publish them to the Perception/Events bus for consumption by the Goal & Intention System and other components.

### 4.3 Goal Proposals

- **ProposeCuriosityGoals**  
  - *Input*: CuriositySignalEvents, current hobby and agent‑self goals, caps on agent‑self activity.  
  - *Effect*: call Goal & Intention APIs (e.g., `ProposeGoalFromPercept`, `CreateOrUpdateGoal`) to create or adjust goals that explore the signalled opportunities, always with `origin = curiosity | agent_self`, appropriate tags (e.g., `hobby`, `exploration`), and ontology relations such as `FOCUSES_ON_HOBBY` / `IS_AGENT_SELF_GOAL` when applicable.

### 4.4 Scheduling and Resource Governance

- **CoordinateCuriosityScheduling**  
  - *Input*: Scheduler policies, resource budgets, current intention set (from Goal & Intention queries).  
  - *Effect*: provide guidance to Scheduler/Goal Arbiter about when curiosity goals should be scheduled (e.g., sleep‑like phases, low‑load windows) and at what intensity (background vs foreground), ensuring that user‑origin and safety‑critical goals remain primary and that configured caps on curiosity activity are respected.


## 5. Interaction Semantics

This section describes how curiosity behaves over time and in relation to user‑origin and maintenance goals.

### 5.1 Relationship to User-Origin Goals

- **User goals are primary**  
  - By default, user‑origin and safety‑critical goals have priority over curiosity and agent‑self goals in Arbiter decisions.  
  - Curiosity may *suggest* additional goals or refinements but must not silently override or derail explicit user intentions.

- **Supportive, not competitive, by design**  
  - For each CuriositySignal, the CuriosityPolicy should classify its relation to existing user goals: {supportive, neutral, potentially competing}.  
  - Supportive examples: discovering better study strategies for an active exam goal; proposing restorative hobbies when stress is high.  
  - Potentially competing examples: proposing time‑consuming side projects during a crunch period.

- **Bias towards supportive exploration**  
  - Signals labelled as supportive receive a positive bias in scoring; competing signals are down‑weighted or deferred unless explicitly approved by the user and Values/Ethics.  
  - When in doubt, curiosity is conservative: it prefers to offer low‑impact, easily dismissible suggestions rather than large structural changes.


### 5.2 Values/Ethics Control of Curiosity

- **Domain policies**  
  - Values & Ethics can define domain‑level rules for where curiosity is allowed, restricted, or requires explicit user consent (e.g., health, finance, intimate relationships).  
  - Curiosity detectors must respect these policies *before* emitting CuriositySignals where possible, and the Values/Ethics gate in 2.3 must re‑check downstream.

- **User preferences and overrides**  
  - Users can configure topics and modalities where AICO should “not poke around” without being asked.  
  - Curiosity must surface some indications of its interests (e.g., “I could explore X if you want”) rather than covertly collecting sensitive information.

- **Redirection instead of suppression when possible**  
  - If a promising curiosity opportunity is blocked for safety or preference reasons, the engine should attempt to redirect it:
    - towards *less intrusive* questions or activities, or  
    - towards related but safer domains (e.g., general time‑management instead of specific employer politics).

- **Auditability**  
  - Curiosity‑driven events and goals must carry provenance indicating that they were initiated by the Curiosity Engine and which policies were applied.  
  - This allows inspection of “why AICO started doing this” and whether Values/Ethics behaved as intended.


### 5.3 Temporal Behaviour and Activity Phases

- **Online interaction vs background phases**  
  - During active chats, curiosity should bias towards lightweight, conversational explorations and suggestions that are easy to accept or reject.  
  - Heavy curiosity work (e.g., scanning large parts of the world model, running many experiments) is deferred to background or sleep‑like phases, coordinated via Scheduler.

- **Sleep‑like phases**  
  - In consolidation or sleep‑like phases, curiosity may be more active in reorganising knowledge, identifying new hobbies, and proposing medium‑term agent‑self projects, still subject to resource and Values/Ethics caps.  
  - Any resulting proposals should be surfaced to the user opportunistically, not dumped as a backlog.

- **Load‑sensitive throttling**  
  - When system load or user context is heavy (many urgent user‑origin goals, high stress, limited compute), curiosity scales back:
    - reducing the rate of CuriositySignal creation,  
    - raising thresholds for promotion to events, and  
    - preferring to update *existing* curiosity goals rather than creating new ones.


### 5.4 Interaction with Goal Arbiter and Metrics

- **Arbiter integration**  
  - Curiosity‑origin and agent‑self goals are fed into the Goal Arbiter with clear markings (`origin`, tags, `curiosity_type`).  
  - The Arbiter uses these markings to enforce caps on active curiosity intentions and to ensure they remain subordinate to user and maintenance priorities.

- **Feedback from outcomes**  
  - Outcomes of curiosity‑driven goals (success, user satisfaction, emotional impact) feed back into CuriosityPolicy and Values/Ethics tuning.  
  - Repeatedly unhelpful curiosity patterns should be down‑weighted over time.

- **Metrics‑driven adjustment**  
  - Metrics from `agency-metrics.md` (e.g., proportion of curiosity goals, hobby activity, impact on user wellbeing signals) should be used to:
    - tune curiosity intensity,  
    - detect when curiosity is under‑ or over‑active, and  
    - inform user‑visible controls (e.g., “turn curiosity up/down”).


## 6. Examples

This section provides concise scenarios illustrating how curiosity behaves in practice.

### 6.1 Discovering a New Hobby (Supportive Curiosity)

**Context**: Over several weeks, AICO observes that the user often talks about drawing and art, but no explicit goals or hobbies exist in that domain.

1. **Signals & detection**  
   - User messages (PerceptualEvents: `UserIntentEvent` and `SocialEvent`) repeatedly mention drawing.  
   - AMS shows many episodic memories tagged `art`, but few goals or plans.  
   - A `CuriositySignal` is created with:  
     - `curiosity_type = hobby_play`, `topic_tags = ["drawing", "art"]`,  
     - moderate novelty, high user relevance, low cost.

2. **Gating & scoring**  
   - Values/Ethics: hobby domain is safe; user has not disabled art‑related exploration → passes.  
   - Emotion/relationship: user mood stable → exploration allowed.  
   - Resources: low load → background capacity available.  
   - CuriosityPolicy classifies the signal as **supportive** (helps user express interests, may reduce stress) and promotes it to event.

3. **Event & goals**  
   - `EmitCuriositySignalEvents` creates a `CuriositySignalEvent` describing “under‑served art/drawing interest”.  
   - Goal System uses `ProposeGoalFromPercept` to create:  
     - a `Hobby` node `h_drawing`,  
     - an agent‑self / curiosity project goal (e.g., "Explore drawing sessions together"),  
     - relations `FOCUSES_ON_HOBBY` and `IS_AGENT_SELF_GOAL`.

4. **User interaction**  
   - During a suitable moment, AICO proposes a light suggestion (“Would you like to schedule some small drawing sessions together?”).  
   - If accepted, the goal becomes an active intention; otherwise, it may be paused or dropped and the policy updated.


### 6.2 Knowledge-Gap Curiosity About the User’s Routine

**Context**: The world model has only sparse information about the user’s daily routine, yet several active goals depend on it (sleep, work, exercise).

1. **Signals & detection**  
   - World Model detectors notice high uncertainty and missing facts about typical time windows for sleep and work.  
   - A `CuriositySignal` is created with:  
     - `curiosity_type = knowledge_gap`, target = "user daily routine",  
     - high uncertainty, high user relevance, moderate cost.

2. **Gating & scoring**  
   - Values/Ethics: allowed, but flagged as potentially sensitive (temporal patterns).  
   - Emotion/relationship: user currently stable; recent conversations mention wanting better sleep.  
   - Resources: schedule indicates an upcoming sleep‑like phase.  
   - Signal passes gates with a good but not extreme combined score.

3. **Event & goal proposal**  
   - A `CuriositySignalEvent` is emitted summarising the knowledge gap and suggesting a project like "Understand and support user’s daily rhythm".  
   - Goal System proposes a curiosity‑origin project goal, which the Arbiter may keep in `proposed` until the user is explicitly asked.

4. **User-facing behaviour**  
   - At an appropriate time, AICO asks: “I realised I don’t fully understand your typical day, and that makes it harder to support your sleep and work. Would you like me to learn more about your routine?”  
   - If the user declines or restricts this, Values/Ethics update policies and future signals of this type are down‑weighted or blocked.


### 6.3 Throttling Curiosity Under Stress

**Context**: The user is under acute work stress; multiple user‑origin goals with tight deadlines are active.

1. **Signals & context**  
   - Emotion Engine reports high stress; PerceptualEvents show repeated mentions of overload.  
   - Several urgent user‑origin goals are active in the Goal System; Arbiter shows high utilisation.

2. **Gating reaction**  
   - Emotion/relationship gate enters a **protective mode**:  
     - lowers allowed curiosity intensity,  
     - raises thresholds for promoting CuriositySignals to events.  
   - Resource gate reports little spare capacity.

3. **Operational effect**  
   - `IngestCuriositySignals` continues to collect signals, but `ScoreCuriosityOpportunities` classifies most as "keep for later" or "discard".  
   - `EmitCuriositySignalEvents` only allows **strongly supportive** signals through (e.g., restorative hobbies or small stress‑relief ideas); exploratory side projects are deferred.

4. **Recovery**  
   - Once deadlines pass and stress drops, thresholds relax. Previously stored “keep for later” signals may be reconsidered and, if still relevant and safe, promoted to events and goals.


## 7. References & Cross‑Links

- `docs/concepts/agency/agency.md` – overall concept of Agency and intrinsic motivation.  
- `docs/concepts/agency/agency-architecture.md` – placement of Curiosity Engine in the Autonomous Agency domain and control flows.  
- `docs/concepts/agency/agency-ontology-schemas.md` – ontology definitions for `CuriositySignalEvent`, `Hobby`, and curiosity‑linked goals.  
- `docs/concepts/agency/agency-component-goals-intentions.md` – how curiosity‑origin goals and PerceptualEvents are represented and managed.  
- `docs/concepts/agency/agency-metrics.md` – metrics related to curiosity activity, hobby goals, and exploration intensity.  

External research (non‑exhaustive):

- Klissarov, M. et al. (2023). *Motif: Intrinsic Motivation from Artificial Intelligence Feedback.*  
- Curiosity‑Driven Reinforcement Learning from Human Feedback (2025, ACL).  
- Desire‑Driven Autonomous Agents (D2A) for LLMs (2024) – value‑ and desire‑based task generation for autonomous LLM agents.
