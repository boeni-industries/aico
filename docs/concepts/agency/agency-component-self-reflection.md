---
title: Agency Component – Self-Reflection & Self-Model
---

# Self-Reflection & Self-Model

## 1. Purpose

Self-Reflection gives AICO a **model of itself**: what it tried, how it behaved, what worked, and what should change. It turns logs, feedback, and memory into **lessons** that adapt policies and skills over time.

## 2. Responsibilities (Conceptual)

- Maintain a **self-model** of capabilities, limits, and recent behavior patterns.
- Periodically run **reflection tasks** (often during sleep-like phases) over:
  - actions taken and their outcomes,
  - user feedback and emotional trajectories,
  - goal completion and drop patterns.
- Extract **lessons and adjustments** (e.g., "speak less during high-stress episodes", "check in earlier when pattern X appears").
- Feed these lessons back into: skill selection, planning templates, curiosity focus, and personality/expression parameters.

## 3. Integration Points

- Reads from: logs/telemetry, AMS, emotion history, social relationship history.
- Writes to: behavioral learning store, policy/skill metadata, self-model summaries available to other components.
- Collaborates with: Curiosity Engine (where to explore), Goal Arbiter (what to deprioritize or emphasize), Values & Ethics (alignment of behavior with declared values).
