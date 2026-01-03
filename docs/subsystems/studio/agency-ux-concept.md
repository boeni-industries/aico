# Agency Page – Comprehensive UX Concept & Design

## Executive Summary

The Agency page is AICO's **mission control for autonomous behavior**. It must serve two distinct but overlapping audiences:

1. **Developers/Researchers**: Deep system understanding, debugging, provenance tracking, learning analysis
2. **Power Users**: High-level oversight, goal management, curiosity monitoring, value configuration

This document synthesizes research on autonomous agent visualization, temporal system evolution, and dashboard design best practices to create a world-class interface for understanding and monitoring AICO's agency system.

---

## 1. Core Design Principles

### 1.1 Research-Backed Principles

Based on analysis of autonomous agent UX research (AgentLens, Microsoft Agent UX, multi-agent systems):

**Transparency & Observability**
- Every agent action must be traceable to its cause
- Show decision-making context (what data informed each choice)
- Stream real-time updates as agency evolves
- Provide "why" explanations for goal prioritization

**Capability Discovery**
- Make system capabilities immediately visible
- Show what AICO can/cannot do autonomously
- Highlight high-reliability vs experimental features
- Surface active skills and available tools

**Interruptibility & Control**
- Users can pause/resume agency operations (future phase)
- Clear indication of what's running vs paused
- Graceful degradation when components fail

**Cost/Risk Awareness**
- Show resource implications (LLM tokens, time, external actions)
- Distinguish low-risk from high-risk operations
- Track proactive behavior intensity

**Temporal Context**
- Not just current state—show evolution over time
- Learning trajectory visualization
- Pattern detection across days/weeks

### 1.2 AICO Studio Design Principles

From `design-principles.md`:

- **Zero cognitive friction**: Immediately understandable structure
- **Maximum 2-level navigation**: No deep nesting
- **Glassmorphic composition**: Floating cards, 36px radius, soft shadows
- **Progressive disclosure**: Details on demand, not upfront clutter
- **Traceability-first**: Every metric links to authoritative source

---

## 2. Information Architecture

### 2.1 Primary Data Dimensions

Agency data exists across multiple dimensions that must be navigable:

**Lifecycle Axis** (Horizontal Flow)
```
Proposed → Active → Paused → Completed → Dropped
```

**Structural Axis** (Vertical Hierarchy)
```
Goal (Theme/Project)
  ├─ Plan (Strategy)
  │   ├─ Step 1 (Skill/Tool)
  │   │   └─ Task Executions
  │   ├─ Step 2
  │   └─ Step 3
  └─ Metadata (Origin, Priority, Provenance)
```

**Temporal Axis** (Time Evolution)
```
Past ←────── Present ────────→ Future
[History]    [Active]         [Planned]
```

**Origin Axis** (Motivation Source)
```
User-Directed | Curiosity-Driven | Hobby/Self | Maintenance
```

**Execution Axis** (Runtime State)
```
Intention Set → Arbiter → Scheduler → Execution → Reflection
```

### 2.2 View Hierarchy

**Level 1: Overview Dashboard** (Default landing)
- High-level metrics and status
- Quick access to all sub-views
- Recent activity timeline

**Level 2: Specialized Views** (Tabs/Cards)
- Intention Set (What AICO is doing now)
- Goal Board (Kanban-style lifecycle)
- Curiosity Engine (What AICO wants to explore)
- Learning & Reflection (How AICO improves)
- Values & Ethics (Boundaries and consent)
- Execution Timeline (Historical analysis)

**Level 3: Detail Drawers** (Slide-in panels)
- Individual goal deep-dive
- Plan step breakdown
- Execution trace
- Memory/perception provenance

---

## 3. Visual Design System

### 3.1 Core Visualization Patterns

**1. Intention Bar (Top Priority Strip)**
```
┌─────────────────────────────────────────────────────────────┐
│ PRIMARY FOCUS: [Help plan weekend trip] ●●●●○ (Score: 0.87) │
│                                                               │
│ ACTIVE: [Learn about user's music taste] ●●●○○ (0.72)       │
│         [Maintain conversation history] ●●○○○ (0.58)         │
│         [Organize photo memories] ●●○○○ (0.54)               │
└─────────────────────────────────────────────────────────────┘
```
- Horizontal scrollable chips
- Color-coded by origin (user=purple, curiosity=teal, hobby=amber, system=gray)
- Priority dots show arbiter score
- Click to expand full goal details

**2. Goal Board (Kanban Columns)**
```
┌──────────┬──────────┬──────────┬──────────┬──────────┐
│ PROPOSED │  ACTIVE  │  PAUSED  │COMPLETED │ DROPPED  │
│    (3)   │   (5)    │   (2)    │   (12)   │   (4)    │
├──────────┼──────────┼──────────┼──────────┼──────────┤
│ [Card 1] │ [Card 1] │ [Card 1] │ [Card 1] │ [Card 1] │
│ [Card 2] │ [Card 2] │ [Card 2] │ [Card 2] │ [Card 2] │
│ [Card 3] │ [Card 3] │          │   ...    │   ...    │
│          │   ...    │          │          │          │
└──────────┴──────────┴──────────┴──────────┴──────────┘
```
- Glassmorphic cards with goal summary
- Progress bar (steps completed/total)
- Age indicator (created 2d ago)
- Drag-and-drop disabled (view-only for now)

**3. Goal Card Anatomy**
```
┌─────────────────────────────────────┐
│ 🎯 Help plan weekend trip           │ ← Title
│ ┌─────────────────────────────────┐ │
│ │ USER · HIGH · 2d ago            │ │ ← Origin, Priority, Age
│ └─────────────────────────────────┘ │
│                                     │
│ Research destinations, book hotel,  │ ← Description (truncated)
│ create itinerary...                 │
│                                     │
│ ▓▓▓▓▓▓▓▓▓░░░░░░ 60% (3/5 steps)   │ ← Progress
│                                     │
│ 📊 Score: 0.87 | 🔄 Plan: Active   │ ← Metrics
└─────────────────────────────────────┘
```

**4. Timeline Visualization (Temporal Evolution)**
```
Time ────────────────────────────────────────────────→
     │
Goal A ●━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━●
       │                                            │
       ├─ Plan created                             └─ Completed
       ├─ Step 1 executed ✓
       ├─ Step 2 executed ✓
       └─ Step 3 in progress...

Goal B     ●━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
           │                                        │
           ├─ Curiosity signal detected            └─ Active
           └─ Plan generated

Goal C                    ●━━━━━━━━━━━━━━━━━━━━━━━━━
                          │                        │
                          └─ User request          └─ Paused
```
- Horizontal timeline with goal lifecycles
- Zoomable (day/week/month/all-time)
- Click event to see details
- Color-coded by origin

**5. Curiosity Heatmap**
```
┌─────────────────────────────────────────────────┐
│ CURIOSITY LEVEL: ████████░░ HIGH (8/10)         │
├─────────────────────────────────────────────────┤
│                                                 │
│ 🔥 User's music preferences                     │
│    Intensity: ████████░░ 0.82                   │
│    Signal: Knowledge gap in conversation        │
│                                                 │
│ 🔥 Photo organization patterns                  │
│    Intensity: ███████░░░ 0.71                   │
│    Signal: Repeated manual sorting              │
│                                                 │
│ 🔥 Weekend activity preferences                 │
│    Intensity: ██████░░░░ 0.64                   │
│    Signal: Seasonal behavior pattern            │
└─────────────────────────────────────────────────┘
```

**6. Learning & Reflection Dashboard**
```
┌─────────────────────────────────────────────────┐
│ REFLECTION RUNS: 1,437 | LESSONS LEARNED: 41    │
├─────────────────────────────────────────────────┤
│                                                 │
│ Recent Lessons:                                 │
│                                                 │
│ ✓ "User prefers morning notifications"          │
│   Confidence: 0.89 | Applied: 12 times          │
│   Outcome: +15% engagement                      │
│                                                 │
│ ✓ "Weekend plans need 2-day lead time"          │
│   Confidence: 0.76 | Applied: 5 times           │
│   Outcome: +20% completion rate                 │
│                                                 │
│ 📈 Learning Velocity: ↑ 12% this week           │
└─────────────────────────────────────────────────┘
```

**7. Execution Provenance Tree**
```
Goal: Help plan weekend trip
  └─ Plan: Multi-step travel planning
      ├─ Step 1: Research destinations ✓
      │   ├─ Skill: web_search
      │   │   └─ Execution #1234 (2m 15s, 2.3k tokens)
      │   │       └─ Memory: User mentioned "beach" 3x
      │   └─ Result: 5 destinations found
      │
      ├─ Step 2: Compare options ✓
      │   ├─ Skill: analyze_preferences
      │   │   └─ Execution #1235 (45s, 800 tokens)
      │   │       └─ Memory: Past trips to mountains
      │   └─ Result: Recommended coastal location
      │
      └─ Step 3: Book hotel (in progress)
          └─ Skill: booking_assistant
              └─ Execution #1236 (running...)
```
- Expandable tree structure
- Click any node to see full context
- Color-coded by status (✓ done, ⟳ running, ○ pending, ✗ failed)
- Shows resource usage (time, tokens)

### 3.2 Color System

**Origin Colors** (Primary identification)
- User-directed: `#B8A1EA` (Soft Lavender - Studio primary)
- Curiosity-driven: `#5EEAD4` (Teal/Cyan - exploration)
- Hobby/Self: `#FCD34D` (Amber - personal growth)
- Maintenance: `#94A3B8` (Slate Gray - system tasks)

**Status Colors** (Lifecycle state)
- Proposed: `#E0E7FF` (Light Indigo)
- Active: `#10B981` (Emerald Green)
- Paused: `#F59E0B` (Amber)
- Completed: `#6B7280` (Gray)
- Dropped: `#EF4444` (Red)

**Priority Colors** (Urgency indication)
- Critical: `#DC2626` (Red)
- High: `#F59E0B` (Amber)
- Normal: `#3B82F6` (Blue)
- Low: `#9CA3AF` (Gray)

### 3.3 Typography & Density

**Goal Titles**: 16px, Semi-bold (600)
**Descriptions**: 14px, Regular (400), line-clamp: 2
**Metrics**: 12px, Medium (500), monospace for numbers
**Timestamps**: 11px, Regular (400), text-secondary

**Card Spacing**:
- Padding: 20px
- Gap between cards: 16px
- Column gap: 24px

---

## 4. Page Layout & Navigation

### 4.1 Top-Level Structure

```
┌─────────────────────────────────────────────────────────────┐
│ [Studio Header with Search, Status, User]                   │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│ ┌──────────────────────────────────────────────────────────┐│
│ │ AGENCY                                    🔄 Auto-refresh ││
│ │                                           ⚙️ Settings     ││
│ └──────────────────────────────────────────────────────────┘│
│                                                              │
│ ┌──────────────────────────────────────────────────────────┐│
│ │ INTENTION BAR (Primary Focus + Active Intentions)        ││
│ └──────────────────────────────────────────────────────────┘│
│                                                              │
│ ┌──────────────────────────────────────────────────────────┐│
│ │ [Overview] [Goals] [Curiosity] [Learning] [Values]       ││ ← Tabs
│ └──────────────────────────────────────────────────────────┘│
│                                                              │
│ ┌──────────────────────────────────────────────────────────┐│
│ │                                                          ││
│ │                  MAIN CONTENT AREA                       ││
│ │                  (Tab-specific view)                     ││
│ │                                                          ││
│ └──────────────────────────────────────────────────────────┘│
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### 4.2 Tab Structure

**Tab 1: Overview** (Default)
- 3-column metric cards
  - Active Goals: 5
  - Curiosity Level: High
  - Plans In-Flight: 3
  - Proactive Messages (24h): 4
  - Reflection Runs (7d): 127
  - Lessons Applied: 8
- Recent activity timeline (last 24h)
- Quick actions (future: create goal, adjust values)

**Tab 2: Goals** (Kanban Board)
- 5-column layout (Proposed/Active/Paused/Completed/Dropped)
- Filters: Origin, Priority, Age, Search
- Sort: Score, Created, Updated
- Click card → Detail drawer

**Tab 3: Curiosity** (Exploration Dashboard)
- Curiosity level gauge
- Top 3-5 curiosity opportunities
- Active curiosity-driven goals
- Curiosity intensity settings (future: editable)
- Allowed domains configuration

**Tab 4: Learning** (Reflection & Growth)
- Reflection run statistics
- Lesson library (searchable/filterable)
- Learning velocity chart (lessons/week)
- Confidence distribution
- Outcome metrics (success rate by lesson)

**Tab 5: Values** (Ethics & Boundaries)
- Value profile summary
- Proactive behavior level
- Sensitive life areas
- Policy rules (allow/warn/block/consent)
- Consent history

### 4.3 Detail Drawer (Right Slide-in)

When clicking a goal card:

```
┌─────────────────────────────────────────┐
│ [×] Goal Details                        │
├─────────────────────────────────────────┤
│                                         │
│ 🎯 Help plan weekend trip               │
│                                         │
│ ┌─────────────────────────────────────┐ │
│ │ Origin: USER                        │ │
│ │ Priority: HIGH                      │ │
│ │ Status: ACTIVE                      │ │
│ │ Created: 2d ago                     │ │
│ │ Updated: 4h ago                     │ │
│ │ Arbiter Score: 0.87                 │ │
│ └─────────────────────────────────────┘ │
│                                         │
│ Description:                            │
│ Research weekend destinations,          │
│ compare options, book accommodation,    │
│ create detailed itinerary.              │
│                                         │
│ ─────────────────────────────────────── │
│                                         │
│ PLAN: Multi-step travel planning        │
│ Strategy: llm_refined                   │
│                                         │
│ ├─ ✓ Research destinations (2m 15s)    │
│ ├─ ✓ Compare options (45s)             │
│ ├─ ⟳ Book hotel (running...)           │
│ ├─ ○ Create itinerary                  │
│ └─ ○ Send confirmation                 │
│                                         │
│ ─────────────────────────────────────── │
│                                         │
│ PROVENANCE:                             │
│ • Conversation: "Let's plan a trip"     │
│ • Memory: Past beach preferences        │
│ • Emotion: Excited (v:0.7, a:0.6)      │
│                                         │
│ ─────────────────────────────────────── │
│                                         │
│ EXECUTIONS: 2 completed, 1 running      │
│ Total time: 3m 0s                       │
│ Total tokens: 3.1k                      │
│                                         │
│ [View Full Execution Log →]            │
│                                         │
└─────────────────────────────────────────┘
```

---

## 5. Interaction Patterns

### 5.1 Real-Time Updates (Polling)

- Poll `/api/v1/agency/state` every 5 seconds
- Update intention bar, active goals, metrics
- Smooth transitions (fade-in new items, fade-out removed)
- Visual indicator when data is stale (>10s)

### 5.2 Progressive Disclosure

**Level 1**: Card summary (title, origin, priority, progress)
**Level 2**: Hover tooltip (description preview, score)
**Level 3**: Click → Detail drawer (full goal, plan, provenance)
**Level 4**: "View Full Log" → Operations page (execution traces)

### 5.3 Cross-Domain Navigation

From Agency, users can jump to:
- **Memory & AMS**: Click provenance memory reference
- **Operations**: Click execution trace
- **Emotion**: Click emotional context
- **Conversations**: Click conversation reference

Each link opens the target domain with pre-filtered context.

### 5.4 Search & Filtering

**Global Search** (top bar):
- Search goals by title/description
- Search plans by strategy
- Search executions by skill name

**View-Specific Filters**:
- Goals: Origin, Priority, Status, Age range
- Curiosity: Intensity threshold, Domain
- Learning: Confidence range, Outcome success
- Values: Policy effect, Consent status

---

## 6. Temporal Evolution Views

### 6.1 Timeline View (Historical Analysis)

**Zoom Levels**:
- Hour: Last 24 hours (detailed events)
- Day: Last 7 days (goal lifecycle milestones)
- Week: Last 4 weeks (learning patterns)
- Month: Last 6 months (long-term trends)
- All: Complete history (macro evolution)

**Event Types**:
- Goal created/activated/paused/completed/dropped
- Plan generated/revised/abandoned
- Curiosity signal detected
- Lesson learned/applied
- Policy triggered
- Consent requested/granted/denied

**Visualization**:
- Horizontal timeline with swimlanes per goal
- Vertical markers for events
- Hover to see event details
- Click to jump to detail drawer

### 6.2 Learning Velocity Chart

```
Lessons Learned per Week
 15 │                                    ●
    │                              ●
 10 │                        ●
    │                  ●
  5 │            ●
    │      ●
  0 └─────┴─────┴─────┴─────┴─────┴─────┴─────→
    W1    W2    W3    W4    W5    W6    W7
```

Shows:
- Trend line (increasing/decreasing/stable)
- Confidence bands
- Milestone markers (major lessons)

### 6.3 Goal Completion Rate

```
Completion Rate by Origin
100% ┤
     │ ████████████████████ USER (85%)
     │ ████████████░░░░░░░░ CURIOSITY (65%)
     │ ██████████████████░░ HOBBY (90%)
     │ ████████████████░░░░ MAINTENANCE (80%)
  0% └────────────────────────────────────
```

---

## 7. Accessibility & Responsiveness

### 7.1 Accessibility

- WCAG AA+ contrast for all text
- Keyboard navigation (Tab, Arrow keys, Enter, Escape)
- Screen reader labels for all interactive elements
- Focus indicators (2px purple outline)
- ARIA roles (navigation, main, complementary)
- Status announcements for live updates

### 7.2 Responsive Breakpoints

**Desktop (≥1440px)**: Full layout with all columns
**Laptop (1024-1439px)**: Reduced column count, narrower cards
**Tablet (768-1023px)**: Single-column Kanban, collapsible drawer
**Mobile (≤767px)**: Stacked views, bottom-sheet drawers

---

## 8. Implementation Phases

### Phase 1: Core Intention & Goals (MVP)
**Scope**: Intention bar, goal board, basic metrics
**Components**:
- IntentionBar (horizontal scrollable chips)
- GoalBoard (5-column Kanban)
- GoalCard (summary with progress)
- MetricCards (active goals, plans, proactive messages)
- DetailDrawer (goal details, plan steps)

**API Endpoints**:
- `/api/v1/agency/intentions`
- `/api/v1/agency/goals` (list with filters)
- `/api/v1/agency/goals/{id}` (detail)

**Estimated Effort**: 2-3 days

### Phase 2: Curiosity & Values
**Scope**: Curiosity dashboard, value profile, policies
**Components**:
- CuriosityGauge (level indicator)
- OpportunityList (top curiosity themes)
- ValueProfile (settings display)
- PolicyList (rules table)

**API Endpoints**:
- `/api/v1/agency/curiosity`
- `/api/v1/agency/profile`
- `/api/v1/agency/policies`

**Estimated Effort**: 1-2 days

### Phase 3: Learning & Reflection
**Scope**: Reflection dashboard, lesson library, charts
**Components**:
- ReflectionStats (run count, success rate)
- LessonLibrary (searchable table)
- LearningVelocityChart (trend line)
- OutcomeMetrics (success by lesson)

**API Endpoints**:
- New endpoints for reflection/lesson data (TBD)

**Estimated Effort**: 2 days

### Phase 4: Temporal Evolution
**Scope**: Timeline view, historical analysis, charts
**Components**:
- TimelineView (zoomable event stream)
- GoalLifecycleViz (swimlanes)
- CompletionRateChart (by origin)
- EventFilter (type, date range)

**API Endpoints**:
- `/api/v1/agency/timeline` (events with filters)

**Estimated Effort**: 2-3 days

### Phase 5: Advanced Features
**Scope**: Provenance tracing, execution logs, cross-domain links
**Components**:
- ProvenanceTree (expandable hierarchy)
- ExecutionTrace (step-by-step log)
- CrossDomainLinks (memory, emotion, operations)

**Estimated Effort**: 2-3 days

---

## 9. Success Metrics

### 9.1 Developer Experience
- Time to understand goal lifecycle: <2 minutes
- Time to trace execution provenance: <30 seconds
- Debugging efficiency: 50% reduction in time to identify issues

### 9.2 System Transparency
- Users can explain what AICO is doing: 90%+ comprehension
- Confidence in agency decisions: 8/10 average rating
- Trust in autonomous behavior: 85%+ positive sentiment

### 9.3 Performance
- Page load time: <1 second
- Real-time update latency: <5 seconds
- Smooth 60fps animations and transitions

---

## 10. Future Enhancements

### 10.1 Interactive Control (Post-MVP)
- Pause/resume goals
- Adjust priority manually
- Create goals from UI
- Edit value profile settings
- Grant/revoke consents

### 10.2 Advanced Analytics
- Goal success prediction
- Resource optimization recommendations
- Anomaly detection (unusual patterns)
- A/B testing for planning strategies

### 10.3 Collaboration Features
- Multi-user goal management
- Shared agency oversight
- Role-based access control
- Audit logs for compliance

---

## 11. Conclusion

This UX concept creates a **world-class interface** for understanding and monitoring autonomous agent behavior. It balances:

- **Simplicity** for quick oversight
- **Depth** for detailed analysis
- **Transparency** for trust-building
- **Evolution** for learning insights

By following research-backed principles and AICO's design language, the Agency page will be:
- **Immediately understandable** to new users
- **Infinitely explorable** for developers
- **Visually stunning** for award-worthy fidelity
- **Functionally complete** for production use

The phased implementation ensures rapid delivery of core value while maintaining architectural flexibility for future enhancements.
