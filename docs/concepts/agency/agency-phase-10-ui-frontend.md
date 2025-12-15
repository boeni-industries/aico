---
title: Phase 10 - UI & Frontend Integration
---

# Phase 10 – UI & Frontend Integration 🔮

**Status:** Future

**Goal:** Build user-facing interfaces for agency monitoring, configuration, and control through web dashboard and Flutter UI.

---

## REST API Endpoints *PENDING*

### Metrics API
- [ ] `GET /api/v1/agency/metrics` - Comprehensive KPI dashboard data
- [ ] `GET /api/v1/agency/reflection-history` - Reflection run history
- [ ] `GET /api/v1/agency/skill-performance` - Skill success rates
- [ ] `GET /api/v1/agency/health` - System health diagnostics
- [ ] Support for time window filtering (`?last=7d`, `?since=<timestamp>`)
- [ ] JSON response format matching CLI output

### Lesson Management API
- [ ] `GET /api/v1/lessons` - List lessons with filtering
- [ ] `GET /api/v1/lessons/{id}` - Detailed lesson view
- [ ] `POST /api/v1/lessons/{id}/approve` - Approve lesson
- [ ] `POST /api/v1/lessons/{id}/reject` - Reject lesson
- [ ] `GET /api/v1/lessons/stats` - Lesson statistics

### Agency State API
- [ ] `GET /api/v1/agency/goals` - Goal listing
- [ ] `GET /api/v1/agency/intentions` - Active intention set
- [ ] `GET /api/v1/agency/plans` - Plan management
- [ ] `GET /api/v1/agency/executions` - Execution tracking

---

## Web Dashboard *PENDING*

### Framework Selection
- [ ] Evaluate options: React, Vue, Svelte, or Next.js
- [ ] Consider server-side rendering vs client-side
- [ ] WebSocket support for real-time updates
- [ ] Authentication integration

### Core Features
- [ ] Real-time metrics visualization
  - Goal completion rates over time
  - Reflection run monitoring
  - Skill performance trends
  - System health indicators
- [ ] Lesson review and approval interface
  - List view with filtering and sorting
  - Detailed lesson view with evidence
  - One-click approve/reject actions
  - Batch operations
- [ ] Agency state overview
  - Active goals and plans
  - Current intention set
  - Recent activity timeline
  - Event log viewer

---

## Flutter UI Integration *PENDING*

### Agency Dashboard Screen
- [ ] Create dedicated agency screen in Flutter app
- [ ] Display active intention set with visual priority indicators
- [ ] Show current curiosity status and opportunities
- [ ] Display agency state overview (goals, hobbies, focus)
- [ ] Real-time updates via WebSocket or polling

### Intention Set Visibility
- [ ] Surface active intentions in conversation UI
  - Tooltips showing current goals
  - Status bar with agency state
  - Visual indicators for proactive behavior
- [ ] Show why AICO is pursuing specific goals
  - Reasons and arbiter scores
  - Priority bands visualization
  - Hobby goals vs user-requested goals distinction

### Value Profile Management
- [ ] UI for adjusting curiosity intensity slider
- [ ] Proactive behavior level selector (quiet/balanced/proactive)
- [ ] Manage sensitive life areas (add/remove)
- [ ] Configure allowed curiosity domains
- [ ] Real-time preview of behavior changes

### Policy & Consent Management
- [ ] View active policy rules with filtering
- [ ] Grant/revoke consents for specific actions
- [ ] See pending consent requests
- [ ] Review policy decisions and their effects
- [ ] Policy suggestion interface

### Conversation Integration
- [ ] Show agency context in conversation tooltips
- [ ] Display when AICO is acting on curiosity vs user request
- [ ] Surface ethics decisions in conversation flow
- [ ] Explain goal selection and prioritization
- [ ] Visual indicators for agency-driven responses

### Behavioral Learning Visibility
- [ ] Display active lessons and their effects
- [ ] Show self-model performance metrics
- [ ] Visualize skill success rates and trends
- [ ] Allow users to approve/reject lesson applications
- [ ] Lesson impact visualization

---

## Embodiment Integration *FUTURE*

### Embodied Cognition Patterns
- [ ] Define internal tasks and routines represented through spatial metaphors
- [ ] Use environment layout and artifacts as memory cues
- [ ] Represent curiosity/hobby work in the 3D flat
- [ ] Spatial representation of agency state

### Conversation & UX Integration
- [ ] Ensure hobbies appear in AICO's visible behavior
- [ ] Integrate agency state with embodiment animations
- [ ] Add spatial context to goal and task representation
- [ ] Visual feedback for agency activities

### Real-World Context Integration
- [ ] Connect agency state with real devices/context under user control
- [ ] Calendar and schedule integration
- [ ] Location-aware agency behavior
- [ ] Time-of-day awareness

---

## Exit Condition

Users can monitor, configure, and control AICO's agency system through intuitive web and mobile interfaces. Complete transparency into agency behavior with real-time updates and interactive controls.

---

## Prerequisites

**Must be completed before Phase 10:**
- ✅ Phase 8: CLI & Analysis (metrics, analytics, health monitoring)
- ✅ Phase 9: Lesson Management CLI (lesson review and approval)
- [ ] API design and specification
- [ ] Authentication and authorization framework
- [ ] WebSocket infrastructure for real-time updates

---

## Implementation Approach

**Stage 1: API Foundation**
1. Design REST API specification (OpenAPI/Swagger)
2. Implement core endpoints for metrics and lessons
3. Add authentication and rate limiting
4. Create API documentation

**Stage 2: Web Dashboard**
1. Select and set up frontend framework
2. Implement metrics visualization
3. Build lesson management interface
4. Add real-time updates

**Stage 3: Flutter Integration**
1. Create agency dashboard screen
2. Integrate with existing conversation UI
3. Add value profile management
4. Implement policy and consent controls

**Stage 4: Advanced Features**
1. Embodiment integration
2. Real-world context awareness
3. Advanced visualizations
4. Performance optimization

---

## Related Documentation

- [Phase 9: Lesson Management](agency-phase-9-lesson-management.md) - Prerequisites
- [Phase 8: CLI & Analysis](agency-phase-8-cli-analysis.md) - Data sources
- [Current Status](agency-roadmap-status.md)
- [Roadmap Overview](agency-roadmap-overview.md)

---

**Note:** This phase represents future work and is not currently scheduled. Items here were previously in "Future Enhancements" but organized into a coherent phase for eventual implementation.
