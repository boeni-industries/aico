---
title: Phase 11 - Flutter Frontend Agency Integration
---

# Phase 11 – Flutter Frontend Agency Integration 🔮

**Status:** Future

**Goal:** Integrate agency system capabilities into Flutter frontend, including proactive messages, intention visibility, goal tracking, and behavioral feedback.

---

## Overview

Phase 11 focuses on making the agency system visible and interactive within the Flutter mobile/desktop application. This includes displaying agency state, handling proactive messages, showing intention sets, and providing user controls for agency behavior.

**Prerequisites:**
- Phase 0-9: Complete (agency system operational)
- Phase 10: REST API endpoints available
- Flutter app: Existing conversation UI

---

## UI/UX Design Approach

### Agency Badge Pattern

**Core Visualization:** Agency state is displayed via a small badge indicator positioned at the bottom-right of the avatar (similar to online status indicators).

**Design Rationale:**
- **Minimal footprint:** Single 8-12px dot, doesn't conflict with avatar emotion ring or inner monologue
- **Familiar pattern:** Users already understand badge indicators from notifications
- **Passive awareness:** Glanceable status without demanding attention
- **Mode-adaptive:** Works in both text and voice modes

**Badge States:**
- **No badge:** No active intentions
- **Purple dot:** Active intention/focus
- **Amber dot + pulse:** Lesson pending review
- **Progress ring:** Goal in progress (partial circle fill)
- **Green burst:** Goal completed (brief celebration animation)

**Interaction:**
- **Text mode:** Tap badge → Opens bottom sheet with full agency panel (intentions, goals, lessons)
- **Voice mode:** Badge visible, voice queries for details ("What are you working on?")
- **Proactive messages:** Badge pulses amber + audio chime + avatar attention animation

**Spatial Layout:**
- **Right drawer:** Inner monologue & emotional journey (reflective content)
- **Avatar center:** Emotion ring (present state)
- **Avatar badge:** Agency focus (forward-looking actions)
- **Center area:** Conversation & interaction

This approach follows established UI patterns while maintaining AICO's design principles of minimalism, progressive disclosure, and glassmorphic aesthetics.

---

## Core Features

### 1. Proactive Message Integration *PENDING*

**Goal:** Display and handle proactive messages initiated by agency system

**Requirements:**
- [ ] WebSocket connection for real-time proactive messages
- [ ] Proactive message notification system
- [ ] Visual distinction from user-initiated messages
- [ ] Proactive message acceptance/dismissal UI
- [ ] Context display (why this message now?)
- [ ] User preferences for proactive frequency

**UI Components:**
- [ ] `ProactiveMessageNotification` - Toast/banner for incoming proactive messages
- [ ] `ProactiveMessageCard` - Special message bubble styling
- [ ] `ProactiveContextPanel` - Shows trigger reason and timing
- [ ] `ProactiveSettingsScreen` - User controls for proactive behavior

**Backend Integration:**
- [ ] `GET /api/v1/agency/proactive/pending` - Check for pending proactive messages
- [ ] `POST /api/v1/agency/proactive/{id}/accept` - User accepts proactive message
- [ ] `POST /api/v1/agency/proactive/{id}/dismiss` - User dismisses proactive message
- [ ] WebSocket topic: `agency.proactive.{user_id}` - Real-time proactive message delivery

**User Experience:**
- Proactive messages appear as gentle notifications
- User can see why AICO initiated the message
- Easy to accept (start conversation) or dismiss
- Respect quiet hours and user preferences
- Track user response patterns for learning

---

### 2. Intention Set Visibility *PENDING*

**Goal:** Show user what AICO is currently focused on and planning

**Requirements:**
- [ ] Intention set display in conversation UI
- [ ] Real-time intention updates
- [ ] Intention priority visualization
- [ ] Intention details and context
- [ ] User ability to influence intentions

**UI Components:**
- [ ] `IntentionChip` - Compact intention display in app bar
- [ ] `IntentionDrawer` - Expandable panel showing full intention set
- [ ] `IntentionDetailSheet` - Bottom sheet with intention details
- [ ] `IntentionPriorityIndicator` - Visual priority representation

**Backend Integration:**
- [ ] `GET /api/v1/agency/intentions` - Current intention set
- [ ] `GET /api/v1/agency/intentions/{id}` - Intention details
- [ ] WebSocket topic: `agency.intentions.{user_id}` - Real-time intention updates

**User Experience:**
- Subtle, non-intrusive display of current focus
- User can expand to see full intention set
- Shows why AICO is focused on specific topics
- Helps user understand AICO's behavior
- Optional: User can dismiss or prioritize intentions

---

### 3. Goal Tracking & Progress *PENDING*

**Goal:** Show active goals and their progress in the UI

**Requirements:**
- [ ] Active goals list view
- [ ] Goal progress indicators
- [ ] Goal completion notifications
- [ ] Goal details and plan view
- [ ] User goal creation/modification

**UI Components:**
- [ ] `GoalsScreen` - Full-screen goal management
- [ ] `GoalCard` - Individual goal display with progress
- [ ] `GoalProgressIndicator` - Visual progress representation
- [ ] `GoalDetailSheet` - Goal details, plans, and history
- [ ] `GoalCompletionDialog` - Celebration on goal completion

**Backend Integration:**
- [ ] `GET /api/v1/agency/goals` - List goals
- [ ] `GET /api/v1/agency/goals/{id}` - Goal details
- [ ] `GET /api/v1/agency/goals/{id}/plans` - Associated plans
- [ ] `POST /api/v1/agency/goals` - Create user goal
- [ ] `PATCH /api/v1/agency/goals/{id}` - Update goal
- [ ] WebSocket topic: `agency.goals.{user_id}` - Real-time goal updates

**User Experience:**
- Easy access to active goals from main screen
- Visual progress tracking
- Notifications on goal completion
- User can create goals explicitly
- Shows how AICO is working toward goals

---

### 4. Behavioral Feedback & Lesson Review *PENDING*

**Goal:** Allow users to provide feedback on AICO behavior and review lessons

**Requirements:**
- [ ] In-conversation feedback buttons
- [ ] Lesson review interface
- [ ] Lesson approval/rejection UI
- [ ] Behavioral feedback history
- [ ] Impact visualization (how feedback changed behavior)

**UI Components:**
- [ ] `MessageFeedbackButtons` - Thumbs up/down on messages
- [ ] `LessonReviewScreen` - Lesson management interface
- [ ] `LessonCard` - Individual lesson display
- [ ] `LessonDetailSheet` - Full lesson details with approve/reject
- [ ] `BehaviorImpactChart` - Shows how lessons affected behavior

**Backend Integration:**
- [ ] `POST /api/v1/feedback/message/{id}` - Feedback on specific message
- [ ] `GET /api/v1/agency/lessons` - List lessons
- [ ] `GET /api/v1/agency/lessons/{id}` - Lesson details
- [ ] `POST /api/v1/agency/lessons/{id}/approve` - Approve lesson
- [ ] `POST /api/v1/agency/lessons/{id}/reject` - Reject lesson
- [ ] `GET /api/v1/agency/lessons/stats` - Lesson statistics

**User Experience:**
- Quick feedback on individual messages
- Dedicated screen for lesson review
- Clear explanation of what each lesson means
- Visual impact of approved lessons
- Gamification: Show learning progress

---

### 5. Agency Settings & Controls *PENDING*

**Goal:** User controls for agency behavior and preferences

**Requirements:**
- [ ] Agency enable/disable toggle
- [ ] Proactive message settings
- [ ] Quiet hours configuration
- [ ] Policy management UI
- [ ] Consent management UI
- [ ] Value profile editing

**UI Components:**
- [ ] `AgencySettingsScreen` - Main agency settings
- [ ] `ProactiveSettingsPanel` - Proactive behavior controls
- [ ] `QuietHoursSelector` - Time range picker for quiet hours
- [ ] `PolicyListScreen` - View and manage policies
- [ ] `ConsentManagementScreen` - Grant/revoke consents
- [ ] `ValueProfileEditor` - Edit user value profile

**Backend Integration:**
- [ ] `GET /api/v1/agency/settings` - Current settings
- [ ] `PATCH /api/v1/agency/settings` - Update settings
- [ ] `GET /api/v1/agency/policies` - List policies
- [ ] `POST /api/v1/agency/policies` - Add policy
- [ ] `DELETE /api/v1/agency/policies/{id}` - Remove policy
- [ ] `GET /api/v1/agency/consents` - List consents
- [ ] `POST /api/v1/agency/consents` - Grant consent
- [ ] `DELETE /api/v1/agency/consents/{id}` - Revoke consent
- [ ] `GET /api/v1/agency/profile` - Value profile
- [ ] `PATCH /api/v1/agency/profile` - Update profile

**User Experience:**
- Easy access from settings menu
- Clear explanations of each setting
- Safe defaults with opt-in for advanced features
- Visual feedback on setting changes
- Help text and examples

---

### 6. Real-Time Updates & WebSocket Integration *PENDING*

**Goal:** Real-time agency state updates without polling

**Requirements:**
- [ ] WebSocket connection management
- [ ] Reconnection logic with exponential backoff
- [ ] Message queue for offline handling
- [ ] State synchronization on reconnect
- [ ] Error handling and fallback to polling

**WebSocket Topics:**
- [ ] `agency.proactive.{user_id}` - Proactive messages
- [ ] `agency.intentions.{user_id}` - Intention set updates
- [ ] `agency.goals.{user_id}` - Goal updates
- [ ] `agency.lessons.{user_id}` - New lessons generated
- [ ] `agency.events.{user_id}` - General agency events

**Implementation:**
- [ ] `AgencyWebSocketService` - WebSocket connection manager
- [ ] `AgencyStateProvider` - State management for agency data
- [ ] `AgencyEventHandler` - Process incoming WebSocket messages
- [ ] Offline queue for actions taken while disconnected

---

### 7. Metrics & Analytics Visualization *PENDING*

**Goal:** Show user their agency metrics and behavioral trends

**Requirements:**
- [ ] Metrics dashboard screen
- [ ] Goal completion rate charts
- [ ] Skill performance visualization
- [ ] Reflection run history
- [ ] Lesson application impact

**UI Components:**
- [ ] `MetricsDashboardScreen` - Full metrics view
- [ ] `GoalCompletionChart` - Line/bar chart of goal completion
- [ ] `SkillPerformanceChart` - Skill success rates over time
- [ ] `ReflectionHistoryList` - Recent reflection runs
- [ ] `LessonImpactChart` - Behavioral changes from lessons

**Backend Integration:**
- [ ] `GET /api/v1/agency/metrics` - Comprehensive metrics
- [ ] `GET /api/v1/agency/reflection-history` - Reflection runs
- [ ] `GET /api/v1/agency/skill-performance` - Skill stats
- [ ] `GET /api/v1/agency/health` - System health

**User Experience:**
- Beautiful, easy-to-understand charts
- Time range selection (24h, 7d, 30d, all)
- Drill-down into specific metrics
- Export data option
- Shareable achievements

---

## Implementation Approach

### Stage 1: Foundation (Week 1-2)
1. Set up WebSocket infrastructure
2. Create base agency state management (Provider/Riverpod)
3. Implement API client for agency endpoints
4. Add basic error handling and offline support

### Stage 2: Proactive Messages (Week 3-4)
1. Implement proactive message notification system
2. Create proactive message UI components
3. Add acceptance/dismissal logic
4. Test proactive message flow end-to-end

### Stage 3: Intention & Goal Visibility (Week 5-6)
1. Create intention display components
2. Implement goal tracking UI
3. Add real-time updates via WebSocket
4. Test intention and goal synchronization

### Stage 4: Behavioral Feedback (Week 7-8)
1. Add message feedback buttons
2. Create lesson review interface
3. Implement approve/reject workflow
4. Add behavioral impact visualization

### Stage 5: Settings & Controls (Week 9-10)
1. Build agency settings screen
2. Implement policy and consent management
3. Add value profile editor
4. Test all user controls

### Stage 6: Metrics & Polish (Week 11-12)
1. Create metrics dashboard
2. Add charts and visualizations
3. Polish UI/UX across all features
4. Performance optimization
5. End-to-end testing

---

## Technical Requirements

### State Management
- Use Provider or Riverpod for agency state
- Separate providers for different agency aspects (goals, intentions, lessons)
- Efficient state updates to avoid unnecessary rebuilds

### API Client
- Extend existing API client with agency endpoints
- Add request/response models for agency data
- Implement caching for frequently accessed data
- Handle authentication and authorization

### WebSocket
- Reliable connection management
- Automatic reconnection with backoff
- Message queuing for offline scenarios
- Proper cleanup on app termination

### UI/UX
- Consistent design language with existing app
- Smooth animations and transitions
- Loading states and error handling
- Accessibility support (screen readers, etc.)

### Performance
- Lazy loading for large lists
- Efficient chart rendering
- Background data synchronization
- Memory management for long-running connections

---

## Exit Condition

Users can:
- ✅ Receive and respond to proactive messages
- ✅ See AICO's current intentions and focus
- ✅ Track active goals and their progress
- ✅ Provide feedback on AICO behavior
- ✅ Review and approve/reject lessons
- ✅ Configure agency settings and preferences
- ✅ View metrics and behavioral trends
- ✅ Experience seamless real-time updates

The Flutter frontend provides complete visibility and control over the agency system, making AICO's autonomous behavior transparent and user-controllable.

---

## Related Documentation

- [Phase 10: Web Dashboard](agency-phase-10-ui-frontend.md)
- [Phase 9: Lesson Management CLI](agency-phase-9-lesson-management.md)
- [Phase 8: CLI & Analysis](agency-phase-8-cli-analysis.md)
- [Roadmap Overview](agency-roadmap-overview.md)
- [Current Status](agency-roadmap-status.md)
