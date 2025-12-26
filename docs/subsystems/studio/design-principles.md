
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

## 4. Visual Design for Studio

Studio inherits the global frontend design language, tuned for data‑dense admin views.

### 4.1 Color

- **Base & Surfaces**
  - Background: `#F5F6FA` (light) / `#181A21` (dark)
  - Primary surfaces: `#FFFFFF` (light) / `#21242E` (dark)
  - Elevated surfaces: `#ECEDF1` (light) / `#2F3241` (dark)

- **Accents**
  - Primary accent: Soft Lavender `#B8A1EA` (Studio actions, selection, focus states).
  - Status colors used consistently:
    - Success: mint / soft green
    - Warning: muted amber
    - Error/destructive: coral `#ED7867`

- **Rules**
  - No large purple backgrounds; accents only on controls, highlights, status rings, and selection.
  - All critical actions (e.g. deletion, key rotation) use the error palette plus explicit labels.

### 4.2 Shape & Composition

- **Radius scale**
  - XLarge (36px): Studio shell containers (main cards, modals, drawers).
  - Large (28px): metric cards, overview cards.
  - Medium (20px): buttons, small panels.
  - Small (12px): tags, chips, pills.

- **Floating composition**
  - 24–40px padding from viewport edges.
  - 16–24px spacing between cards and sections.
  - No full‑bleed panels; even data tables live inside a floating card.

### 4.3 Glassmorphism & Depth

- **Studio Home & Dashboards**
  - Use heavy backdrop blur (20–30px) on primary cards.
  - Luminous white borders (1.5px, 10–30% opacity).
  - Single strong shadow layer for main content, lighter shadows for secondary items.

- **Tables & Forms**
  - Slightly subtler glass effect to preserve text legibility.
  - Higher contrast between rows; use alternating backgrounds or divider lines at 8–12% opacity.

- **Context Panel**
  - Feels like a floating drawer sliding over the background.
  - Same 36px radius, blur, and border treatment as other primary containers.

### 4.4 Typography & Density

- Same base typography as main UI (Inter, 1.0rem body, etc.), with:
  - **Headline 2** for domain titles.
  - **Subtitle** for metric labels.
  - **Body** for table cells and descriptions.

- **Density rules**
  - Max ~10–12 visible rows per table without scrolling on typical desktop height (avoid microscopic text).
  - Prefer progressive disclosure (expandable sections, drawers) over cramming.

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

- All colors and text meet WCAG AA+ contrast.
- Full keyboard navigation across sidebar, cards, tables, and modals.
- ARIA roles for navigation, main content, and live regions (for toasts/status).
- Responsive breakpoints:
  - Desktop: sidebar + main + optional context panel.
  - Tablet: collapsible sidebar, stacked content.
  - Mobile: single column, bottom‑sheet style modals instead of wide dialogs.

---

## 8. Implementation Notes (React / React‑Admin)

- **Shell vs. Modules**
  - Studio shell handles layout, navigation, theming, and discovery.
  - Individual modules are React‑Admin resources or micro‑frontends that plug into predefined slots.

- **Navigation Integration**
  - Sidebar is driven by the module manifest, grouped by `category`.
  - Domain dashboards are composed from manifest metadata + module‑specific components.

- **Consistent Theming**
  - Use a shared theme and design tokens so all modules (including external ones) inherit Studio’s look and feel with minimal configuration.

This document is the **single source of truth** for the Studio navigation and visual language. All new Studio features and modules must be evaluated against these principles to maintain a coherent, high‑fidelity, award‑worthy admin experience.

