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
    def feedback_service(self, db):
        """Create behavioral feedback service with logger."""
        logger = Mock()
        return BehavioralFeedbackService(db, logger=logger)
    
    @pytest.fixture
    def test_skill_id(self, db):
        """Create a test skill."""
        skill_id = "test-skill-coverage-1"
        db.execute(
            """INSERT OR IGNORE INTO ams_behavioral_skills 
               (skill_id, skill_name, skill_type, trigger_context, procedure_template, dimension_vector, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (skill_id, "Test Skill", "base", "test_context", "test_template", "[]",
             datetime.now(UTC).isoformat(), datetime.now(UTC).isoformat())
        )
        db.commit()
        return skill_id
    
    # ========================================================================
    # Error Handling Tests
    # ========================================================================
    
    def test_record_skill_execution_with_error_message(self, feedback_service, test_user, test_skill_id):
        """Test recording skill execution with error message (covers line 108)."""
        execution_id = feedback_service.record_skill_execution(
            skill_id=test_skill_id,
            user_id=test_user,
            outcome=SkillOutcome.ERROR,
            error_message="Connection timeout",
            execution_time_ms=5000
        )
        
        assert execution_id is not None
        
        # Verify error message stored
        row = feedback_service.db.fetch_one(
            "SELECT * FROM agency_skill_executions WHERE execution_id = ?",
            (execution_id,)
        )
        assert row["error_message"] == "Connection timeout"
        assert row["outcome"] == "error"
    
    def test_record_skill_execution_with_context(self, feedback_service, test_user, test_skill_id):
        """Test recording execution with context (covers line 109, 128, 147)."""
        context = {
            "input_params": {"query": "test"},
            "environment": "production",
            "retry_count": 2
        }
        
        execution_id = feedback_service.record_skill_execution(
            skill_id=test_skill_id,
            user_id=test_user,
            outcome=SkillOutcome.SUCCESS,
            context=context
        )
        
        row = feedback_service.db.fetch_one(
            "SELECT * FROM agency_skill_executions WHERE execution_id = ?",
            (execution_id,)
        )
        
        stored_context = json.loads(row["context_json"])
        assert stored_context == context
    
    def test_record_skill_execution_database_error(self, feedback_service, test_user, db):
        """Test error handling when database fails (covers lines 161-164)."""
        # Mock database error
        with patch.object(db, 'execute', side_effect=Exception("DB error")):
            with pytest.raises(Exception):
                feedback_service.record_skill_execution(
                    skill_id="test-skill",
                    user_id=test_user,
                    outcome=SkillOutcome.SUCCESS
                )
        
        # Verify logger was called
        assert feedback_service.logger.error.called
    
    def test_link_execution_to_goal_with_order(self, feedback_service, test_user, test_skill_id, db):
        """Test linking execution with execution order (covers line 171)."""
        # Create goal
        goal_id = "test-goal-link-1"
        db.execute(
            """INSERT INTO agency_goals 
               (goal_id, user_id, origin, goal_type, title, description, priority, status, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (goal_id, test_user, "user", "work", "Test", "Test", "normal", "active",
             datetime.now(UTC).isoformat(), datetime.now(UTC).isoformat())
        )
        db.commit()
        
        # Record execution
        execution_id = feedback_service.record_skill_execution(
            skill_id=test_skill_id,
            user_id=test_user,
            outcome=SkillOutcome.SUCCESS
        )
        
        # Link with execution order
        feedback_service.link_execution_to_goal(
            goal_id=goal_id,
            skill_id=test_skill_id,
            execution_id=execution_id,
            execution_order=3
        )
        
        # Verify link
        row = db.fetch_one(
            "SELECT * FROM agency_goal_skill_executions WHERE execution_id = ?",
            (execution_id,)
        )
        assert row["execution_order"] == 3
        assert feedback_service.logger.debug.called
    
    def test_link_execution_database_error(self, feedback_service, test_skill_id):
        """Test error handling when linking fails (covers lines 207-210)."""
        with pytest.raises(Exception):
            feedback_service.link_execution_to_goal(
                goal_id="nonexistent-goal",
                skill_id=test_skill_id,
                execution_id="nonexistent-execution",
                execution_order=1
            )
        
        assert feedback_service.logger.error.called
    
    def test_get_goal_executions_empty(self, feedback_service):
        """Test getting executions for goal with no executions (covers line 244)."""
        executions = feedback_service.get_goal_executions("nonexistent-goal")
        
        assert executions == []
    
    def test_get_goal_executions_with_null_context(self, feedback_service, test_user, test_skill_id, db):
        """Test getting executions with null context_json (covers line 235)."""
        # Create goal
        goal_id = "test-goal-exec-1"
        db.execute(
            """INSERT INTO agency_goals 
               (goal_id, user_id, origin, goal_type, title, description, priority, status, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (goal_id, test_user, "user", "work", "Test", "Test", "normal", "active",
             datetime.now(UTC).isoformat(), datetime.now(UTC).isoformat())
        )
        
        # Record execution without context
        execution_id = feedback_service.record_skill_execution(
            skill_id=test_skill_id,
            user_id=test_user,
            outcome=SkillOutcome.SUCCESS,
            context=None
        )
        
        feedback_service.link_execution_to_goal(
            goal_id=goal_id,
            skill_id=test_skill_id,
            execution_id=execution_id
        )
        
        executions = feedback_service.get_goal_executions(goal_id)
        assert len(executions) == 1
        assert executions[0].context == {}
    
    def test_get_goal_executions_database_error(self, feedback_service, db):
        """Test error handling when fetching executions fails (covers lines 241-244)."""
        # Simulate database error by closing connection temporarily
        with patch.object(db, 'fetch_all', side_effect=Exception("DB error")):
            executions = feedback_service.get_goal_executions("test-goal")
            
            assert executions == []
            assert feedback_service.logger.error.called
    
    # ========================================================================
    # Behavioral Feedback Recording Tests
    # ========================================================================
    
    def test_record_feedback_without_outcome(self, feedback_service, test_user, test_skill_id):
        """Test recording feedback without outcome (covers line 300)."""
        feedback_id = feedback_service.record_behavioral_feedback(
            user_id=test_user,
            message_id="msg-test-1",
            skill_id=test_skill_id,
            reward=1,
            outcome=None
        )
        
        row = feedback_service.db.fetch_one(
            "SELECT * FROM ams_behavioral_feedback WHERE feedback_id = ?",
            (feedback_id,)
        )
        
        assert row["outcome"] is None
    
    def test_record_feedback_without_context(self, feedback_service, test_user, test_skill_id):
        """Test recording feedback without context (covers line 302)."""
        feedback_id = feedback_service.record_behavioral_feedback(
            user_id=test_user,
            message_id="msg-test-2",
            skill_id=test_skill_id,
            reward=0,
            context=None
        )
        
        row = feedback_service.db.fetch_one(
            "SELECT * FROM ams_behavioral_feedback WHERE feedback_id = ?",
            (feedback_id,)
        )
        
        assert row["context_json"] is None
    
    def test_record_feedback_database_error(self, feedback_service, test_user, test_skill_id):
        """Test error handling when recording feedback fails (covers lines 316-319)."""
        with patch.object(feedback_service.db, 'execute', side_effect=Exception("DB error")):
            with pytest.raises(Exception):
                feedback_service.record_behavioral_feedback(
                    user_id=test_user,
                    message_id="msg-test-3",
                    skill_id=test_skill_id,
                    reward=1
                )
            
            assert feedback_service.logger.error.called
    
    # ========================================================================
    # Outcome Detection Tests
    # ========================================================================
    
    def test_detect_outcome_database_error(self, feedback_service, db):
        """Test error handling when detecting outcome fails (covers lines 349-352)."""
        with patch.object(db, 'fetch_one', side_effect=Exception("DB error")):
            outcome = feedback_service.detect_outcome_from_execution("test-exec-id")
            
            assert outcome is None
            assert feedback_service.logger.warning.called
    
    def test_update_feedback_outcome_database_error(self, feedback_service, db):
        """Test error handling when updating outcome fails (covers lines 399-402)."""
        with patch.object(db, 'execute', side_effect=Exception("DB error")):
            with pytest.raises(Exception):
                feedback_service.update_feedback_with_outcome(
                    feedback_id="test-feedback-id",
                    outcome=SkillOutcome.SUCCESS
                )
            
            assert feedback_service.logger.error.called
    
    # ========================================================================
    # User Feedback Collection Tests
    # ========================================================================
    
    def test_create_feedback_request_with_execution(self, feedback_service, test_user, test_skill_id):
        """Test creating feedback request with execution_id (covers line 415)."""
        execution_id = feedback_service.record_skill_execution(
            skill_id=test_skill_id,
            user_id=test_user,
            outcome=SkillOutcome.SUCCESS
        )
        
        request_id = feedback_service.create_feedback_request(
            user_id=test_user,
            feedback_type=FeedbackType.QUALITY,
            question="How was the execution?",
            execution_id=execution_id
        )
        
        row = feedback_service.db.fetch_one(
            "SELECT * FROM user_feedback_requests WHERE request_id = ?",
            (request_id,)
        )
        
        assert row["execution_id"] == execution_id
    
    def test_create_feedback_request_database_error(self, feedback_service, test_user, db):
        """Test error handling when creating request fails (covers lines 461-464)."""
        with patch.object(db, 'execute', side_effect=Exception("DB error")):
            with pytest.raises(Exception):
                feedback_service.create_feedback_request(
                    user_id=test_user,
                    feedback_type=FeedbackType.SATISFACTION,
                    question="Test question"
                )
            
            assert feedback_service.logger.error.called
    
    def test_record_feedback_response_database_error(self, feedback_service, test_user, db):
        """Test error handling when recording response fails (covers lines 496-499)."""
        request_id = feedback_service.create_feedback_request(
            user_id=test_user,
            feedback_type=FeedbackType.HELPFULNESS,
            question="Test"
        )
        
        with patch.object(db, 'execute', side_effect=Exception("DB error")):
            with pytest.raises(Exception):
                feedback_service.record_feedback_response(
                    request_id=request_id,
                    response="Test response"
                )
            
            assert feedback_service.logger.error.called
    
    def test_get_pending_requests_with_responded_at(self, feedback_service, test_user):
        """Test getting pending requests handles responded_at (covers line 525)."""
        # Create and respond to a request
        request_id = feedback_service.create_feedback_request(
            user_id=test_user,
            feedback_type=FeedbackType.SATISFACTION,
            question="Test"
        )
        
        feedback_service.record_feedback_response(
            request_id=request_id,
            rating=5.0
        )
        
        # Get pending (should be empty)
        pending = feedback_service.get_pending_feedback_requests(test_user)
        assert len(pending) == 0
    
    def test_get_pending_requests_database_error(self, feedback_service, test_user, db):
        """Test error handling when fetching requests fails (covers lines 531-534)."""
        with patch.object(db, 'fetch_all', side_effect=Exception("DB error")):
            requests = feedback_service.get_pending_feedback_requests(test_user)
            
            assert requests == []
            assert feedback_service.logger.error.called
    
    # ========================================================================
    # Analytics Tests
    # ========================================================================
    
    def test_get_skill_success_rate_with_user_filter(self, feedback_service, test_user, test_skill_id):
        """Test success rate calculation with user filter (covers lines 560-570)."""
        # Record some executions
        for outcome in [SkillOutcome.SUCCESS, SkillOutcome.SUCCESS, SkillOutcome.FAILURE]:
            feedback_service.record_skill_execution(
                skill_id=test_skill_id,
                user_id=test_user,
                outcome=outcome
            )
        
        success_rate = feedback_service.get_skill_success_rate(
            skill_id=test_skill_id,
            user_id=test_user,
            days=30
        )
        
        # 2 successes out of 3 = 0.666...
        assert 0.6 <= success_rate <= 0.7
    
    def test_get_skill_success_rate_without_user_filter(self, feedback_service, test_user, test_skill_id):
        """Test success rate calculation without user filter (covers lines 571-581)."""
        # Record executions
        feedback_service.record_skill_execution(
            skill_id=test_skill_id,
            user_id=test_user,
            outcome=SkillOutcome.SUCCESS
        )
        
        success_rate = feedback_service.get_skill_success_rate(
            skill_id=test_skill_id,
            user_id=None,
            days=30
        )
        
        assert success_rate == 1.0
    
    def test_get_skill_success_rate_no_data(self, feedback_service, db):
        """Test success rate with no data (covers line 586)."""
        # Clean up any leftover data
        db.execute("DELETE FROM agency_skill_executions WHERE skill_id = ?", ("nonexistent-skill-coverage",))
        db.commit()
        
        success_rate = feedback_service.get_skill_success_rate(
            skill_id="nonexistent-skill-coverage",
            days=30
        )
        
        assert success_rate == 0.5
    
    def test_get_skill_success_rate_database_error(self, feedback_service, test_skill_id, db):
        """Test error handling when calculating success rate fails (covers lines 588-591)."""
        with patch.object(db, 'fetch_one', side_effect=Exception("DB error")):
            success_rate = feedback_service.get_skill_success_rate(
                skill_id=test_skill_id,
                days=30
            )
            
            assert success_rate == 0.5
            assert feedback_service.logger.error.called
    
    def test_get_user_satisfaction_trend(self, feedback_service, test_user):
        """Test getting user satisfaction trend (covers lines 593-632)."""
        # Create and respond to multiple requests
        for i in range(3):
            request_id = feedback_service.create_feedback_request(
                user_id=test_user,
                feedback_type=FeedbackType.SATISFACTION,
                question=f"Question {i}"
            )
            
            feedback_service.record_feedback_response(
                request_id=request_id,
                rating=float(i + 3)
            )
        
        trend = feedback_service.get_user_satisfaction_trend(
            user_id=test_user,
            days=30
        )
        
        # Should have at least one data point
        assert len(trend) >= 1
        for point in trend:
            assert "date" in point
            assert "avg_rating" in point
            assert "count" in point
    
    def test_get_user_satisfaction_trend_database_error(self, feedback_service, test_user, db):
        """Test error handling when fetching trend fails (covers lines 634-637)."""
        with patch.object(db, 'fetch_all', side_effect=Exception("DB error")):
            trend = feedback_service.get_user_satisfaction_trend(
                user_id=test_user,
                days=30
            )
            
            assert trend == []
            assert feedback_service.logger.error.called
    
    # ========================================================================
    # Logging Tests
    # ========================================================================
    
    def test_logging_on_success_operations(self, feedback_service, test_user, test_skill_id):
        """Test that logger is called on successful operations."""
        # Record execution
        feedback_service.record_skill_execution(
            skill_id=test_skill_id,
            user_id=test_user,
            outcome=SkillOutcome.SUCCESS
        )
        assert feedback_service.logger.info.called
        
        # Record feedback
        feedback_service.record_behavioral_feedback(
            user_id=test_user,
            message_id="msg-log-test",
            skill_id=test_skill_id,
            reward=1
        )
        assert feedback_service.logger.info.call_count >= 2
        
        # Create feedback request
        feedback_service.create_feedback_request(
            user_id=test_user,
            feedback_type=FeedbackType.SATISFACTION,
            question="Test"
        )
        assert feedback_service.logger.info.call_count >= 3
