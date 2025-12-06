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
