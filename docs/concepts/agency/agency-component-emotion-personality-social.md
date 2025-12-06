---
title: Agency Component – Emotion, Personality & Social Context
---

# Emotion, Personality & Social Context

## Component Description

This component integrates three existing systems into agency decisions:

- **Personality Simulation** – trait vector and value system describing who AICO is.  
- **Emotion Engine** – current emotional state and history (valence, arousal, feeling labels, style parameters).  
- **Social Relationship Modeling** – relationship vectors (intimacy, authority, care responsibility, stability) for each user.

Agency uses these signals to:

- Decide which goals are appropriate and when to pursue them (feeding directly into the Goal Arbiter scoring function).  
- Shape how initiatives and responses are phrased and timed (Planner and Skills layer heuristics).  
- Bias Curiosity and Values & Ethics (e.g., conservative curiosity under high stress, stricter policies in fragile contexts).  
- Maintain a coherent long‑term character and relationship arc.

Future iterations will formalize decision rules and weighting schemes that tie these signals into goal/plan selection, curiosity gating, and value/policy evaluation.
