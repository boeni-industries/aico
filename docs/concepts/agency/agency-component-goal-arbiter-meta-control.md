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

- Reads from: Goal & Intention System (goal candidates), Curiosity Engine, Values & Ethics, Scheduler & Resource Monitor.
- Writes to: Planning System (selected goals and their priorities), Scheduler (execution priorities).
- Collaborates with: Conversation Engine to expose which goals are currently active and why.
