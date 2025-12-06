---
title: Agency Component – Memory & AMS Integration
---

# Memory & AMS Integration

## Component Description

This component describes how agency uses AICO’s **memory stack** as the backbone for the World Model, Goals, Curiosity, and Self-Reflection:

- **Working memory** (LMDB) for recent conversation context.  
- **Semantic memory** (ChromaDB + libSQL) for facts, segments, and hybrid search.  
- **Knowledge graph / World Model** (shared libSQL-backed KG + schemas) for structured entities (`Person`, `Activity`, `Goal`, `WorldStateFact`, `Skill`, etc.) and relations.  
- **Adaptive Memory System (AMS)** for consolidation, temporal evolution, and behavioral learning on top of that shared store.

Agency relies on this stack to:

- Retrieve context and open loops when forming goals.  
- Provide the data and facts the World Model exposes to Planner, Curiosity, and Values & Ethics.  
- Store commitments and important events as explicit `MemoryItem`s and `WorldStateFact`s.  
- Use AMS “sleep phases” to reshape future goals, preferences, skills, and world-model structure.

Later versions will define the exact APIs and query patterns between agency and MemoryManager/AMS.
