# Emotion Detection

## Overview

This document describes how AICO detects the **user's emotional state** from their inputs and exposes it as structured signals for other components (Emotion Simulation, AMS, crisis detection, memory, frontend).

For AICO's own internal emotional life (AppraisalCloudPCT/CPM), see [`emotion-simulation.md`](./emotion-simulation.md).
For system-wide integration and believability, see [`emotion-integration.md`](./emotion-integration.md).

## Goals

- Accurately infer the user's emotional state from multimodal inputs (initially text, later voice/vision).
- Provide **compact, structured** signals that are easy for other components to consume.
- Support **real-time responsiveness** and **privacy-preserving**, local-first processing.

## Core Responsibilities

- Analyze user inputs for:
  - Primary and secondary emotions.
  - Valence, arousal, and dominance.
  - Stress, fatigue, and crisis indicators.
  - Interaction intent related to emotion (e.g., venting, celebrating, seeking advice).
- Publish these results as message bus events (topics TBD in Phase 2 implementation).
- Provide stable REST endpoints (via the backend) for diagnostic and tooling purposes.

## Modelservice Integration

- **Sentiment vs Emotion**
  - **Sentiment**: Lightweight polarity/intensity (negative/neutral/positive) for coarse-grained signals.
  - **Emotion**: Richer, multi-dimensional affect (labels, valence, arousal, dominance, dimensional vectors).
- Both are implemented as standard modelservice request/response topics and mirrored via REST endpoints (e.g. `/api/v1/affective/sentiment`, `/api/v1/affective/emotion`).

## Message Bus Topics

- Input (from other systems):
  - `CONVERSATION_USER_INPUT` – current user messages from conversation engine.
  - Conversation context from memory/AMS systems.
- Output (produced by detection):
  - User emotion signals published to message bus for consumption by EmotionEngine and other components.
  - Voice analysis signals (future multimodal).

Detailed JSON examples for these messages are defined in [`emotion-messages.md`](./emotion-messages.md).

## Downstream Consumers

- **Emotion Simulation** – uses user emotion as input to appraisal.
- **AMS/Memory** – records emotional context and patterns to learn effective strategies.
- **Crisis Detection** – monitors for high-risk emotional states and triggers protocols.
- **Frontend** – may show user-facing indicators or adapt UI subtly (e.g., warning banners for crisis).

## Design Principles

- Local-first, privacy-preserving processing.
- Compact, stable schemas for easy consumption.
- Clear separation from AICO's **simulated emotion** while remaining tightly integrated through the dual emotion system.
