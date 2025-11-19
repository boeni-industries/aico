# Emotion Integration

## Overview

This document explains how AICO's dual emotion system integrates across all major subsystems to create a believable emotional companion:

- **User Emotion Detection** – understanding what the user feels.
- **AICO Emotion Simulation** – maintaining AICO's own internal emotional state.
- **System Integration** – how both layers interact with ConversationEngine, Memory/AMS/KG, Modelservice, Frontend/Embodiment, and CLI/dev tools.

For conceptual details of AICO's internal emotional model, see [`emotion-simulation.md`](./emotion-simulation.md).
For low-level architecture of the simulation module, see [`emotion-simulation-architecture.md`](./emotion-simulation-architecture.md).
For message formats, see [`emotion-messages.md`](./emotion-messages.md).

## System Overview

AICO's emotion system integrates **simulation** (AICO's internal state) and **detection** (user emotion recognition) with ConversationEngine, Memory/AMS/KG, and frontend.

## Dual Emotion System

AICO's emotion capabilities are split into two coordinated layers:

- **User Emotion Detection (input view)**
  - Detects the user's emotional state from conversation text (and future voice/vision), using dedicated modelservice endpoints and recognition components.
  - Publishes structured signals via message bus with labels, valence/arousal, stress indicators, and crisis hints.
  - Feeds multiple consumers: EmotionEngine (simulation), AMS, crisis detection, and memory.
  - **Status**: Not yet implemented (Phase 2+).

- **AICO Emotion Simulation (internal view)**
  - Implemented in `/backend/services/emotion_engine.py` using AppraisalCloudPCT/CPM.
  - Maintains AICO's own internal emotional state based on user emotion, conversation events, relationship history, and personality.
  - Publishes to `EMOTION_STATE_CURRENT` and `LLM_PROMPT_CONDITIONING_RESPONSE` topics.
  - Provides expression guidance for text (Phase 1), voice and avatar (Phase 4).
  - Represents AICO's "feelings" in a way that is consistent, personality-aligned, and relationship-aware.
  - **Status**: Phase 1 complete.

The **goal** of this dual system is **believability**: AICO should both understand how you feel and exhibit a coherent emotional life of her own that evolves over time.

## Integration Flow

**Per-turn cycle**:
1. User sends message → `CONVERSATION_USER_INPUT` published
2. EmotionEngine receives event, performs 4-stage appraisal
3. Generates CPM emotional state, publishes to `EMOTION_STATE_CURRENT`
4. **Persists state to database** - current state + history for continuity across restarts
5. ConversationEngine retrieves state, adds to LLM system prompt
6. LLM generates response conditioned by emotional tone
7. Emotional state stored in memory for learning (Phase 2+)

**No scheduled jobs required** - emotions are event-driven, updating only on conversation turns per CPM research.

**State Persistence** - Emotional state and history are persisted to encrypted database (schema v17) to maintain emotional continuity across system restarts. On startup, EmotionEngine loads the last known state, ensuring AICO "remembers" how she felt.

## Integration with Agency & Autonomy

**Emotion drives autonomous behavior**: EmotionEngine's appraisal results (relevance, goal impact, coping capability) inform AgencyEngine's goal generation and proactive behavior. High-relevance emotional states trigger autonomous initiatives—e.g., warm concern → proactive check-in, curiosity → follow-up questions, protective → safety suggestions.

**Motivational component bridges systems**: CPM's motivational tendency (approach/withdraw/engage) directly influences agency decisions. Emotional intensity modulates proactive behavior frequency and assertiveness.

**Personality mediates both**: Personality traits constrain both emotional responses and autonomous actions, ensuring consistent character across reactive (emotion) and proactive (agency) behaviors.

**Future integration** (Phase 3+): Agency goals will feed back into appraisal (goal conduciveness check), creating closed-loop emotional-behavioral system where autonomous actions shape emotional responses and vice versa.

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
  - EmotionEngine subscribes to `CONVERSATION_USER_INPUT` to receive per-turn conversation events.
  - Processes user messages through 4-stage appraisal to generate emotional responses.

- **Conditioning LLM Responses**
  - ConversationEngine retrieves AICO's current emotional state from EmotionEngine service.
  - Converts emotional state into **compact conditioning profile** (warmth, directness, energy) added to system prompt.
  - This profile influences LLM tone and approach via natural language guidance.
  - ConversationEngine remains the **single orchestrator** for LLM calls; emotion acts as a controller, not a separate generator.
  - **Implementation**: See `_build_system_prompt()` in `/backend/services/conversation_engine.py`.

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

- **Current Emotional State**
  - EmotionEngine publishes to `EMOTION_STATE_CURRENT` topic with compact projection format.
  - Backend exposes REST endpoints: `GET /api/v1/emotion/current`, `GET /api/v1/emotion/history` (JWT authentication required).
  - State persists across restarts via encrypted database (schema v17).
  - Frontend can use this to:
    - Apply **subtle mood theming** (background gradients, accent colors).
    - Show the **strongest active emotion** as a small, unobtrusive indicator.
    - Provide an optional **"today's mood arc"** or sparkline showing how AICO's state evolved across the session.
  - See `Frontend Emotional Projection` in [`emotion-messages.md`](./emotion-messages.md) for data format.

- **Transparency & Trust**
  - An optional "What I'm feeling / why" panel can translate AICO's internal emotional state and key appraisal factors into user-friendly language.
  - This supports debugging, trust-building, and gives users a sense of AICO's inner life without overwhelming them.

- **Future Embodiment (Phase 4)**
  - The same compact emotional profile that conditions text will drive avatar expressions and voice prosody:
    - Avatar micro-expressions, posture, gaze.
    - TTS prosody parameters.
  - This ensures **cross-modal coherence**: text, colors, and avatar all reflect the same emotion.

## Integration with CLI and Developer Tooling

- **CLI Commands** (`aico emotion`):
  - `aico emotion status` - Show current emotional state and recent transitions
  - `aico emotion history` - View emotional state history and mood arcs
  - `aico emotion reset` - Reset to neutral baseline state
  - `aico emotion export` - Export emotional state data for analysis
  - Inspect recent `emotion.state.current` values and histories for debugging.
  - Test sentiment/emotion endpoints and appraisal pipelines in isolation.
  - Provide simple diagnostics for crisis detection and regulation behavior.

- **Database Persistence**:
  - Emotional state stored in `emotion_state` table (single row, current state)
  - History stored in `emotion_history` table (time-series data for mood arcs)
  - Managed via schema version 17 in core database
  - Accessible via `aico db` commands for backup/restore

- Developer tools and logs should focus on **structure, not raw text**:
  - Log high-level emotional labels and transitions, not sensitive conversational content.
  - Allow developers to understand how detection and simulation behaved on a given turn.

## Believability as Design Constraint

Across all tiers, the dual emotion system and its integrations are designed with a single guiding constraint:

> **AICO should feel like an emotionally present companion, not a rule engine.**

- User emotion detection ensures AICO genuinely perceives how you feel.
- AICO's simulated emotion ensures she responds from a coherent internal perspective.
- Memory, AMS, KG, and frontend visualization ensure these patterns **persist and evolve** over time, making AICO's emotional behavior feel stable, deep, and trustworthy.
