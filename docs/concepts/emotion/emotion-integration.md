# Emotion Integration

## Overview

This document explains how AICO's dual emotion system integrates across all major subsystems to create a believable emotional companion:

- **User Emotion Detection** – understanding what the user feels.
- **AICO Emotion Simulation** – maintaining AICO's own internal emotional state.
- **System Integration** – how both layers interact with ConversationEngine, Memory/AMS/KG, Modelservice, Frontend/Embodiment, and CLI/dev tools.

For conceptual details of AICO's internal emotional model, see [`emotion-simulation.md`](./emotion-simulation.md).
For low-level architecture of the simulation module, see [`emotion-simulation-architecture.md`](./emotion-simulation-architecture.md).
For message formats, see [`emotion-messages.md`](./emotion-messages.md).

## Dual Emotion System

AICO's emotion capabilities are split into two coordinated layers:

- **User Emotion Detection (input view)**
  - Detects the user's emotional state from conversation text (and future voice/vision), using dedicated modelservice endpoints and recognition components.
  - Publishes structured signals such as `user.emotion.detected` and `voice.analysis` with labels, valence/arousal, stress indicators, and crisis hints.
  - Feeds multiple consumers: Emotion Simulation, AMS, crisis detection, and memory.

- **AICO Emotion Simulation (internal view)**
  - Uses AppraisalCloudPCT/CPM to maintain AICO's own internal emotional state based on user emotion, conversation events, relationship history, and personality.
  - Produces `emotion.state.current` and expression guidance for text, voice, and avatar.
  - Represents AICO's "feelings" in a way that is consistent, personality-aligned, and relationship-aware.

The **goal** of this dual system is **believability**: AICO should both understand how you feel and exhibit a coherent emotional life of her own that evolves over time.

## Integration with Modelservice

- **Sentiment & Emotion Endpoints**
  - Sentiment and emotion are exposed as separate, but related, modelservice capabilities:
    - `sentiment` – lightweight polarity/intensity (negative/neutral/positive) for fast, coarse-grained signals.
    - `emotion` – richer multi-dimensional affect (primary/secondary labels, valence, arousal, dominance, dimensional vectors).
  - Both are implemented as standard modelservice request/response topics and mirrored via REST endpoints (e.g. `/api/v1/affective/sentiment`, `/api/v1/affective/emotion`).

- **Usage**
  - User Emotion Detection primarily calls the **emotion** endpoint to infer user affect.
  - AMS and other components may use **sentiment** where a simple polarity signal is sufficient (e.g. quick heuristics, lightweight scoring).

## Integration with ConversationEngine

- **Input to Emotion Simulation**
  - ConversationEngine publishes or passes per-turn context (user/assistant messages, metadata) that, combined with user emotion, feeds the appraisal process.

- **Conditioning LLM Responses**
  - ConversationEngine obtains AICO's current `EmotionalState` (via EmotionProcessor or message bus) and converts it into a **compact conditioning profile** (e.g. warmth, directness, energy).
  - This profile influences:
    - The LLM messages (short behavioral hints about tone/approach).
    - Decoding parameters (temperature, response length, etc.) within configured bounds.
  - ConversationEngine remains the **single orchestrator** for LLM calls; emotion acts as a controller, not a separate generator.

## Integration with Memory, AMS, and Knowledge Graph

- **Working Memory**
  - Each significant turn can be annotated with:
    - Detected user emotion.
    - AICO's simulated emotional state.
  - These annotations are stored alongside recent messages in working memory for short-term context and analysis.

- **Semantic Memory & AMS**
  - Emotionally significant events (strong emotions, crises, breakthroughs) are promoted into semantic memory with emotional summaries.
  - AMS uses emotional outcomes (which strategies led to positive/negative emotional shifts) as feedback when selecting skills, strategies, and what to recall.

- **Knowledge Graph (KG)**
  - User and relationship nodes carry **affective properties**, such as:
    - Typical emotional responses to themes (e.g. work, family, health).
    - Preferred support styles (validation first, advice first, playful, etc.).
    - Known stressors and comfort topics.
  - Emotion Simulation and ConversationEngine query these properties to shape both appraisal and response style.

## Integration with Frontend & Embodiment

- **Current Emotional State (`emotion.state.current`)**
  - Backend exposes AICO's current emotional state as a **compact projection** (see `Frontend Emotional Projection` in [`emotion-messages.md`](./emotion-messages.md)) via REST and/or WebSocket.
  - The frontend can use this to:
    - Apply **subtle mood theming** (background gradients, accent colors).
    - Show the **strongest active emotion** as a small, unobtrusive indicator.
    - Provide an optional **"today's mood arc"** or sparkline showing how AICO's state evolved across the session.

- **Transparency & Trust**
  - An optional "What I'm feeling / why" panel can translate AICO's internal emotional state and key appraisal factors into user-friendly language.
  - This supports debugging, trust-building, and gives users a sense of AICO's inner life without overwhelming them.

- **Future Embodiment**
  - The same compact emotional profile that conditions text should drive avatar expressions and, later, voice prosody:
    - Avatar micro-expressions, posture, gaze.
    - TTS prosody (if/when voice is added).
  - This ensures **cross-modal coherence**: text, colors, and avatar all reflect the same emotion.

## Integration with CLI and Developer Tooling

- CLI commands can:
  - Inspect recent `emotion.state.current` values and histories for debugging.
  - Test sentiment/emotion endpoints and appraisal pipelines in isolation.
  - Provide simple diagnostics for crisis detection and regulation behavior.

- Developer tools and logs should focus on **structure, not raw text**:
  - Log high-level emotional labels and transitions, not sensitive conversational content.
  - Allow developers to understand how detection and simulation behaved on a given turn.

## Believability as Design Constraint

Across all tiers, the dual emotion system and its integrations are designed with a single guiding constraint:

> **AICO should feel like an emotionally present companion, not a rule engine.**

- User emotion detection ensures AICO genuinely perceives how you feel.
- AICO's simulated emotion ensures she responds from a coherent internal perspective.
- Memory, AMS, KG, and frontend visualization ensure these patterns **persist and evolve** over time, making AICO's emotional behavior feel stable, deep, and trustworthy.
