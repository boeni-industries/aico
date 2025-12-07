---
title: Agency Component – Goal Arbiter & Meta-Control
---

# Goal Arbiter & Meta-Control

## 1. Purpose

The Goal Arbiter & Meta-Control layer decides **which goals AICO should pursue when**, balancing user-requested goals, curiosity-driven goals, and system-maintenance/self-development goals under safety, resource, and value constraints.

## 2. Responsibilities (Conceptual)

- Collect **candidate goals** from:
  - user interactions,
  - Curiosity Engine,
  - system/self-maintenance tasks,
  - longer-term relationship themes.
- Score and rank goals using:
  - personality and value system,
  - emotion and social context,
  - safety/ethics constraints,
  - resource budgets and user preferences.
- Maintain a **current intention set** (active goals) and gracefully drop, pause, or downgrade others.
- Provide **meta-decisions** such as when to prioritize intrinsic goals vs. immediate user requests.

## 3. Integration Points

- Reads from: Goal & Intention System (goal candidates), Curiosity Engine (CuriositySignals and hypotheses), World Model (hypotheses/conflicts in key LifeAreas), Values & Ethics (EvaluationResult for goals), Scheduler & Resource Monitor (current load).
- Writes to: Planning System (selected goals and their priorities), Scheduler (execution priorities), World Model (e.g., clarification goals linked to hypotheses).
- Publishes: an explicit **active intention set** (goals + priorities + brief reasons) that Conversation Engine and UI can surface.

## 4. Example Scoring & Prioritisation (Conceptual)

The Arbiter can use a simple weighted scoring scheme per goal, for example:

- `score(goal) = w_priority * priority + w_origin * origin_weight + w_life_area * life_area_weight + w_emotion * emotion_alignment + w_values * values_ok - w_load * system_load`.

Where:

- `origin_weight` prefers user-origin and safety/maintenance over curiosity/agent_self by default.  
- `life_area_weight` boosts critical LifeAreas (Health, Finance, Safety) when not blocked by Values & Ethics.  
- `emotion_alignment` boosts/rests goals depending on current EmotionState (e.g., prefer restorative goals under high stress).  
- `values_ok` is 0 if Values & Ethics returns `block`, reduced if `needs_consent`.  
- `system_load` reflects Scheduler/Resource Monitor pressure (high load penalises non-urgent goals).

Priority bands can then be derived (e.g., **urgent**, **normal**, **background**) and exposed with reasons (which terms dominated), so downstream components and UIs can explain why some goals are active and others deferred.

## 5. Data Model (Conceptual)

- **GoalCandidate**  
  - `goal_id`, `origin` (user_request/curiosity/maintenance/agent_self), `life_areas` (linked LifeAreas from WM),  
  - `priority_hint` (from caller), `metadata` (e.g., source signal IDs, hypotheses it addresses).

- **Intention**  
  - `intention_id`, `goal_id`, `status` (proposed/active/paused/dropped/completed),  
  - `score` (from Arbiter), `priority_band` (urgent/normal/background),  
  - `reasons` (short explanation: origin, key LifeAreas, values decision, load state).

- **IntentionSet**  
  - snapshot of current Intentions the Arbiter considers **active** or **queued**, made available to Planner, Scheduler, Conversation, and UI.

These are conceptual structures; concrete storage can reuse existing goal tables plus Arbiter-specific fields.

## 6. Operations / Behaviour

- **CollectCandidates()** – pull GoalCandidates from user requests, CuriositySignals, maintenance queues, and self-model needs.  
- **EvaluateWithPolicies(goal)** – call Values & Ethics to obtain an `EvaluationResult` (allow/needs_consent/block) and attach it to the goal.  
- **ScoreCandidates()** – compute scores using the weighted scheme above, incorporating emotion, social context, LifeAreas, hypotheses, and system load.  
- **SelectIntentionSet()** – choose a set of Intentions to mark `active`, respecting:
  - global caps (e.g., max concurrent active goals),  
  - resource constraints (Scheduler feedback),  
  - user overrides (pinned/blocked goals).
- **PublishIntentionSet()** – expose the active set (with reasons) to Planner and Scheduler, and optionally to Conversation/UI.  
- **UpdateFromFeedback()** – adjust scores or statuses when:
  - plans succeed/fail,  
  - user gives direct feedback,  
  - Values & Ethics policies change,  
  - Self-Reflection suggests promoting/demoting certain goal types.

In v1, these behaviours can be implemented with simple tables and scheduled evaluation loops, leaving room for more advanced bandit-style or RL-based meta-control later.

## 7. Configuration & Cadence

- **Weights and thresholds**  
  - Stored in config (or simple DB tables) for: `w_priority`, `w_origin`, `w_life_area`, `w_emotion`, `w_values`, `w_load`.  
  - Thresholds for mapping scores → priority bands (urgent/normal/background).  
  - Per-install defaults with optional user-/developer-level overrides.

- **Caps and limits**  
  - Max concurrent active intentions.  
  - Per-origin caps (e.g., at most N active curiosity goals).  
  - Optional per-LifeArea caps to avoid over-focus on a single domain.

- **Pin/block controls**  
  - User or higher-level logic can **pin** specific goals (never fully deprioritised) or **block** them (never activated) via flags attached to the goal/intention.  
  - Arbiter respects these before finalising the IntentionSet.

- **Evaluation cadence**  
  - Event-driven triggers: on new GoalCandidate, on EvaluationResult change, on major EmotionState/relationship shifts, on plan completion/failure.  
  - Periodic sweep: low-frequency background pass (e.g., every few minutes or at lifecycle boundaries) to recompute scores and refresh the IntentionSet.

This keeps the Arbiter simple to implement while making its behaviour configurable, inspectable, and easy to tune.
