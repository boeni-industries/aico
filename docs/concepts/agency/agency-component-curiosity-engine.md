---
title: Agency Component – Curiosity Engine
---

# Curiosity Engine

## 1. Purpose

The Curiosity Engine provides **intrinsic motivation** for AICO. It detects gaps, anomalies, and under-explored regions in AICO’s world model and relationship with the user, and turns them into **self-generated goals**.

## 2. Responsibilities (Conceptual)

- **Detect informational gaps** in AMS, semantic memory, and the knowledge/property graph.
- **Measure intrinsic value** of exploring a gap (e.g., uncertainty reduction, information gain, relevance to the relationship).
- **Generate curiosity-driven goals** and feed them into the Goal & Intention System.
- **Coordinate with emotion and personality** so curiosity expresses as warm, safe, user-aligned exploration.
- **Respect safety and user preferences**, never bypassing explicit boundaries.

## 3. Integration Points

- Reads from: AMS, semantic memory, knowledge/property graph, conversation history, emotion/personality state.
- Writes to: Goal & Intention System (candidate intrinsic goals, with scores and rationales).
- Collaborates with: Scheduler & Resource Governance to allocate background time for curiosity projects.
