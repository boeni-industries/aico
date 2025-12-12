---
title: Agency Component – World Model & Knowledge Graph
---

# World Model & Knowledge/Property Graph

## 1. Purpose

The World Model component maintains AICO’s structured understanding of **people, entities, situations, routines, and environments**. It is a **hybrid world model**, informed by recent research, that combines:

- an explicit **knowledge/property graph** and JSON schemas (see `agency-ontology-schemas.md`) as the canonical store of entities and relations,  
- **semantic memory and embeddings** for similarity, clustering, and soft generalisation, and  
- an **LLM-based "simulator lens"** that can roll forward plausible futures and counterfactuals over the structured state (for planning, explanation, and self‑reflection).

The primary focus is on **social and everyday-life world modelling** rather than low-level physics: people, relationships, projects, habits, hobbies, and daily/weekly routines are first‑class. The World Model must:

- support **graph-augmented queries** and simulations needed by planning, goal selection, curiosity, self‑reflection, and Values/Ethics,  
- stay continuously reconciled with real observations via PerceptualEvents, and  
- treat ethical, safety, and privacy concerns as built‑in design constraints when representing and using detailed knowledge about the user’s life.


## 2. Conceptual Model

This section describes what the World Model "is" at a conceptual level and how it relates to other components.

### 2.1 Core Concepts

- **Explicit, symbolic backbone**  
  The World Model is first and foremost an explicit **knowledge/property graph** and associated JSON schemas, as defined in `agency-ontology-schemas.md`. It represents:
  - **Who**: Person/User/AICOAgent and their relationships.  
  - **What**: Activities, Projects, Tasks, Habits, Hobbies, Skills/Tools, MemoryItems, WorldStateFacts.  
  - **Where/When**: Places, Devices, temporal scopes (e.g., daily/weekly routines).  
  - **Why/How**: links between goals, plans, outcomes, and facts.

- **Complementary semantic memory and embeddings**  
  Alongside the graph, the World Model maintains:
  - **Semantic memory views** over AMS (e.g., important episodes, reflections, preferences keyed by entities or life areas).  
  - **Embedding indices** for “soft” queries such as:  
    - "days that look similar to today",  
    - "people similar to this contact",  
    - "projects similar to this one that went well/badly".

- **LLM as simulator, not database**  
  LLM-based components **consume** the structured state from the World Model to:
  - simulate plausible futures and counterfactuals over current state,  
  - generate explanations and narratives grounded in graph facts,  
  - propose hypotheses and candidate updates.  
  They do **not** replace the World Model as the source of record; any durable knowledge must be written back as explicit `WorldStateFact`s or related entities.

- **Confidence and temporal awareness**  
  Each fact in the World Model has some notion of:  
  - **confidence** (how strongly AICO currently believes it), and  
  - **temporal scope** (when it was true, last observed, or last refreshed).  
  Other components are encouraged to take these into account rather than treating the World Model as an infallible oracle.


### 2.2 Represented Domains

The World Model focuses on **social and everyday-life structure**, not full physical simulation. Domains are **extensible over time** via the shared ontology in `agency-ontology-schemas.md`; what follows is the initial core set.

- **User life areas and themes**  
  - Long‑term concerns (e.g., health, work, creativity, relationships, learning).  
  - How current projects and habits map onto these areas.

- **Projects, tasks, habits, and routines**  
  - Ongoing and past projects and their relationships (dependencies, shared participants, shared resources).  
  - Repeating habits and routines (e.g., typical sleep times, work blocks, exercise patterns), with uncertainty where data is sparse.

- **People and relationships**  
  - Key people in the user’s life, relationship types and strengths, roles (family, colleagues, clients, etc.).  
  - Relevant social contexts (e.g., household, team, communities).

- **Places, devices, and environments**  
  - Places meaningful to the user (home, work, gym, frequent digital spaces).  
  - Devices through which AICO perceives and acts (phone, laptop, sensors), with ownership and capabilities.

- **Hobbies, interests, and value‑laden domains**  
  - User’s stated and inferred hobbies and interests, with links to activities, memories, and emotional patterns.  
  - Domains where Values/Ethics impose special handling (e.g., health, finance, intimate relationships).

Domains that require **detailed external knowledge** (e.g., medical knowledge, global news) are typically fetched from external services and represented in the World Model only to the extent needed to ground goals, explanations, and safety reasoning.


### 2.3 Relationship to AMS and PerceptualEvents

- **From PerceptualEvents to WorldStateFacts and MemoryItems**  
  - PerceptualEvents provide the interpreted, semantic view of new information (see `agency-ontology-schemas.md`).  
  - For each relevant event, ingestion logic may:  
    - create or update **WorldStateFacts** (e.g., "user started a new project", "relationship status changed"), and/or  
    - create or update **MemoryItems** in AMS (episodic or reflective entries linked back to the same entities).

- **Continuous reconciliation and drift detection**  
  - As new PerceptualEvents arrive, the World Model must detect:  
    - **inconsistencies** (e.g., two incompatible facts about a job, relationship, or schedule), and  
    - **drifts** (e.g., habits that have changed over time).  
  - These are either resolved automatically (e.g., by favouring more recent, higher‑confidence evidence) or escalated as hypotheses to be clarified via planning, curiosity, or direct user questions.

- **Structured views for other components**  
  - Planning and Goals use the World Model to answer questions like:  
    - "What projects exist in this life area?",  
    - "Who is affected by this goal?",  
    - "What constraints (time, relationships, places) apply here?"  
  - The Curiosity Engine queries it for:  
    - under‑represented or highly uncertain regions of the user’s life,  
    - patterns that suggest potential hobbies or agent‑self learning opportunities.  
  - Values/Ethics uses it to understand **actors, relationships, and contexts** when evaluating plans and initiatives.

- **AMS as companion, not duplicate**  
  - AMS focuses on **how experiences are stored and compressed over time** (episodic, semantic, reflective memories).  
  - The World Model focuses on the **current structural picture** and its evolution.  
  - Links between AMS and the World Model (via shared entity IDs and provenance fields) ensure that structural facts are always traceable back to concrete experiences.


## 3. Data Model

This section will specify the concrete data structures and schemas the World Model exposes, building directly on `agency-ontology-schemas.md`.

### 3.1 Core Entity and Relation Types

At the ontology level, the World Model **reuses** all core entities defined in `agency-ontology-schemas.md` (Person, User, AICOAgent, Activity/Project/Task/Habit/Hobby, Goal, EmotionState, Relationship, Place, Device, MemoryItem, WorldStateFact, Skill, PerceptualEvent) and adds a **small, explicit set of extensions**. These must be treated as concrete schema changes to the shared AMS knowledge graph.

The World Model graph is expected to **build on and extend** the existing knowledge graph infrastructure used by AMS (`/docs/concepts/memory`), using the **same underlying persistence/DB** (current implementation: libSQL-backed property graph) but richer schemas and views.

Concretely, v1 of the World Model requires the following **schema extensions**:

- **New node types**  
  - `Routine` (subtype of Activity) – recurring, structured pattern of behaviour.  
    - Fields (conceptual): `routine_id`, `title`, `description`, `schedule_pattern`, `owner_id`, `stability_score`.  
  - `LifeArea` – conceptual domain of the user’s life.  
    - Fields: `life_area_id`, `name` (e.g., Health, Work, Relationships, Learning, Creativity), `description`, `priority_score`.

- **New / extended relations**  
  - `PART_OF_ROUTINE(Activity|Habit, Routine)` – links specific activities or habits to the routine that organises them.  
  - `LOCATED_IN(Activity|Device|WorldStateFact, Place)` – captures where an activity typically occurs, where a device is used, or where a fact is situated.  
  - `AFFECTS_LIFE_AREA(Activity|Goal|WorldStateFact, LifeArea)` – encodes which life areas are impacted by a given project, habit, goal, or fact.  
  - `DERIVED_FROM(WorldStateFact, MemoryItem)` – links stable facts in the World Model back to the AMS memories from which they were inferred.  
  - `EVIDENCED_BY(WorldStateFact, PerceptualEvent)` – finer-grained provenance link to the PerceptualEvents that support a fact.

- **Additional attributes on existing types**  
  - On `WorldStateFact` (extending the definition in the ontology doc):  
    - `validity_interval` (start/end or open interval),  
    - `confidence` (0–1 or bucketed),  
    - `source_percept_ids` (list of PerceptualEvent IDs; can be normalised via `EVIDENCED_BY` edges),  
    - `value_safety_flags` (e.g., `is_sensitive_domain`, `requires_explicit_consent`, `high_risk_context`).  
  - On `Relationship`, `Activity` and `Habit` (optional but recommended for WM quality):  
    - temporal metrics (e.g., `first_seen_at`, `last_updated_at`),  
    - stability / regularity scores where applicable.

- **New logical views on the shared KG**  
  These are **query-layer constructs**, not new storage, but they must be specified so implementations expose them consistently:  
  - **Life-area subgraphs** – filtered view over entities and facts grouped by `LifeArea` via `AFFECTS_LIFE_AREA`.  
  - **Routine timelines** – view that orders `Routine` and their linked activities/habits over time.  
  - **Relationship-centric egonets** – view for a person’s local social graph (Persons, Relationships, shared Activities/Goals).

All of the above are to be introduced by **updating `agency-ontology-schemas.md` and the libSQL/graph schema used by AMS**, not by creating a separate graph database for the World Model.

### 3.2 Storage and Indexing Views

The World Model shares the **same physical store** as AMS (libSQL-backed property/knowledge graph) but exposes several **logical views** optimised for different consumers. Conceptually, the same entities are accessible via:

- **Graph views (primary source of record)**  
  - Nodes and edges as per `agency-ontology-schemas.md` (Person, Activity, Routine, LifeArea, WorldStateFact, etc.).  
  - Used for:
    - neighbourhood/constraint queries in planning,  
    - social/relationship reasoning,  
    - life-area and routine analyses.

- **Denormalised SQL tables / materialised views**  
  These are read-optimised projections over the graph, implemented as SQL tables or materialised views in the same libSQL database. Examples:
  - `wm_projects_by_life_area` – rows linking `project_id` ↔ `life_area_id` with cached aggregates (e.g. number of active tasks, last_activity_at).  
  - `wm_routines` – routine-level table (`routine_id`, schedule descriptors, stability metrics) plus derived fields useful for scheduling and explanation.  
  - `wm_social_egonets` – per-person summary rows (counts of relationships by type, centrality scores, last_interaction_at).  
  - `wm_world_facts_index` – flat index over `WorldStateFact` (`fact_id`, `subject_entity_id`, `predicate`, `object_type`, `is_current`, `life_area_ids`, `confidence_bucket`).  
  These tables should be **rebuildable** from the graph and used for hot-path queries (dashboards, planners, curiosity scans).

- **Embedding indices**  
  For soft similarity and pattern discovery, the World Model maintains embedding stores (can be implemented as:
  - separate tables in libSQL with `vector`-like columns, or
  - external vector DB, as long as IDs map back to graph entities).

  Typical indices:
  - `wm_day_signature_embeddings` – summarised embeddings of days/sessions linked to `MemoryItem`/PerceptualEvent IDs, used for "days like this" queries.  
  - `wm_entity_profile_embeddings` – embeddings for Persons, Projects, Hobbies generated from their linked memories and facts, enabling similarity-based retrieval (e.g. similar projects that succeeded/failed).  
  - `wm_routine_pattern_embeddings` – embeddings of routines/habits based on temporal patterns and associated emotions.

Implementations are free to choose the exact physical layout, but must:
- honour the **ontology IDs and types** as the primary key space, and  
- ensure that any denormalised/embedding view is **losslessly traceable** back to the underlying graph nodes/edges.

### 3.3 Provenance and Versioning

The World Model must make it possible to answer: *"Why does AICO believe this, and how current is that belief?"* This requires explicit provenance and a lightweight versioning model.

- **Per-fact provenance**  
  - `WorldStateFact` carries:  
    - `source_percept_ids` – list of PerceptualEvent IDs that first introduced or last updated the fact.  
    - `validity_interval` – `valid_from` / `valid_to` or open interval, reflecting when the fact was believed true.  
    - `confidence` – scalar or bucket used by downstream components.  
    - `value_safety_flags` – marks facts in sensitive domains (health, finance, intimate relationships, etc.).  
  - Graph-level edges complement these fields:  
    - `DERIVED_FROM(WorldStateFact, MemoryItem)` – links to underlying AMS memories.  
    - `EVIDENCED_BY(WorldStateFact, PerceptualEvent)` – explicit evidence edges, allowing traversal from fact → events → raw inputs.

- **Entity-level provenance**  
  - Core entities (Person, Activity, Routine, LifeArea) should record at least:  
    - `created_at`, `last_updated_at`,  
    - `created_by_component`, `last_updated_by_component` (e.g., world_model_ingestor, goals_system, curiosity_engine),  
    - `provenance_score` or similar indicator of how well-grounded the entity is (number/diversity of supporting events and memories).

- **Soft versioning and conflict handling**  
  - Instead of heavy-weight version branches, we treat conflicting beliefs as **multiple facts with different validity intervals and confidences**:  
    - e.g., two `WorldStateFact`s about job title with overlapping or disjoint intervals.  
  - Consistency logic (Section 2.3) operates over these:  
    - marks older/low-confidence facts as **superseded** or **hypothesis**;  
    - may raise CuriositySignals or questions for the user when high-impact conflicts persist.

- **Audit trail for critical changes**  
  - For selected predicates and domains (health, finance, permissions, safety-critical configuration), the World Model (or AMS layer beneath it) should keep a **change log table** with:  
    - `change_id`, `entity_id`/`fact_id`, `changed_field`, `old_value`, `new_value`, `timestamp`, `actor`/component, `triggering_percept_id`.  
  - This log is primarily for:
    - explainability to the user ("when did this belief change?");  
    - debugging of agent behaviour during development and evaluation.

This provenance and versioning model is intentionally **lightweight**: it is rich enough to support explanation, safety review, and curiosity-driven reconciliation, without imposing a full temporal-DB or git-like history on every entity.


## 4. Operations / APIs

This section outlines the main **operation categories** the World Model service supports. Exact transport (HTTP, gRPC, in-process) is implementation-specific; the important part is the **behavioural contract** and how it interacts with AMS, Goals, Curiosity, and Values/Ethics.

### 4.1 Ingestion Operations

- **Ingest PerceptualEvent → update graph**  
  - Input: a `PerceptualEvent` (ID + full payload) plus optional hints from upstream (e.g. suggested entities/goals).  
  - Behaviour:  
    - resolve or create referenced entities (Person, Activity, Goal, etc.) using ontology IDs;  
    - create or update `WorldStateFact`s and their provenance edges (`EVIDENCED_BY`, `DERIVED_FROM` when AMS memories are present);  
    - update relevant Routine/LifeArea relations (`PART_OF_ROUTINE`, `AFFECTS_LIFE_AREA`) where patterns are clear;  
    - record consistency/hypothesis flags when conflicts are detected.  
  - Output: summary of changes (entities/facts upserted, conflicts detected, hypotheses opened).

- **Upsert entity / relation**  
  - Generic operations to create/update ontology entities (Person, Activity, Routine, LifeArea, Place, Device, etc.) and relations between them.  
  - Expected to be used by:  
    - AMS consolidation jobs,  
    - Goal & Intention System (e.g. when creating new projects/tasks/goals),  
    - external service adapters (calendar, task managers, CRMs).

- **Assert / retract fact**  
  - `assert_fact` – insert or update a `WorldStateFact` with given subject/predicate/object, optional validity interval, and provenance (percept IDs, source component).  
  - `retract_fact` – mark a fact as obsolete or incorrect, with reason and provenance (e.g. corrected user input, external override), optionally soft-deleting or closing its validity interval.  
  - Both operations must:  
    - keep provenance complete enough for later explanation;  
    - trigger consistency checking when predicates are known to be high-impact (employment, relationship status, health markers, permissions, safety configuration).

### 4.2 Query Operations

- **Graph neighbourhood / constraint queries**  
  - Input: seed entities (Person, Goal, Activity, Place, LifeArea) and query parameters (radius, relation filters, time filters).  
  - Output: subgraph view (nodes + edges + selected attributes) suitable for:  
    - planning (constraints, resources, dependencies),  
    - Values/Ethics (actors, relationships, sensitive domains),  
    - explanation (who/what/where/why context around a decision).

- **Life-area and routine summaries**  
  - Operations that expose the denormalised views defined in Section 3.2, for example:  
    - `get_life_area_overview(user_id)` – for each `LifeArea`, return key projects, habits, recent WorldStateFacts, and risk/opportunity signals.  
    - `get_routines_for_person(person_id)` – list routines, their stability, and linked activities/habits.  
  - Used by:  
    - Goal & Intention System (for goal selection and rebalancing),  
    - Curiosity Engine (for under-represented or unstable areas),  
    - front-end and explanation views.

- **Fact lookup and reasoning support**  
  - `get_facts(subject_id, predicate_filter, time_range, min_confidence)` – retrieve WorldStateFacts with provenance, suitable for planners and Values/Ethics.  
  - `get_conflicting_facts(subject_id, predicate)` – return sets of overlapping/contradictory facts, annotated with confidence and recency.  
  - `get_fact_explanation(fact_id)` – return the chain: fact → PerceptualEvents → MemoryItems → raw observations (IDs), using the provenance model from Section 3.3.

- **Similarity / pattern queries (via embeddings)**  
  - Operations that leverage the embedding indices (Section 3.2):  
    - `find_similar_days(reference_day_id, k)` – for experience-based recommendations and reflection.  
    - `find_similar_projects(project_id, k)` – for planning and risk estimation.  
    - `suggest_related_hobbies_or_routines(person_id)` – for curiosity and well-being support.

### 4.3 Hypothesis and Consistency Operations

- **Hypothesis management**  
  - `open_hypothesis(hypothesis_id, description, affected_entities, initial_evidence)` – create a tracked, named hypothesis (e.g. "user is changing jobs", "sleep pattern is improving").  
  - `update_hypothesis(hypothesis_id, new_evidence, confidence_delta, status)` – attach new PerceptualEvents/WorldStateFacts and adjust confidence/state (open, confirmed, rejected, needs_user_confirmation).  
  - Hypotheses should be first-class objects linkable from CuriositySignals, Goals, and explanations.

- **Consistency and drift checks**  
  - `run_consistency_check(scope)` – evaluate selected predicates/entities or global invariants (e.g. one primary employer at a time, mutually exclusive relationship states).  
  - `detect_drifts(entity_id or pattern_spec)` – analyse temporal changes in routines, habits, or emotional patterns (using both facts and embeddings).  
  - Outputs:  
    - structured reports of conflicts/drifts,  
    - suggested resolutions (e.g. favour more recent evidence, open hypothesis, ask user, suppress low-confidence fact),  
    - optional CuriositySignals to be emitted.

- **Integration with other components**  
  - Goal & Intention System may:  
    - query open hypotheses to prioritise clarification goals;  
    - receive notifications when hypotheses about key domains (health, work, relationships, agent-self) change state.  
  - Curiosity Engine may:  
    - request targeted consistency/drift checks for under-explored regions;  
    - create hypotheses when it detects interesting but uncertain patterns.  
  - Values/Ethics may:  
    - veto or constrain automatic resolutions in sensitive domains;  
    - require explicit user confirmation before certain hypotheses are treated as confirmed.


## 5. Interaction Semantics

This section describes **behavioural rules over time** – how the World Model behaves beyond individual API calls.

### 5.1 Conflict handling and belief updates

- **Multiple facts, not silent overwrite**  
  - When new evidence about a predicate arrives (e.g. job, relationship status), the World Model **adds or updates `WorldStateFact`s with explicit validity intervals and confidences** rather than blindly overwriting old entries.  
  - Conflicts are represented as:
    - overlapping or incompatible facts for the same subject/predicate, and/or  
    - sharp confidence shifts on previously stable facts.

- **Resolution strategy**  
  - For low-impact predicates, simple heuristics apply:
    - favour more recent, higher-confidence evidence;  
    - mark older/contradicted facts as `superseded` but keep them for history and explanation.  
  - For high-impact domains (health, finance, permissions, safety-critical configuration, close relationships), the default is **caution**:
    - keep both versions as separate facts;  
    - open or update a **hypothesis** (Section 4.3);  
    - optionally request user confirmation via Goals/Conversation;  
    - allow Values/Ethics to veto automatic resolution.

- **Surface conflicts, don’t hide them**  
  - Query operations (Section 4.2) that retrieve facts for sensitive domains must be able to indicate "there is a conflict" rather than returning a single, cleaned-up answer.  
  - Downstream components (planning, Values/Ethics, Curiosity) can then decide whether to pause, clarify, or proceed conservatively.


### 5.2 Confidence, recency, and what is exposed

- **Context-aware filtering**  
  - Default query behaviour is to emphasise **recent, higher-confidence facts**, but callers can override this via parameters (e.g. to inspect historical state).  
  - For each returned fact, the World Model should expose at least:  
    - `confidence` (or bucket),  
    - `validity_interval` and `last_updated_at`,  
    - whether it is `current`, `superseded`, or `hypothesis`.

- **Safety-aware exposure**  
  - Facts tagged with sensitive `value_safety_flags` may be:
    - hidden from non-privileged components, or  
    - returned only in aggregated/obfuscated form, as dictated by Values/Ethics and configuration.  
  - User-facing explanations should respect these flags and safety policies when deciding how much detail to present.

- **Explainability-first**  
  - For any fact or pattern that materially influences agent behaviour (goal choice, plan selection, strong recommendation), the World Model must be able to support:  
    - a short, human-readable explanation rooted in its provenance (Section 3.3);  
    - a more detailed technical trace (PerceptualEvents, MemoryItems, change-log entries) for debugging.


### 5.3 Interaction with AMS and consolidation

- **Bidirectional flow with AMS**  
  - AMS writes: consolidated memories and learned patterns feed new or updated `WorldStateFact`s (e.g. new habits, correlations).  
  - AMS reads: World Model facts and structures influence which experiences are selected for consolidation and reflection (e.g. emphasising emerging routines or unstable relationships).

- **Sleep-like consolidation cycles**  
  - During off-peak times, the World Model participates in scheduled consolidation:
    - recomputing routines and LifeArea mappings from recent data;  
    - pruning or down-weighting stale, low-impact facts;  
    - updating embedding indices and denormalised views;  
    - revisiting open hypotheses to see if new evidence has arrived.

- **No direct ownership of raw traces**  
  - The World Model does not own raw sensor data or full conversation logs; it relies on AMS and Perception to manage those.  
  - Its responsibility is to maintain a **clean, structured, and explainable slice** of the user’s ongoing life that other components can safely rely on.


### 5.4 Collaboration with Goals, Curiosity, and Values/Ethics

- **Goals & Intentions**  
  - Uses the World Model to:
    - ground goals in concrete entities (projects, people, places, LifeAreas);  
    - assess impact and feasibility (constraints, dependencies, conflicts);  
    - select clarification goals for open hypotheses.  
  - In turn, goal decisions can update the World Model (e.g. marking a project as active, associating goals with LifeAreas).

- **Curiosity Engine**  
  - Reads the World Model to detect **gaps, anomalies, and under-explored regions** (sparse facts, low coverage in certain LifeAreas, unstable routines).  
  - Opens hypotheses and emits CuriositySignals that point back to specific entities and facts.  
  - Its actions are constrained by:
    - safety flags on facts and entities;  
    - values/ethics policies that mark some areas as off-limits or user-consent-only.

- **Values/Ethics**  
  - Uses the World Model as the structured source for:
    - identifying affected actors and relationships;  
    - locating actions within sensitive life domains;  
    - checking relevant history and patterns (e.g. burnout risk, recurring conflicts).  
  - May enforce policies such as:  
    - blocking automatic updates in certain domains without user confirmation;  
    - masking or aggregating facts before they are passed to non-privileged components;  
    - requiring explicit representation of uncertainty for risky decisions.


### 5.5 LLM simulator lens and world model integrity

- **One-way grounding constraint**  
  - LLM components **read** from the World Model to simulate futures, generate counterfactuals, and produce narratives.  
  - They may **propose** candidate updates (new facts, entity states, hypotheses), but these must go through the same ingestion and safety checks as any other source.  
  - LLMs are never treated as an oracle that can directly mutate the graph without provenance.

- **Guardrails for hallucinations**  
  - The World Model acts as a **hard grounding constraint**: if an LLM-generated plan or explanation contradicts high-confidence facts, planners and Values/Ethics should prefer the graph or require explicit user override.  
  - Only when evidence accumulates (via PerceptualEvents, AMS patterns, user confirmation) should the graph itself change, not simply because the LLM narrative suggested it.


## 6. Examples

This section gives short, non-code walkthroughs of typical World Model flows.

### 6.1 User project represented in the graph

- A user tells AICO they want to "prepare a portfolio for a new design job".  
- Goals & Intentions creates a `Goal` and a `Project` (subtype of Activity), both owned by the `User`, and links them via `HAS_GOAL(Project, Goal)`.  
- The World Model ensures:
  - a `Project` node with fields populated (title, description, status, tags),  
  - a `Goal` node with `origin = user`, appropriate `horizon` and `priority`,  
  - relations:  
    - `OWNED_BY(Project, User)` and `OWNED_BY(Goal, User)`,  
    - `HAS_GOAL(Project, Goal)`,  
    - `AFFECTS_LIFE_AREA(Project, LifeArea: Work)`.
- As the user works on tasks and shares progress, additional `Task` nodes, `MemoryItem`s, and `WorldStateFact`s (for example "portfolio draft completed") are linked into the same subgraph.  
- When planners, Curiosity, or Values/Ethics query the World Model for current work-related projects, this project appears as part of the Work life-area subgraph with its linked facts and goals.

### 6.2 From PerceptualEvent to WorldStateFact

- A calendar integration notices a new recurring event: "Morning run" three times a week, tagged as a workout.  
- Perception constructs a `PerceptualEvent` of type `StateChangeEvent` with:  
  - `actors = [User]`,  
  - `topic_tags = ["exercise", "health"]`,  
  - a `time_window` set to the scheduled slots,  
  - a `location_ref` pointing to `Place: neighbourhood`.
- The ingestion operation "Ingest PerceptualEvent and update graph" (Section 4.1):  
  - creates or updates a `Habit` ("morning run") and, if appropriate, a `Routine` ("weekday morning routine"),  
  - asserts a `WorldStateFact` such as:  
    - subject: `Habit: morning_run`, predicate: `has_schedule_pattern`, object: structured schedule,  
  - sets provenance fields and edges:  
    - `source_percept_ids = [percept_id]`,  
    - `EVIDENCED_BY(WorldStateFact, PerceptualEvent)`,  
  - adds `AFFECTS_LIFE_AREA(Habit: morning_run, LifeArea: Health)` and optionally `LOCATED_IN(Habit: morning_run, Place: neighbourhood)`.
- Later, when planning or Values/Ethics evaluate suggestions about health or time allocation, they can query the World Model for current health-related habits and see this fact and its provenance.

### 6.3 Hypothesis lifecycle

- Over a few weeks, AMS and Perception produce PerceptualEvents indicating the user:  
  - interacts less with colleagues on work channels,  
  - browses job listings,  
  - mentions being "tired of current job" in conversation.
- The World Model ingests these events and, via consistency and drift checks (Section 4.3), detects a pattern inconsistent with previously stable `WorldStateFact`s about job satisfaction and stability.  
- A hypothesis is opened:  
  - `hypothesis_id = H1`, description: "User is considering changing jobs",  
  - linked entities: `User`, `LifeArea: Work`, relevant `Project`s,  
  - initial evidence: recent PerceptualEvents and `MemoryItem`s.
- Interaction semantics (Section 5) apply:
  - Curiosity Engine may generate a CuriositySignal to explore this area gently (for example by asking reflective questions or suggesting a check-in).  
  - Goals & Intentions may propose a clarification goal ("Clarify work situation or career direction").  
  - Values/Ethics ensures any action respects sensitivity flags (career decisions, well-being).
- As new evidence arrives (for example an explicit statement from the user or new employment details), the hypothesis is updated:  
  - if confirmed, relevant `WorldStateFact`s are updated (for example new employer, changed job satisfaction),  
  - older inconsistent facts become `superseded`,  
  - the hypothesis transitions to `confirmed` or `rejected` and remains linked for future explanations of why certain plans or goals were suggested.


## 7. References & Cross‑Links

- `docs/concepts/agency/agency.md` – overall concept of Agency and the role of world modelling.  
- `docs/concepts/agency/agency-architecture.md` – architecture sections on Intelligence & Memory domain and World Model Service.  
- `docs/concepts/agency/agency-ontology-schemas.md` – canonical ontology and schemas for entities/facts represented here.  
- `docs/concepts/agency/agency-component-goals-intentions.md` – how goals reference world model entities and provenance.  
- `docs/concepts/agency/agency-component-curiosity-engine.md` – how curiosity uses world model gaps and patterns.

External research (non‑exhaustive):

- *Understanding World or Predicting Future? A Comprehensive Survey of World Models* (ACM CSUR, 2024/2025).  
- Park, J. S. et al. (2023). *Generative Agents: Interactive Simulacra of Human Behavior.* CHI 2023.  
- Recent work on model‑based LLM agents and world‑model‑driven planning (e.g., WorldCoder‑style architectures).
