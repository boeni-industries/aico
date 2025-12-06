---
title: Agency Component – Scheduler & Resource Governance
---

# Scheduler & Resource Governance

## Component Description

The Scheduler & Resource Governance component ensures AICO’s autonomy is **bounded and respectful** of system and user constraints:

- Uses the **Task Scheduler** for long‑running and background jobs (consolidation, analysis, recurring plans, skill executions).  
- Uses the **Resource Monitor** to enforce CPU, memory, and battery budgets based on each task’s `resource_profile` and `runtime_context`.  
- Applies **user and policy constraints** (quiet hours, allowed activities, priority levels, EvaluationResult from Values & Ethics).

Agency delegates execution to this layer so that:

- High‑level intentions and plan steps (with chosen Skills) become scheduled, observable tasks.  
- Background work never overwhelms the device or user experience.  
- Autonomy can be tuned or paused without breaking higher‑level logic.

Later drafts will define task schemas (linking tasks to plan steps and `InvokeSkill` calls), prioritization strategies, and governance policies.
