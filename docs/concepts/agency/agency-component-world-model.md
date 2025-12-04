---
title: Agency Component – World Model & Knowledge Graph
---

# World Model & Knowledge/Property Graph

## 1. Purpose

The World Model component maintains AICO’s structured understanding of **people, entities, situations, routines, and environments**. It integrates the **knowledge/property graph**, semantic memory, and embeddings into a coherent substrate for planning, curiosity, and self-reflection.

## 2. Responsibilities (Conceptual)

- Maintain a **long-lived knowledge/property graph** of entities and their relations.
- Provide **schema-level structure** for recurring situations (projects, habits, contexts, places).
- Detect **inconsistencies, drifts, and unknowns** (e.g., missing details about an important life area).
- Support **graph-augmented queries** for planning, goal selection, and curiosity.
- Expose APIs for **hypothesis generation and testing** ("I think X is true about the user; check it softly over time").

## 3. Integration Points

- Reads from: AMS (semantic memory), Conversation Engine, social relationship modeling.
- Writes to: knowledge/property graph storage, derived schemas and summaries.
- Serves: Goal & Intention System, Planning, Curiosity Engine, Self-Reflection as a shared world model service.
