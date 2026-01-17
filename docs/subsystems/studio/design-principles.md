
# AICO Studio – Design & Navigation Principles

> **Scope:** This document defines the navigation model and visual language for the React‑based **Studio** admin UI. It extends the global AICO UI principles to a data‑dense, admin‑oriented environment while preserving the same floating, glassmorphic, emotionally present aesthetic.

Studio is the **single, unified dashboard** for all administrative and observability tasks across AICO. It must feel like part of the same world as the Flutter companion UI, but optimized for expert workflows, clarity, and trust.

---

## 1. UX Goals

- **Zero cognitive friction**
  - New users can immediately understand the overall structure.
  - No nested menus beyond two levels; orientation is always obvious.

- **System transparency & trust**
  - Studio answers: *“What is AICO doing? Is it healthy? Why is it behaving this way?”*
  - Key health and status signals are always visible but non‑intrusive.

- **Fast, expert workflows**
  - Common tasks are reachable within **1–2 clicks** from the Studio home.
  - Power users can jump directly via search, keyboard shortcuts, and deep links.

- **Visual continuity with the main UI**
  - Same color language (soft purple accents, neutral bases).
  - Same floating, glassmorphic composition and organic curves.

- **Safety by design**
  - Destructive or high‑impact actions are visually distinct, gated, and explained.

---

## 2. Global Navigation Model

### 2.1 Single Entry Point

- **Route:** `/admin` (or `/studio` behind the gateway)
- Entry opens the **Studio Home** with:
  - Global system health summary
  - Quick access cards for main domains
  - Recent activity / important alerts

No other scattered admin pages: everything routes through this single Studio shell.

### 2.2 Layout Skeleton

Desktop layout (≥ 1200px width):

```text
[Global Top Bar]

[Sidebar Nav]   [Main Content Area]        [Context Panel (optional)]
```

- **Global Top Bar** (persistent)
  - Left: AICO wordmark + "Studio" label
  - Center: Global search (entities, logs, metrics, goals…)
  - Right: Connection status, environment badge (local/dev/prod), active user, theme toggle

- **Sidebar Navigation** (persistent, collapsible)
  - Primary navigation for major domains (4–7 items max)
  - Icons + labels, with clear grouping and section headers where needed

- **Main Content Area**
  - Hosts the active view (dashboard, table, detail, editor, etc.)

- **Context Panel** (right, optional)
  - Collapsible, used for detail inspectors, related entities, or quick filters.

Tablet/mobile:

- Sidebar collapses into a **floating drawer** triggered from the top bar.
- Content becomes single‑column; context panel becomes overlay.

### 2.3 Navigation Hierarchy

**Core rule:** **Maximum two levels** of navigation depth.

1. **Primary Level – Domains (Sidebar)**
   - Example structure (not exhaustive):

     ```text
     Overview
     ├─ Dashboard
     
     Operations
     ├─ Runtime Health
     ├─ Logs & Traces
     ├─ Tasks & Scheduler
     
     Intelligence
     ├─ Memory & AMS
     ├─ Knowledge Graph
     ├─ Agency & Goals
     
     Security
     ├─ Keys & Identity
     ├─ Access & Sessions
     
     System
     ├─ Configuration
     ├─ Updates
     ├─ Plugins
     ```

   - Each item opens a **domain home** in the main content area.

2. **Secondary Level – Within Domain (Tabs or Card Grid)**
   - Each domain home uses **one** of two patterns:

     - **Horizontal Tabs** (max 4–6):
       - e.g. "Overview", "Resources", "Metrics", "Diagnostics".
       - Tabs switch full panels, not nested navigation.

     - **Card Grid**:
       - For heterogeneous tools within a domain.
       - Each card is a launch point to a focused view or modal.

**No third‑level menus.** Deep detail uses:

- In‑place **drill‑down** (row click opens detail view or slides in context panel), or
- **Modal/wizard** for short, focused flows.

### 2.4 Module Discovery & Routing

Studio integrates backend admin modules dynamically:

- A central endpoint (e.g. `/admin/modules`) returns a manifest per module with:
  - `id`, `name`, `icon`, `category` (maps to a sidebar domain), `route`, `type`, `capabilities`.
- The shell:
  - Maps `category` → appropriate sidebar section.
  - Renders each module as a **card** in its domain or as a **tab** where appropriate.
  - For `type = resource`, uses shared table/form patterns; for `type = dashboard` or `custom`, loads the module’s micro‑frontend into a framed surface.

Navigation must never expose raw technical routing complexity; modules appear as first‑class citizens in the domain structure.

### 2.5 Global Search & Jump‑To

- Keyboard shortcut (e.g. `⌘K` / `Ctrl+K`) opens a **command palette**:
  - Jump to module ("Memory / AMS", "Scheduler", "Agency Goals")
  - Search entities (users, conversations, goals, tasks…)
  - Trigger tools ("Run health check", "Tail logs")
- Results are grouped and clearly labeled to avoid confusion between navigation targets and actions.

---

## 3. Page Archetypes

Studio uses a small set of highly polished page types.

1. **Studio Home (Overview)**
   - Glassmorphic hero panel with system status (green/amber/red, explanation text).
   - Grid of **primary cards** for each domain (Operations, Intelligence, Security, System).
   - Recent alerts / events as horizontally scrollable chips or cards.

2. **Domain Dashboard**
   - Top: domain title + short description.
   - Tabs or card grid for sub‑areas.
   - Key metrics in glass cards (3–6 max), never over‑dense; link through to details.

3. **Resource Explorer (Table View)**
   - Used for users, tasks, logs, goals, skills, etc.
   - Floating table card with:
     - Sticky header, column sorting, global filter.
     - Left filter rail or right context panel for rich filtering.
   - Row click opens **detail drawer** (context panel) instead of full navigation.

4. **Detail View / Editor**
   - Focused on a single entity (user, goal, task, module config).
   - Split layout: primary details on the left, timeline/related items on the right.
   - Destructive actions grouped at the bottom, visually distinct.

5. **Wizards & Modals**
   - For multi‑step actions (e.g. new plugin, key rotation, advanced scheduler tasks).
   - 3–5 clear steps maximal; progress indicator at the top.
   - Modal occupies a centered glass card; dims but does not obscure context.

---

## 4. Visual Design Principles

Studio inherits the global frontend design language, tuned for data‑dense admin views. Detailed visual specifications are maintained in separate theme documentation.

### 4.1 Color Philosophy

- **Domain-specific color system**: Each navigation domain has a dedicated color palette for consistency and visual hierarchy.
- **Status colors**: Success, warning, and error states use semantic colors consistently across all domains.
- **Accessibility-first**: All color combinations must meet WCAG AA+ contrast requirements (4.5:1 minimum).
- **Light theme readability**: Light theme requires special attention to contrast and text weight to ensure readability.
- **Color-independent cues**: Never rely on color alone—always pair with icons, labels, or patterns.

### 4.1.1 Domain Color Assignment

**Each main navigation domain has a dedicated color** for:
- Sidebar icons and active states
- Domain cards on Overview page
- Page headers and hero sections
- Gradient backgrounds

**Domain Color Mapping:**

| Domain | Color Family | Icon | Use Cases |
|--------|--------------|------|-----------|
| **Overview** | Neutral Gray | 🏠 | Dashboard, system-wide views, root hub |
| **Operations** | Blue | ⚡ | System health, users, sessions, scheduler, runtime |
| **Emotion** | Pink/Magenta | 😊 | Emotion tracking, valence, arousal, circumplex |
| **Memory & AMS** | Purple | 📖 | Memory tiers, KG, semantic search, AMS, albums |
| **Agency** | Coral/Orange | ✨ | Goals, learning, curiosity, values, autonomy |
| **System** | Cyan/Teal | ⚙️ | Configuration, updates, plugins, health, settings |

**Consistency Rules:**
1. **Sidebar Navigation**: Active domain uses its primary color for icon and text
2. **Overview Cards**: Each domain card uses its dedicated color for icon, accents, and gradients
3. **Page Headers**: Domain pages use their color for the page icon and accent elements
4. **Hero Sections**: Large dashboard panels use domain color in gradient backgrounds
5. **Status Badges**: Always use semantic colors (success/warning/error), not domain colors

*See theme documentation for exact color values, gradients, and implementation details.*

### 4.2 Shape & Composition Philosophy

- **Radius scale**: Consistent corner radius system from small (chips) to extra-large (modals)
- **Floating composition**: Cards float with breathing room, never full-bleed
- **Glassmorphism**: Backdrop blur and luminous borders for depth
- **Gradient layering**: Radial + linear gradients for hero sections

*See theme documentation for exact values and implementation patterns.*

### 4.3 Typography & Density

- **Base typography**: Inter font family, consistent scale across all views
- **Density rules**: Max 10–12 visible rows per table, prefer progressive disclosure over cramming
- **Hierarchy**: Clear distinction between headlines, subtitles, body, and captions

### 4.4 Dashboard Design Best Practices (2026)

Studio dashboards follow modern UX research principles for data-dense, decision-oriented interfaces:

**Progressive Disclosure & Cognitive Load**
- Show the **pulse in 5–30 seconds**: One dominant primary KPI, 3–5 secondary metrics, critical alerts only.
- Everything else lives behind drill-downs, expandable sections, or detail drawers.
- The era of "show everything" is over—prioritize ruthlessly.

**Problem-First, Not Status-First**
- Surface **anomalies and issues** prominently; healthy services collapse into summary counts.
- Show **deltas and trends** (not just current state): "Database +12% in last hour" vs "Database 78%".
- Context-aware actions: "Archive Old Conversations (will free ~3.2GB)" vs generic "Free Space".

**Data Storytelling Over Raw Numbers**
- Pair every metric with a **declarative sentence**: "Backend responding 3x slower than baseline (45ms → 135ms)".
- Convert vitals into short, concrete narratives that explain impact.
- AI should interpret, not mystify—always include "Why?" tooltips.

**Zero-Interface Philosophy**
- Dashboards should **anticipate needs without active querying**.
- Proactive alerts, context-aware visualizations, automated anomaly detection.
- Surface the right metric at the right moment without hunting.

**Semantic Color + Micro-Interactions**
- Traffic-light logic: green (good), orange (watch), red (act now).
- **Color-independent cues**: Icons, labels, patterns—never color alone (accessibility).
- Subtle animations that spot anomalies faster than static charts.
- Motion guides attention when complexity is high.

**Card-Based Modular Layout**
- Organize metrics into **discrete, self-contained cards**.
- Each card: quick snapshot + "now vs usual" + tap/click for detail.
- Users can pin/reorder/hide cards based on priorities (future: AI-powered personalization).
- Grid systems that scale from mobile to desktop.

**Audience Segmentation**
- Different roles see different views:
  - **Operators**: Real-time, granular, actionable controls.
  - **Administrators**: System health, configuration, maintenance.
  - **Developers**: Data-heavy, filters, drill-downs, technical details.
- Avoid one-size-fits-all dashboards.

---

## 5. Interaction & Feedback

- **Hover & Focus**
  - All interactive elements use soft purple outlines, glows, or background tint on hover/focus.
  - Keyboard focus rings are clearly visible, not subtle.

- **Loading & Progress**
  - Long‑running admin operations (migrations, key rotation, graph rebuilds) surface clear, step‑based progress with human‑readable explanations.
  - Background operations show small, non‑blocking toasts or status banners, never modal‑locking the entire Studio.

- **Destructive Actions**
  - Always use confirmation modals with:
    - Clear, specific copy (what exactly will happen).
    - Red primary button, neutral secondary.
    - Optional extra guard for very high‑risk operations (type‑to‑confirm).

- **Contextual Explanations**
  - Tooltips on icons and status indicators.
  - Inline helper text below complex form fields.
  - "Why" links where agency or scheduler decisions are explained.

---

## 6. Studio‑Specific Navigation Patterns

### 6.1 Domain Dashboards as Hubs

Each sidebar domain has a **hub page** that:

- Explains the domain in 1–2 sentences.
- Surfaces 3–6 key metrics or status cards.
- Provides a card grid of tools and sub‑areas (e.g. "Open Task Queue", "View Agency Goals", "Inspect Memory Tiers").

This keeps navigation discoverable without nested menus.

### 6.2 Card Grid for Tools

- Fixed card size (approx. 280×140px) for visual rhythm.
- Each card shows:
  - Title
  - Short description
  - Status badge (if applicable)
  - Icon reflecting function (logs, graph, shield, etc.)

Clicking a card either:

- Navigates within the domain (resource view), or
- Opens a modal/wizard for self‑contained tools.

### 6.3 Detail Drawers & Linked Context

For entities that appear in multiple domains (e.g. users, devices, goals):

- Row click opens a **detail drawer** from the right, not a full route change.
- Drawer shows:
  - Primary properties
  - Related metrics (e.g. last activity)
  - Links to open the entity in other relevant domains ("Open in Logs", "Open in Agency Goals").

This preserves context while allowing cross‑cutting navigation.

### 6.4 Breadcrumbs & Back Behavior

- Breadcrumbs appear at the top of the main content area:

  ```text
  Studio / Intelligence / Memory & AMS / Semantic Memory
  ```

- They reflect the domain and sub‑area only (no deep internal state).
- The browser back button always respects user expectations; Studio does not override default history semantics with magical behaviors.

---

## 7. Accessibility & Responsiveness

### 7.1 Accessibility Requirements (WCAG 3.0 Ready)

**Contrast & Visual Clarity**
- All colors and text meet **WCAG AA+ contrast** minimum (4.5:1 for body text, 3:1 for large text).
- Status indicators use **color-independent cues**: icons, labels, patterns—never color alone.
- Test with real users: older adults, people with disabilities, low-literacy groups.

**Keyboard Navigation**
- **Full keyboard operability** without mouse across sidebar, cards, tables, and modals.
- **Visible focus rings** on all interactive elements (not subtle—clearly visible).
- Tab order follows logical reading flow.
- Escape key closes modals/drawers, Enter activates primary actions.

**Screen Reader Support**
- ARIA roles for navigation, main content, and live regions (for toasts/status updates).
- Meaningful alt text for all icons and status indicators.
- Form labels properly associated with inputs.
- Dynamic content changes announced to screen readers.

**Touch & Interaction**
- **48px minimum tap targets** for mobile (avoid tiny buttons).
- Sufficient spacing between interactive elements (8px minimum).
- Gesture-based interactions have keyboard/mouse alternatives.

### 7.2 Mobile-First Architecture

**90% of users expect responsive design**—Studio must work seamlessly across devices:

**Responsive Breakpoints**
- **Desktop (≥1200px)**: Sidebar + main + optional context panel.
- **Tablet (768px–1199px)**: Collapsible sidebar, stacked content, single-column cards.
- **Mobile (<768px)**: Single column, bottom-sheet style modals, hamburger navigation.

**Mobile Optimizations**
- Avoid complex visualizations on small screens—use simplified charts or data tables.
- **Seamless hand-off**: Start task on phone, finish on desktop (state preservation).
- Progressive web app (PWA) capabilities for offline access and app-like experience.
- Touch-optimized controls: swipe timelines, pinch to zoom, long-press for context menus.

---

## 8. AI-Powered Personalization & Future Roadmap

### 8.1 Death of One-Size-Fits-All Dashboards

By 2026, dashboards **fundamentally restructure based on how each person actually makes decisions**—learning interaction patterns and anticipating the next question.

**Phase 1: User Preferences (Current)**
- Manual card reordering, pinning, hiding.
- Saved filter sets and view configurations.
- Role-based default layouts (operator vs administrator vs developer).

**Phase 2: Behavioral Learning (Roadmap)**
- Track which metrics users check first, how often, and in what sequence.
- Automatically surface frequently-accessed data higher in the hierarchy.
- Predict next likely action based on current context (e.g., after viewing high disk usage, suggest archive tools).

**Phase 3: Proactive Intelligence (Future)**
- **Anticipatory interfaces**: Dashboard restructures before user realizes they need different data.
- **Next-best-action recommendations**: "Based on current system state, you might want to..."
- **Contextual explanations**: AI interprets anomalies and suggests root causes.
- **Natural language queries**: "Show me why the backend is slow" → generates custom dashboard view.

### 8.2 Explainability & Trust

All AI-driven personalization must be:
- **Transparent**: "Why?" tooltips explain why a metric is surfaced or an action is recommended.
- **Controllable**: Users can always revert to manual layouts or disable AI suggestions.
- **Privacy-aware**: Learning happens locally or with explicit consent; no hidden data collection.

---

## 9. Implementation Notes (React / React‑Admin)

- **Shell vs. Modules**
  - Studio shell handles layout, navigation, theming, and discovery.
  - Individual modules are React‑Admin resources or micro‑frontends that plug into predefined slots.

- **Navigation Integration**
  - Sidebar is driven by the module manifest, grouped by `category`.
  - Domain dashboards are composed from manifest metadata + module‑specific components.

- **Consistent Theming**
  - Use a shared theme and design tokens so all modules (including external ones) inherit Studio’s look and feel with minimal configuration.

This document is the **single source of truth** for the Studio navigation and visual language. All new Studio features and modules must be evaluated against these principles to maintain a coherent, high‑fidelity, award‑worthy admin experience.

