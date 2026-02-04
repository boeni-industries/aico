"""
Comprehensive Tests for Phase 6.6: Behavioral Feedback Integration

Tests skill execution tracking, behavioral feedback with outcomes,
automatic outcome detection, user feedback collection, and analytics.
"""

import pytest
from datetime import datetime, timedelta, UTC
from unittest.mock import Mock
import json

from aico.ai.agency.behavioral_feedback import (
    BehavioralFeedbackService,
    SkillOutcome,
    FeedbackType,
    SkillExecution,
    FeedbackRequest
)


# ============================================================================
# SKILL EXECUTION TRACKING TESTS
# ============================================================================

class TestSkillExecutionTracking:
    """Test skill execution tracking functionality."""
    
    @pytest.fixture
    def db(self, test_db):
        """Use test database fixture."""
        return test_db

    @pytest.fixture
    async def session_factory(self):
        from aico.data.postgres.connection import get_session_factory

        return await get_session_factory()

    @pytest.fixture
    async def uow(self, session_factory):
        from aico.data.uow import UnitOfWork

        async with UnitOfWork(session_factory) as uow:
            yield uow
            await uow.rollback()

    @pytest.fixture
    def agency_service(self, uow):
        from aico.services.agency_service import AgencyService

        return AgencyService(uow)

    @pytest.fixture
    async def session_factory(self):
        from aico.data.postgres.connection import get_session_factory

        return await get_session_factory()

    @pytest.fixture
    async def uow(self, session_factory):
        from aico.data.uow import UnitOfWork

        async with UnitOfWork(session_factory) as uow:
            yield uow
            await uow.rollback()

    @pytest.fixture
    def agency_service(self, uow):
        from aico.services.agency_service import AgencyService

        return AgencyService(uow)

    @pytest.fixture
    async def session_factory(self):
        from aico.data.postgres.connection import get_session_factory

        return await get_session_factory()

    @pytest.fixture
    async def uow(self, session_factory):
        from aico.data.uow import UnitOfWork

        async with UnitOfWork(session_factory) as uow:
            yield uow
            await uow.rollback()

    @pytest.fixture
    def agency_service(self, uow):
        from aico.services.agency_service import AgencyService

        return AgencyService(uow)
    
    @pytest.fixture
    def feedback_service(self, agency_service):
        """Create behavioral feedback service."""
        return BehavioralFeedbackService(agency_service)
    
    @pytest.fixture
    def test_skill_id(self, db):
        """Create a test skill."""
        skill_id = "test-skill-1"
        with db.cursor() as cursor:
            cursor.execute(
                """INSERT INTO ams_behavioral_skills 
                   (skill_id, skill_name, skill_type, trigger_context, procedure_template, dimension_vector, created_at, updated_at)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                   ON CONFLICT (skill_id) DO NOTHING""",
                (
                    skill_id,
                    "Test Skill",
                    "base",
                    '{"intent": ["test"], "time_of_day": "any"}',
                    "test_template",
                    '[0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5]',
                    datetime.now(UTC).isoformat(),
                    datetime.now(UTC).isoformat(),
                ),
            )
        db.commit()
        yield skill_id
        # Cleanup after test
        with db.cursor() as cursor:
            cursor.execute("DELETE FROM ams_behavioral_skills WHERE skill_id = %s", (skill_id,))
        db.commit()
    
    @pytest.mark.asyncio
    async def test_record_skill_execution_success(self, feedback_service, test_user, test_skill_id, db):
        """Test recording a successful skill execution."""
        execution_id = await feedback_service.record_skill_execution(
            execution_id="",
            skill_id=test_skill_id,
            user_id=test_user,
            outcome=SkillOutcome.SUCCESS,
            execution_time_ms=150,
            context={"test": "data"}
        )
        
        assert execution_id is not None
        assert len(execution_id) > 0
        
        # Verify in database
        with db.cursor() as cursor:
            cursor.execute(
                "SELECT * FROM agency_skill_executions WHERE execution_id = %s",
                (execution_id,),
            )
            row = cursor.fetchone()
        
        assert row is not None
        assert row["skill_id"] == test_skill_id
        assert row["user_id"] == test_user
        assert row["outcome"] == "success"
        assert row["execution_time_ms"] == 150
    
    @pytest.mark.asyncio
    async def test_record_skill_execution_failure(self, feedback_service, test_user, test_skill_id, db):
        """Test recording a failed skill execution."""
        execution_id = await feedback_service.record_skill_execution(
            execution_id="",
            skill_id=test_skill_id,
            user_id=test_user,
            outcome=SkillOutcome.FAILURE,
            error_message="Test error",
            execution_time_ms=50
        )
        
        assert execution_id is not None

        with db.cursor() as cursor:
            cursor.execute(
                "SELECT * FROM agency_skill_executions WHERE execution_id = %s",
                (execution_id,),
            )
            row = cursor.fetchone()
        
        assert row["outcome"] == "failure"
        assert row["error_message"] == "Test error"
    
    @pytest.mark.asyncio
    async def test_record_skill_execution_with_goal(self, feedback_service, test_user, test_skill_id, db):
        """Test recording skill execution linked to a goal."""
        # Create test goal
        goal_id = "test-goal-exec-1"
        with db.cursor() as cursor:
            cursor.execute(
                """INSERT INTO agency_goals 
                   (goal_id, user_id, origin, goal_type, title, description, priority, status, created_at, updated_at)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                   ON CONFLICT (goal_id) DO NOTHING""",
                (
                    goal_id,
                    test_user,
                    "user",
                    "work",
                    "Test goal",
                    "Test",
                    "normal",
                    "active",
                    datetime.now(UTC).isoformat(),
                    datetime.now(UTC).isoformat(),
                ),
            )
        db.commit()
        
        execution_id = await feedback_service.record_skill_execution(
            execution_id="",
            skill_id=test_skill_id,
            user_id=test_user,
            outcome=SkillOutcome.SUCCESS,
            goal_id=goal_id
        )
        
        with db.cursor() as cursor:
            cursor.execute(
                "SELECT * FROM agency_skill_executions WHERE execution_id = %s",
                (execution_id,),
            )
            row = cursor.fetchone()
        
        assert row["goal_id"] == goal_id
    
    @pytest.mark.asyncio
    async def test_link_execution_to_goal(self, feedback_service, test_user, test_skill_id, db):
        """Test linking an execution to a goal."""
        # Create goal
        goal_id = "test-goal-link-1"
        with db.cursor() as cursor:
            cursor.execute(
                """INSERT INTO agency_goals 
                   (goal_id, user_id, origin, goal_type, title, description, priority, status, created_at, updated_at)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                   ON CONFLICT (goal_id) DO NOTHING""",
                (
                    goal_id,
                    test_user,
                    "user",
                    "work",
                    "Test goal",
                    "Test",
                    "normal",
                    "active",
                    datetime.now(UTC).isoformat(),
                    datetime.now(UTC).isoformat(),
                ),
            )
        db.commit()
        
        # Record execution
        execution_id = await feedback_service.record_skill_execution(
            execution_id="",
            skill_id=test_skill_id,
            user_id=test_user,
            outcome=SkillOutcome.SUCCESS
        )
        
        # Link to goal
        await feedback_service.link_execution_to_goal(
            goal_id=goal_id,
            skill_id=test_skill_id,
            execution_id=execution_id,
            execution_order=1
        )
        
        # Verify link
        with db.cursor() as cursor:
            cursor.execute(
                "SELECT * FROM agency_goal_skill_executions WHERE execution_id = %s",
                (execution_id,),
            )
            row = cursor.fetchone()
        
        assert row is not None
        assert row["goal_id"] == goal_id
        assert row["execution_order"] == 1
    
    @pytest.mark.asyncio
    async def test_get_goal_executions(self, feedback_service, test_user, test_skill_id, db):
        """Test retrieving all executions for a goal."""
        # Clean up first
        goal_id = "test-goal-get-exec-1"
        with db.cursor() as cursor:
            cursor.execute("DELETE FROM agency_goal_skill_executions WHERE goal_id = %s", (goal_id,))
            cursor.execute("DELETE FROM agency_skill_executions WHERE goal_id = %s", (goal_id,))
            cursor.execute("DELETE FROM agency_goals WHERE goal_id = %s", (goal_id,))
        db.commit()
        
        # Create goal
        with db.cursor() as cursor:
            cursor.execute(
                """INSERT INTO agency_goals 
                   (goal_id, user_id, origin, goal_type, title, description, priority, status, created_at, updated_at)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                   ON CONFLICT (goal_id) DO NOTHING""",
                (
                    goal_id,
                    test_user,
                    "user",
                    "work",
                    "Test goal",
                    "Test",
                    "normal",
                    "active",
                    datetime.now(UTC).isoformat(),
                    datetime.now(UTC).isoformat(),
                ),
            )
        db.commit()
        
        # Record multiple executions
        exec_ids = []
        for i in range(3):
            exec_id = await feedback_service.record_skill_execution(
                execution_id="",
                skill_id=test_skill_id,
                user_id=test_user,
                goal_id=goal_id,
                outcome=SkillOutcome.SUCCESS if i < 2 else SkillOutcome.FAILURE,
            )
            await feedback_service.link_execution_to_goal(
                goal_id=goal_id,
                skill_id=test_skill_id,
                execution_id=exec_id,
                execution_order=i
            )
            exec_ids.append(exec_id)
        
        # Get executions
        executions = await feedback_service.get_goal_executions(goal_id)
        
        assert len(executions) == 3
        outcomes = [e.outcome for e in executions]
        assert outcomes.count(SkillOutcome.SUCCESS) == 2
        assert outcomes.count(SkillOutcome.FAILURE) == 1


# ============================================================================
# BEHAVIORAL FEEDBACK TESTS
# ============================================================================

class TestBehavioralFeedback:
    """Test behavioral feedback recording with outcomes."""
    
    @pytest.fixture
    def db(self, test_db):
        """Use test database fixture."""
        return test_db

    @pytest.fixture
    async def session_factory(self):
        from aico.data.postgres.connection import get_session_factory

        return await get_session_factory()

    @pytest.fixture
    async def uow(self, session_factory):
        from aico.data.uow import UnitOfWork

        async with UnitOfWork(session_factory) as uow:
            yield uow
            await uow.rollback()

    @pytest.fixture
    def agency_service(self, uow):
        from aico.services.agency_service import AgencyService

        return AgencyService(uow)
    
    @pytest.fixture
    def feedback_service(self, agency_service):
        """Create behavioral feedback service."""
        return BehavioralFeedbackService(agency_service)
    
    @pytest.fixture
    def test_skill_id(self, db):
        """Create a test skill."""
        skill_id = "test-skill-feedback-1"
        with db.cursor() as cursor:
            cursor.execute(
                """INSERT INTO ams_behavioral_skills 
                   (skill_id, skill_name, skill_type, trigger_context, procedure_template, dimension_vector, created_at, updated_at)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                   ON CONFLICT (skill_id) DO NOTHING""",
                (
                    skill_id,
                    "Test Skill",
                    "base",
                    '{"intent": ["test"], "time_of_day": "any"}',
                    "test_template",
                    '[0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5]',
                    datetime.now(UTC).isoformat(),
                    datetime.now(UTC).isoformat(),
                ),
            )
        db.commit()
        yield skill_id
        # Cleanup after test
        with db.cursor() as cursor:
            cursor.execute("DELETE FROM ams_behavioral_skills WHERE skill_id = %s", (skill_id,))
        db.commit()
    
    @pytest.mark.asyncio
    async def test_record_behavioral_feedback_with_outcome(self, feedback_service, test_user, test_skill_id, db):
        """Test recording behavioral feedback with outcome."""
        feedback_id = await feedback_service.record_behavioral_feedback(
            user_id=test_user,
            message_id="msg-1",
            skill_id=test_skill_id,
            reward=1,
            outcome=SkillOutcome.SUCCESS,
            reason="Worked well",
            execution_time_ms=200,
            user_satisfaction=0.9
        )
        
        assert feedback_id is not None
        
        # Verify in database
        with db.cursor() as cursor:
            cursor.execute(
                "SELECT * FROM ams_behavioral_feedback WHERE feedback_id = %s",
                (feedback_id,),
            )
            row = cursor.fetchone()
        
        assert row is not None
        assert row["reward"] == 1
        assert row["outcome"] == "success"
        assert row["execution_time_ms"] == 200
        assert row["user_satisfaction"] == 0.9
    
    @pytest.mark.asyncio
    async def test_record_behavioral_feedback_negative(self, feedback_service, test_user, test_skill_id, db):
        """Test recording negative behavioral feedback."""
        feedback_id = await feedback_service.record_behavioral_feedback(
            user_id=test_user,
            message_id="msg-2",
            skill_id=test_skill_id,
            reward=-1,
            outcome=SkillOutcome.FAILURE,
            reason="Did not work",
            user_satisfaction=0.2
        )

        with db.cursor() as cursor:
            cursor.execute(
                "SELECT * FROM ams_behavioral_feedback WHERE feedback_id = %s",
                (feedback_id,),
            )
            row = cursor.fetchone()
        
        assert row["reward"] == -1
        assert row["outcome"] == "failure"
        assert row["user_satisfaction"] == 0.2
    
    @pytest.mark.asyncio
    async def test_record_behavioral_feedback_with_context(self, feedback_service, test_user, test_skill_id, db):
        """Test recording feedback with execution context."""
        context = {
            "input": "test input",
            "parameters": {"param1": "value1"},
            "environment": "test"
        }
        
        feedback_id = await feedback_service.record_behavioral_feedback(
            user_id=test_user,
            message_id="msg-3",
            skill_id=test_skill_id,
            reward=1,
            outcome=SkillOutcome.SUCCESS,
            context=context
        )

        with db.cursor() as cursor:
            cursor.execute(
                "SELECT * FROM ams_behavioral_feedback WHERE feedback_id = %s",
                (feedback_id,),
            )
            row = cursor.fetchone()
        
        stored_context = json.loads(row["context_json"])
        assert stored_context == context
    
    @pytest.mark.asyncio
    async def test_record_behavioral_feedback_invalid_reward(self, feedback_service, test_user, test_skill_id):
        """Test that invalid reward values are rejected."""
        with pytest.raises(ValueError, match="Reward must be -1, 0, or 1"):
            await feedback_service.record_behavioral_feedback(
                user_id=test_user,
                message_id="msg-4",
                skill_id=test_skill_id,
                reward=5,  # Invalid
                outcome=SkillOutcome.SUCCESS
            )


# ============================================================================
# OUTCOME DETECTION TESTS
# ============================================================================

class TestOutcomeDetection:
    """Test automatic outcome detection."""
    
    @pytest.fixture
    def db(self, test_db):
        """Use test database fixture."""
        return test_db

    @pytest.fixture
    async def session_factory(self):
        from aico.data.postgres.connection import get_session_factory

        return await get_session_factory()

    @pytest.fixture
    async def uow(self, session_factory):
        from aico.data.uow import UnitOfWork

        async with UnitOfWork(session_factory) as uow:
            yield uow
            await uow.rollback()

    @pytest.fixture
    def agency_service(self, uow):
        from aico.services.agency_service import AgencyService

        return AgencyService(uow)
    
    @pytest.fixture
    def feedback_service(self, agency_service):
        """Create behavioral feedback service."""
        return BehavioralFeedbackService(agency_service)
    
    @pytest.fixture
    def test_skill_id(self, db):
        """Create a test skill."""
        skill_id = "test-skill-outcome-1"
        with db.cursor() as cursor:
            cursor.execute(
                """INSERT INTO ams_behavioral_skills 
                   (skill_id, skill_name, skill_type, trigger_context, procedure_template, dimension_vector, created_at, updated_at)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                   ON CONFLICT (skill_id) DO NOTHING""",
                (
                    skill_id,
                    "Test Skill",
                    "base",
                    '{"intent": ["test"], "time_of_day": "any"}',
                    "test_template",
                    '[0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5]',
                    datetime.now(UTC).isoformat(),
                    datetime.now(UTC).isoformat(),
                ),
            )
        db.commit()
        yield skill_id
        # Cleanup after test
        with db.cursor() as cursor:
            cursor.execute("DELETE FROM ams_behavioral_skills WHERE skill_id = %s", (skill_id,))
        db.commit()
    
    @pytest.mark.asyncio
    async def test_detect_outcome_from_execution(self, feedback_service, test_user, test_skill_id):
        """Test detecting outcome from execution record."""
        execution_id = await feedback_service.record_skill_execution(
            execution_id="",
            skill_id=test_skill_id,
            user_id=test_user,
            outcome=SkillOutcome.SUCCESS,
        )

        detected_outcome = await feedback_service.detect_outcome_from_execution(execution_id)
        
        assert detected_outcome == SkillOutcome.SUCCESS
    
    @pytest.mark.asyncio
    async def test_detect_outcome_nonexistent_execution(self, feedback_service):
        """Test detecting outcome for nonexistent execution."""
        outcome = await feedback_service.detect_outcome_from_execution("nonexistent-id")
        
        assert outcome is None
    
    def test_infer_outcome_from_reward_positive(self, feedback_service):
        """Test inferring outcome from positive reward."""
        outcome = feedback_service.infer_outcome_from_reward(1)
        
        assert outcome == SkillOutcome.SUCCESS
    
    def test_infer_outcome_from_reward_negative(self, feedback_service):
        """Test inferring outcome from negative reward."""
        outcome = feedback_service.infer_outcome_from_reward(-1)
        
        assert outcome == SkillOutcome.FAILURE
    
    def test_infer_outcome_from_reward_neutral(self, feedback_service):
        """Test inferring outcome from neutral reward."""
        outcome = feedback_service.infer_outcome_from_reward(0)
        
        assert outcome == SkillOutcome.PARTIAL
    
    @pytest.mark.asyncio
    async def test_update_feedback_with_outcome(self, feedback_service, test_user, test_skill_id, db):
        """Test updating existing feedback with detected outcome."""
        # Record feedback without outcome
        feedback_id = await feedback_service.record_behavioral_feedback(
            user_id=test_user,
            message_id="msg-5",
            skill_id=test_skill_id,
            reward=1
        )
        
        # Update with outcome
        await feedback_service.update_feedback_with_outcome(
            feedback_id=feedback_id,
            outcome=SkillOutcome.SUCCESS
        )
        
        # Verify update
        with db.cursor() as cursor:
            cursor.execute(
                "SELECT * FROM ams_behavioral_feedback WHERE feedback_id = %s",
                (feedback_id,),
            )
            row = cursor.fetchone()
        
        assert row["outcome"] == "success"


# ============================================================================
# USER FEEDBACK COLLECTION TESTS
# ============================================================================

class TestUserFeedbackCollection:
    """Test user feedback request and response system."""

    @pytest.fixture
    def db(self, test_db):
        """Use test database fixture."""
        return test_db

    @pytest.fixture
    async def session_factory(self):
        from aico.data.postgres.connection import get_session_factory

        return await get_session_factory()

    @pytest.fixture
    async def uow(self, session_factory):
        from aico.data.uow import UnitOfWork

        async with UnitOfWork(session_factory) as uow:
            yield uow
            await uow.rollback()

    @pytest.fixture
    def agency_service(self, uow):
        from aico.services.agency_service import AgencyService

        return AgencyService(uow)

    @pytest.fixture
    def feedback_service(self, agency_service):
        """Create behavioral feedback service."""
        return BehavioralFeedbackService(agency_service)

    @pytest.mark.asyncio
    async def test_create_feedback_request(self, feedback_service, test_user, db):
        """Test creating a user feedback request."""
        request_id = await feedback_service.create_feedback_request(
            user_id=test_user,
            feedback_type=FeedbackType.SATISFACTION,
            question="How satisfied are you with this result?",
        )

        assert request_id is not None

        with db.cursor() as cursor:
            cursor.execute(
                "SELECT * FROM user_feedback_requests WHERE request_id = %s",
                (request_id,),
            )
            row = cursor.fetchone()

        assert row is not None
        assert row["user_id"] == test_user
        assert row["feedback_type"] == "satisfaction"
        assert row["responded_at"] is None
    
    @pytest.mark.asyncio
    async def test_create_feedback_request_with_goal(self, feedback_service, test_user, db):
        """Test creating feedback request linked to a goal."""
        # Create goal
        goal_id = "test-goal-feedback-1"
        with db.cursor() as cursor:
            cursor.execute(
                """INSERT INTO agency_goals 
                   (goal_id, user_id, origin, goal_type, title, description, priority, status, created_at, updated_at)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                   ON CONFLICT (goal_id) DO NOTHING""",
                (
                    goal_id,
                    test_user,
                    "user",
                    "work",
                    "Test goal",
                    "Test",
                    "normal",
                    "active",
                    datetime.now(UTC).isoformat(),
                    datetime.now(UTC).isoformat(),
                ),
            )
        db.commit()
        
        request_id = await feedback_service.create_feedback_request(
            user_id=test_user,
            feedback_type=FeedbackType.QUALITY,
            question="Was this goal helpful?",
            goal_id=goal_id
        )

        with db.cursor() as cursor:
            cursor.execute(
                "SELECT * FROM user_feedback_requests WHERE request_id = %s",
                (request_id,),
            )
            row = cursor.fetchone()
        
        assert row["goal_id"] == goal_id
    
    @pytest.mark.asyncio
    async def test_record_feedback_response_text(self, feedback_service, test_user, db):
        """Test recording text response to feedback request."""
        request_id = await feedback_service.create_feedback_request(
            user_id=test_user,
            feedback_type=FeedbackType.HELPFULNESS,
            question="What could be improved?"
        )
        
        await feedback_service.record_feedback_response(
            request_id=request_id,
            response="It was very helpful, thanks!"
        )

        with db.cursor() as cursor:
            cursor.execute(
                "SELECT * FROM user_feedback_requests WHERE request_id = %s",
                (request_id,),
            )
            row = cursor.fetchone()
        
        assert row["response"] == "It was very helpful, thanks!"
        assert row["responded_at"] is not None
    
    @pytest.mark.asyncio
    async def test_record_feedback_response_rating(self, feedback_service, test_user, db):
        """Test recording numeric rating response."""
        request_id = await feedback_service.create_feedback_request(
            user_id=test_user,
            feedback_type=FeedbackType.SATISFACTION,
            question="Rate your satisfaction (1-5)"
        )
        
        await feedback_service.record_feedback_response(
            request_id=request_id,
            rating=4.5
        )

        with db.cursor() as cursor:
            cursor.execute(
                "SELECT * FROM user_feedback_requests WHERE request_id = %s",
                (request_id,),
            )
            row = cursor.fetchone()
        
        assert row["rating"] == 4.5
    
    @pytest.mark.asyncio
    async def test_get_pending_feedback_requests(self, feedback_service, test_user):
        """Test retrieving pending feedback requests."""
        # Create multiple requests
        for i in range(3):
            await feedback_service.create_feedback_request(
                user_id=test_user,
                feedback_type=FeedbackType.SATISFACTION,
                question=f"Question {i}"
            )
        
        # Respond to one
        requests = await feedback_service.get_pending_feedback_requests(test_user)
        if requests:
            await feedback_service.record_feedback_response(
                request_id=requests[0].request_id,
                rating=5.0
            )
        
        # Get pending (should be 2 now)
        pending = await feedback_service.get_pending_feedback_requests(test_user)
        
        assert len(pending) == 2
        for req in pending:
            assert req.responded_at is None


# ============================================================================
# ANALYTICS TESTS
# ============================================================================

class TestAnalytics:
    """Test analytics and reporting functionality."""
    
    @pytest.fixture
    def db(self, test_db):
        """Use test database fixture."""
        return test_db

    @pytest.fixture
    async def session_factory(self):
        from aico.data.postgres.connection import get_session_factory

        return await get_session_factory()

    @pytest.fixture
    async def uow(self, session_factory):
        from aico.data.uow import UnitOfWork

        async with UnitOfWork(session_factory) as uow:
            yield uow
            await uow.rollback()

    @pytest.fixture
    def agency_service(self, uow):
        from aico.services.agency_service import AgencyService

        return AgencyService(uow)
    
    @pytest.fixture
    def feedback_service(self, agency_service):
        """Create behavioral feedback service."""
        return BehavioralFeedbackService(agency_service)
    
    @pytest.fixture
    def test_skill_id(self, db):
        """Create a test skill."""
        skill_id = "test-skill-analytics-1"
        with db.cursor() as cursor:
            cursor.execute(
                """INSERT INTO ams_behavioral_skills 
                   (skill_id, skill_name, skill_type, trigger_context, procedure_template, dimension_vector, created_at, updated_at)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                   ON CONFLICT (skill_id) DO NOTHING""",
                (
                    skill_id,
                    "Test Skill",
                    "base",
                    '{"intent": ["test"], "time_of_day": "any"}',
                    "test_template",
                    '[0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5]',
                    datetime.now(UTC).isoformat(),
                    datetime.now(UTC).isoformat(),
                ),
            )
        db.commit()
        yield skill_id
        # Cleanup after test
        with db.cursor() as cursor:
            cursor.execute("DELETE FROM ams_behavioral_skills WHERE skill_id = %s", (skill_id,))
        db.commit()
    
    @pytest.mark.asyncio
    async def test_get_skill_success_rate(self, feedback_service, test_user, test_skill_id, db):
        """Test calculating skill success rate."""
        with db.cursor() as cursor:
            cursor.execute("DELETE FROM ams_behavioral_feedback WHERE skill_id = %s", (test_skill_id,))
        db.commit()
        
        # Record multiple feedback entries
        for i in range(10):
            outcome = SkillOutcome.SUCCESS if i < 7 else SkillOutcome.FAILURE
            await feedback_service.record_behavioral_feedback(
                user_id=test_user,
                message_id=f"msg-analytics-{i}",
                skill_id=test_skill_id,
                reward=1 if outcome == SkillOutcome.SUCCESS else -1,
                outcome=outcome,
            )

        with db.cursor() as cursor:
            cursor.execute(
                "SELECT COUNT(*) AS count FROM ams_behavioral_feedback WHERE skill_id = %s AND user_id = %s",
                (test_skill_id, test_user),
            )
            count_row = cursor.fetchone()
        assert count_row["count"] == 10, f"Expected 10 feedback rows, got {count_row['count']}"

        success_rate = await feedback_service.get_skill_success_rate(
            skill_id=test_skill_id,
            user_id=test_user,
            days=30
        )
        
        assert success_rate == pytest.approx(0.7, abs=0.01)
    
    @pytest.mark.asyncio
    async def test_get_skill_success_rate_no_data(self, feedback_service, db):
        """Test success rate with no data returns neutral."""
        with db.cursor() as cursor:
            cursor.execute("DELETE FROM ams_behavioral_feedback WHERE skill_id = %s", ("nonexistent-skill",))
        db.commit()
        
        success_rate = await feedback_service.get_skill_success_rate(
            skill_id="nonexistent-skill",
            days=30
        )
        
        assert success_rate == 0.5
    
    @pytest.mark.asyncio
    async def test_get_user_satisfaction_trend(self, feedback_service, test_user):
        """Test getting user satisfaction trend over time."""
        # Create feedback requests with ratings
        for i in range(5):
            request_id = await feedback_service.create_feedback_request(
                user_id=test_user,
                feedback_type=FeedbackType.SATISFACTION,
                question="Rate satisfaction"
            )
            await feedback_service.record_feedback_response(
                request_id=request_id,
                rating=float(i + 1)  # Ratings 1-5
            )
        
        trend = await feedback_service.get_user_satisfaction_trend(
            user_id=test_user,
            days=30
        )
        
        assert len(trend) > 0
        # Should have aggregated ratings
        assert all("avg_rating" in point for point in trend)
        assert all("count" in point for point in trend)


# ============================================================================
# INTEGRATION TESTS
# ============================================================================

class TestBehavioralFeedbackIntegration:
    """Test end-to-end behavioral feedback integration."""
    
    @pytest.fixture
    def db(self, test_db):
        """Use test database fixture."""
        return test_db

    @pytest.fixture
    async def session_factory(self):
        from aico.data.postgres.connection import get_session_factory

        return await get_session_factory()

    @pytest.fixture
    async def uow(self, session_factory):
        from aico.data.uow import UnitOfWork

        async with UnitOfWork(session_factory) as uow:
            yield uow
            await uow.rollback()

    @pytest.fixture
    def agency_service(self, uow):
        from aico.services.agency_service import AgencyService

        return AgencyService(uow)
    
    @pytest.fixture
    def feedback_service(self, agency_service):
        """Create behavioral feedback service."""
        return BehavioralFeedbackService(agency_service)
    
    @pytest.fixture
    def test_skill_id(self, db):
        """Create a test skill."""
        skill_id = "test-skill-integration-1"
        with db.cursor() as cursor:
            cursor.execute(
                """INSERT INTO ams_behavioral_skills 
                   (skill_id, skill_name, skill_type, trigger_context, procedure_template, dimension_vector, created_at, updated_at)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                   ON CONFLICT (skill_id) DO NOTHING""",
                (
                    skill_id,
                    "Test Skill",
                    "base",
                    '{"intent": ["test"], "time_of_day": "any"}',
                    "test_template",
                    '[0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5]',
                    datetime.now(UTC).isoformat(),
                    datetime.now(UTC).isoformat(),
                ),
            )
        db.commit()
        yield skill_id
        # Cleanup after test
        with db.cursor() as cursor:
            cursor.execute("DELETE FROM ams_behavioral_skills WHERE skill_id = %s", (skill_id,))
        db.commit()
    
    @pytest.mark.asyncio
    async def test_complete_feedback_loop(self, feedback_service, test_user, test_skill_id, db):
        """Test complete feedback loop from execution to user feedback."""
        # Clean up first
        goal_id = "test-goal-complete-1"
        with db.cursor() as cursor:
            cursor.execute("DELETE FROM agency_goal_skill_executions WHERE goal_id = %s", (goal_id,))
            cursor.execute("DELETE FROM agency_skill_executions WHERE goal_id = %s", (goal_id,))
            cursor.execute("DELETE FROM agency_goals WHERE goal_id = %s", (goal_id,))
        db.commit()
        
        # 1. Create goal
        with db.cursor() as cursor:
            cursor.execute(
                """INSERT INTO agency_goals 
                   (goal_id, user_id, origin, goal_type, title, description, priority, status, created_at, updated_at)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                   ON CONFLICT (goal_id) DO NOTHING""",
                (
                    goal_id,
                    test_user,
                    "user",
                    "work",
                    "Test goal",
                    "Test",
                    "normal",
                    "active",
                    datetime.now(UTC).isoformat(),
                    datetime.now(UTC).isoformat(),
                ),
            )
        db.commit()
        
        # 2. Record skill execution
        execution_id = await feedback_service.record_skill_execution(
            execution_id="",
            skill_id=test_skill_id,
            user_id=test_user,
            outcome=SkillOutcome.SUCCESS,
            execution_time_ms=250,
            goal_id=goal_id
        )
        
        # 3. Link to goal
        await feedback_service.link_execution_to_goal(
            goal_id=goal_id,
            skill_id=test_skill_id,
            execution_id=execution_id
        )
        
        # 4. Record behavioral feedback
        feedback_id = await feedback_service.record_behavioral_feedback(
            user_id=test_user,
            message_id="msg-complete-1",
            skill_id=test_skill_id,
            reward=1,
            outcome=SkillOutcome.SUCCESS,
            execution_time_ms=250
        )
        
        # 5. Create user feedback request
        request_id = await feedback_service.create_feedback_request(
            user_id=test_user,
            feedback_type=FeedbackType.SATISFACTION,
            question="How satisfied are you?",
            goal_id=goal_id,
            skill_id=test_skill_id,
            execution_id=execution_id
        )
        
        # 6. User responds
        await feedback_service.record_feedback_response(
            request_id=request_id,
            rating=4.5,
            response="Very satisfied!"
        )
        
        # Verify complete loop
        executions = await feedback_service.get_goal_executions(goal_id)
        assert len(executions) == 1
        assert executions[0].outcome == SkillOutcome.SUCCESS

        with db.cursor() as cursor:
            cursor.execute(
                "SELECT * FROM ams_behavioral_feedback WHERE feedback_id = %s",
                (feedback_id,),
            )
            feedback_row = cursor.fetchone()
            cursor.execute(
                "SELECT * FROM user_feedback_requests WHERE request_id = %s",
                (request_id,),
            )
            request_row = cursor.fetchone()

        assert feedback_row["outcome"] == "success"
        assert request_row["rating"] == 4.5
        assert request_row["response"] == "Very satisfied!"
    
    @pytest.mark.asyncio
    async def test_reflection_engine_compatibility(self, feedback_service, test_user, test_skill_id, db):
        """Test that schema supports reflection engine queries."""
        # Record feedback with outcomes
        for i in range(5):
            outcome = SkillOutcome.SUCCESS if i < 3 else SkillOutcome.FAILURE
            await feedback_service.record_behavioral_feedback(
                user_id=test_user,
                message_id=f"msg-reflect-{i}",
                skill_id=test_skill_id,
                reward=1 if outcome == SkillOutcome.SUCCESS else -1,
                outcome=outcome
            )
        
        # Query like reflection engine does
        with db.cursor() as cursor:
            cursor.execute(
                """SELECT skill_id, outcome, COUNT(*) as count
                   FROM ams_behavioral_feedback
                   WHERE user_id = %s AND outcome IS NOT NULL
                   GROUP BY skill_id, outcome""",
                (test_user,),
            )
            rows = cursor.fetchall()
        
        assert len(rows) > 0
        # Should have both success and failure outcomes
        outcomes = [row["outcome"] for row in rows]
        assert "success" in outcomes
        assert "failure" in outcomes
