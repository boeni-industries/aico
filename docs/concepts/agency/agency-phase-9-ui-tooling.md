---
title: Phase 9 - User Interfaces & Tooling
---

# Phase 9 – User Interfaces & Tooling 🚧

**Status:** In Progress

**Goal:** Build user-facing interfaces for agency monitoring, lesson review, and configuration.

---

## Agency Metrics *PARTIAL*

### Metrics Data Collection ✅
**Completed:**
- [x] Comprehensive event logging system operational
- [x] Reflection-specific metrics (41 lessons, 1,437 reflection runs, 2,257 self-model entries)
- [x] Curiosity → learning pipeline tracked (108 goals, 486 skills)
- [x] Database tables: `agency_events`, `agency_events_log`, `event_metrics`

**Pending:**
- [ ] REST API endpoints for metrics

### Metrics CLI ✅
**Completed:**
- [x] `aico agency status` command
- [x] `aico agency goals` command
- [x] `aico agency intentions` command
- [x] `aico agency plans` command
- [x] `aico agency executions` command

**Pending:**
- [ ] `aico agency metrics` (advanced analytics)
- [ ] Reflection run history viewer

### Metrics Dashboard *FUTURE*
- [ ] Real-time metrics visualization
- [ ] Reflection run monitoring
- [ ] Goal and plan tracking

---

## Lesson Management UI *PENDING*

### CLI Commands
- [ ] `aico lessons list` command
- [ ] `aico lessons review <lesson_id>` command
- [ ] `aico lessons approve/reject <lesson_id>` command
- [ ] Show lesson evidence and confidence scores

**Note:** Data available (41 lessons in database), UI pending

### Web Interface *FUTURE*
- [ ] Lesson review and approval workflow
- [ ] Policy suggestion visualization
- [ ] Self-model visualization

---

## Flutter UI & User-Facing Agency Controls *PENDING*

### Agency Dashboard Screen
- [ ] Create dedicated agency screen in Flutter app
- [ ] Display active intention set with visual priority indicators
- [ ] Show current curiosity status and opportunities
- [ ] Display agency state overview (goals, hobbies, focus)

### Intention Set Visibility
- [ ] Surface active intentions in conversation UI (tooltips, status bar)
- [ ] Show why AICO is pursuing specific goals (reasons, scores)
- [ ] Display priority bands and arbiter scores visually
- [ ] Allow users to see hobby goals vs user-requested goals

### Value Profile Management
- [ ] UI for adjusting curiosity intensity slider
- [ ] Proactive behavior level selector (quiet/balanced/proactive)
- [ ] Manage sensitive life areas (add/remove)
- [ ] Configure allowed curiosity domains

### Policy & Consent Management
- [ ] View active policy rules with filtering
- [ ] Grant/revoke consents for specific actions
- [ ] See pending consent requests
- [ ] Review policy decisions and their effects

### Conversation Integration
- [ ] Show agency context in conversation tooltips
- [ ] Display when AICO is acting on curiosity vs user request
- [ ] Surface ethics decisions in conversation flow
- [ ] Explain goal selection and prioritization

### Behavioral Learning Visibility
- [ ] Display active lessons and their effects
- [ ] Show self-model performance metrics
- [ ] Visualize skill success rates and trends
- [ ] Allow users to approve/reject lesson applications

---

## Embodiment as Cognitive Substrate *FUTURE*

### Embodied Cognition Patterns
- [ ] Define internal tasks and routines represented through spatial metaphors
- [ ] Use environment layout and artefacts as memory cues
- [ ] Represent curiosity/hobby work in the 3D flat

### Conversation & UX Integration
- [ ] Ensure hobbies appear in AICO's visible behaviour
- [ ] Integrate agency state with embodiment animations
- [ ] Add spatial context to goal and task representation

### Integration with Real-World Context
- [ ] Connect agency state with real devices/context under user control
- [ ] Add calendar and schedule integration

---

## Exit Condition

Complete CLI tooling for metrics and lesson management. Users can see what AICO is working on, why, and adjust her agency behavior through the Flutter UI. Full transparency and control over agency system.

---

## Current Progress

**Completed:**
- ✅ Core metrics data collection
- ✅ 9 CLI commands for agency management
- ✅ Event logging infrastructure

**In Progress:**
- 🚧 Advanced analytics CLI commands
- 🚧 Lesson management UI

**Next Steps:**
1. Implement advanced analytics commands
2. Create lesson management CLI
3. Design Flutter UI components
4. Build REST API endpoints

---

## Related Documentation

- [Phase 8: CLI & Analysis](agency-phase-8-cli-analysis.md)
- [Current Status](agency-roadmap-status.md)
- [Roadmap Overview](agency-roadmap-overview.md)
