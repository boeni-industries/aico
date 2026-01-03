# Operations – Layout & Content Design

## 1. Information Design Concept

The Operations section presents **runtime health, performance, and activity** of AICO's infrastructure:

- API Gateway & REST/WebSocket
- Message Bus
- Scheduler & Jobs
- Logs & Metrics

Conceptually, Operations is the **"how is the system running right now"** lens. It consolidates technical details into a set of visual components that:

- Surface problems and trends without requiring command-line access.
- Preserve full traceability from high-level KPIs down to individual jobs, requests, or log entries.
- Integrate with Agency and Memory views where runtime behavior intersects with goals and tasks.

Information flows are structured as:

- **Aggregated status tiles** → **Domain-specific panels** → **Entity-level drawers** (job, service, log event).
- Every aggregated metric is derived from—and links to—canonical data sources (gateway, scheduler, log store, metrics).

## 2. Page Layout

### 2.1 Main Layout

- **Top row – Runtime snapshot**
  - Tile 1: Services status (gateway, modelservice, scheduler, bus, studio).
  - Tile 2: Request & message throughput (last 5–15 minutes).
  - Tile 3: Error & failure overview.

- **Two-column body**
  - **Left column:**
    - API Gateway panel.
    - Message Bus panel.
  - **Right column:**
    - Scheduler & jobs panel.
    - Logs & alerts panel.

- **Bottom row – Timeline**
  - Unified timeline of **operational events** (deploys, restarts, failures, key job completions).

### 2.2 Panels

- All panels are glassmorphic cards with:
  - Title + subtle icon.
  - Primary KPI at top.
  - Dense but legible charts/tables below.

## 3. Content Design

### 3.1 Services Status Tile

- **Visuals**
  - Row of pill chips: Gateway, Modelservice, Scheduler, Bus, Studio.
  - Each chip: color-coded dot (green/amber/red), label, uptime.

- **Functions**
  - Click chip → open side drawer with:
    - Recent restarts & uptime history.
    - Key metrics (latency, error rate) for that service.
    - Quick action links: "Open Logs", "Go to Operations → {Service}".

### 3.2 API Gateway Panel

- **Visuals**
  - Small line chart of requests per second.
  - Error rate (HTTP 4xx/5xx) stacked area or bar.
  - Top 5 endpoint groups by traffic.

- **Functions**
  - Filter by timeframe (last 5m, 1h, 24h).
  - Click an endpoint group → open drawer with more details (latency distribution, sample errors) and link to API docs (if available).

### 3.3 Message Bus Panel

- **Visuals**
  - Topic/channel list with **message rate** and **backlog depth**.
  - Mini health badges for each consumer group.

- **Functions**
  - Click topic → detail drawer with last errors and connected services.
  - Integrate with Agency where certain topics are tied to agency events.

### 3.4 Scheduler & Jobs Panel

- **Visuals**
  - Histogram of jobs executed per minute/hour.
  - Breakdown by queue: user_facing, background_light, background_heavy, maintenance.
  - List of last N failed jobs.

- **Functions**
  - Clicking a queue opens a filtered jobs table.
  - Each job row links to:
    - Raw job details.
    - Related Agency goal/plan/step (if present in metadata).

### 3.5 Logs & Alerts Panel

- **Visuals**
  - Table of recent high-severity log events.
  - Status row for log persistence and disk usage.

- **Functions**
  - Filter by service and severity.
  - Click event → detail drawer with full log, context, and quick links:
    - Open same time range in other panels (gateway, scheduler).

### 3.6 Timeline

- Single, horizontally scrollable timeline summarizing key events:
  - Restarts, deploys, spikes in errors, job failures, important agency events.
- Clicking an event focuses relevant panels and opens its detail drawer.

## 4. Navigation & Traceability

- From Operations you can reach:
  - **Agency** (via jobs tied to goals/plans).
  - **Security** (via auth-related errors).
  - **System** (via version changes or migrations).
- All rows in tables and charts provide drill-down paths to canonical data; there are no dead-end summaries.

## 5. UX Notes

- Optimized for at-a-glance diagnosis first, deep debugging second.
- No nested navigation on the left; all intra-Operations navigation is via tabs/cards within the page and drawers.
- Uses consistent iconography and card design across panels, following Studio design principles and developer guidelines.
