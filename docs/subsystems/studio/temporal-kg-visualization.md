# Temporal Knowledge Graph Visualization - AICO Studio

**Status:** Design Proposal  
**Component:** Studio Intelligence Tab  
**Research Basis:** Bi-temporal data visualization best practices (2025)

---

## Overview

A hyper-UX visualization for AICO's temporal knowledge graph that makes relationship evolution, entity history, and temporal queries intuitive and beautiful.

---

## Core Concept: "Time Travel Knowledge Graph"

**Philosophy:** Make time a first-class citizen in the UI, not an afterthought.

**Key Insight:** Users don't think "show me is_current=1 nodes" - they think:
- "What did I know about Sarah last month?"
- "When did my relationship with this project change?"
- "How has my knowledge evolved over time?"

---

## UI Components

### 1. **Timeline Scrubber** (Primary Control)

**Location:** Top of graph view, always visible

**Design:**
```
┌─────────────────────────────────────────────────────────────┐
│  [◀] ──●────────────────────────────────────────────── [▶]  │
│       Jan 2024        Jun 2024        Dec 2024    NOW        │
│                                                               │
│  📊 Activity Heatmap (density of changes)                    │
│  ▁▂▁▃▅▇▅▃▂▁▁▂▃▅▇▅▃▂▁▁▂▃▅▇▅▃▂▁▁▂▃▅▇▅▃▂▁                      │
└─────────────────────────────────────────────────────────────┘
```

**Features:**
- **Drag scrubber** to any point in time → graph updates to show state at that moment
- **Activity heatmap** shows when knowledge changed (darker = more activity)
- **Hotspots** are clickable → jump to moments of significant change
- **Keyboard shortcuts**: ← → to step through changes, Space to play/pause animation
- **Presets**: "Last week", "Last month", "6 months ago", "1 year ago", "All time"

**Interaction:**
- Hover over timeline → tooltip shows "23 changes on Dec 15, 2024"
- Click hotspot → graph animates to that moment, highlights what changed
- Double-click → open "Change Detail Panel" for that timestamp

---

### 2. **Graph View with Temporal States**

**Visual Language:**

**Current Entities (is_current=1):**
- **Solid nodes** with full opacity
- **Bright colors** (blue for PERSON, green for PROJECT, etc.)
- **Thick edges** (2px stroke)
- **Pulsing glow** for recently updated entities

**Historical Entities (is_current=0):**
- **Dashed outline** nodes (ghost mode)
- **Muted colors** (30% opacity)
- **Thin edges** (1px stroke, dashed)
- **Fade-in animation** when scrubber moves to their time period

**Temporal Transitions:**
- **Morphing animation** when entity properties change
- **Split animation** when entity is superseded (old fades, new appears)
- **Merge animation** when duplicates are resolved

**Example:**
```
Sarah (girlfriend) ──[2024-01-01]──> Sarah (wife)
     ↓                                    ↓
  [Dashed]                            [Solid]
  30% opacity                         100% opacity
  (historical)                        (current)
```

---

### 3. **Entity Timeline Panel** (Right Sidebar)

**Triggered by:** Clicking any node

**Content:**
```
┌─────────────────────────────────────────┐
│  Sarah                                   │
│  PERSON                                  │
├─────────────────────────────────────────┤
│                                          │
│  📅 Timeline                             │
│                                          │
│  ● NOW (Current)                         │
│  │  Status: Wife                         │
│  │  Relationship: Family                 │
│  │                                       │
│  ├─ Dec 2024                             │
│  │  Changed: Status (girlfriend → wife)  │
│  │  Reason: Marriage                     │
│  │                                       │
│  ├─ Jun 2024                             │
│  │  Changed: Added property "anniversary"│
│  │                                       │
│  ○ Jan 2024 (First mentioned)            │
│     Status: Girlfriend                   │
│     Source: "Sarah and I are dating"     │
│                                          │
│  [View Full History →]                   │
└─────────────────────────────────────────┘
```

**Features:**
- **Vertical timeline** of all changes to this entity
- **Diff view** for property changes (old → new)
- **Source attribution** (which conversation mentioned it)
- **Reason tracking** (why it changed - user correction, conflict resolution, etc.)
- **Click any point** → scrubber jumps to that time, graph updates

---

### 4. **Relationship Evolution View**

**Triggered by:** Clicking any edge

**Content:**
```
┌─────────────────────────────────────────┐
│  Michael → Sarah                         │
│  Relationship Evolution                  │
├─────────────────────────────────────────┤
│                                          │
│  ● NOW                                   │
│  │  MARRIED_TO                           │
│  │  Since: Dec 2024                      │
│  │                                       │
│  ├─ Dec 2024                             │
│  │  DATING → MARRIED_TO                  │
│  │  Event: Wedding                       │
│  │                                       │
│  ○ Jan 2024                              │
│     DATING                                │
│     First mentioned: "Sarah and I..."    │
│                                          │
│  📊 Interaction Frequency                │
│  ▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇                  │
│  Jan  Mar  May  Jul  Sep  Nov  NOW      │
│                                          │
└─────────────────────────────────────────┘
```

**Features:**
- **Relationship type changes** over time
- **Interaction frequency graph** (how often mentioned together)
- **Event markers** (marriage, move, job change, etc.)
- **Sentiment tracking** (if emotional memory is enabled)

---

### 5. **Change Feed** (Bottom Panel, Collapsible)

**Real-time stream of knowledge graph changes:**

```
┌─────────────────────────────────────────────────────────────┐
│  🔄 Recent Changes                                           │
├─────────────────────────────────────────────────────────────┤
│  ● 2 minutes ago                                             │
│    Added: PROJECT "AICO Studio"                              │
│    Source: Conversation #1234                                │
│                                                              │
│  ● 5 minutes ago                                             │
│    Updated: PERSON "Sarah" (girlfriend → wife)               │
│    Reason: User correction                                   │
│                                                              │
│  ● 10 minutes ago                                            │
│    Merged: TOPIC "Python" (3 duplicates → 1 canonical)       │
│    Reason: Entity resolution                                 │
│                                                              │
│  [View All Changes →]                                        │
└─────────────────────────────────────────────────────────────┘
```

**Features:**
- **Live updates** as knowledge graph changes
- **Click any change** → jump to that entity/time
- **Filter by type** (Added, Updated, Merged, Deleted)
- **Search changes** by entity name or date range

---

### 6. **Temporal Query Builder** (Advanced Feature)

**Location:** Top toolbar, "Query" button

**Interface:**
```
┌─────────────────────────────────────────────────────────────┐
│  🔍 Temporal Query                                           │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  Show me: [All entities ▼]                                  │
│                                                              │
│  As of:   [● Now  ○ Specific date  ○ Date range]            │
│           [Dec 15, 2024 ▼]                                   │
│                                                              │
│  Where:   [+ Add filter]                                    │
│           • Label = PERSON                                   │
│           • Property "status" changed                        │
│                                                              │
│  [Run Query]                                                 │
└─────────────────────────────────────────────────────────────┘
```

**Example Queries:**
- "Show all PERSON entities as of 6 months ago"
- "Show entities that changed last week"
- "Show relationships that ended (valid_until is set)"
- "Show all versions of entity 'Sarah'"

---

### 7. **Comparison Mode** (Split View)

**Triggered by:** "Compare" button in toolbar

**Layout:**
```
┌──────────────────────┬──────────────────────┐
│  Jan 2024            │  NOW                 │
│                      │                      │
│  [Graph State]       │  [Graph State]       │
│                      │                      │
│  • 15 entities       │  • 42 entities       │
│  • 8 relationships   │  • 48 relationships  │
│                      │                      │
│  [Diff: +27 entities, +40 relationships]    │
└──────────────────────┴──────────────────────┘
```

**Features:**
- **Side-by-side comparison** of graph at two points in time
- **Highlight differences** (green = added, red = removed, yellow = changed)
- **Sync scrolling/zooming** between views
- **Diff summary** shows what changed

---

## Visual Design Language

### Color Palette (Temporal States)

**Current (is_current=1):**
- Primary: `#3B82F6` (blue) - vibrant, solid
- Success: `#10B981` (green) - active, healthy
- Accent: `#8B5CF6` (purple) - important

**Historical (is_current=0):**
- Muted: `#94A3B8` (slate) - 30% opacity
- Ghost: `#E2E8F0` (light slate) - dashed outline
- Faded: `#CBD5E1` (very light slate) - background

**Transitions:**
- Change: `#F59E0B` (amber) - something evolved
- Merge: `#06B6D4` (cyan) - entities combined
- Split: `#EC4899` (pink) - entity superseded

### Animation Principles

**Smooth Transitions:**
- **Duration**: 300ms for state changes, 150ms for hovers
- **Easing**: `cubic-bezier(0.4, 0.0, 0.2, 1)` (Material Design)
- **Stagger**: 50ms delay between nodes for cascading effect

**Temporal Scrubbing:**
- **Playback speed**: 1 month per second (adjustable)
- **Frame rate**: 60fps for smooth animation
- **Interpolation**: Smooth morphing between states

**Feedback:**
- **Hover**: Gentle glow (0-8px blur)
- **Click**: Ripple effect from click point
- **Selection**: Pulsing outline (1s cycle)

---

## Interaction Patterns

### Keyboard Shortcuts

- `←` / `→`: Step backward/forward in time (1 day)
- `Shift + ←/→`: Jump backward/forward (1 month)
- `Space`: Play/pause timeline animation
- `Cmd/Ctrl + Z`: Undo temporal navigation
- `Cmd/Ctrl + F`: Open temporal query builder
- `Cmd/Ctrl + D`: Toggle comparison mode
- `H`: Toggle historical entities (show/hide)

### Mouse Interactions

- **Click node**: Open entity timeline panel
- **Double-click node**: Zoom to entity neighborhood
- **Right-click node**: Context menu (View history, Compare versions, etc.)
- **Drag node**: Reposition (layout persists)
- **Scroll**: Zoom in/out
- **Cmd/Ctrl + Scroll**: Scrub timeline

### Touch Gestures (Mobile/Tablet)

- **Pinch**: Zoom graph
- **Two-finger swipe left/right**: Scrub timeline
- **Long press**: Open entity timeline panel
- **Double-tap**: Zoom to entity

---

## Technical Implementation

### Data Structure

```typescript
interface TemporalNode {
  id: string;
  label: string;
  properties: Record<string, any>;
  is_current: boolean;
  valid_from: string;  // ISO 8601
  valid_until: string | null;
  created_at: string;
  updated_at: string;
  canonical_id: string;
  versions: TemporalNode[];  // Historical versions
}

interface TemporalEdge {
  id: string;
  source_id: string;
  target_id: string;
  relation_type: string;
  is_current: boolean;
  valid_from: string;
  valid_until: string | null;
  versions: TemporalEdge[];
}
```

### API Endpoints

```typescript
// Get graph state at specific time
GET /api/v1/kg/temporal?user_id={id}&as_of={timestamp}

// Get entity history
GET /api/v1/kg/nodes/{node_id}/history

// Get changes in time range
GET /api/v1/kg/changes?from={timestamp}&to={timestamp}

// Compare graph states
GET /api/v1/kg/compare?from={timestamp}&to={timestamp}
```

### Frontend Stack

**Graph Rendering:**
- **Library**: D3.js + Force-directed layout
- **Canvas**: WebGL for performance (1000+ nodes)
- **Fallback**: SVG for smaller graphs (<100 nodes)

**Timeline:**
- **Library**: Custom React component
- **Scrubbing**: RAF (requestAnimationFrame) for 60fps
- **Heatmap**: Canvas-based density visualization

**State Management:**
- **Store**: Zustand (lightweight, fast)
- **Time travel**: Built-in undo/redo stack
- **Caching**: React Query for API responses

---

## User Flows

### Flow 1: "When did my relationship with Sarah change?"

1. User opens Intelligence tab
2. Searches for "Sarah" in graph
3. Clicks Sarah node → Entity timeline panel opens
4. Sees timeline: "girlfriend (Jan 2024) → wife (Dec 2024)"
5. Clicks "Dec 2024" change → scrubber jumps to that moment
6. Graph animates to show state at that time
7. User sees relationship edge change from DATING to MARRIED_TO

### Flow 2: "What did I know about Python 6 months ago?"

1. User opens temporal query builder
2. Sets: "Show TOPIC entities as of 6 months ago"
3. Adds filter: "name contains 'Python'"
4. Runs query → graph shows historical state
5. Sees: Only 2 Python-related entities (vs 15 now)
6. Clicks "Compare to now" → split view shows growth

### Flow 3: "Show me how my knowledge grew this year"

1. User drags timeline scrubber to Jan 1, 2024
2. Clicks "Play" button
3. Graph animates through the year (1 month/second)
4. User sees entities appear, relationships form, duplicates merge
5. Activity heatmap highlights busy periods
6. User pauses at interesting moment, explores changes

---

## Accessibility

**Screen Reader Support:**
- **ARIA labels** for all interactive elements
- **Keyboard navigation** for entire graph
- **Text alternatives** for visual states
- **Announcements** for temporal changes

**Visual Accessibility:**
- **High contrast mode** for historical/current distinction
- **Color-blind safe palette** (tested with Coblis)
- **Adjustable animation speed** (or disable entirely)
- **Zoom up to 400%** without layout breaking

**Cognitive Accessibility:**
- **Progressive disclosure** (hide complexity by default)
- **Tooltips** explain temporal concepts
- **Undo/redo** for all actions
- **Clear visual hierarchy**

---

## Performance Targets

**Graph Rendering:**
- **<100 nodes**: 60fps, instant updates
- **100-500 nodes**: 30fps, <100ms updates
- **500-1000 nodes**: 15fps, <200ms updates
- **1000+ nodes**: Pagination or clustering

**Timeline Scrubbing:**
- **60fps** during animation
- **<50ms** to compute graph state at any point
- **<100ms** to render state change

**API Response:**
- **<100ms** for temporal queries (with caching)
- **<500ms** for complex comparisons
- **<1s** for full history retrieval

---

## Future Enhancements

### Phase 2: Predictive Timeline

**Concept:** AI predicts future knowledge graph states

**Features:**
- "Based on patterns, you'll likely learn X next month"
- Suggested entities to explore
- Relationship drift detection ("You haven't talked to John in 3 months")

### Phase 3: Collaborative Temporal Graphs

**Concept:** Multiple users' knowledge graphs intersect

**Features:**
- Shared entities (e.g., "Sarah" in both Michael's and Alice's graphs)
- Relationship triangulation (how do I know John? Through Sarah)
- Privacy-preserving temporal queries

### Phase 4: Temporal Anomaly Detection

**Concept:** AI highlights unusual temporal patterns

**Features:**
- "Sudden spike in PROJECT entities last week"
- "Relationship with X has been declining"
- "You learned 5x more about Y than usual this month"

---

## Conclusion

This temporal visualization transforms AICO's knowledge graph from a static snapshot into a **living, breathing timeline of the user's evolving knowledge**. 

**Key Differentiators:**
- ✅ **Time as first-class citizen** (not an afterthought)
- ✅ **Intuitive scrubbing** (drag to any point in time)
- ✅ **Beautiful animations** (smooth state transitions)
- ✅ **Powerful queries** (temporal SQL made visual)
- ✅ **Accessible** (keyboard, screen reader, high contrast)

**Impact:**
- Users understand how their knowledge evolved
- Relationship changes are visible and traceable
- Temporal queries become intuitive
- Trust increases (full transparency into what AICO knows)
