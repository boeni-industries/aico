# Operations Page - Navigation & Structure Design

## Executive Summary

The Operations page provides real-time visibility into AICO's runtime health, performance, and infrastructure activity. It follows a **glanceable-first, progressive-disclosure** pattern inspired by industry leaders like Grafana, Datadog, and Kubernetes Dashboard, while maintaining Studio's award-winning glassmorphic aesthetic.

---

## Navigation Philosophy

### **1. Zero-Click Health Check**
**Goal:** Answer "Is everything OK?" in <1 second without any interaction.

**Implementation:**
- **Runtime Snapshot** at the top displays all 5 critical services (Gateway, Modelservice, Scheduler, Bus, Studio)
- Color-coded health status (green/amber/red) with visual icons
- Key metrics visible immediately (latency, throughput, uptime)
- Overall system status chip provides instant health summary

**Why This Works:**
- Follows **F-pattern reading** (users scan top-left first)
- Matches **Grafana's dashboard pattern** (critical metrics at top)
- Reduces **cognitive load** (no clicking required for basic health check)

---

### **2. Domain-Based Grid Layout**
**Goal:** Organize operational concerns into scannable, self-contained panels.

**Structure:**
```
┌─────────────────────────────────────────────────────────┐
│  RUNTIME SNAPSHOT (Horizontal Scroll)                   │
│  [Gateway] [Modelservice] [Scheduler] [Bus] [Studio]   │
├──────────────────────┬──────────────────────────────────┤
│  API GATEWAY         │  SCHEDULER & JOBS                │
│  • Request metrics   │  • Queue visualization           │
│  • Error rates       │  • Job history                   │
│  • Top endpoints     │  • Failed jobs                   │
├──────────────────────┼──────────────────────────────────┤
│  MESSAGE BUS         │  LOGS & ALERTS                   │
│  • Topic health      │  • Severity filtering            │
│  • Backlog depth     │  • Service filtering             │
│  • Consumer groups   │  • Recent events                 │
├──────────────────────┴──────────────────────────────────┤
│  OPERATIONAL TIMELINE                                   │
│  ●────●────●────●────●────●────●────●                  │
└─────────────────────────────────────────────────────────┘
```

**Why This Works:**
- **2-column grid** maximizes screen real estate (desktop: 50/50, mobile: stacked)
- **Self-contained panels** prevent context switching
- **Consistent card height** creates visual rhythm
- **No nested navigation** (follows Studio's 2-level max rule)

---

### **3. Progressive Disclosure Pattern**
**Goal:** Show summaries first, details on demand.

**Levels:**
1. **L1 - Glance:** Runtime Snapshot (all services, 1 row)
2. **L2 - Scan:** Domain panels (KPIs + charts, grid layout)
3. **L3 - Drill:** Detail drawers (click any metric/row)
4. **L4 - Deep:** Cross-link to related domains (Agency, Security, System)

**Example Flow:**
```
User sees error spike in API Gateway panel
  ↓ Click error rate metric
  ↓ Detail drawer opens (right side)
  ↓ Shows: error distribution, sample logs, affected endpoints
  ↓ Click "Open in Logs & Alerts" link
  ↓ Logs panel auto-filters to gateway errors
  ↓ Click specific log event
  ↓ Detail drawer shows: full stack trace, related requests, time correlation
```

**Why This Works:**
- **Preserves context** (drawers don't navigate away)
- **Reduces clicks** (most tasks = 1-2 clicks from home)
- **Follows Kubernetes Dashboard pattern** (detail panels slide in)

---

## Visual Design Rationale

### **1. Glassmorphic Cards - Consistent with Memory & AMS**
All panels use Studio's signature glassmorphic design:

```tsx
{
  p: 3,
  borderRadius: '20px',
  bgcolor: 'rgba(255, 255, 255, 0.02)',
  backdropFilter: 'blur(12px)',
  border: '1px solid',
  borderColor: 'divider',
}
```

**Why:**
- **Visual continuity** with Memory & AMS pages
- **Depth perception** (floating cards feel premium)
- **Readability** (subtle blur doesn't obscure data)

### **2. Color-Coded Status System**
Consistent status colors across all components:

- **Healthy:** `#10B981` (mint green) - success, normal operation
- **Degraded:** `#F59E0B` (amber) - warning, attention needed
- **Critical:** `#EF4444` (coral red) - error, immediate action required
- **Accent:** `#B8A1EA` (lavender) - Studio primary, interactive elements

**Why:**
- **Universal color language** (green=good, red=bad)
- **Accessibility** (WCAG AA+ contrast ratios)
- **Consistency** (matches Memory & AMS health indicators)

### **3. Typography Hierarchy**
```
- Panel Titles: 0.75rem, uppercase, 600 weight, letter-spacing 0.1em
- KPI Values: h5 (1.1-1.5rem), 700 weight, color-coded
- Metric Labels: 0.7rem caption, text.secondary
- Table Data: 0.75rem, monospace for IDs/paths
```

**Why:**
- **Scannable** (clear visual hierarchy)
- **Dense but legible** (fits ~10 rows per panel)
- **Professional** (matches Datadog/Grafana density)

---

## Component Architecture

### **Runtime Snapshot**
**Purpose:** Instant health check for all services

**Features:**
- Horizontal scrollable cards (5 services)
- Color-coded status dots with icons
- Key metric per service (latency, jobs, throughput, users)
- Uptime display
- Overall system status chip

**Inspiration:** Kubernetes Dashboard node status, Grafana service overview

---

### **API Gateway Panel**
**Purpose:** HTTP/WebSocket traffic monitoring

**Features:**
- Request/sec and error rate KPIs
- Area chart showing request volume over time
- Top 5 endpoints table with latency and error rates
- Timeframe selector (5m, 1h, 24h)
- Hover-to-drill pattern for endpoint details

**Inspiration:** Datadog APM, AWS CloudWatch metrics

**Why Charts Work Here:**
- **Trends matter** (spike detection is visual)
- **Time-series data** (requests over time)
- **Comparison** (normal vs. anomalous patterns)

---

### **Scheduler & Jobs Panel**
**Purpose:** Background task execution monitoring

**Features:**
- Jobs today, failed count, success rate KPIs
- Queue utilization bars (4 queues: user_facing, background_light, background_heavy, maintenance)
- Recent jobs list with status icons
- Color-coded priority badges
- Click job → detail drawer with Agency goal links

**Inspiration:** Kubernetes job status, Airflow DAG runs

**Why Linear Progress Bars:**
- **Capacity visualization** (queue fullness at a glance)
- **Comparison** (which queues are busy)
- **Threshold awareness** (80%+ = warning)

---

### **Message Bus Panel**
**Purpose:** Inter-service communication health

**Features:**
- Messages/sec, backlog, topic count KPIs
- Topic list with health indicators
- Message rate and backlog depth per topic
- Consumer group count
- Click topic → detail drawer with error logs

**Inspiration:** Kafka monitoring tools, RabbitMQ management UI

**Why Topic Cards:**
- **Self-contained** (each topic is independent)
- **Status at a glance** (health icon + metrics)
- **Hover interaction** (no click required for basic info)

---

### **Logs & Alerts Panel**
**Purpose:** System-wide logging and issue tracking

**Features:**
- Error and warning count chips
- Severity filter (error, warning, info, debug)
- Service filter (gateway, modelservice, scheduler, memory, bus)
- Recent events list with color-coded severity
- Storage status indicator (disk usage)
- Click event → detail drawer with full log and context

**Inspiration:** Splunk, ELK Stack, Datadog Logs

**Why Filtering First:**
- **Noise reduction** (focus on relevant logs)
- **Common workflow** (filter → scan → drill)
- **Performance** (don't render 1000s of logs)

---

### **Operational Timeline**
**Purpose:** Historical event context

**Features:**
- Vertical timeline with event dots
- Event types: deploys, restarts, errors, job completions
- Time-ordered (most recent first)
- Click event → focuses relevant panels and opens detail
- Visual continuity line connecting events

**Inspiration:** GitHub activity timeline, Linear issue history

**Why Timeline Format:**
- **Temporal correlation** (see what happened when)
- **Causality** (deploy → restart → error spike)
- **Narrative** (tells the story of system behavior)

---

## Navigation Patterns

### **1. No Nested Menus**
Operations uses **tabs within the page** (not sidebar sub-items):
- All operational domains visible in grid
- No hidden functionality
- Maximum 2 clicks to any feature

### **2. Detail Drawers (Not Full Pages)**
Clicking any metric/row opens a **right-side drawer**:
- Preserves context (main view still visible)
- Faster than page navigation
- Matches Memory & AMS pattern (card detail modal)

### **3. Cross-Domain Links**
Every panel can link to related domains:
- API Gateway errors → Security (auth failures)
- Scheduler jobs → Agency (goal-linked tasks)
- Logs → System (version/migration events)

### **4. Auto-Refresh**
Consistent with Memory & AMS:
- Toggle auto-refresh (5s interval)
- Manual refresh button
- Loading indicators during refresh
- No jarring full-page reloads

---

## Why This Structure Beats Alternatives

### **❌ Alternative 1: Tabbed Interface**
```
[Services] [Gateway] [Scheduler] [Bus] [Logs]
```
**Problem:** Hides information, requires clicking to see each domain

### **❌ Alternative 2: Single Long Page**
```
[All panels stacked vertically]
```
**Problem:** Requires scrolling, no at-a-glance overview

### **✅ Our Approach: Grid + Snapshot**
```
[Snapshot Row]
[2x2 Grid of Panels]
[Timeline]
```
**Benefits:**
- **Glanceable** (all domains visible)
- **Scannable** (grid layout, consistent heights)
- **Actionable** (click anywhere to drill)

---

## Best-in-Class Features

### **1. Visual-First Design**
- **Charts over tables** where trends matter (API Gateway)
- **Progress bars** for capacity (Scheduler queues)
- **Color-coded status** everywhere (health, severity, metrics)
- **Icons** for quick recognition (service types, event types)

### **2. Contextual Intelligence**
- **Cross-panel correlation** (timeline event → filter logs)
- **Agency integration** (scheduler jobs → goal links)
- **Time-based filtering** (5m/1h/24h views)

### **3. Professional Density**
- **~10 items per panel** (Datadog/Grafana standard)
- **Compact but legible** (0.7-0.85rem fonts)
- **Efficient use of space** (no wasted whitespace)

### **4. Interaction Patterns**
- **Hover for details** (tooltips, highlights)
- **Click for drill-down** (drawers, not navigation)
- **Filter-first** (logs, severity, timeframe)

---

## Implementation Notes

### **Component Reusability**
All panels share common patterns:
- `Paper` wrapper with glassmorphic styling
- Header with title + status chip
- KPI row (2-3 metrics)
- Main content area (chart/table/list)
- Consistent spacing (p: 3, gap: 2-3)

### **Data Flow**
```
OperationsPage (container)
  ↓ Fetches data from API
  ↓ Passes to child components
  ↓ RuntimeSnapshot, ApiGatewayPanel, etc.
  ↓ Components render with auto-refresh
```

### **Responsive Behavior**
- **Desktop (≥1200px):** 2-column grid
- **Tablet (768-1199px):** 2-column grid (narrower)
- **Mobile (<768px):** Single column stack

---

## Conclusion

The Operations page achieves **award-winning visual fidelity** and **maximum UX** through:

1. **Glanceable health** (Runtime Snapshot)
2. **Domain separation** (Grid layout)
3. **Progressive disclosure** (Drawers, not pages)
4. **Visual-first** (Charts, colors, icons)
5. **Professional density** (Datadog/Grafana standard)
6. **Consistent design** (Glassmorphic Studio aesthetic)

Every design decision prioritizes **speed to insight** while maintaining **visual excellence**.
