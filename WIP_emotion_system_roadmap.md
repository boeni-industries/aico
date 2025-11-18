# WIP Emotion System Roadmap

This document tracks the implementation of AICO's Emotion Simulation system (AppraisalCloudPCT + CPM) and its integration with ConversationEngine, memory/AMS/KG, and embodiment.

## Phase 0 – Foundations & Scoping

- [ ] Confirm Emotion Simulation scope for Companion/Confidante phases (what must ship in v1 vs. later).
- [ ] Inventory existing models/services we will reuse (sentiment, emotion, intent, memory, KG, AMS).
- [ ] Define minimal success criteria for Emotion v1 (UX-focused, not infra-focused).

## Phase 1 – Core Emotion Loop (Text-Only, Single Modality)

- [ ] Implement a basic appraisal + CPM state representation (no avatar/voice yet).
- [ ] Wire conversation turn events into the emotion module (user+AI messages, context).
- [ ] Generate a compact emotional state per turn and log it.
- [ ] Feed emotional state into ConversationEngine as LLM conditioning (tone/style parameters).
- [ ] Add minimal evaluation hooks to observe impact on responses.

## Phase 2 – Memory & AMS Integration

- [ ] Store emotional labels and trajectories alongside working memory entries.
- [ ] Attach emotional summaries to semantic/KG entries where relevant (relationship nodes, key events).
- [ ] Integrate emotional outcomes with AMS (feedback on which strategies worked for which patterns).
- [ ] Add queries/APIs to retrieve emotion-enriched context for ConversationEngine.

## Phase 3 – Relationship & KG Intelligence

- [ ] Define "relationship affect profile" schema for KG nodes (typical valence, support preferences, stressors).
- [ ] Implement update logic that learns these profiles over time from interactions.
- [ ] Expose KG affect profiles to emotion module and ConversationEngine for decision-making.
- [ ] Add evaluation scenarios that test long-term, relationship-aware emotional behavior.

## Phase 4 – Multimodal Expression API

- [ ] Design a modality-agnostic expression profile (e.g., energy, warmth, engagement, focus).
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
