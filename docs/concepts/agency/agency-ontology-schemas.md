# AICO Ontology & Schemas

## 1. Purpose and Scope

This document defines the **core ontology and schemas** used by AICO’s agency subsystem and related services. It serves as the single source of truth for:

- **Shared concepts and types** used across conversation, memory, world model, planning, curiosity, values/safety, and embodiment.
- **Event and data schemas** (especially `PerceptualEvent`) that specify how raw inputs are interpreted into semantic structures.
- **Relations between entities** (user, AICO, projects, tasks, hobbies, memories, emotions, environment, sensors, goals, plans, tools).
- **Usage boundaries**: which subsystem owns which part of the ontology and how they are allowed to extend it.

This is a **conceptual and implementation-guiding** ontology:

- It is designed to back a **property/knowledge graph plus JSON schemas**, not a heavyweight OWL logic stack.
- It is intentionally minimal but **stable enough** to support early implementations of:
  - Perception / Sensors → `PerceptualEvent`
  - World Model Service / KG+Schemas
  - Goals & Intentions subsystem
  - Curiosity Engine
  - Values & Ethics / Safety


## 2. Design Principles

- **2.1 Pragmatic, not maximalist**  
  Start with a small, high-value core that is stable, then extend.

- **2.2 Shared language across components**  
  All subsystems must use the same terminology and identifiers for core entities and events.

- **2.3 Hybrid representation**  
  Every important object has:
  - **Natural-language fields** for explanations (`summary_text`, titles, descriptions).
  - **Structured fields** (JSON-like slots, IDs, scores) for machine reasoning and validation.

- **2.4 Explicit provenance**  
  Events and entities must include provenance (source, time, responsible component, triggering percepts) to support explainability, auditing, and metrics.

- **2.5 Extendable by domain**  
  - Core ontology here is **global and stable**.
  - Domains (e.g. specific apps, devices, verticals) may add:
    - new subtypes under core types,
    - additional slots,
    - domain-specific relations, without breaking core invariants.


## 3. High-Level Conceptual Areas

We define the ontology in five interlocking areas:

- **A. Agents and Persons**  
  User(s), AICO as an agent, other people and organisations.

- **B. Activities, Goals, and Hobbies**  
  Projects, tasks, routines, goals, habits, hobbies, plans.

- **C. Mental and Social State**  
  Emotion/mood, personality traits, relationships, social context.

- **D. World, Environment, and Sensors**  
  Places, devices, sensor observations, environment context, `PerceptualEvent`.

- **E. Knowledge, Memory, and Facts**  
  Memory items, world facts, learned patterns, preferences, skills/tools.


## 4. Core Types and Identifiers

This section lists the **primary types and relations** AICO commits to. Actual storage can be in a property graph (nodes/edges) or equivalent, but these types must exist conceptually.

### 4.1 Agents and Persons

- **Person**  
  Generic human or organisation actor.
  - Key fields: `person_id`, `display_name`, `relation_to_user` (self, family, friend, colleague, org, unknown), `importance_score`.

- **User (subtype of Person)**  
  The primary human owner/controller of AICO.
  - Additional fields: preferences summary, safety profile ID, access-rights profile ID.

- **AICOAgent**  
  The software agent representing AICO as an acting entity.
  - Fields: `agent_id`, `name`, `persona_profile_id`, `capabilities_profile_id`.

- **Relations**
  - `INTERACTS_WITH(Person, Person|AICOAgent)`
  - `PRIMARY_USER_OF(AICOAgent, User)`
  - `BELONGS_TO(Person, Organisation)` (organisation as a Person subtype or separate node type).


### 4.2 Activities, Goals, Tasks, Hobbies, Routines, Life Areas

These link directly to the **Goals & Intentions** subsystem schemas, but here we define the conceptual ontology.

- **Activity** (abstract supertype)  
  Something that unfolds over time and may have goals, tasks, and events.

- **Project (subtype of Activity)**  
  Larger, multi-step activity with a clear purpose.
  - Fields: `project_id`, `title`, `description`, `owner_id` (User or AICOAgent), `status`, `tags`.

- **Task (subtype of Activity)**  
  Smaller, more concrete unit of work.
  - Fields: `task_id`, `title`, `description`, `parent_project_id`, `status`, `estimated_effort`, `due_at`.

- **Habit (subtype of Activity)**  
  Repeating activity with temporal pattern.
  - Fields: `habit_id`, `title`, `description`, `schedule_pattern`, `owner_id`.

- **Routine (subtype of Activity)**  
  Recurring, structured pattern of behaviour that may group habits and tasks (e.g. morning routine, weekly review).
  - Fields: `routine_id`, `title`, `description`, `schedule_pattern`, `owner_id`, `stability_score`.

- **Hobby (subtype of Activity, often AICO-owned)**  
  Activity primarily driven by AICO’s **intrinsic interest**, not just user-imposed.
  - Fields: `hobby_id`, `title`, `description`, `owner_id` (often `AICOAgent`), `intrinsic_value_tags`, `curiosity_link_strength`.

- **Goal**  
  Conceptual definition aligns with `agency-component-goals-intentions.md`:
  - A temporally extended desired world/mental/social state.  
  - Key links: `goal_id`, `owner_id`, `horizon`, `origin`, `state`, `priority`, `tags`.

- **LifeArea**  
  Conceptual domain of the user’s life that projects, habits, goals, and facts can affect.
  - Fields: `life_area_id`, `name` (e.g. Health, Work, Relationships, Learning, Creativity), `description`, `priority_score`.

- **Relations**
  - `HAS_GOAL(Activity|Hobby|Project, Goal)`
  - `PART_OF(Task, Project)`
  - `DERIVED_FROM(Goal_child, Goal_parent)` (goal decomposition graph)
  - `SUPPORTS(Activity|Task, Goal)` (task directly supports a goal)
  - `OWNED_BY(Activity|Goal|Hobby, User|AICOAgent)`
  - `FOCUSES_ON_HOBBY(Goal, Hobby)` – links agent-self or curiosity-origin goals to concrete Hobby activities they advance.
  - `IS_AGENT_SELF_GOAL(Goal)` – unary marker (can be modelled as a tag/flag) for goals whose `origin = agent_self` and whose primary beneficiary is AICO rather than the user.
  - `PART_OF_ROUTINE(Activity|Habit, Routine)` – links specific activities or habits to the routine that organises them.
  - `AFFECTS_LIFE_AREA(Activity|Goal|WorldStateFact, LifeArea)` – encodes which life areas are impacted by a given project, habit, goal, or fact.


### 4.3 Mental and Social State

- **EmotionState**  
  Coarse-grained emotional or affective label for AICO or user.
  - Fields: `emotion_id`, `label` (e.g. calm, stressed, curious, bored), `intensity`, `valence`, `source` (perceived, inferred, simulated), `timestamp`.

- **PersonaTrait**  
  Stable or slowly changing trait defining AICO’s personality.
  - Fields: `trait_id`, `name`, `description`, `value` (e.g. openness: 0.8).

- **Relationship**  
  Social relation between two actors.
  - Fields: `relationship_id`, `actor_a`, `actor_b`, `type` (friend, colleague, romantic, client, etc.), `closeness_score`, `trust_score`.

- **Relations**
  - `CURRENT_EMOTION(Subject, EmotionState)`
  - `HAS_TRAIT(AICOAgent, PersonaTrait)`
  - `RELATES(Person|AICOAgent, Person|AICOAgent, Relationship)`
  - `EMOTION_INFLUENCES_GOAL(EmotionState, Goal)` – conceptual link used by the Goal Arbiter to record that a particular emotional state biased the adoption, suppression, or reprioritisation of a goal (e.g., sustained stress increasing priority of rest-related goals).
  - `GOAL_AFFECTS_EMOTION(Goal, EmotionState)` – link from goals to typical emotional consequences (e.g., hobby or relationship goals associated with positive affect), used by planning and curiosity to prefer emotionally beneficial pursuits when values/safety allow.

These types are used by the **Emotion/Personality/Social** components and influence **Goal origins, priorities, and Arbiter decisions**.


### 4.4 World, Environment, Sensors

- **Place / Location**  
  Physical or virtual place.
  - Fields: `place_id`, `name`, `type` (room, city, virtual_room, url), `coordinates_or_locator`.

- **Device**  
  Device providing sensors or actuation.
  - Fields: `device_id`, `type` (phone, laptop, camera, microphone, IoT_sensor), `owner_id`, `capabilities`.

- **SensorObservation**  
  Low-level reading from a sensor.
  - Fields: `observation_id`, `sensor_id`, `timestamp`, `raw_value`, `units`, `confidence`.

- **PerceptualEvent**  
  The **central interpreted event unit** consumed by the agency subsystem, already defined at high level in other docs. Here we define the core ontology for it.

  Minimal conceptual slots:
  - Identity: `percept_id`, `timestamp`, `source_component` (conversation_engine, world_model, ams, sensor_adapter, external_service_adapter, scheduler, etc.).
  - Type: `percept_type` (see 5.1 Event taxonomy).
  - Natural-language: `summary_text`.
  - Structured slots (examples):
    - `actors` (list of Person/AICOAgent IDs or entity refs),
    - `topic_tags` (strings/ontology tags),
    - `time_window` (start, end, granularity),
    - `location_ref` (Place ID or descriptor),
    - `salience_score`,
    - `urgency_score`,
    - `risk_score`,
    - `opportunity_score`,
    - `confidence_score`.
  - Provenance:
    - `raw_observation_ids` (link to SensorObservation, message IDs, logs),
    - `interpretation_chain` (which components or LLM calls produced/refined it).

- **Relations**
  - `OBSERVED_AT(PerceptualEvent, Place)`
  - `OBSERVED_ON_DEVICE(PerceptualEvent, Device)`
  - `ABOUT(PerceptualEvent, Person|Activity|Goal|Hobby|EnvironmentContext)`
   - `LOCATED_IN(Activity|Device|WorldStateFact, Place)` – captures where an activity typically occurs, where a device is used, or where a fact is situated.


### 4.5 Knowledge, Memory, and Facts

- **MemoryItem**  
  Persistent memory entry in the Adaptive Memory System (AMS).
  - Fields: `memory_id`, `type` (episodic, semantic, preference, pattern, reflection), `summary_text`, `slots` (JSON-like), `created_at`, `last_accessed_at`, `importance_score`, `source_percept_id`.

- **WorldStateFact**  
  Fact or belief about the world (or the user/AICO) in the World Model.
  - Fields: `fact_id`, `subject_entity_id`, `predicate`, `object`, `validity_interval`, `confidence`, `source_percept_ids`, `value_safety_flags` (e.g., `is_sensitive_domain`, `requires_explicit_consent`, `high_risk_context`).

- **Skill / Tool**  
  Capability AICO can invoke.
  - Fields: `skill_id`, `name`, `description`, `input_schema_id`, `output_schema_id`, `side_effect_tags`, `safety_level`.

- **Relations**
  - `REALISES(WorldStateFact, Goal)` (fact satisfies or contributes to goal conditions)
  - `REFERENCES(MemoryItem, Goal|Activity|Person|Hobby)`
  - `LEARNED_FROM(MemoryItem, PerceptualEvent)`
  - `AVAILABLE_TO(AICOAgent, Skill)`
  - `DERIVED_FROM(WorldStateFact, MemoryItem)` – links stable facts in the World Model back to AMS memories from which they were inferred.
  - `EVIDENCED_BY(WorldStateFact, PerceptualEvent)` – provenance link from facts to supporting PerceptualEvents.


## 5. Perceptual Event Taxonomy

This is a **taxonomy of `percept_type` values** that upstream components must use when constructing `PerceptualEvent`s. It is global and stable.

### 5.1 Top-Level Percept Types

- **UserIntentEvent**  
  Interpreted user intention, typically from conversation.
  - Example: "User wants to study for exam X next week".

- **StateChangeEvent**  
  Change in world, system, or user state.
  - Example: calendar event added/changed; deadline approaching; CPU usage spike.

- **PatternEvent**  
  AMS or World Model detects a pattern or anomaly.
  - Example: "User tends to work late before deadlines"; "Drop in mood correlated with social media use".

- **SocialEvent**  
  Social interaction or relationship-relevant signal.
  - Example: message from a key contact; relationship conflict; new connection relevant to a project.

- **RiskOrOpportunityEvent**  
  Something that may harm or benefit the user or AICO's long-term objectives.
  - Example: overwork risk, health opportunity, learning opportunity, hobby opportunity.

- **SystemMaintenanceEvent**  
  Events related to AICO’s own health, resources, or configuration.
  - Example: model performance degradation, memory saturation, safety profile change.

- **CuriositySignalEvent**  
  Internal signal from the Curiosity Engine.
  - Example: "Unexplored pattern in user’s creative work"; "Under-explored hobby area".


### 5.2 PerceptualEvent → Goal / Intention Links

Every PerceptualEvent may:

- **Propose a new Goal** (e.g. a UserIntentEvent mapping to a new task/project goal).
- **Update existing Goals** (change priority, state, or supporting evidence).
- **Trigger curiosity-driven activities** (CuriositySignalEvent → new `agent_self` or `hobby` goals).

Data fields (conceptual, aligned with Goals doc):

- `candidate_goal_summaries` (list of suggested NL goal titles/descriptions).
- `candidate_goal_horizon` (suggested horizon: theme / project / task).
- `candidate_origin` (user / agent_self / curiosity / system_maintenance).

The **Goals & Intentions component** is responsible for consuming these and deciding which become actual goals, but the ontology ensures all components use the same structure.


## 6. How and Where the Ontology is Used

This section ties the ontology to concrete components described in other agency docs.

### 6.1 Perception / Sensors Layer

- **Upstream owners**: Conversation Engine, AMS/World Model, sensor adapters, external service adapters.
- **Responsibilities**:
  - Map raw signals (messages, logs, sensor readings, API payloads) into:
    - `SensorObservation` nodes (optional, when low-level data is persisted).
    - `PerceptualEvent` nodes structured according to this doc.
  - Use the **Perceptual Event Taxonomy** (Section 5) to set `percept_type`.
  - Populate **provenance** fields and **candidate goal metadata** where applicable.

### 6.2 World Model Service / KG+Schemas

- Represents **Person, User, AICOAgent, Activity, Project, Task, Habit, Hobby, Place, Device, MemoryItem, WorldStateFact, Skill** as nodes and edges according to Section 4.
- Uses PerceptualEvents as **ingestion edges**:
  - `LEARNED_FROM(MemoryItem, PerceptualEvent)`
  - `REALISES(WorldStateFact, Goal)` via events that confirm success.
- Provides schema-aware APIs to other components (see `agency-component-world-model.md`).

### 6.3 Goals & Intentions Component

- Consumes PerceptualEvents and:
  - Creates/updates **Goal** nodes and their graph structure.
  - Links goals to Activities, Hobbies, Persons, WorldStateFacts.
- Uses ontology relations:
  - `HAS_GOAL(Activity, Goal)`
  - `DERIVED_FROM(Goal_child, Goal_parent)`
  - `SUPPORTS(Task, Goal)`.
- Tracks provenance via:
  - `last_percept_event_id` and related fields described in `agency-component-goals-intentions.md`.

### 6.4 Curiosity Engine

- Reads from World Model and AMS using ontology types:
  - Under-represented topics, patterns, or Hobbies.
- Emits **CuriositySignalEvent** PerceptualEvents.
- Proposes new `agent_self` or `hobby` Goals that are clearly distinguished by `origin` and `owner_id`.

### 6.5 Values, Ethics, and Safety

- Uses ontology structure to:
  - Identify **actors** (User vs others vs AICO) involved in actions.
  - Understand **relations** (e.g. closeness of relationship).
  - Assess **risk/opportunity** based on tagged types and scores.
- Can apply policies conditioned on:
  - Percept types (e.g. special scrutiny for `RiskOrOpportunityEvent`).
  - Entity types (e.g. stricter rules for financial activities).

### 6.6 Metrics and Explainability

- Metrics in `agency-metrics.md` refer to ontology-based entities:
  - Goals by horizon/origin/state.
  - PerceptualEvents by type, salience, origin component.
  - Hobby-related goals and activities.
- Explainability:
  - When explaining why AICO did something, references are:
    - `PerceptualEvent` chain,
    - linked `MemoryItem`s and `WorldStateFact`s,
    - related `Goal`s and `Activity` objects.


## 7. Representation and Implementation Notes

- **Primary store**: property/knowledge graph (e.g. nodes and edges), plus:
  - **JSON-like schemas** for PerceptualEvents, MemoryItems, Goals, Skills.
- **We do not require** heavy OWL reasoning in v1.  
  Reasoning is largely delegated to:
  - LLM-based components (goal interpretation, planning, explanation).
  - Lightweight rules and validators (type checks, policy checks, referential integrity).
- **Schema evolution**:
  - Core types and relations in Section 4 and Section 5 must remain stable or evolve via explicit migrations.
  - Domain- and feature-specific extensions must not violate the meaning of core types.


## 8. References and Cross-Links

- `docs/concepts/agency/agency.md` – overall concept of Agency.
- `docs/concepts/agency/agency-architecture.md` – architecture and Perception/Sensors layer.
- `docs/concepts/agency/agency-component-world-model.md` – world model and knowledge/property graph integration.
- `docs/concepts/agency/agency-component-goals-intentions.md` – detailed goal/intention data model and operations.
- `docs/concepts/agency/agency-component-curiosity-engine.md` – curiosity-driven signals and agent-self/hobby goals.
- `docs/concepts/agency/agency-component-values-ethics.md` – values, ethics, and safety policies consuming ontology types.
