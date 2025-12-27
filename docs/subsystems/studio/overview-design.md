# Studio Overview – Layout & Content Design

## 1. Information Design Concept

The Studio Overview is the **root information hub** for the admin UI. It does not expose raw subsystem details; instead, it gathers **cross-domain signals** into a single, low-friction view. The design goals are:

- **Single-glance system understanding** without drilling anywhere.
- **Zero cognitive overload**: only the most important status indicators are shown by default.
- **Traceability-first structure**: every card and metric is a *linkable entry point* into a deeper domain view (Operations, Intelligence, Memory & AMS, Agency, Security, System).

Information is structured as a **lens over other domains**, not a separate data silo:

- Each overview card is backed by an authoritative subsystem (e.g., Scheduler, AMS, KG, Security) and links to its respective domain hub.
- Clicking any metric, anomaly, or warning drills down into the responsible **domain page**, optionally further into a **detail drawer** for the specific entity (goal, job, memory, etc.).
- The overview never shows information that cannot be reached again via domain pages; everything is traceable and revisitable.

The overview must work equally well on **desktop and large laptop screens** (primary target) while gracefully degrading on tablets.

## 2. Page Layout

### 2.1 Global Layout

- **Top section (Hero band)**
  - Left: "System Status" card row with 3–4 high-level chips:
    - Overall health (OK / Degraded / Attention).
    - Uptime since last restart.
    - Active conversations count.
    - Active agency goals count.
  - Right: environment & build info (DEV / PROD, version, schema version).

- **Middle section (Domain summary cards)**
  - Responsive **2–3 column grid** of glassmorphic `Paper` cards.
  - Each card represents a **primary left-hand domain**:
    - Operations
    - Intelligence
    - Emotion
    - Memory & AMS
    - Agency
    - Security
    - System
  - Each card shows 2–4 key metrics and one trend or sparkline.

- **Bottom section (Recent events & anomalies)**
  - Timeline or table of **important recent events** merged from multiple domains:
    - Failed jobs, degraded models, security alerts, agency anomalies.
  - Each row links to the responsible domain view.

### 2.2 Card Design

- **Visual style**
  - Glassmorphic cards with large radius (≈36px), subtle gradient, and soft shadows.
  - Minimal iconography; each card has one icon in the top-left corner representing the domain.
  - Primary accent (`#B8A1EA`) is used sparingly for highlights and status dots, not large fills.

- **Information structure per card**
  - **Title** (e.g., "Operations")
  - **Primary KPI** (large text)
  - **Secondary KPIs** (2–3 inline labeled metrics)
  - **Trend indicator** (up/down arrow or tiny sparkline) where applicable
  - **Action affordance**: "Open {Domain}" text button linking to the domain hub.

## 3. Content Design

### 3.1 Operations Summary

- **Primary KPI**: current number of healthy services vs. total.
- **Secondary KPIs**:
  - Last 5 minutes error rate (HTTP 5xx and message bus errors).
  - Number of scheduled jobs currently running.
- **Drill-down**: click card → Operations domain hub.

### 3.2 Intelligence Summary

- **Primary KPI**: AI model availability score (how many key models are healthy).
- **Secondary KPIs**:
  - Average LLM response latency.
  - Sentiment/emotion analysis success rate.
- **Drill-down**: opens Intelligence domain hub.

### 3.3 Memory & AMS Summary ✅ FULLY IMPLEMENTED

- **Primary KPI**: retrieval quality index (combined score from hybrid search + AMS).
- **Secondary KPIs**:
  - Working memory items count.
  - Semantic vectors count.
  - Knowledge graph nodes count.
- **Drill-down**: opens Memory & AMS hub, with quick links to Working, Semantic, KG, and Memory Album.
- **Implementation status**: Complete with 5 tabs (Overview, Working Memory, Semantic Memory, Knowledge Graph, Memory Album), interactive graph visualization, system map showing tier connections, and comprehensive metrics panels.

### 3.4 Agency Summary ✅ FULLY IMPLEMENTED

- **Primary KPI**: active goals count.
- **Secondary KPIs**:
  - Curiosity level (low/medium/high).
  - Lessons learned count.
- **Drill-down**: opens Agency hub (goal board view).
- **Implementation status**: Complete with all 5 tabs (Overview, Goals, Curiosity, Learning, Values), glassmorphic design, detail drawer with plan/provenance/execution history.

### 3.5 Security Summary

- **Primary KPI**: security posture status (OK / Rotation due / Alerts).
- **Secondary KPIs**:
  - Age of master key.
  - Failed auth attempts in last 24h.
- **Drill-down**: opens Security hub.

### 3.6 Emotion Summary

- **Primary KPI**: dominant emotion band (e.g. calm / curious / warm_concern) over recent window.
- **Secondary KPIs**:
  - Average valence and arousal (mood position).
  - Time spent in high-intensity or crisis-regulated states.
- **Drill-down**: opens Emotion hub, focusing the emotion strip and circumplex for the same time window.

### 3.7 System Summary

- **Primary KPI**: version alignment (are backend, modelservice, frontend, Studio aligned?).
- **Secondary KPIs**:
  - Database schema version.
  - Number of active plugins.
- **Drill-down**: opens System hub.

## 4. Navigation & Traceability

- Every metric is **clickable** and leads to a domain-specific view.
- The events/anomalies list rows link to:
  - The domain hub.
  - Optionally directly to an entity drawer (job, goal, model, security event).
- No information is "orphaned": if it is shown here, it must have a canonical home view under a domain section.

## 5. UX Notes

- Zero horizontal scrolling; all important content is visible within one viewport on 1440px width.
- Progressive disclosure: additional technical details appear in drawers and secondary panels, never cluttering the overview grid.
- Accessible typography and contrast follow the global Studio design principles and developer guidelines.
