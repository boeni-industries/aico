---
title: Agency Component – Planning & Decomposition
---

# Planning & Decomposition

## Component Description

The Planning & Decomposition component turns abstract **goals and intentions** into **executable plans**:

- Breaks goals into ordered or conditional steps.  
- Binds steps to skills and tool calls with explicit preconditions and expected outcomes.  
- Produces artifacts that the scheduler and conversation engine can execute and monitor.

It will use both LLM‑based reasoning and symbolic templates to:

- Propose plans, alternatives, and fallbacks.  
- Update plans based on feedback, failures, and changing context.

Future revisions will define plan representations, update algorithms, and integration with the scheduler.
