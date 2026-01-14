# Memory & AMS – Layout & Content Design

## 1. Information Design Concept

The Memory & AMS section presents AICO's **complete memory architecture** as a coherent, layered system:

- Working Memory (fast, short-term, LMDB).
- Semantic Memory + Knowledge Graph (slow, long-term, ChromaDB + PostgreSQL + KG).
- Adaptive Memory System (AMS) as the orchestration layer.
- Memory Album as the user-curated view.

The core concept is **"layered transparency"**:

- At a glance, the user sees how much AICO remembers, how it retrieves, and how it consolidates.
- Every statistic or visualization maps back to a specific memory tier and can be traced down to individual records or conversations.
- Visual complexity is tamed via **layered diagrams** and **drill-down drawers**, never by dumping raw entries in the main view.

## 2. Page Layout

### 2.1 Main Layout

- **Top band – Memory system map**
  - Horizontal diagram showing Working → Semantic → KG → AMS → Album.
  - Each node is a clickable mini-card with size, health, and last activity.

- **Middle – Tier panels (stacked)**
  - Working Memory panel.
  - Semantic Memory panel.
  - Knowledge Graph panel.
  - AMS panel.
  - Memory Album panel.

- **Bottom – Example flows**
  - Visual flow of a single conversation through the tiers (ingestion, retrieval, consolidation).

## 3. Content Design

### 3.1 System Map

- **Visuals**
  - Glassmorphic strip with 5 nodes, connected by arrows.
  - Each node shows:
    - Count (entries, vectors, nodes/edges).
    - Last read/write time.
    - Health chip.

- **Functions**
  - Click node → scroll/jump to corresponding panel and open its drawer.

### 3.2 Working Memory Panel

- **Metrics**
  - Number of active items.
  - TTL utilization and eviction rate.
  - Recent activity timeline.

- **Functions**
  - Example entry viewer: inspect a few anonymized records and their metadata.
  - Link to Conversation & Memory Album for user-facing view.

### 3.3 Semantic Memory Panel

- **Metrics**
  - Vector count.
  - Index size.
  - Average retrieval latency.

- **Functions**
  - Sample search console: show how top-N items are selected.
  - Link to Intelligence for model-related retrieval insights.

### 3.4 Knowledge Graph Panel

- **Metrics**
  - Node and edge counts.
  - Graph analytics scores (PageRank, communities).

- **Visuals**
  - Static or gently animated mini-graph view highlighting key entities.

- **Functions**
  - Click entity in mini-graph → open KG detail drawer (connected persons, events, tags).

### 3.5 AMS Panel

- **Metrics**
  - Consolidation job schedule and last run.
  - Behavioral learning updates.

- **Functions**
  - Show the last few consolidation sessions and outcomes.
  - Link to Agency (where AMS influences planning and behavior).

### 3.6 Memory Album Panel

- **Visuals**
  - Grid/list of recent conversations with title, timestamp, main sentiment.

- **Functions**
  - Click conversation → open album detail view with summary and key moments.
  - Filters for person, tag, time window.

## 4. Navigation & Traceability

- Any memory-related data in other sections (e.g., Agency goals referencing memories) should link back here.
- Every visualization element either:
  - Links to a more detailed drawer.
  - Links to a canonical list view (e.g., album list, KG entity list).

## 5. UX Notes

- Emphasize **calm, contemplative visuals**: smooth gradients, soft transitions, no aggressive flashing or animations.
- Default views avoid raw text dumps; exploration is guided by visuals and filters.
