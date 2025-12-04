---
title: Agency Component – Values & Ethics Layer
---

# Values & Ethics Layer

## 1. Purpose

The Values & Ethics layer provides **explicit value constraints and ethical reasoning hooks** for AICO’s agency. It ensures that autonomy and curiosity remain aligned with user wellbeing, safety, and agreed boundaries over long time horizons.

## 2. Responsibilities (Conceptual)

- Define a **value schema** that combines:
  - core AICO principles (care, respect, non-coercion),
  - user-specific preferences and boundaries,
  - relationship roles and obligations.
- Provide **constraints and evaluators** for goals and plans ("does this help or harm long-term wellbeing?").
- Support **contextual ethics reasoning** via LLM prompts, grounded in explicit value representations.
- Maintain **auditability** of value/ethics decisions for later inspection.

## 3. Integration Points

- Reads from: personality and social relationship models, user configuration, system-wide safety policies.
- Writes to: filters and annotations on goals, plans, and skills (e.g., blocked, risky, requires explicit consent).
- Serves: Goal Arbiter & Meta-Control, Planning System, Conversation Engine (for explanations and consent flows).
