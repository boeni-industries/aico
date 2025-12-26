# Intelligence – Layout & Content Design

## 1. Information Design Concept

The Intelligence section focuses on **AI capabilities and model health**:

- LLMs and conversation models.
- Entity extraction and knowledge graph enrichment.
- Embeddings & retrieval.
- Sentiment and emotion classifiers.
- Intent classification.
- TTS engines.

Conceptually, this page answers: **"Is AICO thinking clearly and are all cognition-related services healthy?"**

Information is organized around **capability clusters** rather than individual models:

- Conversation & Reasoning.
- Understanding & Extraction.
- Retrieval & Knowledge Graph support.
- Emotion & Sentiment.
- Voice & Presence.

Each cluster groups models that serve a shared function and links back to the underlying modelservice metrics and logs.

## 2. Page Layout

### 2.1 Main Layout

- **Top row – Cognitive health summary**
  - Overall "Intelligence Health" score.
  - Latency and error rate snapshot for core conversation model.

- **Capability sections (stacked)**
  - Each section is a large glass card with:
    - Title + icon.
    - List of models in the cluster.
    - Health/status, latency, and usage metrics.
    - Optional tiny chart for key metrics (latency, error rate, throughput).

- **Bottom – Test console (developer only)**
  - Collapsible panel with quick test forms:
    - Conversation test.
    - Entity extraction / KG enrichment test.
    - Sentiment/emotion probe.

## 3. Content Design

### 3.1 Cognitive Health Summary

- **Visuals**
  - Single score (0–100) combining availability, latency, and error rates for core models.
  - Breakdown chips showing per-cluster scores.

- **Functions**
  - Click a cluster chip to scroll/jump to that section.

### 3.2 Conversation & Reasoning Section

- **Models**
  - Primary conversation LLM.
  - Lightweight LLMs for simple tasks.

- **Metrics**
  - Average and p95 latency.
  - Tokens/s throughput.
  - Error rate per time bucket.

- **Functions**
  - Inspect model details (drawer with configuration, version, and past failures).
  - Link to Operations → Modelservice logs for deeper debugging.

### 3.3 Understanding & Extraction Section

- **Models**
  - GLiNER (entities).
  - Intent classifiers.

- **Metrics**
  - Calls/minute.
  - Error rate and timeouts.
  - Coverage across conversations.

- **Functions**
  - Sample extraction viewer: pick a recent conversation snippet and view extracted entities and intents (for debugging).

### 3.4 Retrieval & Knowledge Support Section

- **Models/Algorithms**
  - Embedding models.
  - BM25, HNSW/RRF.

- **Metrics**
  - Retrieval latency.
  - Index sizes.
  - Approximate "quality" indicators (e.g., proportion of successful retrievals used in answers).

- **Functions**
  - Mini search console: enter a query and inspect ranked results and their sources.

### 3.5 Emotion & Sentiment Section

- **Models**
  - Sentiment classifiers.
  - Emotion analysis models.

- **Metrics**
  - Coverage of messages.
  - Conflicts between models.

- **Functions**
  - Side-by-side comparison of model outputs for a sample conversation.
  - Link to Emotion page for episode-level analysis.

### 3.6 Voice & Presence Section

- **Models**
  - Piper TTS.
  - Coqui XTTS.

- **Metrics**
  - Synthesis latency.
  - Error rate.
  - Usage by voice/personality.

- **Functions**
  - Quick TTS test with sample text.
  - Link to Embodiment/Frontend docs for integration behavior.

## 4. Navigation & Traceability

- From Intelligence you can navigate to:
  - **Operations** (modelservice runtime logs, resource usage).
  - **Conversation & Memory** (effect of retrieval quality).
  - **Emotion** (downstream use of emotion models).
- All model cards are clickable and open drawers with direct links to logs and metrics.

## 5. UX Notes

- Strong emphasis on **readability** and **grouping by capability**, not by implementation detail.
- Cards avoid overwhelming tables; only the most important metrics are shown by default.
- Advanced diagnostic views live in collapsible developer sections.
