---
title: Agency Component – Control, Safety & Transparency
---

# Control, Safety & Transparency

## Component Description

The Control, Safety & Transparency component defines **how far** AICO’s agency can go and **how it is surfaced** to users:

- **User primacy** – users can configure, pause, and reset autonomous behavior.  
- **Permissions & capabilities** – explicit whitelists for tools, integrations, and action types, implemented on top of the structured policy engine described in `agency-component-values-ethics.md`.  
- **Audit logging** – records of autonomous actions, triggering goals, EvaluationResult decisions, and tools used.  
- **Explainability** – mechanisms to answer "why did you do this?" for significant actions, using ontology-backed provenance.

This component is the primary UX/infra bridge between agency and AICO’s privacy/security architecture, exposing and controlling the behaviour of the underlying Values & Ethics / policy engine, and ensuring that autonomy remains aligned, inspectable, and reversible.
