"""
Unit of Work Pattern

Provides transaction management across multiple repositories.
Ensures atomic operations - all succeed or all fail together.
"""

from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from contextlib import asynccontextmanager

from aico.core.logging import get_logger

logger = get_logger("shared.data.uow")


class UnitOfWork:
    """
    Unit of Work pattern for managing database transactions.
    
    Provides:
    - Transaction boundaries (commit/rollback)
    - Lazy-loaded repository access
    - Automatic cleanup on context exit
    
    Usage:
        async with uow_factory() as uow:
            user = await uow.users.create(user_data)
            session = await uow.sessions.create(session_data)
            await uow.commit()  # Both committed atomically
    """
    
    def __init__(self, session_factory: async_sessionmaker):
        """
        Initialize Unit of Work with session factory.
        
        Args:
            session_factory: SQLAlchemy async session factory
        """
        self._session_factory = session_factory
        self._session: Optional[AsyncSession] = None
        
        # Lazy-loaded repositories
        self._user_repository = None
        self._user_profiles_repository = None
        self._user_relationships_repository = None
        self._user_skill_confidence_repository = None
        self._user_time_preferences_repository = None
        self._user_proactive_preferences_repository = None
        self._device_repository = None
        self._auth_devices_repository = None
        self._auth_sessions_repository = None
        self._auth_user_credentials_repository = None
        self._session_repository = None
        self._credentials_repository = None
        self._agency_event_repository = None
        self._agency_events_log_repository = None
        self._agency_followups_repository = None
        self._agency_reflection_notes_repository = None
        self._agency_reminders_repository = None
        self._agency_arbiter_adjustments_repository = None
        self._goal_repository = None
        self._plan_repository = None
        self._lesson_repository = None
        self._policy_repository = None
        self._kg_node_repository = None
        self._kg_edge_repository = None
        self._ams_behavioral_skills_repository = None
        self._ams_behavioral_feedback_repository = None
        self._ams_context_preference_vectors_repository = None
        self._ams_context_skill_stats_repository = None
        self._ams_consolidation_state_repository = None
        self._ams_trajectories_repository = None
        self._ams_user_memories_repository = None
        self._arbiter_ab_tests_repository = None
        self._arbiter_bandit_arms_repository = None
        self._consent_user_consents_repository = None
        self._consent_records_repository = None
        self._consent_audit_log_repository = None
        self._trajectory_repository = None
        self._feedback_repository = None
        self._scheduler_tasks_repository = None
        self._scheduler_task_executions_repository = None
        self._task_execution_repository = None
        self._conversation_initiations_repository = None
        self._conversation_initiation_repository = None
        self._workflow_executions_repository = None
        self._workflow_stages_repository = None
        self._system_event_metrics_repository = None
        self._system_event_replay_sessions_repository = None
        self._system_events_repository = None
        self._system_event_repository = None
        self._emotion_state_repository = None
        self._emotion_history_repository = None
        self._user_feedback_requests_repository = None
        self._ethics_decisions_cache_repository = None
        self._ethics_gate_audit_repository = None
        self._ethics_policy_rules_repository = None
        self._ethics_value_profiles_repository = None
        self._kg_nodes_repository = None
        self._kg_edges_repository = None
        self._kg_node_properties_repository = None
        self._kg_edge_properties_repository = None
        self._proactive_analytics_repository = None
        self._proactive_reminder_clusters_repository = None
        self._auth_access_policies_repository = None
        self._user_skill_confidence_repository = None
        self._auth_access_policies_repository = None
        self._user_skill_confidence_repository = None
        self._system_health_checks_repository = None
        self._system_issues_repository = None
        self._policy_rules_repository = None
    
    async def __aenter__(self):
        """Enter context - create session."""
        self._session = self._session_factory()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """
        Exit context - commit or rollback.
        
        If exception occurred, rollback automatically.
        Otherwise, commit if not already committed.
        """
        if exc_type is not None:
            # Exception occurred - rollback
            await self.rollback()
        else:
            # No exception - commit if not already done
            if self._session and self._session.in_transaction():
                await self.commit()
        
        # Always close session
        if self._session:
            await self._session.close()
            self._session = None
    
    async def commit(self):
        """Commit current transaction."""
        if self._session:
            await self._session.commit()
            logger.debug("Transaction committed")
    
    async def rollback(self):
        """Rollback current transaction."""
        if self._session:
            await self._session.rollback()
            logger.debug("Transaction rolled back")
    
    async def flush(self):
        """Flush pending changes without committing."""
        if self._session:
            await self._session.flush()
    
    # ========================================================================
    # Repository Properties (Lazy-loaded)
    # ========================================================================
    
    @property
    def users(self):
        """Get UserRepository instance."""
        if self._user_repository is None:
            from .repositories.postgres.user_repository import PostgresUserRepository
            self._user_repository = PostgresUserRepository(self._session)
        return self._user_repository
    
    @property
    def user_profiles(self):
        """Get UserProfilesRepository instance."""
        if self._user_profiles_repository is None:
            from .repositories.postgres.user_profiles_repository import PostgresUserProfilesRepository
            self._user_profiles_repository = PostgresUserProfilesRepository(self._session)
        return self._user_profiles_repository
    
    @property
    def user_relationships(self):
        """Get UserRelationshipsRepository instance."""
        if self._user_relationships_repository is None:
            from .repositories.postgres.user_relationships_repository import PostgresUserRelationshipsRepository
            self._user_relationships_repository = PostgresUserRelationshipsRepository(self._session)
        return self._user_relationships_repository
    
    @property
    def user_skill_confidence(self):
        """Get UserSkillConfidenceRepository instance."""
        if self._user_skill_confidence_repository is None:
            from .repositories.postgres.user_skill_confidence_repository import PostgresUserSkillConfidenceRepository
            self._user_skill_confidence_repository = PostgresUserSkillConfidenceRepository(self._session)
        return self._user_skill_confidence_repository
    
    @property
    def user_time_preferences(self):
        """Get UserTimePreferencesRepository instance."""
        if self._user_time_preferences_repository is None:
            from .repositories.postgres.user_time_preferences_repository import PostgresUserTimePreferencesRepository
            self._user_time_preferences_repository = PostgresUserTimePreferencesRepository(self._session)
        return self._user_time_preferences_repository
    
    @property
    def user_proactive_preferences(self):
        """Get UserProactivePreferencesRepository instance."""
        if self._user_proactive_preferences_repository is None:
            from .repositories.postgres.user_proactive_preferences_repository import PostgresUserProactivePreferencesRepository
            self._user_proactive_preferences_repository = PostgresUserProactivePreferencesRepository(self._session)
        return self._user_proactive_preferences_repository
    
    @property
    def devices(self):
        """Get DeviceRepository instance."""
        if self._device_repository is None:
            from .repositories.postgres.device_repository import PostgresDeviceRepository
            self._device_repository = PostgresDeviceRepository(self._session)
        return self._device_repository
    
    @property
    def auth_devices(self):
        """Get AuthDevicesRepository instance."""
        if self._auth_devices_repository is None:
            from .repositories.postgres.auth_devices_repository import PostgresAuthDevicesRepository
            self._auth_devices_repository = PostgresAuthDevicesRepository(self._session)
        return self._auth_devices_repository
    
    @property
    def auth_sessions(self):
        """Get AuthSessionsRepository instance."""
        if self._auth_sessions_repository is None:
            from .repositories.postgres.auth_sessions_repository import PostgresAuthSessionsRepository
            self._auth_sessions_repository = PostgresAuthSessionsRepository(self._session)
        return self._auth_sessions_repository
    
    @property
    def auth_user_credentials(self):
        """Get AuthUserCredentialsRepository instance."""
        if self._auth_user_credentials_repository is None:
            from .repositories.postgres.auth_user_credentials_repository import PostgresAuthUserCredentialsRepository
            self._auth_user_credentials_repository = PostgresAuthUserCredentialsRepository(self._session)
        return self._auth_user_credentials_repository
    
    @property
    def sessions(self):
        """Get SessionRepository instance."""
        if self._session_repository is None:
            from .repositories.postgres.session_repository import PostgresSessionRepository
            self._session_repository = PostgresSessionRepository(self._session)
        return self._session_repository
    
    @property
    def credentials(self):
        """Get CredentialsRepository instance."""
        if self._credentials_repository is None:
            from .repositories.postgres.credentials_repository import PostgresCredentialsRepository
            self._credentials_repository = PostgresCredentialsRepository(self._session)
        return self._credentials_repository
    
    @property
    def agency_events(self):
        """Get AgencyEventRepository instance."""
        if self._agency_event_repository is None:
            from .repositories.postgres.agency_event_repository import PostgresAgencyEventRepository
            self._agency_event_repository = PostgresAgencyEventRepository(self._session)
        return self._agency_event_repository
    
    @property
    def agency_events_log(self):
        """Get AgencyEventsLogRepository instance."""
        if self._agency_events_log_repository is None:
            from .repositories.postgres.agency_events_log_repository import PostgresAgencyEventsLogRepository
            self._agency_events_log_repository = PostgresAgencyEventsLogRepository(self._session)
        return self._agency_events_log_repository
    
    @property
    def agency_followups(self):
        """Get AgencyFollowupsRepository instance."""
        if self._agency_followups_repository is None:
            from .repositories.postgres.agency_followups_repository import PostgresAgencyFollowupsRepository
            self._agency_followups_repository = PostgresAgencyFollowupsRepository(self._session)
        return self._agency_followups_repository
    
    @property
    def agency_reflection_notes(self):
        """Get AgencyReflectionNotesRepository instance."""
        if self._agency_reflection_notes_repository is None:
            from .repositories.postgres.agency_reflection_notes_repository import PostgresAgencyReflectionNotesRepository
            self._agency_reflection_notes_repository = PostgresAgencyReflectionNotesRepository(self._session)
        return self._agency_reflection_notes_repository
    
    @property
    def agency_reminders(self):
        """Get AgencyRemindersRepository instance."""
        if self._agency_reminders_repository is None:
            from .repositories.postgres.agency_reminders_repository import PostgresAgencyRemindersRepository
            self._agency_reminders_repository = PostgresAgencyRemindersRepository(self._session)
        return self._agency_reminders_repository
    
    @property
    def agency_arbiter_adjustments(self):
        """Get AgencyArbiterAdjustmentsRepository instance."""
        if self._agency_arbiter_adjustments_repository is None:
            from .repositories.postgres.agency_arbiter_adjustments_repository import PostgresAgencyArbiterAdjustmentsRepository
            self._agency_arbiter_adjustments_repository = PostgresAgencyArbiterAdjustmentsRepository(self._session)
        return self._agency_arbiter_adjustments_repository
    
    @property
    def goals(self):
        """Get GoalRepository instance."""
        if self._goal_repository is None:
            from .repositories.postgres.goal_repository import PostgresGoalRepository
            self._goal_repository = PostgresGoalRepository(self._session)
        return self._goal_repository
    
    @property
    def plans(self):
        """Get PlanRepository instance."""
        if self._plan_repository is None:
            from .repositories.postgres.plan_repository import PostgresPlanRepository
            self._plan_repository = PostgresPlanRepository(self._session)
        return self._plan_repository
    
    @property
    def lessons(self):
        """Get LessonRepository instance."""
        if self._lesson_repository is None:
            from .repositories.postgres.lesson_repository import PostgresLessonRepository
            self._lesson_repository = PostgresLessonRepository(self._session)
        return self._lesson_repository
    
    @property
    def policies(self):
        """Get PolicyRepository instance."""
        if self._policy_repository is None:
            from .repositories.postgres.policy_repository import PostgresPolicyRepository
            self._policy_repository = PostgresPolicyRepository(self._session)
        return self._policy_repository
    
    @property
    def kg_nodes(self):
        """Get KGNodeRepository instance."""
        if self._kg_node_repository is None:
            from .repositories.postgres.kg_node_repository import PostgresKGNodeRepository
            self._kg_node_repository = PostgresKGNodeRepository(self._session)
        return self._kg_node_repository
    
    @property
    def kg_edges(self):
        """Get KGEdgeRepository instance."""
        if self._kg_edge_repository is None:
            from .repositories.postgres.kg_edge_repository import PostgresKGEdgeRepository
            self._kg_edge_repository = PostgresKGEdgeRepository(self._session)
        return self._kg_edge_repository
    
    @property
    def ams_behavioral_skills(self):
        """Get AMSBehavioralSkillsRepository instance."""
        if self._ams_behavioral_skills_repository is None:
            from .repositories.postgres.ams_behavioral_skills_repository import PostgresAMSBehavioralSkillsRepository
            self._ams_behavioral_skills_repository = PostgresAMSBehavioralSkillsRepository(self._session)
        return self._ams_behavioral_skills_repository
    
    @property
    def ams_behavioral_feedback(self):
        """Get AMSBehavioralFeedbackRepository instance."""
        if self._ams_behavioral_feedback_repository is None:
            from .repositories.postgres.ams_behavioral_feedback_repository import PostgresAMSBehavioralFeedbackRepository
            self._ams_behavioral_feedback_repository = PostgresAMSBehavioralFeedbackRepository(self._session)
        return self._ams_behavioral_feedback_repository
    
    @property
    def ams_context_preference_vectors(self):
        """Get AMSContextPreferenceVectorsRepository instance."""
        if self._ams_context_preference_vectors_repository is None:
            from .repositories.postgres.ams_context_preference_vectors_repository import PostgresAMSContextPreferenceVectorsRepository
            self._ams_context_preference_vectors_repository = PostgresAMSContextPreferenceVectorsRepository(self._session)
        return self._ams_context_preference_vectors_repository
    
    @property
    def ams_context_skill_stats(self):
        """Get AMSContextSkillStatsRepository instance."""
        if self._ams_context_skill_stats_repository is None:
            from .repositories.postgres.ams_context_skill_stats_repository import PostgresAMSContextSkillStatsRepository
            self._ams_context_skill_stats_repository = PostgresAMSContextSkillStatsRepository(self._session)
        return self._ams_context_skill_stats_repository
    
    @property
    def ams_consolidation_state(self):
        """Get AMSConsolidationStateRepository instance."""
        if self._ams_consolidation_state_repository is None:
            from .repositories.postgres.ams_consolidation_state_repository import PostgresAMSConsolidationStateRepository
            self._ams_consolidation_state_repository = PostgresAMSConsolidationStateRepository(self._session)
        return self._ams_consolidation_state_repository
    
    @property
    def ams_trajectories(self):
        """Get AMSTrajectoriesRepository instance."""
        if self._ams_trajectories_repository is None:
            from .repositories.postgres.ams_trajectories_repository import PostgresAMSTrajectoriesRepository
            self._ams_trajectories_repository = PostgresAMSTrajectoriesRepository(self._session)
        return self._ams_trajectories_repository
    
    @property
    def ams_user_memories(self):
        """Get AMSUserMemoriesRepository instance."""
        if self._ams_user_memories_repository is None:
            from .repositories.postgres.ams_user_memories_repository import PostgresAMSUserMemoriesRepository
            self._ams_user_memories_repository = PostgresAMSUserMemoriesRepository(self._session)
        return self._ams_user_memories_repository
    
    @property
    def arbiter_ab_tests(self):
        """Get ArbiterABTestsRepository instance."""
        if self._arbiter_ab_tests_repository is None:
            from .repositories.postgres.arbiter_ab_tests_repository import PostgresArbiterABTestsRepository
            self._arbiter_ab_tests_repository = PostgresArbiterABTestsRepository(self._session)
        return self._arbiter_ab_tests_repository
    
    @property
    def arbiter_bandit_arms(self):
        """Get ArbiterBanditArmsRepository instance."""
        if self._arbiter_bandit_arms_repository is None:
            from .repositories.postgres.arbiter_bandit_arms_repository import PostgresArbiterBanditArmsRepository
            self._arbiter_bandit_arms_repository = PostgresArbiterBanditArmsRepository(self._session)
        return self._arbiter_bandit_arms_repository
    
    @property
    def consent_user_consents(self):
        """Get ConsentUserConsentsRepository instance."""
        if self._consent_user_consents_repository is None:
            from .repositories.postgres.consent_user_consents_repository import PostgresConsentUserConsentsRepository
            self._consent_user_consents_repository = PostgresConsentUserConsentsRepository(self._session)
        return self._consent_user_consents_repository
    
    @property
    def consent_records(self):
        """Get ConsentRecordsRepository instance."""
        if self._consent_records_repository is None:
            from .repositories.postgres.consent_records_repository import PostgresConsentRecordsRepository
            self._consent_records_repository = PostgresConsentRecordsRepository(self._session)
        return self._consent_records_repository
    
    @property
    def consent_audit_log(self):
        """Get ConsentAuditLogRepository instance."""
        if self._consent_audit_log_repository is None:
            from .repositories.postgres.consent_audit_log_repository import PostgresConsentAuditLogRepository
            self._consent_audit_log_repository = PostgresConsentAuditLogRepository(self._session)
        return self._consent_audit_log_repository
    
    @property
    def trajectories(self):
        """Get TrajectoryRepository instance."""
        if self._trajectory_repository is None:
            from .repositories.postgres.trajectory_repository import PostgresTrajectoryRepository
            self._trajectory_repository = PostgresTrajectoryRepository(self._session)
        return self._trajectory_repository
    
    @property
    def feedback(self):
        """Get FeedbackRepository instance."""
        if self._feedback_repository is None:
            from .repositories.postgres.feedback_repository import PostgresFeedbackRepository
            self._feedback_repository = PostgresFeedbackRepository(self._session)
        return self._feedback_repository
    
    @property
    def scheduler_tasks(self):
        """Get SchedulerTasksRepository instance."""
        if self._scheduler_tasks_repository is None:
            from .repositories.postgres.scheduler_tasks_repository import PostgresSchedulerTasksRepository
            self._scheduler_tasks_repository = PostgresSchedulerTasksRepository(self._session)
        return self._scheduler_tasks_repository
    
    @property
    def scheduler_task_executions(self):
        """Get SchedulerTaskExecutionsRepository instance."""
        if self._scheduler_task_executions_repository is None:
            from .repositories.postgres.scheduler_task_executions_repository import PostgresSchedulerTaskExecutionsRepository
            self._scheduler_task_executions_repository = PostgresSchedulerTaskExecutionsRepository(self._session)
        return self._scheduler_task_executions_repository
    
    @property
    def conversation_initiations(self):
        """Get ConversationInitiationsRepository instance."""
        if self._conversation_initiations_repository is None:
            from .repositories.postgres.conversation_initiations_repository import PostgresConversationInitiationsRepository
            self._conversation_initiations_repository = PostgresConversationInitiationsRepository(self._session)
        return self._conversation_initiations_repository
    
    @property
    def workflow_executions(self):
        """Get WorkflowExecutionsRepository instance."""
        if self._workflow_executions_repository is None:
            from .repositories.postgres.workflow_executions_repository import PostgresWorkflowExecutionsRepository
            self._workflow_executions_repository = PostgresWorkflowExecutionsRepository(self._session)
        return self._workflow_executions_repository
    
    @property
    def workflow_stages(self):
        """Get WorkflowStagesRepository instance."""
        if self._workflow_stages_repository is None:
            from .repositories.postgres.workflow_stages_repository import PostgresWorkflowStagesRepository
            self._workflow_stages_repository = PostgresWorkflowStagesRepository(self._session)
        return self._workflow_stages_repository
    
    @property
    def system_event_metrics(self):
        """Get SystemEventMetricsRepository instance."""
        if self._system_event_metrics_repository is None:
            from .repositories.postgres.system_event_metrics_repository import PostgresSystemEventMetricsRepository
            self._system_event_metrics_repository = PostgresSystemEventMetricsRepository(self._session)
        return self._system_event_metrics_repository
    
    @property
    def system_event_replay_sessions(self):
        """Get SystemEventReplaySessionsRepository instance."""
        if self._system_event_replay_sessions_repository is None:
            from .repositories.postgres.system_event_replay_sessions_repository import PostgresSystemEventReplaySessionsRepository
            self._system_event_replay_sessions_repository = PostgresSystemEventReplaySessionsRepository(self._session)
        return self._system_event_replay_sessions_repository
    
    @property
    def system_events(self):
        """Get SystemEventsRepository instance."""
        if self._system_events_repository is None:
            from .repositories.postgres.system_events_repository import PostgresSystemEventsRepository
            self._system_events_repository = PostgresSystemEventsRepository(self._session)
        return self._system_events_repository
    
    @property
    def old_system_events(self):
        """Get SystemEventRepository instance."""
        if self._system_event_repository is None:
            from .repositories.postgres.system_event_repository import PostgresSystemEventRepository
            self._system_event_repository = PostgresSystemEventRepository(self._session)
        return self._system_event_repository
    
    @property
    def emotion_state(self):
        """Get EmotionStateRepository instance."""
        if self._emotion_state_repository is None:
            from .repositories.postgres.emotion_state_repository import PostgresEmotionStateRepository
            self._emotion_state_repository = PostgresEmotionStateRepository(self._session)
        return self._emotion_state_repository
    
    @property
    def emotion_history(self):
        """Get EmotionHistoryRepository instance."""
        if self._emotion_history_repository is None:
            from .repositories.postgres.emotion_history_repository import PostgresEmotionHistoryRepository
            self._emotion_history_repository = PostgresEmotionHistoryRepository(self._session)
        return self._emotion_history_repository
    
    @property
    def user_feedback_requests(self):
        """Get UserFeedbackRequestsRepository instance."""
        if self._user_feedback_requests_repository is None:
            from .repositories.postgres.user_feedback_requests_repository import PostgresUserFeedbackRequestsRepository
            self._user_feedback_requests_repository = PostgresUserFeedbackRequestsRepository(self._session)
        return self._user_feedback_requests_repository
    
    @property
    def ethics_decisions_cache(self):
        """Get EthicsDecisionsCacheRepository instance."""
        if self._ethics_decisions_cache_repository is None:
            from .repositories.postgres.ethics_decisions_cache_repository import PostgresEthicsDecisionsCacheRepository
            self._ethics_decisions_cache_repository = PostgresEthicsDecisionsCacheRepository(self._session)
        return self._ethics_decisions_cache_repository
    
    @property
    def ethics_gate_audit(self):
        """Get EthicsGateAuditRepository instance."""
        if self._ethics_gate_audit_repository is None:
            from .repositories.postgres.ethics_gate_audit_repository import PostgresEthicsGateAuditRepository
            self._ethics_gate_audit_repository = PostgresEthicsGateAuditRepository(self._session)
        return self._ethics_gate_audit_repository
    
    @property
    def ethics_policy_rules(self):
        """Get EthicsPolicyRulesRepository instance."""
        if self._ethics_policy_rules_repository is None:
            from .repositories.postgres.ethics_policy_rules_repository import PostgresEthicsPolicyRulesRepository
            self._ethics_policy_rules_repository = PostgresEthicsPolicyRulesRepository(self._session)
        return self._ethics_policy_rules_repository
    
    @property
    def ethics_value_profiles(self):
        """Get EthicsValueProfilesRepository instance."""
        if self._ethics_value_profiles_repository is None:
            from .repositories.postgres.ethics_value_profiles_repository import PostgresEthicsValueProfilesRepository
            self._ethics_value_profiles_repository = PostgresEthicsValueProfilesRepository(self._session)
        return self._ethics_value_profiles_repository
    
    @property
    def kg_nodes(self):
        """Get KGNodesRepository instance."""
        if self._kg_nodes_repository is None:
            from .repositories.postgres.kg_nodes_repository import PostgresNodesRepository
            self._kg_nodes_repository = PostgresNodesRepository(self._session)
        return self._kg_nodes_repository
    
    @property
    def kg_edges(self):
        """Get KGEdgesRepository instance."""
        if self._kg_edges_repository is None:
            from .repositories.postgres.kg_edges_repository import PostgresEdgesRepository
            self._kg_edges_repository = PostgresEdgesRepository(self._session)
        return self._kg_edges_repository
    
    @property
    def kg_node_properties(self):
        """Get KGNodePropertiesRepository instance."""
        if self._kg_node_properties_repository is None:
            from .repositories.postgres.kg_node_properties_repository import PostgresKGNodePropertiesRepository
            self._kg_node_properties_repository = PostgresKGNodePropertiesRepository(self._session)
        return self._kg_node_properties_repository
    
    @property
    def kg_edge_properties(self):
        """Get KGEdgePropertiesRepository instance."""
        if self._kg_edge_properties_repository is None:
            from .repositories.postgres.kg_edge_properties_repository import PostgresKGEdgePropertiesRepository
            self._kg_edge_properties_repository = PostgresKGEdgePropertiesRepository(self._session)
        return self._kg_edge_properties_repository
    
    @property
    def proactive_analytics(self):
        """Get ProactiveAnalyticsRepository instance."""
        if self._proactive_analytics_repository is None:
            from .repositories.postgres.proactive_analytics_repository import PostgresProactiveAnalyticsRepository
            self._proactive_analytics_repository = PostgresProactiveAnalyticsRepository(self._session)
        return self._proactive_analytics_repository
    
    @property
    def proactive_reminder_clusters(self):
        """Get ProactiveReminderClustersRepository instance."""
        if self._proactive_reminder_clusters_repository is None:
            from .repositories.postgres.proactive_reminder_clusters_repository import PostgresProactiveReminderClustersRepository
            self._proactive_reminder_clusters_repository = PostgresProactiveReminderClustersRepository(self._session)
        return self._proactive_reminder_clusters_repository
    
    @property
    def auth_access_policies(self):
        """Get AuthAccessPoliciesRepository instance."""
        if self._auth_access_policies_repository is None:
            from .repositories.postgres.auth_access_policies_repository import PostgresAuthAccessPoliciesRepository
            self._auth_access_policies_repository = PostgresAuthAccessPoliciesRepository(self._session)
        return self._auth_access_policies_repository
    
    @property
    def user_skill_confidence(self):
        """Get UserSkillConfidenceRepository instance."""
        if self._user_skill_confidence_repository is None:
            from .repositories.postgres.user_skill_confidence_repository import PostgresUserSkillConfidenceRepository
            self._user_skill_confidence_repository = PostgresUserSkillConfidenceRepository(self._session)
        return self._user_skill_confidence_repository
    
    @property
    def executions(self):
        """Get ExecutionRepository instance."""
        if self._execution_repository is None:
            from .repositories.postgres.execution_repository import PostgresExecutionRepository
            self._execution_repository = PostgresExecutionRepository(self._session)
        return self._execution_repository
    
    @property
    def agency_execution_snapshots(self):
        """Get AgencyExecutionSnapshotsRepository instance."""
        if not hasattr(self, '_agency_execution_snapshots'):
            self._agency_execution_snapshots = None
        if self._agency_execution_snapshots is None:
            from .repositories.postgres.agency_execution_snapshots_repository import PostgresAgencyExecutionSnapshotsRepository
            self._agency_execution_snapshots = PostgresAgencyExecutionSnapshotsRepository(self._session)
        return self._agency_execution_snapshots
    
    @property
    def agency_goal_dependencies(self):
        """Get AgencyGoalDependenciesRepository instance."""
        if not hasattr(self, '_agency_goal_dependencies'):
            self._agency_goal_dependencies = None
        if self._agency_goal_dependencies is None:
            from .repositories.postgres.agency_goal_dependencies_repository import PostgresAgencyGoalDependenciesRepository
            self._agency_goal_dependencies = PostgresAgencyGoalDependenciesRepository(self._session)
        return self._agency_goal_dependencies
    
    @property
    def agency_goal_outcomes(self):
        """Get AgencyGoalOutcomesRepository instance."""
        if not hasattr(self, '_agency_goal_outcomes'):
            self._agency_goal_outcomes = None
        if self._agency_goal_outcomes is None:
            from .repositories.postgres.agency_goal_outcomes_repository import PostgresAgencyGoalOutcomesRepository
            self._agency_goal_outcomes = PostgresAgencyGoalOutcomesRepository(self._session)
        return self._agency_goal_outcomes
    
    @property
    def agency_goal_skill_executions(self):
        """Get AgencyGoalSkillExecutionsRepository instance."""
        if not hasattr(self, '_agency_goal_skill_executions'):
            self._agency_goal_skill_executions = None
        if self._agency_goal_skill_executions is None:
            from .repositories.postgres.agency_goal_skill_executions_repository import PostgresAgencyGoalSkillExecutionsRepository
            self._agency_goal_skill_executions = PostgresAgencyGoalSkillExecutionsRepository(self._session)
        return self._agency_goal_skill_executions
    
    @property
    def agency_intention_set(self):
        """Get AgencyIntentionSetRepository instance."""
        if not hasattr(self, '_agency_intention_set'):
            self._agency_intention_set = None
        if self._agency_intention_set is None:
            from .repositories.postgres.agency_intention_set_repository import PostgresAgencyIntentionSetRepository
            self._agency_intention_set = PostgresAgencyIntentionSetRepository(self._session)
        return self._agency_intention_set
    
    @property
    def agency_plan_executions(self):
        """Get AgencyPlanExecutionsRepository instance."""
        if not hasattr(self, '_agency_plan_executions'):
            self._agency_plan_executions = None
        if self._agency_plan_executions is None:
            from .repositories.postgres.agency_plan_executions_repository import PostgresAgencyPlanExecutionsRepository
            self._agency_plan_executions = PostgresAgencyPlanExecutionsRepository(self._session)
        return self._agency_plan_executions
    
    @property
    def agency_reflection_runs(self):
        """Get AgencyReflectionRunsRepository instance."""
        if not hasattr(self, '_agency_reflection_runs'):
            self._agency_reflection_runs = None
        if self._agency_reflection_runs is None:
            from .repositories.postgres.agency_reflection_runs_repository import PostgresAgencyReflectionRunsRepository
            self._agency_reflection_runs = PostgresAgencyReflectionRunsRepository(self._session)
        return self._agency_reflection_runs
    
    @property
    def agency_self_model(self):
        """Get AgencySelfModelRepository instance."""
        if not hasattr(self, '_agency_self_model'):
            self._agency_self_model = None
        if self._agency_self_model is None:
            from .repositories.postgres.agency_self_model_repository import PostgresAgencySelfModelRepository
            self._agency_self_model = PostgresAgencySelfModelRepository(self._session)
        return self._agency_self_model
    
    @property
    def agency_skill_gaps(self):
        """Get AgencySkillGapsRepository instance."""
        if not hasattr(self, '_agency_skill_gaps'):
            self._agency_skill_gaps = None
        if self._agency_skill_gaps is None:
            from .repositories.postgres.agency_skill_gaps_repository import PostgresAgencySkillGapsRepository
            self._agency_skill_gaps = PostgresAgencySkillGapsRepository(self._session)
        return self._agency_skill_gaps
    
    @property
    def agency_skill_executions(self):
        """Get AgencySkillExecutionsRepository instance."""
        if not hasattr(self, '_agency_skill_executions'):
            self._agency_skill_executions = None
        if self._agency_skill_executions is None:
            from .repositories.postgres.agency_skill_executions_repository import PostgresAgencySkillExecutionsRepository
            self._agency_skill_executions = PostgresAgencySkillExecutionsRepository(self._session)
        return self._agency_skill_executions
    
    @property
    def agency_skill_learning_data(self):
        """Get AgencySkillLearningDataRepository instance."""
        if not hasattr(self, '_agency_skill_learning_data'):
            self._agency_skill_learning_data = None
        if self._agency_skill_learning_data is None:
            from .repositories.postgres.agency_skill_learning_data_repository import PostgresAgencySkillLearningDataRepository
            self._agency_skill_learning_data = PostgresAgencySkillLearningDataRepository(self._session)
        return self._agency_skill_learning_data
    
    @property
    def agency_step_executions(self):
        """Get AgencyStepExecutionsRepository instance."""
        if not hasattr(self, '_agency_step_executions'):
            self._agency_step_executions = None
        if self._agency_step_executions is None:
            from .repositories.postgres.agency_step_executions_repository import PostgresAgencyStepExecutionsRepository
            self._agency_step_executions = PostgresAgencyStepExecutionsRepository(self._session)
        return self._agency_step_executions
    
    @property
    def system_health_checks(self):
        """Get SystemHealthCheckRepository instance."""
        if self._system_health_checks_repository is None:
            from .repositories.system_health_checks import SystemHealthCheckRepository
            self._system_health_checks_repository = SystemHealthCheckRepository(self._session)
        return self._system_health_checks_repository
    
    @property
    def system_issues(self):
        """Get SystemIssueRepository instance."""
        if self._system_issues_repository is None:
            from .repositories.system_issues import SystemIssueRepository
            self._system_issues_repository = SystemIssueRepository(self._session)
        return self._system_issues_repository
    
    @property
    def policy_rules(self):
        """Get PolicyRuleRepository instance."""
        if self._policy_rules_repository is None:
            from .repositories.postgres.policy_rule_repository import PostgresPolicyRuleRepository
            self._policy_rules_repository = PostgresPolicyRuleRepository(self._session)
        return self._policy_rules_repository


@asynccontextmanager
async def get_uow(session_factory: async_sessionmaker):
    """
    Context manager for Unit of Work.
    
    Usage:
        async with get_uow(session_factory) as uow:
            user = await uow.users.create(user_data)
            await uow.commit()
    
    Args:
        session_factory: SQLAlchemy async session factory
        
    Yields:
        UnitOfWork instance
    """
    uow = UnitOfWork(session_factory)
    async with uow:
        yield uow
