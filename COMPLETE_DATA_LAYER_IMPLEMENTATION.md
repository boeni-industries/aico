# Complete Data Layer Implementation Plan

**Total Tables:** 65  
**Implemented:** 11  
**Remaining:** 54

---

## ✅ Completed Repositories (11)

### User/Auth (3)
- ✅ UserRepository (user_profiles)
- ✅ SessionRepository (auth_sessions)
- ✅ CredentialsRepository (auth_user_credentials)

### Agency Core (3)
- ✅ GoalRepository (agency_goals)
- ✅ PlanRepository (agency_plans)
- ✅ PolicyRepository (agency_policy_rules)

### Knowledge Graph (2)
- ✅ KGNodeRepository (kg_nodes)
- ✅ KGEdgeRepository (kg_edges)

### AMS (2)
- ✅ TrajectoryRepository (ams_trajectories)
- ✅ BehavioralFeedbackRepository (ams_behavioral_feedback)

### Scheduler (1)
- ✅ SchedulerTaskRepository (scheduler_tasks)

---

## 🚧 Remaining Repositories (54)

### Agency Domain (17 tables)
1. ❌ ArbiterAdjustmentRepository (agency_arbiter_adjustments)
2. ❌ AgencyEventRepository (agency_events)
3. ❌ AgencyEventLogRepository (agency_events_log)
4. ❌ ExecutionSnapshotRepository (agency_execution_snapshots)
5. ❌ FollowupRepository (agency_followups)
6. ❌ GoalDependencyRepository (agency_goal_dependencies)
7. ❌ GoalOutcomeRepository (agency_goal_outcomes)
8. ❌ GoalSkillExecutionRepository (agency_goal_skill_executions)
9. ❌ IntentionSetRepository (agency_intention_set)
10. ❌ LessonRepository (agency_lessons)
11. ❌ PlanExecutionRepository (agency_plan_executions)
12. ❌ ReflectionNoteRepository (agency_reflection_notes)
13. ❌ ReflectionRunRepository (agency_reflection_runs)
14. ❌ ReminderRepository (agency_reminders)
15. ❌ SelfModelRepository (agency_self_model)
16. ❌ SkillGapRepository (agency_skill_gaps)
17. ❌ SkillExecutionRepository (agency_skill_executions)
18. ❌ SkillLearningDataRepository (agency_skill_learning_data)
19. ❌ StepExecutionRepository (agency_step_executions)

### AMS Domain (6 tables)
20. ❌ BehavioralSkillRepository (ams_behavioral_skills)
21. ❌ ContextPreferenceVectorRepository (ams_context_preference_vectors)
22. ❌ SkillPerformanceRepository (ams_skill_performance)
23. ❌ UserMemoryRepository (ams_user_memories)
24. ❌ UserPreferenceRepository (ams_user_preferences)
25. ❌ WorldStateRepository (ams_world_state)

### Auth Domain (1 table)
26. ❌ DeviceRepository (auth_devices)

### Conversation Domain (6 tables)
27. ❌ ConversationRepository (conversations)
28. ❌ ConversationMessageRepository (conversation_messages)
29. ❌ ConversationSegmentRepository (conversation_segments)
30. ❌ ConversationSummaryRepository (conversation_summaries)
31. ❌ ConversationTopicRepository (conversation_topics)
32. ❌ MessageEmbeddingRepository (message_embeddings)

### Knowledge Graph Domain (2 tables)
33. ❌ KGEntityMetadataRepository (kg_entity_metadata)
34. ❌ KGRelationMetadataRepository (kg_relation_metadata)

### Memory Domain (4 tables)
35. ❌ MemoryConsolidationStateRepository (memory_consolidation_state)
36. ❌ MemorySegmentRepository (memory_segments)
37. ❌ MemorySnapshotRepository (memory_snapshots)
38. ❌ WorkingMemoryRepository (working_memory)

### Proactive Domain (4 tables)
39. ❌ ProactiveFeedbackRequestRepository (proactive_feedback_requests)
40. ❌ ProactiveOpportunityRepository (proactive_opportunities)
41. ❌ ProactiveReminderRepository (proactive_reminders)
42. ❌ ProactiveReminderClusterRepository (proactive_reminder_clusters)

### Scheduler Domain (2 tables)
43. ❌ TaskExecutionRepository (scheduler_task_executions)
44. ❌ TaskLockRepository (scheduler_task_locks)

### System Domain (9 tables)
45. ❌ SystemEventRepository (system_events)
46. ❌ SystemEventMetricRepository (system_event_metrics)
47. ❌ SystemLogRepository (system_logs)
48. ❌ SystemMetricRepository (system_metrics)
49. ❌ SystemStateRepository (system_state)
50. ❌ BackgroundTaskRepository (background_tasks)
51. ❌ BackgroundTaskExecutionRepository (background_task_executions)
52. ❌ CacheEntryRepository (cache_entries)
53. ❌ FeatureFlagRepository (feature_flags)

### Other Tables (3)
54. ❌ UserSettingRepository (user_settings)
55. ❌ UserActivityRepository (user_activity)
56. ❌ NotificationRepository (notifications)

---

## Implementation Strategy

### Phase 1: High-Priority Domains (20 repositories)
**Focus:** Tables actively used by current application

1. **Conversation Domain (6)** - Core functionality
2. **Memory Domain (4)** - Core functionality  
3. **Agency Execution (5)** - Active agency features
4. **Scheduler (2)** - Task management
5. **Auth Devices (1)** - User management
6. **System Logs (2)** - Monitoring

### Phase 2: Medium-Priority Domains (20 repositories)
**Focus:** Supporting features and analytics

1. **Agency Analytics (8)** - Lessons, reflections, outcomes
2. **AMS Extended (6)** - Skills, preferences, world state
3. **Proactive (4)** - Proactive features
4. **KG Metadata (2)** - Enhanced KG features

### Phase 3: Low-Priority Domains (14 repositories)
**Focus:** System infrastructure and future features

1. **System Infrastructure (7)** - Metrics, cache, features
2. **Agency Support (5)** - Followups, reminders, gaps
3. **User Management (2)** - Settings, activity

---

## Estimated Effort

- **Models:** ~54 new dataclasses
- **Table Definitions:** ~54 new Table objects in tables.py
- **Repositories:** ~54 new repository classes
- **Tests:** ~400-500 new integration tests (8-10 per repository)
- **UnitOfWork Updates:** Add 54 new properties

**Total Estimated Time:** This is a multi-day effort requiring systematic implementation.

---

## Current Status
- Starting Phase 1: High-Priority Domains
- Target: Complete 20 high-priority repositories first
