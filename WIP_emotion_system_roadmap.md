# WIP Emotion System Roadmap

This document tracks the implementation of AICO's **dual emotion system**:
1. **Emotion Simulation** (AICO's internal emotional state via AppraisalCloudPCT/CPM)
2. **Emotion Detection** (user emotion recognition from text/voice/facial)

Both systems integrate with ConversationEngine, memory/AMS/KG, and embodiment.

**Current Status**: Phase 1 Complete (Emotion Simulation core loop)  
**Implementation**: `/backend/services/emotion_engine.py` (simulation only)

## Phase 0 – Foundations & Scoping

- [x] Confirm Emotion Simulation scope for Companion/Confidante phases (what must ship in v1 vs. later).
- [x] Inventory existing models/services we will reuse (sentiment, emotion, intent, memory, KG, AMS).
  - Modelservice: sentiment endpoint, emotion endpoint, intent classification.
  - Memory: working memory store, semantic memory, KG/graph layer.
  - AMS: strategy/skill selection with feedback channels.
  - ConversationEngine: turn orchestration and LLM prompt construction.
  - Frontend: chat UI + future avatar/voice surfaces for emotional projection.
- [x] Define minimal success criteria for Emotion v1 (UX-focused, not infra-focused).
  - User can perceive a stable, believable emotional presence in text-only chats (no avatar/voice required).
  - AICO reliably detects coarse user valence and a small set of emotional intents (e.g., venting vs. celebrating).
  - AICO’s responses adapt tone and style (warmth, directness, energy) in ways that feel appropriate and non-random.
  - Emotional state and simple mood history are exposed via the compact frontend projection and are observable in the UI.
  - No regressions in safety: crisis/edge-case behavior is at least as safe as the non-emotional baseline.

## Phase 1 – Core Emotion Loop (Text-Only, Single Modality)

**Scope**: AICO's Emotion Simulation only (internal emotional state). User emotion detection deferred to Phase 2+.

**Implementation**: `/backend/services/emotion_engine.py`

### Emotion Simulation (AICO's Internal State)
- [x] Implement 4-stage appraisal (relevance, implication, coping, normative).
- [x] Implement CPM 5-component emotional state representation.
- [x] Event-driven architecture (no scheduled jobs - per CPM research).
- [x] Wire conversation turn events via `CONVERSATION_USER_INPUT`.
- [x] Generate compact emotional state per turn.
- [x] Publish to `EMOTION_STATE_CURRENT`, `LLM_PROMPT_CONDITIONING_RESPONSE`.
- [x] ConversationEngine integration for LLM conditioning.
- [x] Emotional state history for mood arcs.
- [x] Service registration in lifecycle manager.
- [ ] REST endpoints: `GET /api/v1/emotion/current`, `GET /api/v1/emotion/history`.
- [ ] Evaluation hooks for response impact analysis.

### Emotion Detection (User Emotion Recognition)
- [ ] **NOT IMPLEMENTED** - Deferred to Phase 2+
- [ ] Will detect user emotions from text/voice/facial inputs
- [ ] Will publish to message bus for consumption by emotion simulation and other components

## Phase 2 – User Emotion Detection & Memory Integration

**Scope**: Implement user emotion detection and integrate both systems with memory/AMS.

### User Emotion Detection (NEW)
- [ ] Implement text-based emotion detection in `/backend/services/` (service pattern, not shared algorithms).
- [ ] Subscribe to `CONVERSATION_USER_INPUT` and analyze user messages.
- [ ] Publish detected user emotions to message bus for consumption by EmotionEngine.
- [ ] Wire user emotion into EmotionEngine appraisal as input.
- [ ] Integrate with modelservice emotion endpoint for enhanced detection.

### Memory & AMS Integration
- [ ] Store emotional labels and trajectories alongside working memory entries.
- [ ] Attach emotional summaries to semantic/KG entries where relevant (relationship nodes, key events).
- [ ] Integrate emotional outcomes with AMS (feedback on which strategies worked for which patterns).
- [ ] Add queries/APIs to retrieve emotion-enriched context for ConversationEngine.
- [ ] Publish emotional experiences to memory system for learning.

## Phase 3 – Agency Integration & Relationship Intelligence

### Agency-Emotion Integration
- [ ] Wire EmotionEngine appraisal results into AgencyEngine for goal generation.
- [ ] Map motivational tendency (approach/withdraw/engage) to proactive behavior triggers.
- [ ] Emotional intensity modulates autonomous initiative frequency.
- [ ] Implement closed-loop: agency goals feed back into appraisal (goal conduciveness).
- [ ] Personality traits constrain both emotional and autonomous behaviors.

### Relationship & KG Intelligence
- [ ] Define "relationship affect profile" schema for KG nodes (typical valence, support preferences, stressors).
- [ ] Implement update logic that learns these profiles over time from interactions.
- [ ] Expose KG affect profiles to EmotionEngine and ConversationEngine for decision-making.
- [ ] Add evaluation scenarios that test long-term, relationship-aware emotional behavior.

## Phase 4 – Multimodal Expression API

- [x] Design a modality-agnostic expression profile (e.g., energy, warmth, engagement, focus).
- [ ] Map expression profile → text guidelines (tone, phrasing, length).
- [ ] Map expression profile → voice parameters (prosody, intensity) for future TTS integration.
- [ ] Map expression profile → avatar parameters (animations, gaze) for future Three.js integration.

## Phase 5 – Safety, Ethics, and Crisis Handling

- [ ] Implement safety/ethics regulation layer between appraisal and expression (intensity caps, disallowed patterns).
- [ ] Integrate crisis indicators and escalation paths with existing crisis/learning topics.
- [ ] Log regulation decisions and outcomes via existing security/log pipelines.
- [ ] Add crisis-specific evaluation scenarios and regression tests.

## Phase 6 – Evaluation & Iteration

- [ ] Extend the existing memory evaluation framework with emotion-focused metrics and scenarios.
- [ ] Define concrete UX success metrics (user trust, emotional resonance, perceived support).
- [ ] Run end-to-end pilots and iterate on mappings and thresholds.
- [ ] Decide which advanced features (cloud enhancement, complex trajectories) to ship vs. defer.

---

This roadmap is intentionally WIP: we will adjust, tick off, and refine items as we implement the emotion systems and see real conversational behavior.
