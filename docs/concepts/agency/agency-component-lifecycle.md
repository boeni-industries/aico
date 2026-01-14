---
title: Agency Component – Lifecycle & Daily Rhythm
---

# Lifecycle & Daily Rhythm

## 1. Purpose

The Lifecycle & Daily Rhythm component treats AICO as a **long‑lived process** with distinct phases (active vs sleep‑like) instead of a purely stateless request/response agent. It coordinates when agency may:

- proactively pursue goals and run skills, vs.  
- focus on consolidation, self‑reflection, and maintenance.

## 2. Conceptual Model

High-level lifecycle states (conceptual, not OS processes):

- **ACTIVE** – AICO can converse, run user‑initiated and high‑priority autonomous tasks.  
- **FOCUSED_WORK** – subset of ACTIVE; high focus on a few important goals, reduced background work.  
- **IDLE_LIGHT** – light background work allowed, ready to engage quickly.  
- **SLEEP_LIKE** – user‑facing activity paused (except critical alerts); background consolidation, reflection, and low‑priority tasks run.  
- **MAINTENANCE** – rare; used for upgrades, migrations, or safety hold.

Lifecycle transitions are driven by time‑of‑day, user activity, device constraints, and user configuration.

## 3. Data Model (Conceptual)

- **LifecycleState**  
  - `state` ∈ {ACTIVE, FOCUSED_WORK, IDLE_LIGHT, SLEEP_LIKE, MAINTENANCE}.  
  - `since` (timestamp), `expected_until` (optional).  
  - `reason` (e.g., user_config, quiet_hours, low_battery, manual_override, daily_consolidation).  
  - `flags`: `allow_proactive`, `allow_background`, `allow_heavy_jobs`, `user_visible`.

- **DailyRhythmConfig**  
  - `active_window` (e.g., 07:00–23:00 local).  
  - `quiet_hours` (e.g., 23:00–07:00, reduced/no proactive actions).  
  - `preferred_sleep_block` (e.g., start ≈ user’s night).  
  - device/resource constraints (max background CPU, etc.).

Lifecycle state is persisted in the shared store and made available to Scheduler, Arbiter, Curiosity, and Embodiment.

### 3.1 Persistence

- **LifecycleState**  
  - Stored in the shared PostgreSQL-backed store (and/or KG) alongside other agency runtime state.  
  - Single current row/node per AICO agent; read by Scheduler, Arbiter, Curiosity, Embodiment, and Conversation.

- **DailyRhythmConfig**  
  - Stored in configuration tables/files in the same PostgreSQL environment as other agency config (values, skills, policies).  
  - Loaded into memory by the Lifecycle component and editable via user/developer settings.

- **Lifecycle history (optional)**  
  - Transition log (`timestamp`, `old_state`, `new_state`, `reason`) stored as an append-only table for debugging, metrics, and Self-Reflection.  
  - Summaries or patterns may be promoted into AMS/KG as `MemoryItem`s if useful, but jobs themselves remain elsewhere.

- **Not owned by Lifecycle**  
  - Task definitions and queues (user-facing, background, maintenance) are persisted and owned by the **Scheduler / Task system**. Lifecycle only controls when different task classes are allowed to run via its state/flags, it does not store or manage individual jobs.

## 4. Operations & Behaviour

- **EvaluateLifecycleTick(context)**  
  - Periodically (e.g., every few minutes) or on key events, evaluate:
    - time‑of‑day vs `DailyRhythmConfig`,  
    - recent user interaction and device state,  
    - outstanding consolidation jobs.  
  - Decide whether to remain in current state or transition.

- **EnterState(new_state, reason)**  
  - Update `LifecycleState` and emit an internal event so Scheduler, Curiosity, Embodiment, and Conversation can adjust behaviour.

- **ScheduleSleepLikePhase()**  
  - During quiet hours, request a SLEEP_LIKE window from Scheduler & Resource Monitor.  
  - Within that window, prioritise AMS consolidation, World Model updates, Self‑Reflection tasks, and low‑impact curiosity probes.

- **RespectUserOverrides()**  
  - User can temporarily force ACTIVE or suppress SLEEP_LIKE (e.g., “stay awake and help me tonight”), within safety/resource limits.

## 5. Integration with Other Components

- **AMS and MemoryManager**  
  - SLEEP_LIKE phases are when AMS runs heavier consolidation and pattern extraction jobs.  
  - Lifecycle ensures these jobs are scheduled when user impact is minimal.

- **World Model Service**  
  - Uses SLEEP_LIKE windows to reconcile new facts, update routines and LifeArea mappings, and normalise hypotheses.

- **Curiosity Engine**  
  - May queue low‑priority curiosity explorations for SLEEP_LIKE execution (e.g., hypothesis checks, background pattern search).

- **Goal Arbiter & Planner**  
  - Lifecycle state informs Arbiter scoring (e.g., deprioritise starting new heavy initiatives near SLEEP_LIKE, prefer wrap‑up/summary goals).  
  - Planner may schedule “end‑of‑day review” or “tomorrow planning” goals before SLEEP_LIKE.

- **Task Scheduler & Resource Monitor**  
  - Enforces that heavy jobs run primarily during SLEEP_LIKE or explicit maintenance windows.  
  - Uses `LifecycleState.flags` to decide which queues are allowed to run.

- **Embodiment**  
  - Maps LifecycleState to visible modes (e.g., ACTIVE at desk, IDLE_LIGHT on couch, SLEEP_LIKE in bedroom).

## 6. Configuration & User Control

- Default daily rhythm derived from device locale/timezone, with simple UI for adjusting active hours and quiet hours.  
- Toggle for “allow proactive behaviour during quiet hours” (default off or limited).  
- Controls for “run heavy background jobs only on power/Wi‑Fi”.  
- Manual overrides (e.g., “focus mode”, “sleep now”, “wake up”) that set or nudge `LifecycleState` subject to safety.

## 7. Examples (Conceptual)

- **Typical day**  
  - 07:00–22:30: ACTIVE/FOCUSED_WORK; AICO can suggest tasks, run skills, and respond normally.  
  - 22:30–23:00: Planner/Arbiter prefer wrap‑up goals (summaries, tomorrow planning).  
  - 23:00–06:30: SLEEP_LIKE; conversation quiet unless user actively engages or critical alerts fire; AMS and World Model jobs run; Curiosity runs background checks.

- **Quiet hours override**  
  - User says: “I’m working late, please stay awake.”  
  - Lifecycle extends ACTIVE window temporarily, defers some heavy background tasks, and resumes the normal rhythm after the override window expires.
