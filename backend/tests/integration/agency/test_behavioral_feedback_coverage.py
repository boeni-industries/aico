"""
Coverage tests for behavioral_feedback.py - targeting uncovered lines.

Focuses on error handling, edge cases, and conditional branches.
"""

import pytest
from datetime import datetime, timedelta, UTC
from unittest.mock import Mock, patch
import json

from aico.ai.agency.behavioral_feedback import (
    BehavioralFeedbackService,
    SkillOutcome,
    FeedbackType,
    SkillExecution,
    FeedbackRequest
)


class TestBehavioralFeedbackCoverage:
    """Tests targeting uncovered lines in behavioral_feedback.py."""
    
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
        """Create behavioral feedback service with logger."""
        logger = Mock()
        return BehavioralFeedbackService(agency_service, logger=logger)
    
    @pytest.fixture
    def test_skill_id(self, db):
        """Create a test skill."""
        skill_id = "test-skill-coverage-1"
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
    
    # ========================================================================
    # Error Handling Tests
    # ========================================================================
    
    @pytest.mark.asyncio
    async def test_record_skill_execution_with_error_message(self, feedback_service, test_user, test_skill_id, db):
        """Test recording skill execution with error message (covers line 108)."""
        execution_id = await feedback_service.record_skill_execution(
            execution_id="",
            skill_id=test_skill_id,
            user_id=test_user,
            outcome=SkillOutcome.ERROR,
            error_message="Connection timeout",
            execution_time_ms=5000
        )
        
        assert execution_id is not None
        
        # Verify error message stored
        with db.cursor() as cursor:
            cursor.execute(
                "SELECT * FROM agency_skill_executions WHERE execution_id = %s",
                (execution_id,),
            )
            row = cursor.fetchone()
        assert row["error_message"] == "Connection timeout"
        assert row["outcome"] == "error"
    
    @pytest.mark.asyncio
    async def test_record_skill_execution_with_context(self, feedback_service, test_user, test_skill_id, db):
        """Test recording execution with context (covers line 109, 128, 147)."""
        context = {
            "input_params": {"query": "test"},
            "environment": "production",
            "retry_count": 2
        }
        
        execution_id = await feedback_service.record_skill_execution(
            execution_id="",
            skill_id=test_skill_id,
            user_id=test_user,
            outcome=SkillOutcome.SUCCESS,
            context=context
        )

        with db.cursor() as cursor:
            cursor.execute(
                "SELECT * FROM agency_skill_executions WHERE execution_id = %s",
                (execution_id,),
            )
            row = cursor.fetchone()
        
        stored_context = row["context_json"]
        if isinstance(stored_context, str):
            stored_context = json.loads(stored_context)
        assert stored_context == context
    
    @pytest.mark.asyncio
    async def test_record_skill_execution_database_error(self, feedback_service, test_user):
        """Test error handling when database fails (covers lines 161-164)."""
        with patch.object(feedback_service.agency_service, "record_skill_execution", side_effect=Exception("DB error")):
            with pytest.raises(Exception):
                await feedback_service.record_skill_execution(
                    execution_id="",
                    skill_id="test-skill",
                    user_id=test_user,
                    outcome=SkillOutcome.SUCCESS,
                )
        
        # Verify logger was called
        assert feedback_service.logger.error.called
    
    @pytest.mark.asyncio
    async def test_link_execution_to_goal_with_order(self, feedback_service, test_user, test_skill_id, db):
        """Test linking execution with execution order (covers line 171)."""
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
                    "Test",
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
        
        # Link with execution order
        await feedback_service.link_execution_to_goal(
            goal_id=goal_id,
            skill_id=test_skill_id,
            execution_id=execution_id,
            execution_order=3
        )
        
        # Verify link
        with db.cursor() as cursor:
            cursor.execute(
                "SELECT * FROM agency_goal_skill_executions WHERE execution_id = %s",
                (execution_id,),
            )
            row = cursor.fetchone()
        assert row["execution_order"] == 3
        assert feedback_service.logger.debug.called
    
    @pytest.mark.asyncio
    async def test_link_execution_database_error(self, feedback_service, test_skill_id):
        """Test error handling when linking fails (covers lines 207-210)."""
        with pytest.raises(Exception):
            await feedback_service.link_execution_to_goal(
                goal_id="nonexistent-goal",
                skill_id=test_skill_id,
                execution_id="nonexistent-execution",
                execution_order=1
            )
        
        assert feedback_service.logger.error.called
    
    @pytest.mark.asyncio
    async def test_get_goal_executions_empty(self, feedback_service):
        """Test getting executions for goal with no executions (covers line 244)."""
        executions = await feedback_service.get_goal_executions("nonexistent-goal")
        
        assert executions == []
    
    @pytest.mark.asyncio
    async def test_get_goal_executions_with_null_context(self, feedback_service, test_user, test_skill_id, db):
        """Test getting executions with null context_json (covers line 235)."""
        # Create goal
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
                    "Test",
                    "Test",
                    "normal",
                    "active",
                    datetime.now(UTC).isoformat(),
                    datetime.now(UTC).isoformat(),
                ),
            )
        db.commit()
        
        # Record execution without context
        execution_id = await feedback_service.record_skill_execution(
            execution_id="",
            skill_id=test_skill_id,
            user_id=test_user,
            outcome=SkillOutcome.SUCCESS,
            goal_id=goal_id,
            context=None
        )
        
        await feedback_service.link_execution_to_goal(
            goal_id=goal_id,
            skill_id=test_skill_id,
            execution_id=execution_id
        )
        
        executions = await feedback_service.get_goal_executions(goal_id)
        assert len(executions) == 1
        assert executions[0].context == {}
    
    @pytest.mark.asyncio
    async def test_get_goal_executions_database_error(self, feedback_service):
        """Test error handling when fetching executions fails (covers lines 241-244)."""
        with patch.object(feedback_service.agency_service, "get_goal_executions", side_effect=Exception("DB error")):
            executions = await feedback_service.get_goal_executions("test-goal")
            assert executions == []
            assert feedback_service.logger.error.called
    
    # ========================================================================
    # Behavioral Feedback Recording Tests
    # ========================================================================
    
    @pytest.mark.asyncio
    async def test_record_feedback_without_outcome(self, feedback_service, test_user, test_skill_id, db):
        """Test recording feedback without outcome (covers line 300)."""
        feedback_id = await feedback_service.record_behavioral_feedback(
            user_id=test_user,
            message_id="msg-test-1",
            skill_id=test_skill_id,
            reward=1,
            outcome=None
        )
        
        with db.cursor() as cursor:
            cursor.execute(
                "SELECT * FROM ams_behavioral_feedback WHERE feedback_id = %s",
                (feedback_id,),
            )
            row = cursor.fetchone()
        
        assert row["outcome"] is None
    
    @pytest.mark.asyncio
    async def test_record_feedback_without_context(self, feedback_service, test_user, test_skill_id, db):
        """Test recording feedback without context (covers line 302)."""
        feedback_id = await feedback_service.record_behavioral_feedback(
            user_id=test_user,
            message_id="msg-test-2",
            skill_id=test_skill_id,
            reward=0,
            context=None
        )
        
        with db.cursor() as cursor:
            cursor.execute(
                "SELECT * FROM ams_behavioral_feedback WHERE feedback_id = %s",
                (feedback_id,),
            )
            row = cursor.fetchone()
        
        assert row["context_json"] is None
    
    @pytest.mark.asyncio
    async def test_record_feedback_database_error(self, feedback_service, test_user, test_skill_id):
        """Test error handling when recording feedback fails (covers lines 316-319)."""
        with patch.object(feedback_service.agency_service, "record_behavioral_feedback", side_effect=Exception("DB error")):
            with pytest.raises(Exception):
                await feedback_service.record_behavioral_feedback(
                    user_id=test_user,
                    message_id="msg-test-3",
                    skill_id=test_skill_id,
                    reward=1,
                )
            
            assert feedback_service.logger.error.called
    
    # ========================================================================
    # Outcome Detection Tests
    # ========================================================================
    
    @pytest.mark.asyncio
    async def test_detect_outcome_database_error(self, feedback_service):
        """Test error handling when detecting outcome fails (covers lines 349-352)."""
        with patch.object(feedback_service.agency_service, "get_skill_execution_outcome", side_effect=Exception("DB error")):
            outcome = await feedback_service.detect_outcome_from_execution("test-exec-id")
            
            assert outcome is None
            assert feedback_service.logger.warning.called
    
    @pytest.mark.asyncio
    async def test_update_feedback_outcome_database_error(self, feedback_service):
        """Test error handling when updating outcome fails (covers lines 399-402)."""
        with patch.object(feedback_service.agency_service, "update_feedback_outcome", side_effect=Exception("DB error")):
            with pytest.raises(Exception):
                await feedback_service.update_feedback_with_outcome(
                    feedback_id="test-feedback-id",
                    outcome=SkillOutcome.SUCCESS,
                )
            
            assert feedback_service.logger.error.called
    
    # ========================================================================
    # User Feedback Collection Tests
    # ========================================================================
    
    @pytest.mark.asyncio
    async def test_create_feedback_request_with_execution(self, feedback_service, test_user, test_skill_id, db):
        """Test creating feedback request with execution_id (covers line 415)."""
        execution_id = await feedback_service.record_skill_execution(
            execution_id="",
            skill_id=test_skill_id,
            user_id=test_user,
            outcome=SkillOutcome.SUCCESS
        )
        
        request_id = await feedback_service.create_feedback_request(
            user_id=test_user,
            feedback_type=FeedbackType.QUALITY,
            question="How was the execution?",
            execution_id=execution_id
        )

        with db.cursor() as cursor:
            cursor.execute(
                "SELECT * FROM user_feedback_requests WHERE request_id = %s",
                (request_id,),
            )
            row = cursor.fetchone()
        
        assert row["execution_id"] == execution_id
    
    @pytest.mark.asyncio
    async def test_create_feedback_request_database_error(self, feedback_service, test_user):
        """Test error handling when creating request fails (covers lines 461-464)."""
        with patch.object(feedback_service.agency_service, "create_feedback_request", side_effect=Exception("DB error")):
            with pytest.raises(Exception):
                await feedback_service.create_feedback_request(
                    user_id=test_user,
                    feedback_type=FeedbackType.SATISFACTION,
                    question="Test question",
                )
            
            assert feedback_service.logger.error.called
    
    @pytest.mark.asyncio
    async def test_record_feedback_response_database_error(self, feedback_service, test_user):
        """Test error handling when recording response fails (covers lines 496-499)."""
        request_id = await feedback_service.create_feedback_request(
            user_id=test_user,
            feedback_type=FeedbackType.HELPFULNESS,
            question="Test"
        )

        with patch.object(feedback_service.agency_service, "respond_to_feedback_request", side_effect=Exception("DB error")):
            with pytest.raises(Exception):
                await feedback_service.record_feedback_response(
                    request_id=request_id,
                    response="Test response",
                )
            
            assert feedback_service.logger.error.called
    
    @pytest.mark.asyncio
    async def test_get_pending_requests_with_responded_at(self, feedback_service, test_user):
        """Test getting pending requests handles responded_at (covers line 525)."""
        # Create and respond to a request
        request_id = await feedback_service.create_feedback_request(
            user_id=test_user,
            feedback_type=FeedbackType.SATISFACTION,
            question="Test"
        )
        
        await feedback_service.record_feedback_response(
            request_id=request_id,
            rating=5.0
        )
        
        # Get pending (should be empty)
        pending = await feedback_service.get_pending_feedback_requests(test_user)
        assert len(pending) == 0
    
    @pytest.mark.asyncio
    async def test_get_pending_requests_database_error(self, feedback_service, test_user):
        """Test error handling when fetching requests fails (covers lines 531-534)."""
        with patch.object(feedback_service.agency_service, "get_pending_feedback_requests", side_effect=Exception("DB error")):
            requests = await feedback_service.get_pending_feedback_requests(test_user)
            assert requests == []
            assert feedback_service.logger.error.called
    
    # ========================================================================
    # Analytics Tests
    # ========================================================================
    
    @pytest.mark.asyncio
    async def test_get_skill_success_rate_with_user_filter(self, feedback_service, test_user, test_skill_id):
        """Test success rate calculation with user filter (covers lines 560-570)."""
        for i, outcome in enumerate([SkillOutcome.SUCCESS, SkillOutcome.SUCCESS, SkillOutcome.FAILURE]):
            await feedback_service.record_behavioral_feedback(
                user_id=test_user,
                message_id=f"msg-sr-user-{i}",
                skill_id=test_skill_id,
                reward=1 if outcome == SkillOutcome.SUCCESS else -1,
                outcome=outcome,
            )

        success_rate = await feedback_service.get_skill_success_rate(
            skill_id=test_skill_id,
            user_id=test_user,
            days=30
        )
        
        # 2 successes out of 3 = 0.666...
        assert 0.6 <= success_rate <= 0.7
    
    @pytest.mark.asyncio
    async def test_get_skill_success_rate_without_user_filter(self, feedback_service, test_user, test_skill_id):
        """Test success rate calculation without user filter (covers lines 571-581)."""
        await feedback_service.record_behavioral_feedback(
            user_id=test_user,
            message_id="msg-sr-all-1",
            skill_id=test_skill_id,
            reward=1,
            outcome=SkillOutcome.SUCCESS,
        )

        success_rate = await feedback_service.get_skill_success_rate(
            skill_id=test_skill_id,
            user_id=None,
            days=30
        )
        
        assert success_rate == 1.0
    
    @pytest.mark.asyncio
    async def test_get_skill_success_rate_no_data(self, feedback_service, db):
        """Test success rate with no data (covers line 586)."""
        with db.cursor() as cursor:
            cursor.execute("DELETE FROM ams_behavioral_feedback WHERE skill_id = %s", ("nonexistent-skill-coverage",))
        db.commit()
        
        success_rate = await feedback_service.get_skill_success_rate(
            skill_id="nonexistent-skill-coverage",
            days=30
        )
        
        assert success_rate == 0.5
    
    @pytest.mark.asyncio
    async def test_get_skill_success_rate_database_error(self, feedback_service, test_skill_id):
        """Test error handling when calculating success rate fails (covers lines 588-591)."""
        with patch.object(feedback_service.agency_service, "get_skill_performance_stats", side_effect=Exception("DB error")):
            success_rate = await feedback_service.get_skill_success_rate(
                skill_id=test_skill_id,
                days=30,
            )

        assert success_rate == 0.5
        assert feedback_service.logger.error.called
    
    @pytest.mark.asyncio
    async def test_get_user_satisfaction_trend(self, feedback_service, test_user):
        """Test getting user satisfaction trend (covers lines 593-632)."""
        # Create and respond to multiple requests
        for i in range(3):
            request_id = await feedback_service.create_feedback_request(
                user_id=test_user,
                feedback_type=FeedbackType.SATISFACTION,
                question=f"Question {i}"
            )
            
            await feedback_service.record_feedback_response(
                request_id=request_id,
                rating=float(i + 3)
            )
        
        trend = await feedback_service.get_user_satisfaction_trend(
            user_id=test_user,
            days=30
        )
        
        # Should have at least one data point
        assert len(trend) >= 1
        for point in trend:
            assert "day" in point
            assert "avg_rating" in point
            assert "count" in point
    
    @pytest.mark.asyncio
    async def test_get_user_satisfaction_trend_database_error(self, feedback_service, test_user):
        """Test error handling when fetching trend fails (covers lines 634-637)."""
        with patch.object(feedback_service.agency_service, "get_user_satisfaction_trend", side_effect=Exception("DB error")):
            with pytest.raises(Exception):
                await feedback_service.get_user_satisfaction_trend(
                    user_id=test_user,
                    days=30,
                )

        assert feedback_service.logger.error.called
    
    # ========================================================================
    # Logging Tests
    # ========================================================================
    
    @pytest.mark.asyncio
    async def test_logging_on_success_operations(self, feedback_service, test_user, test_skill_id):
        """Test that logger is called on successful operations."""
        # Record execution
        await feedback_service.record_skill_execution(
            execution_id="",
            skill_id=test_skill_id,
            user_id=test_user,
            outcome=SkillOutcome.SUCCESS
        )
        assert feedback_service.logger.info.called
        
        # Record feedback
        await feedback_service.record_behavioral_feedback(
            user_id=test_user,
            message_id="msg-log-test",
            skill_id=test_skill_id,
            reward=1
        )
        assert feedback_service.logger.info.call_count >= 2
        
        # Create feedback request
        await feedback_service.create_feedback_request(
            user_id=test_user,
            feedback_type=FeedbackType.SATISFACTION,
            question="Test"
        )
        assert feedback_service.logger.info.call_count >= 3
