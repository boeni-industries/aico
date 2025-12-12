---
title: Agency Component – Emotion, Personality & Social Context
---

# Emotion, Personality & Social Context

## 1. Purpose

This component provides a **small, explicit state** for:

- how AICO currently feels (EmotionState),  
- who AICO is over time (PersonalityProfile),  
- how AICO relates to each user (SocialRelationship).

It ensures agency decisions are **emotionally, personally, and socially coherent**, not just text-style consistent.

## 2. Conceptual Model

- **EmotionState** – short-term, fast-changing state (valence/arousal ± discrete label) derived from ongoing interactions and events.
- **PersonalityProfile** – long-term, slowly changing trait/value vector shaping default behaviours and risk posture.
- **SocialRelationship** – per-user relationship state capturing role, intimacy, trust, and stability.

These three latent variables influence Goals, Planning, Curiosity, Values & Ethics, Conversation, and Embodiment.

## 3. Data Model (Conceptual)

Aligned with the ontology document (EmotionState, Personality, SocialRelationship types) and the existing Emotion Simulation system in `/docs/concepts/emotion`. This component **does not re-simulate** emotions; it consumes the Emotion Simulation outputs and exposes them to agency.

### 3.1 EmotionState

`EmotionState` here is the **same core emotional state** produced by the CPM-based Emotion Simulation module and published on the bus as `emotion.state.current`.

- Fields (conceptual view of that state):
  - `valence` ∈ [-1, 1] (negative → positive).  
  - `arousal` ∈ [0, 1] (calm → activated).  
  - optional `dominance` ∈ [0, 1] if needed.  
  - `discrete_label` (e.g., joy, frustration, calm, anxious).  
  - `confidence` (0–1).  
  - `last_updated_at`.  
  - `sources` (PerceptualEvent IDs or conversation turns that drove the update).

### 3.2 EmotionEpisode / Trace

- **EmotionEpisode**  
  - start/end timestamps, peak valence/arousal, main triggers (references to events/goals).
- Aggregated into an **EmotionTrace** for reflection, metrics, and narrative continuity.
- Both are **derived views** over persisted emotional experiences coming from `emotion.memory.store` and AMS/KG, not a separate state store.

### 3.3 PersonalityProfile

- Fields:
  - trait vector (e.g., `O`, `C`, `E`, `A`, `N` ∈ [-1, 1] or [0, 1]).  
  - core value weights (e.g., `care`, `autonomy`, `exploration`, `stability`).  
  - style parameters used by Conversation/Embodiment (e.g., `directness`, `warmth`, `playfulness`).  
  - `stability_params` (how quickly behaviour can be adapted by Self-Reflection and explicit user edits).

### 3.4 SocialRelationship

- Per user (or user group):
  - `relationship_role` (acquaintance, friend, partner, coach, etc.).  
  - dimensions: `intimacy`, `authority`, `care_responsibility`, `trust`, `stability` (all 0–1).  
  - `history_refs` (key shared events, long-running projects/goals).  
  - `last_interaction_at`, `recent_valence_trend` (how recent interactions felt overall).

### 3.5 Links to Other Entities

- Relations:
  - `HAS_EMOTION_STATE(AICOAgent, EmotionState)`  
  - `HAS_PERSONALITY(AICOAgent, PersonalityProfile)`  
  - `HAS_RELATIONSHIP(AICOAgent, Person)` with SocialRelationship payload  
  - Links from EmotionEpisode to Goals, PerceptualEvents, Activities for explainability.

## 4. Operations & Dynamics

### 4.1 Emotion updates

- **UpdateEmotionFromEvents(percepts, conversation)**  
  - Use classifiers/LLM heuristics over recent text + PerceptualEvents to propose Δ(valence, arousal, label).  
  - Combine with current state via smoothing (e.g., exponential moving average) and clamp to allowed ranges.

- **DecayEmotion(dt)**  
  - Gradually move toward a neutral baseline over time without strong stimuli.

### 4.2 Personality usage & adaptation

- Personality parameters are **read-mostly**:
  - used to choose default stances (e.g., more/less proactive, more/less explorative).  
  - injected into prompts and world model hypotheses about what AICO will prefer to do.
- Slow adaptation:
  - **AdjustPersonalityFromHistory()** – Self-Reflection can make small, bounded adjustments based on long-term patterns or explicit user instructions ("be more direct", "be less pushy").

### 4.3 SocialRelationship updates

- **UpdateRelationshipFromInteraction(outcome)**  
  - Positive episodes, kept commitments → increase trust/intimacy/stability slightly.  
  - Negative episodes, broken expectations → decrease trust/stability.  
  - Explicit user statements ("I want you to be more like a coach") can change `relationship_role` and caps.

### 4.4 Temporal scales

- EmotionState: seconds–hours.  
- SocialRelationship: days–months.  
- PersonalityProfile: months–years (or until explicitly edited).

## 5. Integration with Other Components

### 5.1 Goal Arbiter & Meta-Control

- Provides `emotion_alignment` and relationship-aware weights in the Arbiter score:  
  - encourage restorative/supportive goals under high user or agent stress,  
  - deprioritise heavy or risky goals when relationship trust is low or fragile.

### 5.2 Planning & Skills

- Influences plan templates and skills chosen for **how** to act, not just **what** to do:  
  - gentle vs direct communication,  
  - frequency and tone of check-ins,  
  - use of playful vs serious modalities.

### 5.3 Curiosity Engine

- Emotion- and relationship-aware curiosity:  
  - dampen over-stimulating or risky explorations under high stress.  
  - prioritise stabilising or comforting explorations for fragile relationships.

### 5.4 Values & Ethics / Policy Engine

- Policy conditions can reference EmotionState and SocialRelationship:  
  - avoid or delay sensitive topics at extreme stress levels,  
  - require stronger consent when relationship_role is weak/early and topic is high-risk.

### 5.5 Conversation & Embodiment

- Conversation uses these signals to set style parameters and prompts.  
- Embodiment uses EmotionState and relationship context to choose posture, movement intensity, and room.

## 6. Configuration & User Control

- **Initial Personality templates** – e.g., "calm helper", "curious coach", with trait presets.  
- **Emotion bounds** – optional caps on how intense or expressive AICO should appear.  
- **Relationship settings** – users can confirm or adjust perceived role and trust level.  
- **Transparency** – UI surfaces simple summaries ("I see us as close collaborators") and lets users correct them.

## 7. Metrics & Evaluation

See `agency-metrics.md` for details; key metrics include:

- Emotion volatility and time in extreme states.  
- Relationship stability and trust trajectories.  
- Correlation between emotional/relational state and user-reported satisfaction.  
- Impact on goal completion and frequency of policy blocks related to emotional context.

## 8. Examples (Conceptual)

- **High user stress scenario**  
  - EmotionState shows high arousal, low valence; relationship marked as caring/supportive.  
  - Arbiter boosts supportive/check-in goals; Planner chooses gentle communication templates; Curiosity avoids heavy exploratory tasks.

- **Low trust new user**  
  - SocialRelationship has low trust and intimacy; policies require explicit consent for sensitive domains.  
  - Arbiter and Values & Ethics veto certain proactive goals; Planner and Conversation keep tone cautious and explanatory.
