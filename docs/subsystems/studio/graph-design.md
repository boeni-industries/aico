# Knowledge Graph Visualization - Design Specification

**Status:** Design Specification  
**Component:** Studio Intelligence Tab - Graph View  
**Version:** 1.0  
**Last Updated:** 2025-12-30

---

## Executive Summary

This document defines the visual design, interaction patterns, and technical architecture for AICO's knowledge graph visualization. The goal is to create an **award-winning, maximum-UX graph interface** that transforms complex temporal knowledge data into an intuitive, beautiful, and highly functional visualization tool.

**Core Philosophy:** Make the invisible visible—transform abstract graph data into a spatial, temporal, and interactive experience that feels natural and empowering.

---

## Design Principles

### 1. **Clarity Over Complexity**
- Avoid "hairball" visualizations at all costs
- Progressive disclosure: show essential information first, details on demand
- Clear visual hierarchy: current > recent > historical

### 2. **Temporal Awareness**
- Time is a first-class citizen, not an afterthought
- Smooth transitions between temporal states
- Visual distinction between current and historical data

### 3. **Performance First**
- 60fps interactions for <500 nodes
- Graceful degradation for larger graphs
- WebGL rendering for maximum performance

### 4. **Accessibility & Inclusivity**
- Keyboard navigation for all features
- Screen reader support with ARIA labels
- Color-blind safe palette
- Adjustable animation speeds

### 5. **Discoverability & Exploration**
- Wikipedia-style navigation (node cards with embedded links)
- Organic discovery through visual connections
- Multiple entry points (search, filter, timeline)

---

## Visual Design Language

### Color Palette

**Current State (is_current=1):**
```
Primary Nodes:     #3B82F6 (blue)      - Vibrant, solid, 100% opacity
Success/Active:    #10B981 (green)     - Healthy, connected
Important:         #8B5CF6 (purple)    - High centrality, key entities
Warning:           #F59E0B (amber)     - Needs attention
```

**Historical State (is_current=0):**
```
Ghost Nodes:       #94A3B8 (slate)     - 30% opacity, dashed outline
Faded Edges:       #CBD5E1 (light)     - 20% opacity, thin stroke
Background:        #E2E8F0 (very light)- Subtle presence
```

**Transitions & Events:**
```
Change:            #F59E0B (amber)     - Property updated
Merge:             #06B6D4 (cyan)      - Entities combined
Split:             #EC4899 (pink)      - Entity superseded
New:               #10B981 (green)     - Recently created
Deleted:           #EF4444 (red)       - Removed/archived
```

**Entity Type Colors:**
```
PERSON:            #3B82F6 (blue)
ORGANIZATION:      #8B5CF6 (purple)
LOCATION:          #10B981 (green)
TOPIC:             #F59E0B (amber)
PROJECT:           #06B6D4 (cyan)
EVENT:             #EC4899 (pink)
DOCUMENT:          #64748B (slate)
```

### Typography

**Node Labels:**
- Primary: Inter, 14px, 600 weight, 100% opacity
- Secondary: Inter, 12px, 400 weight, 70% opacity
- Metadata: Inter, 10px, 400 weight, 50% opacity

**UI Elements:**
- Headings: Inter, 16-24px, 700 weight
- Body: Inter, 14px, 400 weight
- Captions: Inter, 12px, 400 weight
- Monospace: Fira Code, 12px (for IDs, timestamps)

### Animation Principles

**Timing:**
- State changes: 300ms
- Hover effects: 150ms
- Timeline scrubbing: 60fps
- Node entrance: 400ms with stagger (50ms delay between nodes)

**Easing:**
- Default: `cubic-bezier(0.4, 0.0, 0.2, 1)` (Material Design)
- Bounce: `cubic-bezier(0.68, -0.55, 0.265, 1.55)` (for emphasis)
- Smooth: `cubic-bezier(0.25, 0.1, 0.25, 1.0)` (for scrubbing)

---

## Layout Algorithms

### Primary: **Force-Directed (ForceAtlas2)**

**Why ForceAtlas2:**
- Industry standard (used by Gephi)
- Excellent for revealing community structure
- Continuous algorithm (smooth real-time updates)
- Handles 1000+ nodes efficiently
- Tunable parameters for different graph types

**Configuration:**
```typescript
{
  gravity: 1.0,              // Pull nodes toward center
  scalingRatio: 2.0,         // Repulsion strength
  strongGravityMode: false,  // Linear vs logarithmic gravity
  barnesHutOptimize: true,   // O(n log n) performance
  barnesHutTheta: 1.2,       // Approximation quality
  edgeWeightInfluence: 1.0,  // Edge weight impact
  linLogMode: false,         // Linear vs log-log mode
  adjustSizes: false,        // Prevent node overlap
  iterationsPerRender: 10    // Smooth animation
}
```

### Secondary Layouts (User-Selectable)

**1. Hierarchical (Top-Down)**
- Best for: Tree structures, organizational charts
- Algorithm: Sugiyama layered layout
- Use case: Temporal evolution, entity relationships

**2. Radial (Circular)**
- Best for: Highlighting central entities
- Algorithm: Concentric circles by centrality
- Use case: Ego networks, entity neighborhoods

**3. Circular**
- Best for: Small graphs, relationship cycles
- Algorithm: Nodes on circle perimeter
- Use case: Simple relationship visualization

**4. Grid (No Overlap)**
- Best for: Dense graphs, readability
- Algorithm: Force-directed + collision detection
- Use case: Maximum label visibility

---

## Node Design

### Visual States

**Current Node (is_current=1):**
- Solid circle, entity-type color
- 100% opacity
- 2px stroke
- Optional activity badge

**Historical Node (is_current=0):**
- Dashed circle outline
- 30% opacity
- 1px stroke
- Timestamp label

**Selected Node:**
- Pulsing glow (8px blur)
- 3px stroke
- Highlighted neighbors
- Detail panel opens

### Node Sizing Strategies

1. **Uniform:** All nodes same size (default)
2. **Degree:** Size by connection count
3. **PageRank:** Size by importance
4. **Betweenness:** Size by bridging role
5. **Custom:** Size by user-defined property

**Size Range:** 24px - 96px diameter

### Node Badges

Position: Top-right corner

Types:
- ⚡ Recent update (last 24h)
- 🔥 High activity (>5 updates/week)
- ⭐ Favorite/pinned
- 🔗 High connectivity (>10 edges)
- ⚠️ Needs review (duplicate, stale)

---

## Edge Design

### Visual States

**Current Edge:**
- Solid line, 2px stroke
- 80% opacity
- Curved (Bézier) for clarity
- Optional arrow for directed edges

**Historical Edge:**
- Dashed line, 1px stroke
- 20% opacity
- Muted color

**Hover/Selected:**
- Thicker stroke (3px)
- 100% opacity
- Highlight connected nodes
- Show relationship label

### Edge Bundling

For dense graphs (>100 edges):
- Group similar edges together
- Reduce visual clutter
- Maintain readability
- User-toggleable

---

## Interaction Patterns

### Mouse Interactions

- **Click node:** Open entity detail panel
- **Double-click node:** Zoom to neighborhood
- **Right-click node:** Context menu (history, compare, etc.)
- **Drag node:** Reposition (layout persists)
- **Scroll:** Zoom in/out
- **Cmd/Ctrl + Scroll:** Scrub timeline

### Keyboard Shortcuts

- `←` / `→`: Step backward/forward in time (1 day)
- `Shift + ←/→`: Jump backward/forward (1 month)
- `Space`: Play/pause timeline animation
- `Cmd/Ctrl + Z`: Undo temporal navigation
- `Cmd/Ctrl + F`: Open search/filter
- `H`: Toggle historical entities
- `L`: Cycle layout algorithms
- `R`: Reset view/zoom

### Touch Gestures

- **Pinch:** Zoom graph
- **Two-finger swipe:** Scrub timeline
- **Long press:** Open detail panel
- **Double-tap:** Zoom to entity

---

## UI Components

### 1. Timeline Scrubber (Top Bar)

```
┌─────────────────────────────────────────────────────────────┐
│  [◀] ──●────────────────────────────────────────────── [▶]  │
│       Jan 2024        Jun 2024        Dec 2024    NOW        │
│  📊 Activity: ▁▂▁▃▅▇▅▃▂▁▁▂▃▅▇▅▃▂▁                           │
└─────────────────────────────────────────────────────────────┘
```

Features:
- Drag scrubber to any point in time
- Activity heatmap shows change density
- Clickable hotspots jump to events
- Play/pause animation
- Preset time ranges

### 2. Control Panel (Bottom Bar)

```
┌─────────────────────────────────────────────────────────────┐
│  [Layout ▼] [Filter ▼] [Search] [Zoom: 100%] [Settings]    │
└─────────────────────────────────────────────────────────────┘
```

Features:
- Layout algorithm selector
- Entity type filters
- Search by name/property
- Zoom controls
- View settings (labels, badges, etc.)

### 3. Entity Detail Panel (Right Drawer)

Opens on node click. Shows:
- Entity name and type
- Current properties
- Temporal timeline of changes
- Connected entities (with links)
- Source attribution
- Action buttons (edit, merge, etc.)

### 4. Legend (Collapsible)

Shows:
- Entity type colors
- Node size meaning
- Edge types
- Visual state indicators

---

## Performance Optimization

### Rendering Strategy

**<100 nodes:** SVG rendering
- High quality
- Easy DOM manipulation
- Good for small graphs

**100-1000 nodes:** Canvas 2D
- Better performance
- Still good quality
- Smooth interactions

**1000+ nodes:** WebGL
- Maximum performance
- Hardware acceleration
- Handles large graphs

### Level of Detail (LOD)

**Zoom levels:**
- **Far (< 50%):** Show only nodes, no labels
- **Medium (50-150%):** Show nodes + primary labels
- **Close (> 150%):** Show all details, badges, properties

### Culling & Clustering

**Viewport culling:**
- Only render visible nodes
- Dramatically improves performance
- Seamless as user pans/zooms

**Clustering (for 1000+ nodes):**
- Group distant nodes into clusters
- Expand on zoom/click
- Show cluster size badge

---

## Research-Backed Best Practices

### From Academic Research (2024)

**Key Findings:**

1. **Avoid Node-Link Diagrams for End Users**
   - Research shows users prefer application-specific views
   - "Ball of yarn" visualizations reduce trust
   - Use graph internally, present differently externally

2. **Knowledge Cards > Full Graph**
   - Wikipedia-style cards balance digestibility and discoverability
   - Show entity details + embedded links to related entities
   - Users can explore without seeing full graph complexity

3. **Temporal Visualization is Critical**
   - Users need to track KG evolution over time
   - Timeline views for entity changes
   - Comparison mode for before/after states

4. **Filter, Drill-Down, Switch Views**
   - Start at user's point of interest (not full graph)
   - Allow filtering/collapsing regions
   - Switch between graph/table/card views

5. **Organic Discovery**
   - Support exploration without overwhelming
   - Progressive disclosure of complexity
   - Clear navigation paths

### Implementation Strategy

**Hybrid Approach:**
- **Primary:** Knowledge cards with embedded links (Wikipedia-style)
- **Secondary:** Full graph view for power users
- **Toggle:** Easy switch between modes
- **Context:** Maintain user's position when switching

---

## Technical Stack Recommendation

### **Recommended: Reagraph**

**Why Reagraph:**
- ✅ WebGL-based (high performance)
- ✅ React + TypeScript native
- ✅ Built-in ForceAtlas2 layout
- ✅ 15+ layout algorithms included
- ✅ Node sizing, clustering, edge bundling
- ✅ Radial context menus
- ✅ Path finding between nodes
- ✅ Lasso selection, drag nodes
- ✅ Light/dark themes
- ✅ Active development (2024)
- ✅ MIT license

**Installation:**
```bash
npm install reagraph
```

**Basic Usage:**
```typescript
import { GraphCanvas } from 'reagraph';

<GraphCanvas
  nodes={nodes}
  edges={edges}
  layoutType="forceDirected2d"
  theme="dark"
  draggable
  onNodeClick={handleNodeClick}
/>
```

### Alternative Options

**If Reagraph doesn't meet needs:**

1. **Cytoscape.js**
   - Mature, feature-rich
   - Canvas-based
   - Large community
   - More complex API

2. **Sigma.js**
   - WebGL rendering
   - Excellent performance
   - Lower-level control
   - Steeper learning curve

3. **D3.js + Force Layout**
   - Maximum flexibility
   - Custom everything
   - Requires more code
   - SVG-based (performance limits)

**Decision Matrix:**

| Feature | Reagraph | Cytoscape | Sigma | D3 |
|---------|----------|-----------|-------|-----|
| Performance | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ |
| React Integration | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐ |
| TypeScript | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐ |
| Built-in Layouts | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐ |
| Ease of Use | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐ |
| Customization | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |

---

## Implementation Phases

### Phase 1: Foundation (Week 1-2)
- Integrate Reagraph library
- Implement basic node/edge rendering
- Add current/historical visual states
- Basic interactions (click, hover, zoom)

### Phase 2: Layouts & Filtering (Week 3-4)
- Implement layout algorithm selector
- Add entity type filters
- Node sizing strategies
- Search functionality

### Phase 3: Temporal Features (Week 5-6)
- Timeline scrubber component
- Temporal state transitions
- Activity heatmap
- Play/pause animation

### Phase 4: Detail Views (Week 7-8)
- Entity detail panel
- Knowledge cards view
- Relationship evolution view
- Source attribution

### Phase 5: Performance & Polish (Week 9-10)
- WebGL optimization
- LOD implementation
- Clustering for large graphs
- Animation refinement

### Phase 6: Advanced Features (Week 11-12)
- Comparison mode
- Temporal queries
- Export/share functionality
- Accessibility improvements

---

## Success Metrics

### Performance Targets

- **<100 nodes:** 60fps, <50ms interaction latency
- **100-500 nodes:** 30fps, <100ms latency
- **500-1000 nodes:** 15fps, <200ms latency
- **1000+ nodes:** Clustering enabled, smooth navigation

### UX Metrics

- **Time to insight:** <30 seconds to find entity
- **Discoverability:** 80% of users find related entities without help
- **Satisfaction:** 4.5/5 average rating
- **Accessibility:** WCAG 2.1 AA compliance

---

## Conclusion

This design specification provides a comprehensive blueprint for building an award-winning knowledge graph visualization that balances:

- **Visual Fidelity:** Beautiful, modern design with attention to detail
- **Maximum UX:** Intuitive interactions, progressive disclosure, organic discovery
- **Performance:** WebGL rendering, smart optimizations, graceful degradation
- **Accessibility:** Keyboard navigation, screen readers, color-blind safe
- **Research-Backed:** Implements best practices from 2024 academic research

**Key Differentiator:** Hybrid approach combining full graph view (for power users) with knowledge cards (for end users), ensuring both discoverability and digestibility.

**Next Steps:**
1. Review and approve this specification
2. Set up Reagraph in development environment
3. Begin Phase 1 implementation
4. Iterate based on user feedback

---

**References:**
- Knowledge Graphs in Practice (2024) - arXiv:2304.01311
- ForceAtlas2 Algorithm - Jacomy et al. (2014)
- Reagraph Documentation - https://reagraph.dev
- AICO Temporal KG Visualization Doc - temporal-kg-visualization.md
