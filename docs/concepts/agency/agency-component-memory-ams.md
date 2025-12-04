---
title: Agency Component – Memory & AMS Integration
---

# Memory & AMS Integration

## Component Description

This component describes how agency uses AICO’s **memory stack**:

- **Working memory** (LMDB) for recent conversation context.  
- **Semantic memory** (ChromaDB + libSQL) for facts, segments, and hybrid search.  
- **Knowledge graph** for structured entities and relationships.  
- **Adaptive Memory System (AMS)** for consolidation, temporal evolution, and behavioral learning.

Agency relies on this stack to:

- Retrieve context and open loops when forming goals.  
- Store commitments and important events as explicit memories.  
- Use AMS “sleep phases” to reshape future goals, preferences, and skills.

Later versions will define the exact APIs and query patterns between agency and MemoryManager/AMS.
