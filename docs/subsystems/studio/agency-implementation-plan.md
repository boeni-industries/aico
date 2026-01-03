# Agency Page – Implementation Plan

## Overview

This document outlines the implementation plan for the Agency page based on the comprehensive UX concept in `agency-ux-concept.md`.

---

## Phase 1: Core Intention & Goals (MVP) - CURRENT FOCUS

### Goals
- Display active intention set with primary focus
- Show goal board with Kanban-style lifecycle columns
- Provide basic metrics and status overview
- Enable goal detail exploration via drawer

### Components to Build

#### 1. AgencyPage.tsx (Main Container)
- Tab navigation (Overview, Goals, Curiosity, Learning, Values)
- Auto-refresh polling (5s interval)
- State management for active tab and selected goal

#### 2. IntentionBar.tsx
- Horizontal scrollable chip display
- Primary focus highlight
- Active intentions list (top 5-10)
- Color-coded by origin
- Priority score visualization
- Click to open detail drawer

#### 3. GoalBoard.tsx
- 5-column Kanban layout (Proposed/Active/Paused/Completed/Dropped)
- Column headers with counts
- Drag-and-drop disabled (view-only)
- Filters: origin, priority, status, search
- Sort options: score, created, updated

#### 4. GoalCard.tsx
- Title, origin badge, priority indicator
- Description (truncated, 2 lines)
- Progress bar (steps completed/total)
- Age indicator (relative time)
- Arbiter score
- Hover tooltip with preview
- Click to open detail drawer

#### 5. GoalDetailDrawer.tsx
- Right slide-in panel (400px width)
- Full goal information
- Plan steps with status icons
- Provenance section (memory, conversation, emotion)
- Execution summary (time, tokens)
- Link to full execution log (Operations page)

#### 6. AgencyMetrics.tsx
- Metric cards for Overview tab
- Active goals count
- Plans in-flight count
- Proactive messages (24h)
- Curiosity level
- Reflection runs (7d)
- Lessons applied

#### 7. RecentActivity.tsx
- Timeline of recent events (24h)
- Event types: goal created/activated/paused/completed
- Click event to filter or open detail

### API Integration

#### Endpoints to Use
```typescript
// Intention set
GET /api/v1/agency/intentions?limit=10

// Goal list with filters
GET /api/v1/agency/goals?status=active&origin=user&limit=50

// Goal detail
GET /api/v1/agency/goals/{goal_id}

// Combined state (for metrics)
GET /api/v1/agency/state
```

#### Data Models
```typescript
interface GoalSummary {
  goal_id: string;
  title: string;
  description?: string;
  origin: 'user' | 'curiosity' | 'hobby' | 'maintenance';
  priority: 'low' | 'normal' | 'high' | 'critical';
  status: 'pending' | 'active' | 'paused' | 'completed' | 'retired';
  score?: number;
  priority_band?: string;
  created_at: string;
  metadata: Record<string, any>;
}

interface IntentionSetResponse {
  user_id: string;
  primary_focus?: GoalSummary;
  active_intentions: GoalSummary[];
  open_goals_total: number;
  hobby_goals_active: GoalSummary[];
  timestamp: string;
}

interface AgencyStateResponse {
  user_id: string;
  intention_set: IntentionSetResponse;
  curiosity_status: CuriosityStatusResponse;
  value_profile: ValueProfileResponse;
  consent_required_actions: any[];
  timestamp: string;
}
```

### Styling Guidelines

#### Colors (Origin-based)
```typescript
const originColors = {
  user: '#B8A1EA',      // Soft Lavender
  curiosity: '#5EEAD4', // Teal
  hobby: '#FCD34D',     // Amber
  maintenance: '#94A3B8' // Slate Gray
};

const statusColors = {
  pending: '#E0E7FF',   // Light Indigo
  active: '#10B981',    // Emerald Green
  paused: '#F59E0B',    // Amber
  completed: '#6B7280', // Gray
  retired: '#EF4444'    // Red
};

const priorityColors = {
  critical: '#DC2626', // Red
  high: '#F59E0B',     // Amber
  normal: '#3B82F6',   // Blue
  low: '#9CA3AF'       // Gray
};
```

#### Card Styling
```typescript
const cardStyle = {
  borderRadius: '20px',
  padding: '20px',
  backdropFilter: 'blur(20px)',
  border: '1.5px solid',
  borderColor: 'rgba(255, 255, 255, 0.2)', // light mode
  // borderColor: 'rgba(255, 255, 255, 0.1)', // dark mode
  boxShadow: '0 8px 32px rgba(0,0,0,0.08)',
};
```

### File Structure
```
studio/src/
├── pages/
│   └── AgencyPage.tsx (main container)
├── components/
│   └── agency/
│       ├── IntentionBar.tsx
│       ├── GoalBoard.tsx
│       ├── GoalCard.tsx
│       ├── GoalDetailDrawer.tsx
│       ├── AgencyMetrics.tsx
│       └── RecentActivity.tsx
├── api/
│   └── agency.ts (API client functions)
└── types/
    └── agency.ts (TypeScript interfaces)
```

### Implementation Steps

1. **Setup API client** (`api/agency.ts`)
   - Create fetch functions for all endpoints
   - Add TypeScript types
   - Handle errors and loading states

2. **Build core data types** (`types/agency.ts`)
   - Define all interfaces matching backend models
   - Add helper types for UI state

3. **Create AgencyPage container**
   - Tab navigation
   - Polling logic (useEffect with setInterval)
   - State management (selected tab, selected goal)
   - Layout structure

4. **Build IntentionBar component**
   - Horizontal scroll container
   - Chip components with origin colors
   - Priority score visualization
   - Click handlers

5. **Build GoalBoard component**
   - Column layout with CSS Grid
   - Filter and sort controls
   - Map goals to columns by status
   - Responsive design

6. **Build GoalCard component**
   - Card layout with all metadata
   - Progress bar calculation
   - Relative time formatting
   - Hover effects

7. **Build GoalDetailDrawer component**
   - Slide-in animation
   - Full goal details layout
   - Plan steps visualization
   - Provenance section
   - Close handler

8. **Build AgencyMetrics component**
   - Metric card grid
   - Number formatting
   - Trend indicators
   - Loading states

9. **Build RecentActivity component**
   - Timeline visualization
   - Event list with icons
   - Time formatting
   - Click handlers

10. **Integration & Testing**
    - Connect all components
    - Test polling behavior
    - Test drawer interactions
    - Test responsive layout
    - Test theme switching (light/dark)

### Acceptance Criteria

- [ ] Intention bar displays primary focus and active intentions
- [ ] Goal board shows all goals in correct lifecycle columns
- [ ] Goal cards display all required metadata
- [ ] Clicking a goal opens detail drawer
- [ ] Detail drawer shows full goal information and plan steps
- [ ] Metrics cards show accurate counts
- [ ] Page auto-refreshes every 5 seconds
- [ ] All colors match design system
- [ ] Responsive layout works on desktop and laptop
- [ ] Theme switching works correctly (light/dark)
- [ ] Loading states are handled gracefully
- [ ] Error states are displayed clearly

### Estimated Timeline
- API client setup: 2 hours
- AgencyPage container: 2 hours
- IntentionBar: 2 hours
- GoalBoard + GoalCard: 4 hours
- GoalDetailDrawer: 3 hours
- AgencyMetrics: 2 hours
- RecentActivity: 2 hours
- Integration & testing: 3 hours

**Total: ~20 hours (2-3 days)**

---

## Phase 2: Curiosity & Values (Next)

### Components
- CuriosityDashboard.tsx
- CuriosityGauge.tsx
- OpportunityList.tsx
- ValueProfileCard.tsx
- PolicyList.tsx

### API Endpoints
- `/api/v1/agency/curiosity`
- `/api/v1/agency/profile`
- `/api/v1/agency/policies`

**Estimated: 1-2 days**

---

## Phase 3: Learning & Reflection (Future)

### Components
- LearningDashboard.tsx
- ReflectionStats.tsx
- LessonLibrary.tsx
- LearningVelocityChart.tsx

### API Endpoints
- TBD (need backend endpoints for reflection/lesson data)

**Estimated: 2 days**

---

## Phase 4: Temporal Evolution (Future)

### Components
- TimelineView.tsx
- GoalLifecycleViz.tsx
- CompletionRateChart.tsx
- EventFilter.tsx

### API Endpoints
- `/api/v1/agency/timeline` (needs backend implementation)

**Estimated: 2-3 days**

---

## Technical Considerations

### Performance
- Use React.memo for expensive components
- Implement virtual scrolling for large goal lists
- Debounce search/filter inputs
- Cache API responses (5s TTL)

### Accessibility
- Keyboard navigation (Tab, Arrow keys, Escape)
- ARIA labels for all interactive elements
- Focus management for drawer
- Screen reader announcements for updates

### Error Handling
- Network errors: Show retry button
- Empty states: Show helpful messages
- Loading states: Skeleton screens
- Stale data: Visual indicator

### Testing Strategy
- Unit tests for utility functions
- Component tests for UI logic
- Integration tests for API calls
- E2E tests for critical flows

---

## Next Steps

1. Review this plan with user
2. Get approval to proceed with Phase 1
3. Start implementation with API client setup
4. Build components incrementally
5. Test and iterate based on feedback
