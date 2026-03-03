# Agency Gateway Implementation - Complete Endpoint List

## Gateway Router Endpoints (26 total)
✅ Implemented in `/backend/api/agency/router_gateway.py`

### Core State & Metrics
1. GET `/agency/state` - Overall agency state
2. GET `/agency/intentions` - Active intention set  
3. GET `/agency/events` - Agency events list
4. GET `/agency/curiosity` - Curiosity status

### Value Profile & Ethics
5. GET `/agency/profile` - Get value profile
6. PUT `/agency/profile` - Update value profile
7. GET `/agency/policies` - List policy rules

### Consent Management
8. POST `/agency/consent` - Grant consent
9. GET `/agency/consent` - List consents
10. DELETE `/agency/consent/{id}` - Revoke consent

### Goal Management
11. GET `/agency/goals` - List goals (with filters)
12. GET `/agency/goals/{id}` - Get goal details
13. GET `/agency/goals/{id}/plans` - Get goal plans
14. POST `/agency/goals/{id}/replan` - Replan goal

### Skills
15. POST `/agency/skills/list` - List all skills
16. POST `/agency/skills/info` - Get skill info
17. POST `/agency/skills/invoke` - Invoke skill
18. POST `/agency/connectivity/scan` - Run connectivity scan

### Tools
19. POST `/agency/tools/list` - List all tools
20. POST `/agency/tools/info` - Get tool info
21. POST `/agency/tools/invoke` - Invoke tool

### Reflection & Self-Model
22. GET `/agency/reflection/runs` - List reflection runs
23. GET `/agency/reflection/lessons` - List lessons learned
24. GET `/agency/reflection/self-model` - List self-model entries
25. GET `/agency/reflection/skills/{id}/performance` - Get skill performance
26. GET `/agency/reflection/summary` - Get reflection summary

## NATS Client Methods Needed
All methods in `GatewayNATSClient` (`backend/api_gateway/core/nats_client.py`):

1. ✅ request_agency_state(user_id)
2. ⏳ request_agency_intentions(user_id, limit)
3. ⏳ request_agency_events(user_id, limit, offset)
4. ⏳ request_agency_curiosity(user_id)
5. ⏳ request_agency_profile(user_id)
6. ⏳ request_agency_profile_update(user_id, update_data)
7. ⏳ request_agency_policies(user_id)
8. ⏳ request_agency_consent_grant(user_id, consent_data)
9. ⏳ request_agency_consents(user_id)
10. ⏳ request_agency_consent_revoke(user_id, consent_id)
11. ✅ request_agency_goals(user_id, status, origin, priority, limit, page)
12. ⏳ request_agency_goal(user_id, goal_id)
13. ⏳ request_agency_goal_plans(user_id, goal_id)
14. ⏳ request_agency_goal_replan(user_id, goal_id)
15. ⏳ request_agency_skills_list(user_id)
16. ⏳ request_agency_skill_info(user_id, skill_id)
17. ⏳ request_agency_skill_invoke(user_id, skill_data)
18. ⏳ request_agency_connectivity_scan(user_id, scan_data)
19. ⏳ request_agency_tools_list(user_id)
20. ⏳ request_agency_tool_info(user_id, tool_id)
21. ⏳ request_agency_tool_invoke(user_id, tool_data)
22. ⏳ request_agency_reflection_runs(user_id, limit)
23. ⏳ request_agency_reflection_lessons(user_id, limit)
24. ⏳ request_agency_reflection_self_model(user_id)
25. ⏳ request_agency_skill_performance(user_id, skill_id)
26. ⏳ request_agency_reflection_summary(user_id, window_days)

## Core NATS Handlers Needed
All handlers in `CoreNATSHandlers` (`backend/core/nats_handlers.py`):

1. ✅ handle_agency_state_request
2. ⏳ handle_agency_intentions_request
3. ⏳ handle_agency_events_request
4. ⏳ handle_agency_curiosity_request
5. ⏳ handle_agency_profile_request
6. ⏳ handle_agency_profile_update_request
7. ⏳ handle_agency_policies_request
8. ⏳ handle_agency_consent_grant_request
9. ⏳ handle_agency_consents_request
10. ⏳ handle_agency_consent_revoke_request
11. ✅ handle_agency_goals_request
12. ⏳ handle_agency_goal_request
13. ⏳ handle_agency_goal_plans_request
14. ⏳ handle_agency_goal_replan_request
15. ⏳ handle_agency_skills_list_request
16. ⏳ handle_agency_skill_info_request
17. ⏳ handle_agency_skill_invoke_request
18. ⏳ handle_agency_connectivity_scan_request
19. ⏳ handle_agency_tools_list_request
20. ⏳ handle_agency_tool_info_request
21. ⏳ handle_agency_tool_invoke_request
22. ⏳ handle_agency_reflection_runs_request
23. ⏳ handle_agency_reflection_lessons_request
24. ⏳ handle_agency_reflection_self_model_request
25. ⏳ handle_agency_skill_performance_request
26. ⏳ handle_agency_reflection_summary_request

## NATS Subscriptions Needed
All subscriptions in core lifecycle (`backend/core/nats_handlers.py`):

1. ✅ agency.state
2. ⏳ agency.intentions
3. ⏳ agency.events
4. ⏳ agency.curiosity
5. ⏳ agency.profile
6. ⏳ agency.profile.update
7. ⏳ agency.policies
8. ⏳ agency.consent.grant
9. ⏳ agency.consents
10. ⏳ agency.consent.revoke
11. ✅ agency.goals
12. ⏳ agency.goal
13. ⏳ agency.goal.plans
14. ⏳ agency.goal.replan
15. ⏳ agency.skills.list
16. ⏳ agency.skill.info
17. ⏳ agency.skill.invoke
18. ⏳ agency.connectivity.scan
19. ⏳ agency.tools.list
20. ⏳ agency.tool.info
21. ⏳ agency.tool.invoke
22. ⏳ agency.reflection.runs
23. ⏳ agency.reflection.lessons
24. ⏳ agency.reflection.self_model
25. ⏳ agency.skill.performance
26. ⏳ agency.reflection.summary

## Implementation Strategy

Due to the large scope (24 remaining endpoints), I'll implement in logical groups:

### Batch 1: Core Metrics (intentions, events, curiosity) - 3 endpoints
### Batch 2: Profile & Policies (profile GET/PUT, policies) - 3 endpoints  
### Batch 3: Consent (grant, list, revoke) - 3 endpoints
### Batch 4: Goals (get, plans, replan) - 3 endpoints
### Batch 5: Skills (list, info, invoke, connectivity) - 4 endpoints
### Batch 6: Tools (list, info, invoke) - 3 endpoints
### Batch 7: Reflection (runs, lessons, self-model, performance, summary) - 5 endpoints

Total: 24 endpoints to implement (2 already done: state, goals list)
