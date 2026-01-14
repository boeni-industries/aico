# Studio Metrics Catalog

> **Scope:** This document defines the metrics that AICO Studio is responsible for visualizing. It is a **contract** between backend services and the Studio UI.
>
> For each metric we specify:
>
> - **ID** – Stable identifier used in code and API contracts.
> - **Description** – What the metric means in human terms.
> - **Source** – Where the data comes from (service, DB table, LMDB/Chroma/KG, config).
> - **Computation** – How the value is derived (including any aggregation window).
> - **Update cadence** – How often Studio should refresh it.
> - **Primary surfaces** – Where it is shown (Overview, Operations, etc.) and how (chip, card, chart).
>
> This catalog is intentionally independent of concrete API endpoints; backend and Studio can evolve as long as they respect these metric contracts.

---

## 1. Overview Metrics

### 1.1 System Health

- **ID:** `overview.system.health_status`
- **Description:** Single health indicator summarizing the overall status of AICO (OK / Degraded / Attention).
- **Source:** Aggregation over service health checks from API Gateway, Scheduler, Modelservice, Message Bus host, DB connectivity.
- **Computation:**
  - `OK` if all required services report healthy and error rates below thresholds.
  - `Degraded` if at least one service is degraded or error rate above soft threshold.
  - `Attention` if any critical service is down or error rate above hard threshold.
- **Update cadence:** 5–15 seconds when Overview is visible; on page load otherwise.
- **Primary surfaces:**
  - **Overview:** Hero chip.
  - **Operations:** Synthesized from detailed service tiles.

### 1.2 Uptime Since Last Restart

- **ID:** `overview.system.uptime`
- **Description:** Wall‑clock duration since the core backend (gateway + scheduler + modelservice) was last started.
- **Source:**
  - Backend service start timestamps (e.g. from process manager or health endpoint).
- **Computation:** `now() - min(service.start_time for required services)`.
- **Update cadence:** 60 seconds.
- **Primary surfaces:**
  - **Overview:** Hero chip.
  - **Operations:** Per‑service uptime in service detail drawers.

### 1.3 Active Conversations

- **ID:** `overview.conversation.active_count`
- **Description:** Count of conversations that have had activity within a recent window.
- **Source:**
  - `conversation_sessions` or equivalent table; working memory LMDB buckets for current conversations.
- **Computation:** Number of distinct conversation IDs with events in the last `N` minutes (e.g. 30m).
- **Update cadence:** 30 seconds.
- **Primary surfaces:**
  - **Overview:** Hero chip.
  - **Memory & AMS:** Conversation list / Memory Album.

### 1.4 Active Agency Goals

- **ID:** `overview.agency.active_goals`
- **Description:** Number of currently active goals in the Agency system.
- **Source:**
  - `agency_goals` table (status column) in the PostgreSQL schema.
- **Computation:** `COUNT(*) FROM agency_goals WHERE status = 'active'`.
- **Update cadence:** 15–30 seconds.
- **Primary surfaces:**
  - **Overview:** Hero chip.
  - **Agency:** Goal board.

### 1.5 Domain Summary Metrics

Each left‑hand domain exposes one primary KPI on the Overview cards.

#### 1.5.1 Operations – Healthy Services

- **ID:** `overview.operations.healthy_services_ratio`
- **Description:** Ratio of healthy core services to total core services.
- **Source:**
  - Health endpoints from: API Gateway, Modelservice, Scheduler, Message Bus host, Studio.
- **Computation:** `healthy_count / total_count`.
- **Update cadence:** 5–15 seconds.
- **Primary surfaces:**
  - **Overview:** Primary KPI of Operations card (with tiny 15m error‑rate sparkline).
  - **Operations:** Detailed service list.

#### 1.5.2 Intelligence – Model Availability

- **ID:** `overview.intelligence.models_healthy_ratio`
- **Description:** Ratio of healthy core models (conversation, embeddings, extraction, sentiment, intent, emotion, TTS) to the configured set.
- **Source:**
  - Modelservice health registry + per‑model health checks.
- **Computation:** `healthy_model_count / configured_model_count`.
- **Update cadence:** 30 seconds.
- **Primary surfaces:**
  - **Overview:** Intelligence card.
  - **Intelligence:** Capability sections per model cluster.

#### 1.5.3 Memory & AMS – Retrieval Quality Index

- **ID:** `overview.memory.retrieval_quality_index`
- **Description:** Composite score (0–100) representing recent retrieval effectiveness from Semantic Memory + KG.
- **Source:**
  - Retrieval logs from backend, Chroma query stats, AMS trajectory feedback.
- **Computation:**
  - Weighted combination of:
    - Retrieval latency.
    - Hit/miss ratio.
    - AMS feedback_reward from `ams_trajectories`.
- **Update cadence:** 5–10 minutes.
- **Primary surfaces:**
  - **Overview:** Memory card.
  - **Memory & AMS:** Retrieval and AMS panels.

#### 1.5.4 Emotion – Dominant State

- **ID:** `overview.emotion.dominant_state`
- **Description:** Short textual summary of the dominant emotional state over a recent window (e.g. "mostly calm / curious" or "recent warm_concern episode").
- **Source:**
  - Aggregation over `EmotionHistoryResponse` samples from the emotion API.
- **Computation:**
  - Mode or weighted mode of `label.primary` over last N minutes, optionally grouped into families.
- **Update cadence:** 1–5 minutes.
- **Primary surfaces:**
  - **Overview:** Emotion card primary KPI.
  - **Emotion:** Summary chip above the emotion strip.

#### 1.5.5 Agency – Active Goals

- **ID:** `overview.agency.active_goals_count`
- **Description:** Same as 1.4, but surfaced as primary KPI on the Agency card.
- **Source:** `agency_goals`.
- **Computation:** See 1.4.
- **Update cadence:** 15–30 seconds.
- **Primary surfaces:** Overview and Agency.

#### 1.5.6 Security – Posture

- **ID:** `overview.security.posture_status`
- **Description:** Aggregated security status (Healthy / Rotation due / Alerts).
- **Source:**
  - Key metadata from DB (e.g. `security_keys`, `auth_sessions`, `auth_devices`, `auth_access_policies`).
  - Audit log health from encrypted log store.
- **Computation:**
  - `Healthy` if no overdue key rotations and low failed‑auth rate.
  - `Rotation due` if master key age > configured threshold.
  - `Alerts` if high failed‑auth, disabled policies, or audit log issues.
- **Update cadence:** 5–10 minutes.
- **Primary surfaces:** Overview Security card; Security domain tiles.

#### 1.5.7 System – Version Alignment

- **ID:** `overview.system.version_alignment`
- **Description:** Whether backend, shared library, modelservice, frontend, and Studio versions are mutually compatible.
- **Source:**
  - Version endpoints or configuration from backend, modelservice, frontend; `VERSIONS` file.
- **Computation:** Boolean + list of mismatches.
- **Update cadence:** On load + when versions change.
- **Primary surfaces:** Overview System card; System page.

### 1.6 Recent Events & Anomalies

- **ID:** `overview.events.stream`
- **Description:** Unified stream of important recent events across domains (failures, retries, goal changes, security alerts).
- **Source:**
  - `agency_events_log`, scheduler job logs, security/audit logs, gateway and modelservice error logs.
- **Computation:**
  - Domain‑specific event selection rules composed into a single ordered list (most recent first).
- **Update cadence:** 10–30 seconds.
- **Primary surfaces:**
  - **Overview:** Event list/timeline.
  - **Domain pages:** Filtered event views.

---

## 2. Operations Metrics

> Detailed metrics for runtime health, performance, and activity. These feed both the Operations domain page and parts of the Overview.

### 2.1 Service Health & Uptime

- **ID:** `operations.services.health` (per service)
- **Description:** Health status (up, degraded, down) and uptime for each managed service.
- **Source:**
  - Health endpoints / process manager for API Gateway, Scheduler, Modelservice, Message Bus host, Studio.
- **Computation:** Service‑specific health logic; uptime from `now() - start_time`.
- **Update cadence:** 5–15 seconds.
- **Surfaces:**
  - Operations service tiles; Overview aggregation.

### 2.2 HTTP Request Metrics (Gateway)

- **ID:** `operations.gateway.requests_per_sec`
- **Description:** Requests per second over rolling windows.
- **Source:** Gateway access logs or in‑memory counters.
- **Computation:** Sliding‑window count/seconds (e.g. last 1m, 5m, 15m).
- **Update cadence:** 5 seconds.
- **Surfaces:** Operations → Gateway panel line chart.

- **ID:** `operations.gateway.error_rate`
- **Description:** Percentage of 4xx/5xx responses over total.
- **Source:** Same as above.
- **Computation:** `errors / total_requests` in window.
- **Update cadence:** 5 seconds.
- **Surfaces:** Operations panel + Overview micro‑chart.

### 2.3 Scheduler & Jobs

- **ID:** `operations.scheduler.jobs_per_minute`
- **Description:** Number of jobs executed per minute.
- **Source:** Scheduler execution history table.
- **Computation:** Count of jobs grouped by minute.
- **Update cadence:** 30 seconds.
- **Surfaces:** Operations → Scheduler panel.

- **ID:** `operations.scheduler.queue_backlog` (per queue)
- **Description:** Number of pending jobs in each queue (user_facing, background_light, background_heavy, maintenance).
- **Source:** Scheduler queue metadata.
- **Computation:** Snapshot counts.
- **Update cadence:** 10–30 seconds.
- **Surfaces:** Operations panel; Agency task queues chart.

### 2.4 Logs & Alerts

- **ID:** `operations.logs.high_severity_count`
- **Description:** Count of ERROR/CRITICAL log entries in a time window.
- **Source:** Encrypted audit/log DB.
- **Computation:** Filtered count per service and severity.
- **Update cadence:** 1 minute.
- **Surfaces:** Operations logs panel; Overview events stream.

---

## 3. Intelligence Metrics

> Metrics describing AI/modelservice health and usage.

### 3.1 Conversation Models

- **ID:** `intelligence.llm.latency_p95`
- **Description:** 95th percentile latency for the primary conversation model.
- **Source:** Modelservice request logs.
- **Computation:** Rolling p95 over last N requests.
- **Update cadence:** 30–60 seconds.
- **Surfaces:** Intelligence Conversation section; Overview micro‑chart.

- **ID:** `intelligence.llm.error_rate`
- **Description:** Error/timeout rate for LLM calls.
- **Source:** Same logs as above.
- **Computation:** `errors / total` in window.
- **Update cadence:** 30–60 seconds.

### 3.2 Extraction & Understanding

- **ID:** `intelligence.extraction.calls_per_min`
- **Description:** Number of GLiNER/entity extraction calls per minute.
- **Source:** Modelservice handler metrics.
- **Update cadence:** 60 seconds.

- **ID:** `intelligence.intent.calls_per_min`
- **Description:** Number of intent classification calls per minute.
- **Source:** Modelservice.

### 3.3 Retrieval & Embeddings

- **ID:** `intelligence.retrieval.latency_avg`
- **Description:** Average latency of hybrid retrieval (Chroma + BM25 + KG).
- **Source:** Backend retrieval logs.
- **Update cadence:** 1–5 minutes.

- **ID:** `intelligence.embeddings.count`
- **Description:** Number of embedding vectors stored in ChromaDB.
- **Source:** Chroma metadata.
- **Update cadence:** 10–30 minutes.

### 3.4 Emotion & Sentiment

- **ID:** `intelligence.emotion.coverage`
- **Description:** Percentage of messages with an attached emotion/sentiment classification.
- **Source:** Emotion and sentiment pipelines.
- **Update cadence:** 5–15 minutes.

### 3.5 TTS

- **ID:** `intelligence.tts.latency_avg`
- **Description:** Average synthesis latency by engine (Piper, Coqui XTTS).
- **Source:** TTS backend logs.
- **Update cadence:** 5–15 minutes.

---

## 4. Memory & AMS Metrics

> Metrics over PostgreSQL schema (e.g. `ams_user_memories`, trajectories), LMDB working memory, and Chroma/KG.

### 4.1 Working Memory (LMDB)

- **ID:** `memory.working.items_active`
- **Description:** Approximate number of active working‑memory items.
- **Source:** LMDB bucket statistics.

- **ID:** `memory.working.ttl_utilization`
- **Description:** Utilization of the 30‑day TTL window.
- **Source:** LMDB key timestamps.

### 4.2 Semantic Memory & KG (PostgreSQL + Chroma)

- **ID:** `memory.semantic.vector_count`
- **Description:** Number of vectors stored in Chroma.

- **ID:** `memory.kg.node_edge_counts`
- **Description:** Node and edge counts in the knowledge graph (PostgreSQL + Chroma indices).

### 4.3 AMS

- **ID:** `memory.ams.consolidation_runs_per_day`
- **Description:** Number of consolidation sessions executed in the last 24h.
- **Source:** `ams_consolidation_state` and scheduler jobs.

- **ID:** `memory.ams.trajectory_count`
- **Description:** Count of AMS trajectories (`ams_trajectories` rows) over recent window.

### 4.4 Memory Album

- **ID:** `memory.album.conversations_total`
- **Description:** Number of curated conversations in `ams_user_memories` with `content_type = 'conversation'`.

---

## 5. Agency Metrics

> Based on `agency_*` tables and AMS trajectories.

### 5.1 Goals & Plans

- **ID:** `agency.goals.by_status`
- **Description:** Counts of goals grouped by status (proposed, active, paused, completed, dropped).
- **Source:** `agency_goals`.

- **ID:** `agency.plans.in_flight`
- **Description:** Number of plans currently executing.
- **Source:** `agency_plans`, `agency_plan_executions`.

### 5.2 Events & Proactivity

- **ID:** `agency.events.per_hour`
- **Description:** Event rate by category from `agency_events_log`.

- **ID:** `agency.followups.pending`
- **Description:** Count of pending follow‑ups in `agency_followups`.

---

## 6. Security Metrics

> Drawn from `auth_*` tables, key management metadata, and audit logs.

### 6.1 Keys & Encryption

- **ID:** `security.keys.master_age_days`
- **Description:** Age of the current master key in days.

### 6.2 Auth & Sessions

- **ID:** `security.auth.failed_logins_24h`
- **Description:** Number of failed auth attempts in last 24 hours.

### 6.3 Audit Logs

- **ID:** `security.audit.entries_24h`
- **Description:** Count of audit log entries over last 24 hours.

---

## 7. System & Extensibility Metrics

### 7.1 Versions & Schema

- **ID:** `system.versions.components`
- **Description:** Current versions of backend, shared library, modelservice, frontend, Studio.

- **ID:** `system.schema.version`
- **Description:** Database schema version (e.g. v33 as per `schema.py`).

### 7.2 Plugins

- **ID:** `system.plugins.active_count`
- **Description:** Number of active plugins in the plugin registry.

---

## 8. Emotion Metrics

> Metrics for AICO's internal emotional state and its representation in Studio.

### 8.1 Timeline & Coverage

- **ID:** `emotion.timeline.samples`
- **Description:** Number of emotion history samples available in a given time window.
- **Source:** Emotion history API (`EmotionHistoryResponse`).
- **Computation:** Count of history entries between `t_start` and `t_end`.
- **Update cadence:** On demand when querying history.
- **Primary surfaces:** Emotion strip (density of segments), Emotion analytics.

- **ID:** `intelligence.emotion.coverage`
- **Description:** Percentage of conversation turns with an attached emotion classification.
- **Source:** Emotion engine logs and/or EmotionState history joined with conversation events.
- **Computation:** `classified_turns / total_turns` over time window.
- **Update cadence:** 5–15 minutes.
- **Primary surfaces:** Intelligence page (Emotion section), Emotion page (diagnostic panel).

### 8.2 Valence–Arousal & Intensity

- **ID:** `emotion.mood.valence_avg`
- **Description:** Average valence over a selected time window.
- **Source:** Emotion history.
- **Computation:** Mean of `valence` for samples in window.
- **Update cadence:** On demand (per query/brush interaction).
- **Surfaces:** Emotion page (summary metrics).

- **ID:** `emotion.mood.arousal_avg`
- **Description:** Average arousal over a selected time window.
- **Source:** Emotion history.

- **ID:** `emotion.mood.intensity_avg`
- **Description:** Average intensity over selected window.

### 8.3 Label Distribution & Episodes

- **ID:** `emotion.labels.distribution`
- **Description:** Frequency distribution of `label.primary` values over a time window.
- **Source:** Emotion history.
- **Computation:** Histogram of labels.
- **Update cadence:** On demand.
- **Surfaces:** Emotion page label distribution chart.

- **ID:** `emotion.episodes.count`
- **Description:** Count of identified emotion episodes (stress, resolution, crisis-regulated) in a time window.
- **Source:** Emotion engine (episode detector) or post-processing of history.
- **Computation:** Episode detection logic as per `emotion-simulation.md` and related docs.
- **Update cadence:** 5–15 minutes.
- **Surfaces:** Emotion episode timeline, Overview event stream.

---

> This file is a **first pass** based on the current schema and docs. As we refine backends and Studio, we will evolve this catalog—adding dimensions, clarifying computations, and decomposing composite scores—while keeping metric IDs stable wherever possible.
