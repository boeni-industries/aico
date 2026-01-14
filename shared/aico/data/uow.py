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
        self._user_proactive_preferences_repository = None
        self._device_repository = None
        self._session_repository = None
        self._credentials_repository = None
        self._agency_event_repository = None
        self._agency_events_log_repository = None
        self._agency_followups_repository = None
        self._agency_reflection_notes_repository = None
        self._agency_reminders_repository = None
        self._goal_repository = None
        self._plan_repository = None
        self._lesson_repository = None
        self._policy_repository = None
        self._kg_node_repository = None
        self._kg_edge_repository = None
        self._ams_behavioral_skills_repository = None
        self._trajectory_repository = None
        self._feedback_repository = None
        self._scheduler_task_repository = None
        self._task_execution_repository = None
        self._conversation_initiation_repository = None
        self._system_event_repository = None
        self._emotion_state_repository = None
    
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
        """Get SchedulerTaskRepository instance."""
        if self._scheduler_task_repository is None:
            from .repositories.postgres.scheduler_task_repository import PostgresSchedulerTaskRepository
            self._scheduler_task_repository = PostgresSchedulerTaskRepository(self._session)
        return self._scheduler_task_repository
    
    @property
    def conversation_initiations(self):
        """Get ConversationInitiationRepository instance."""
        if self._conversation_initiation_repository is None:
            from .repositories.postgres.conversation_initiation_repository import PostgresConversationInitiationRepository
            self._conversation_initiation_repository = PostgresConversationInitiationRepository(self._session)
        return self._conversation_initiation_repository
    
    @property
    def system_events(self):
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
    def executions(self):
        """Get ExecutionRepository instance."""
        if self._execution_repository is None:
            from .repositories.postgres.execution_repository import PostgresExecutionRepository
            self._execution_repository = PostgresExecutionRepository(self._session)
        return self._execution_repository


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
