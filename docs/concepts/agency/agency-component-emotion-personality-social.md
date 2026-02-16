---
title: Agency Component – Emotion, Personality & Social Context
---

# Emotion, Personality & Social Context

## Status

- **Implemented (v1)**: internal emotion simulation service `EmotionEngine` in `backend/services/emotion_engine.py` (publishes compact emotional state; persisted history; REST access via `backend/api/emotion/router.py`).
- **Partially implemented (v1)**: conversation conditioning can include emotion guidance when enabled via feature flag in `backend/services/conversation_engine.py` (`enable_emotion_integration`).
- **Implemented (v1, baseline)**: `PersonalityService` exists (`shared/aico/ai/personality/service.py`) and provides a `PersonalityContext` with default traits + relationship vector (Phase 2 defaults).
- **WIP**: `PersonalityPlugin` contract exists (`backend/services/personality_engine.py`), but does not yet perform real analysis.
- **WIP**: Social relationship modeling as described here (role/intimacy/trust/stability dynamics) is not implemented end-to-end; only foundational persistence models exist (e.g., `shared/aico/data/user/relationship_models.py`).

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

**Implementation note (v1):** the Emotion API currently exposes the engine’s *global* state; per-user emotional states are **WIP** (see `backend/api/emotion/router.py`).

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

**WIP**: EmotionEpisode/Trace and `emotion.memory.store` as an explicit, queryable abstraction; current persistence is primarily via EmotionEngine’s own state history / DB history endpoints.

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

**WIP**: the full `SocialRelationship` state and update rules described here; current codebase contains only baseline relationship persistence models (e.g., `UserRelationship`) rather than the multidimensional relationship vector.

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

**Implementation note (v1):** emotion dynamics are implemented inside `backend/services/emotion_engine.py` as part of the simulation loop (CPM appraisal + inertia), not as an agency PerceptualEvent consumer.

### 4.2 Personality usage & adaptation

- Personality parameters are **read-mostly**:
  - used to choose default stances (e.g., more/less proactive, more/less explorative).  
  - injected into prompts and world model hypotheses about what AICO will prefer to do.
- Slow adaptation:
  - **AdjustPersonalityFromHistory()** – Self-Reflection can make small, bounded adjustments based on long-term patterns or explicit user instructions ("be more direct", "be less pushy").

**Implementation note (v1):** `PersonalityService.get_personality_context(user_id)` currently returns Phase 2 default traits + relationship vector; adaptive updates are **WIP**.

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

**Implementation note (v1):** the `GoalArbiter` accepts `context` inputs such as `emotion_boost` and `personality_fit` (see `shared/aico/ai/agency/arbiter.py`), but there is no single, canonical pipeline yet that computes these values from the emotion/personality services end-to-end (**WIP**).

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

- Conversation uses these signals to set style parameters and prompts (emotion conditioning is implemented behind feature flags; personality/social conditioning is **WIP**).  
- Embodiment uses EmotionState and relationship context to choose posture, movement intensity, and room.

**WIP**: embodiment mapping to posture/room is not implemented end-to-end (see `agency-component-embodiment.md`).

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
