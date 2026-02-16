---
title: Agency Component – Memory & AMS Integration
---

# Memory & AMS Integration

## Status

- **Implemented (v1)**: `MemoryManager` orchestrates working + semantic memory and context assembly (`shared/aico/ai/memory/manager.py`, `shared/aico/ai/memory/context/*`).
- **Implemented (v1)**: `ConversationEngine` retrieves memory context via `memory_manager.assemble_context(...)` and injects it into the LLM context (`backend/services/conversation_engine.py`).
- **Implemented (v1)**: AMS-facing REST endpoints exist under `/api/v1/ams/*` (`backend/api/ams/router.py`) exposing consolidation status + behavioral learning / preferences derived from persisted tables.
- **WIP**: tight coupling of AMS heavy consolidation to Lifecycle “SLEEP_LIKE” windows as a first-class, shared subsystem (see `agency-component-lifecycle.md`).

## 1. Purpose

This component defines **how agency uses AICO’s memory stack** (working, semantic, KG/World Model, AMS) as its long-term backbone for:

- context retrieval for Goals & Planning,  
- stable facts for the World Model,  
- behavioural learning for Skills/Tools,  
- and consolidation/self-reflection during Lifecycle SLEEP_LIKE phases.

It does not replace the existing Memory/AMS system; it **integrates** with it using shared stores and APIs.

## 2. Conceptual Model of the Memory Stack

- **Working memory** (e.g., LMDB)  
  - Short-lived buffers for recent conversation context and transient state.  
  - Fast access, limited size, no long-term guarantees.

  **Implementation note (v1):** working memory is implemented as a store within `shared/aico/ai/memory/working.py` and coordinated by `MemoryManager`.

- **Semantic memory** (ChromaDB + PostgreSQL)  
  - Text segments, embeddings, and hybrid search indices.  
  - Used for “what has happened” retrieval via similarity and metadata filtering.

  **Implementation note (v1):** semantic memory is implemented in `shared/aico/ai/memory/semantic.py` and used by `MemoryManager` when enabled in config.

- **Knowledge graph / World Model** (shared PostgreSQL-backed KG + schemas)  
  - Structured entities and relations (`Person`, `Activity`, `Goal`, `WorldStateFact`, `Skill`, etc.) as defined in the ontology and World Model docs.  
  - Provides stable, queryable facts and links that agency uses as its externalised “world state”.

  **Implementation note (v1):** knowledge graph storage/extraction is integrated into `MemoryManager` (see `PropertyGraphStorage` usage in `shared/aico/ai/memory/manager.py`).

- **Adaptive Memory System (AMS)**  
  - Consolidation and evolution layer over working, semantic, and KG.  
  - Learns patterns, routines, preferences; manages long-horizon learning and cleanup.  
  - Uses SLEEP_LIKE phases (Lifecycle) to run heavier consolidation and pattern extraction.

  **WIP**: explicit, shared Lifecycle windows driving AMS scheduling.

Agency sits **on top** of this stack: it does not own the stores, but defines **how agency components read/write** via MemoryManager/AMS/World Model APIs.

## 3. Data & Interaction Model (Conceptual)

Agency interacts with memory via a small set of conceptual operations:

- **ReadContext(query)**  
  - Inputs: query about user, goals, LifeAreas, open loops, or recent events.  
  - Backed by: semantic search + KG queries + recent working memory context.  
  - Used by: Goals, Planner, Curiosity, Values & Ethics, Emotion.

- **WriteMemoryItem(memory)**  
  - Inputs: `MemoryItem` (episodic, semantic, preference, pattern, reflection) with `summary_text` and `slots`.  
  - Backed by: AMS/MemoryManager inserting into semantic/KG layers.  
  - Used by: Planner (plan outcomes), Self-Reflection (lessons), Values & Ethics (policy-relevant events).

- **UpdateWorldStateFact(fact_change)**  
  - Inputs: new or updated `WorldStateFact` plus provenance (`PerceptualEvent`s, `MemoryItem`s).  
  - Backed by: World Model service over the shared KG.  
  - Used by: Goals, Arbiter, Planner, Curiosity, Values & Ethics.

- **AMSSignals & LearningOutputs**  
  - Inputs/outputs: AMS may emit pattern events (e.g., open loops, habits, routines) and behavioural learning signals (skill success, preference adjustments).  
  - Used by: Curiosity (interesting patterns), Skills/Tools (updating success rates), Values & Ethics (policy tuning), Self-Reflection.

The exact concrete APIs are defined in the existing Memory/AMS and World Model implementation; this doc specifies **what agency expects** logically.

## 4. Operations from the Agency Perspective

- **Context for Goal Formation**  
  - When interpreting user intents or CuriositySignals, Goals & Intentions call ReadContext to:  
    - find relevant past episodes,  
    - identify related Activities/Goals/Hobbies,  
    - surface open loops and constraints.

- **Plan/Execution Logging**  
  - Planner and Skills write important steps and outcomes as `MemoryItem`s (episodic and reflection), with links to goals, LifeAreas, and WorldStateFacts.  
  - These records feed AMS for later consolidation and pattern learning.

- **World Model Updates**  
  - Execution outcomes or new evidence become `WorldStateFact` changes via World Model ingestion APIs.  
  - Provenance always points back to `MemoryItem`s and `PerceptualEvent`s.

- **AMS-Driven Consolidation**  
  - During SLEEP_LIKE phases (see Lifecycle component), AMS runs consolidation jobs tagged as agency-relevant (e.g., routine extraction, preference updates).  
  - Agency components treat these as **asynchronous improvements** to World Model, skills metadata, and preferences.

  **Implementation note (v1):** AMS consolidation is visible via `/api/v1/ams/*` endpoints and underlying tables; scheduling against Lifecycle phases is **WIP**.

- **Self-Reflection Hooks**  
  - Self-Reflection reads from:  
    - logs and `MemoryItem`s about past decisions and outcomes,  
    - AMS-learned patterns (e.g., recurring failure contexts),  
    - emotion/relationship traces stored via `emotion.memory.store`. **WIP**  
  - Writes back: reflection memories and small adjustments to skill/goal/policy metadata.

## 5. Integration with Other Components

- **World Model Service**  
  - Shares the underlying PostgreSQL/KG with AMS.  
  - Exposes schema-aware APIs for `WorldStateFact` and entity/relationship queries used by agency.

- **Goals & Intentions / Arbiter / Planner**  
  - Use ReadContext and World Model queries to ground goals and plans in actual user history and world state.  
  - Log significant goal and plan events as memories for AMS and future reflection.

- **Curiosity Engine**  
  - Scans AMS/World Model for under-represented areas, anomalies, or patterns.  
  - Emits CuriositySignals based on memory and fact gaps, which may become goals.

- **Lifecycle & Scheduler**  
  - Lifecycle defines SLEEP_LIKE windows when AMS and World Model consolidation can run heavier jobs.  
  - Scheduler enforces when AMS tasks execute, using Lifecycle flags and resource budgets.

- **Emotion / Personality / Social**  
  - Emotion simulation stores experiences via `emotion.memory.store`; these become part of the semantic/KG store that agency reads for emotional patterns and relationship history. **WIP**

## 6. Persistence Notes

- All long-lived memory structures (`MemoryItem`, semantic embeddings, KG/WorldStateFact, AMS patterns) are persisted in the existing **Memory/AMS + World Model** stack (PostgreSQL + ChromaDB + KG schemas).  
- Agency **does not introduce a separate memory store**; it reuses the shared stack and adds:
  - conventions for how goals/plans/skills log to it,  
  - expectations for how AMS and World Model expose learned patterns and facts.

Future iterations will specify concrete API shapes (`GetContextForGoal`, `RecordPlanOutcome`, etc.) once the implementation surface stabilises.
