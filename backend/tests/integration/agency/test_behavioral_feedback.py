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
    def feedback_service(self, db):
        """Create behavioral feedback service."""
        return BehavioralFeedbackService(db)
    
    @pytest.fixture
    def test_skill_id(self, db):
        """Create a test skill."""
        skill_id = "test-skill-1"
        db.execute(
            """INSERT OR IGNORE INTO skills 
               (skill_id, skill_name, skill_type, trigger_context, procedure_template, dimension_vector, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (skill_id, "Test Skill", "base", "test_context", "test_template", "[]",
             datetime.now(UTC).isoformat(), datetime.now(UTC).isoformat())
        )
        db.commit()
        return skill_id
    
    def test_record_skill_execution_success(self, feedback_service, test_user, test_skill_id):
        """Test recording a successful skill execution."""
        execution_id = feedback_service.record_skill_execution(
            skill_id=test_skill_id,
            user_id=test_user,
            outcome=SkillOutcome.SUCCESS,
            execution_time_ms=150,
            context={"test": "data"}
        )
        
        assert execution_id is not None
        assert len(execution_id) > 0
        
        # Verify in database
        row = feedback_service.db.fetch_one(
            "SELECT * FROM skill_executions WHERE execution_id = ?",
            (execution_id,)
        )
        
        assert row is not None
        assert row["skill_id"] == test_skill_id
        assert row["user_id"] == test_user
        assert row["outcome"] == "success"
        assert row["execution_time_ms"] == 150
    
    def test_record_skill_execution_failure(self, feedback_service, test_user, test_skill_id):
        """Test recording a failed skill execution."""
        execution_id = feedback_service.record_skill_execution(
            skill_id=test_skill_id,
            user_id=test_user,
            outcome=SkillOutcome.FAILURE,
            error_message="Test error",
            execution_time_ms=50
        )
        
        assert execution_id is not None
        
        row = feedback_service.db.fetch_one(
            "SELECT * FROM skill_executions WHERE execution_id = ?",
            (execution_id,)
        )
        
        assert row["outcome"] == "failure"
        assert row["error_message"] == "Test error"
    
    def test_record_skill_execution_with_goal(self, feedback_service, test_user, test_skill_id, db):
        """Test recording skill execution linked to a goal."""
        # Create test goal
        goal_id = "test-goal-exec-1"
        db.execute(
            """INSERT INTO agency_goals 
               (goal_id, user_id, origin, goal_type, title, description, priority, status, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (goal_id, test_user, "user", "work", "Test goal", "Test", "normal", "active",
             datetime.now(UTC).isoformat(), datetime.now(UTC).isoformat())
        )
        db.commit()
        
        execution_id = feedback_service.record_skill_execution(
            skill_id=test_skill_id,
            user_id=test_user,
            outcome=SkillOutcome.SUCCESS,
            goal_id=goal_id
        )
        
        row = feedback_service.db.fetch_one(
            "SELECT * FROM skill_executions WHERE execution_id = ?",
            (execution_id,)
        )
        
        assert row["goal_id"] == goal_id
    
    def test_link_execution_to_goal(self, feedback_service, test_user, test_skill_id, db):
        """Test linking an execution to a goal."""
        # Create goal
        goal_id = "test-goal-link-1"
        db.execute(
            """INSERT INTO agency_goals 
               (goal_id, user_id, origin, goal_type, title, description, priority, status, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (goal_id, test_user, "user", "work", "Test goal", "Test", "normal", "active",
             datetime.now(UTC).isoformat(), datetime.now(UTC).isoformat())
        )
        db.commit()
        
        # Record execution
        execution_id = feedback_service.record_skill_execution(
            skill_id=test_skill_id,
            user_id=test_user,
            outcome=SkillOutcome.SUCCESS
        )
        
        # Link to goal
        feedback_service.link_execution_to_goal(
            goal_id=goal_id,
            skill_id=test_skill_id,
            execution_id=execution_id,
            execution_order=1
        )
        
        # Verify link
        row = feedback_service.db.fetch_one(
            "SELECT * FROM goal_skill_executions WHERE execution_id = ?",
            (execution_id,)
        )
        
        assert row is not None
        assert row["goal_id"] == goal_id
        assert row["execution_order"] == 1
    
    def test_get_goal_executions(self, feedback_service, test_user, test_skill_id, db):
        """Test retrieving all executions for a goal."""
        # Clean up first
        goal_id = "test-goal-get-exec-1"
        db.execute("PRAGMA foreign_keys = OFF")
        db.execute("DELETE FROM goal_skill_executions WHERE goal_id = ?", (goal_id,))
        db.execute("DELETE FROM agency_goals WHERE goal_id = ?", (goal_id,))
        db.commit()
        db.execute("PRAGMA foreign_keys = ON")
        
        # Create goal
        db.execute(
            """INSERT INTO agency_goals 
               (goal_id, user_id, origin, goal_type, title, description, priority, status, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (goal_id, test_user, "user", "work", "Test goal", "Test", "normal", "active",
             datetime.now(UTC).isoformat(), datetime.now(UTC).isoformat())
        )
        db.commit()
        
        # Record multiple executions
        exec_ids = []
        for i in range(3):
            exec_id = feedback_service.record_skill_execution(
                skill_id=test_skill_id,
                user_id=test_user,
                outcome=SkillOutcome.SUCCESS if i < 2 else SkillOutcome.FAILURE
            )
            feedback_service.link_execution_to_goal(
                goal_id=goal_id,
                skill_id=test_skill_id,
                execution_id=exec_id,
                execution_order=i
            )
            exec_ids.append(exec_id)
        
        # Get executions
        executions = feedback_service.get_goal_executions(goal_id)
        
        assert len(executions) == 3
        assert executions[0].outcome == SkillOutcome.SUCCESS
        assert executions[1].outcome == SkillOutcome.SUCCESS
        assert executions[2].outcome == SkillOutcome.FAILURE


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
    def feedback_service(self, db):
        """Create behavioral feedback service."""
        return BehavioralFeedbackService(db)
    
    @pytest.fixture
    def test_skill_id(self, db):
        """Create a test skill."""
        skill_id = "test-skill-feedback-1"
        db.execute(
            """INSERT OR IGNORE INTO skills 
               (skill_id, skill_name, skill_type, trigger_context, procedure_template, dimension_vector, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (skill_id, "Test Skill", "base", "test_context", "test_template", "[]",
             datetime.now(UTC).isoformat(), datetime.now(UTC).isoformat())
        )
        db.commit()
        return skill_id
    
    def test_record_behavioral_feedback_with_outcome(self, feedback_service, test_user, test_skill_id):
        """Test recording behavioral feedback with outcome."""
        feedback_id = feedback_service.record_behavioral_feedback(
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
        row = feedback_service.db.fetch_one(
            "SELECT * FROM ams_behavioral_feedback WHERE feedback_id = ?",
            (feedback_id,)
        )
        
        assert row is not None
        assert row["reward"] == 1
        assert row["outcome"] == "success"
        assert row["execution_time_ms"] == 200
        assert row["user_satisfaction"] == 0.9
    
    def test_record_behavioral_feedback_negative(self, feedback_service, test_user, test_skill_id):
        """Test recording negative behavioral feedback."""
        feedback_id = feedback_service.record_behavioral_feedback(
            user_id=test_user,
            message_id="msg-2",
            skill_id=test_skill_id,
            reward=-1,
            outcome=SkillOutcome.FAILURE,
            reason="Did not work",
            user_satisfaction=0.2
        )
        
        row = feedback_service.db.fetch_one(
            "SELECT * FROM ams_behavioral_feedback WHERE feedback_id = ?",
            (feedback_id,)
        )
        
        assert row["reward"] == -1
        assert row["outcome"] == "failure"
        assert row["user_satisfaction"] == 0.2
    
    def test_record_behavioral_feedback_with_context(self, feedback_service, test_user, test_skill_id):
        """Test recording feedback with execution context."""
        context = {
            "input": "test input",
            "parameters": {"param1": "value1"},
            "environment": "test"
        }
        
        feedback_id = feedback_service.record_behavioral_feedback(
            user_id=test_user,
            message_id="msg-3",
            skill_id=test_skill_id,
            reward=1,
            outcome=SkillOutcome.SUCCESS,
            context=context
        )
        
        row = feedback_service.db.fetch_one(
            "SELECT * FROM ams_behavioral_feedback WHERE feedback_id = ?",
            (feedback_id,)
        )
        
        stored_context = json.loads(row["context_json"])
        assert stored_context == context
    
    def test_record_behavioral_feedback_invalid_reward(self, feedback_service, test_user, test_skill_id):
        """Test that invalid reward values are rejected."""
        with pytest.raises(ValueError, match="Reward must be -1, 0, or 1"):
            feedback_service.record_behavioral_feedback(
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
    def feedback_service(self, db):
        """Create behavioral feedback service."""
        return BehavioralFeedbackService(db)
    
    @pytest.fixture
    def test_skill_id(self, db):
        """Create a test skill."""
        skill_id = "test-skill-outcome-1"
        db.execute(
            """INSERT OR IGNORE INTO skills 
               (skill_id, skill_name, skill_type, trigger_context, procedure_template, dimension_vector, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (skill_id, "Test Skill", "base", "test_context", "test_template", "[]",
             datetime.now(UTC).isoformat(), datetime.now(UTC).isoformat())
        )
        db.commit()
        return skill_id
    
    def test_detect_outcome_from_execution(self, feedback_service, test_user, test_skill_id):
        """Test detecting outcome from execution record."""
        execution_id = feedback_service.record_skill_execution(
            skill_id=test_skill_id,
            user_id=test_user,
            outcome=SkillOutcome.SUCCESS
        )
        
        detected_outcome = feedback_service.detect_outcome_from_execution(execution_id)
        
        assert detected_outcome == SkillOutcome.SUCCESS
    
    def test_detect_outcome_nonexistent_execution(self, feedback_service):
        """Test detecting outcome for nonexistent execution."""
        outcome = feedback_service.detect_outcome_from_execution("nonexistent-id")
        
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
    
    def test_update_feedback_with_outcome(self, feedback_service, test_user, test_skill_id):
        """Test updating existing feedback with detected outcome."""
        # Record feedback without outcome
        feedback_id = feedback_service.record_behavioral_feedback(
            user_id=test_user,
            message_id="msg-5",
            skill_id=test_skill_id,
            reward=1
        )
        
        # Update with outcome
        feedback_service.update_feedback_with_outcome(
            feedback_id=feedback_id,
            outcome=SkillOutcome.SUCCESS
        )
        
        # Verify update
        row = feedback_service.db.fetch_one(
            "SELECT * FROM ams_behavioral_feedback WHERE feedback_id = ?",
            (feedback_id,)
        )
        
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
    def feedback_service(self, db):
        """Create behavioral feedback service."""
        return BehavioralFeedbackService(db)
    
    def test_create_feedback_request(self, feedback_service, test_user):
        """Test creating a user feedback request."""
        request_id = feedback_service.create_feedback_request(
            user_id=test_user,
            feedback_type=FeedbackType.SATISFACTION,
            question="How satisfied are you with this result?"
        )
        
        assert request_id is not None
        
        # Verify in database
        row = feedback_service.db.fetch_one(
            "SELECT * FROM user_feedback_requests WHERE request_id = ?",
            (request_id,)
        )
        
        assert row is not None
        assert row["user_id"] == test_user
        assert row["feedback_type"] == "satisfaction"
        assert row["responded_at"] is None
    
    def test_create_feedback_request_with_goal(self, feedback_service, test_user, db):
        """Test creating feedback request linked to a goal."""
        # Create goal
        goal_id = "test-goal-feedback-1"
        db.execute(
            """INSERT INTO agency_goals 
               (goal_id, user_id, origin, goal_type, title, description, priority, status, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (goal_id, test_user, "user", "work", "Test goal", "Test", "normal", "active",
             datetime.now(UTC).isoformat(), datetime.now(UTC).isoformat())
        )
        db.commit()
        
        request_id = feedback_service.create_feedback_request(
            user_id=test_user,
            feedback_type=FeedbackType.QUALITY,
            question="Was this goal helpful?",
            goal_id=goal_id
        )
        
        row = feedback_service.db.fetch_one(
            "SELECT * FROM user_feedback_requests WHERE request_id = ?",
            (request_id,)
        )
        
        assert row["goal_id"] == goal_id
    
    def test_record_feedback_response_text(self, feedback_service, test_user):
        """Test recording text response to feedback request."""
        request_id = feedback_service.create_feedback_request(
            user_id=test_user,
            feedback_type=FeedbackType.HELPFULNESS,
            question="What could be improved?"
        )
        
        feedback_service.record_feedback_response(
            request_id=request_id,
            response="It was very helpful, thanks!"
        )
        
        row = feedback_service.db.fetch_one(
            "SELECT * FROM user_feedback_requests WHERE request_id = ?",
            (request_id,)
        )
        
        assert row["response"] == "It was very helpful, thanks!"
        assert row["responded_at"] is not None
    
    def test_record_feedback_response_rating(self, feedback_service, test_user):
        """Test recording numeric rating response."""
        request_id = feedback_service.create_feedback_request(
            user_id=test_user,
            feedback_type=FeedbackType.SATISFACTION,
            question="Rate your satisfaction (1-5)"
        )
        
        feedback_service.record_feedback_response(
            request_id=request_id,
            rating=4.5
        )
        
        row = feedback_service.db.fetch_one(
            "SELECT * FROM user_feedback_requests WHERE request_id = ?",
            (request_id,)
        )
        
        assert row["rating"] == 4.5
    
    def test_get_pending_feedback_requests(self, feedback_service, test_user):
        """Test retrieving pending feedback requests."""
        # Create multiple requests
        for i in range(3):
            feedback_service.create_feedback_request(
                user_id=test_user,
                feedback_type=FeedbackType.SATISFACTION,
                question=f"Question {i}"
            )
        
        # Respond to one
        requests = feedback_service.get_pending_feedback_requests(test_user)
        if requests:
            feedback_service.record_feedback_response(
                request_id=requests[0].request_id,
                rating=5.0
            )
        
        # Get pending (should be 2 now)
        pending = feedback_service.get_pending_feedback_requests(test_user)
        
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
    def feedback_service(self, db):
        """Create behavioral feedback service."""
        return BehavioralFeedbackService(db)
    
    @pytest.fixture
    def test_skill_id(self, db):
        """Create a test skill."""
        skill_id = "test-skill-analytics-1"
        db.execute(
            """INSERT OR IGNORE INTO skills 
               (skill_id, skill_name, skill_type, trigger_context, procedure_template, dimension_vector, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (skill_id, "Test Skill", "base", "test_context", "test_template", "[]",
             datetime.now(UTC).isoformat(), datetime.now(UTC).isoformat())
        )
        db.commit()
        return skill_id
    
    def test_get_skill_success_rate(self, feedback_service, test_user, test_skill_id, db):
        """Test calculating skill success rate."""
        # Clean up any existing executions for this skill
        db.execute("DELETE FROM skill_executions WHERE skill_id = ?", (test_skill_id,))
        db.commit()
        
        # Record multiple executions
        for i in range(10):
            outcome = SkillOutcome.SUCCESS if i < 7 else SkillOutcome.FAILURE
            feedback_service.record_skill_execution(
                skill_id=test_skill_id,
                user_id=test_user,
                outcome=outcome
            )
        
        # Verify executions were recorded
        count = db.fetch_one(
            "SELECT COUNT(*) as count FROM skill_executions WHERE skill_id = ? AND user_id = ?",
            (test_skill_id, test_user)
        )
        assert count["count"] == 10, f"Expected 10 executions, got {count['count']}"
        
        success_rate = feedback_service.get_skill_success_rate(
            skill_id=test_skill_id,
            user_id=test_user,
            days=30
        )
        
        assert success_rate == pytest.approx(0.7, abs=0.01)
    
    def test_get_skill_success_rate_no_data(self, feedback_service):
        """Test success rate with no data returns neutral."""
        success_rate = feedback_service.get_skill_success_rate(
            skill_id="nonexistent-skill",
            days=30
        )
        
        assert success_rate == 0.5
    
    def test_get_user_satisfaction_trend(self, feedback_service, test_user):
        """Test getting user satisfaction trend over time."""
        # Create feedback requests with ratings
        for i in range(5):
            request_id = feedback_service.create_feedback_request(
                user_id=test_user,
                feedback_type=FeedbackType.SATISFACTION,
                question="Rate satisfaction"
            )
            feedback_service.record_feedback_response(
                request_id=request_id,
                rating=float(i + 1)  # Ratings 1-5
            )
        
        trend = feedback_service.get_user_satisfaction_trend(
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
    def feedback_service(self, db):
        """Create behavioral feedback service."""
        return BehavioralFeedbackService(db)
    
    @pytest.fixture
    def test_skill_id(self, db):
        """Create a test skill."""
        skill_id = "test-skill-integration-1"
        db.execute(
            """INSERT OR IGNORE INTO skills 
               (skill_id, skill_name, skill_type, trigger_context, procedure_template, dimension_vector, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (skill_id, "Test Skill", "base", "test_context", "test_template", "[]",
             datetime.now(UTC).isoformat(), datetime.now(UTC).isoformat())
        )
        db.commit()
        return skill_id
    
    def test_complete_feedback_loop(self, feedback_service, test_user, test_skill_id, db):
        """Test complete feedback loop from execution to user feedback."""
        # Clean up first
        goal_id = "test-goal-complete-1"
        db.execute("PRAGMA foreign_keys = OFF")
        db.execute("DELETE FROM goal_skill_executions WHERE goal_id = ?", (goal_id,))
        db.execute("DELETE FROM skill_executions WHERE skill_id = ?", (test_skill_id,))
        db.execute("DELETE FROM agency_goals WHERE goal_id = ?", (goal_id,))
        db.commit()
        db.execute("PRAGMA foreign_keys = ON")
        
        # 1. Create goal
        db.execute(
            """INSERT INTO agency_goals 
               (goal_id, user_id, origin, goal_type, title, description, priority, status, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (goal_id, test_user, "user", "work", "Test goal", "Test", "normal", "active",
             datetime.now(UTC).isoformat(), datetime.now(UTC).isoformat())
        )
        db.commit()
        
        # 2. Record skill execution
        execution_id = feedback_service.record_skill_execution(
            skill_id=test_skill_id,
            user_id=test_user,
            outcome=SkillOutcome.SUCCESS,
            execution_time_ms=250,
            goal_id=goal_id
        )
        
        # 3. Link to goal
        feedback_service.link_execution_to_goal(
            goal_id=goal_id,
            skill_id=test_skill_id,
            execution_id=execution_id
        )
        
        # 4. Record behavioral feedback
        feedback_id = feedback_service.record_behavioral_feedback(
            user_id=test_user,
            message_id="msg-complete-1",
            skill_id=test_skill_id,
            reward=1,
            outcome=SkillOutcome.SUCCESS,
            execution_time_ms=250
        )
        
        # 5. Create user feedback request
        request_id = feedback_service.create_feedback_request(
            user_id=test_user,
            feedback_type=FeedbackType.SATISFACTION,
            question="How satisfied are you?",
            goal_id=goal_id,
            skill_id=test_skill_id,
            execution_id=execution_id
        )
        
        # 6. User responds
        feedback_service.record_feedback_response(
            request_id=request_id,
            rating=4.5,
            response="Very satisfied!"
        )
        
        # Verify complete loop
        executions = feedback_service.get_goal_executions(goal_id)
        assert len(executions) == 1
        assert executions[0].outcome == SkillOutcome.SUCCESS
        
        feedback_row = feedback_service.db.fetch_one(
            "SELECT * FROM ams_behavioral_feedback WHERE feedback_id = ?",
            (feedback_id,)
        )
        assert feedback_row["outcome"] == "success"
        
        request_row = feedback_service.db.fetch_one(
            "SELECT * FROM user_feedback_requests WHERE request_id = ?",
            (request_id,)
        )
        assert request_row["rating"] == 4.5
        assert request_row["response"] == "Very satisfied!"
    
    def test_reflection_engine_compatibility(self, feedback_service, test_user, test_skill_id):
        """Test that schema supports reflection engine queries."""
        # Record feedback with outcomes
        for i in range(5):
            outcome = SkillOutcome.SUCCESS if i < 3 else SkillOutcome.FAILURE
            feedback_service.record_behavioral_feedback(
                user_id=test_user,
                message_id=f"msg-reflect-{i}",
                skill_id=test_skill_id,
                reward=1 if outcome == SkillOutcome.SUCCESS else -1,
                outcome=outcome
            )
        
        # Query like reflection engine does
        rows = feedback_service.db.fetch_all(
            """SELECT skill_id, outcome, COUNT(*) as count
               FROM ams_behavioral_feedback
               WHERE user_id = ? AND outcome IS NOT NULL
               GROUP BY skill_id, outcome""",
            (test_user,)
        )
        
        assert len(rows) > 0
        # Should have both success and failure outcomes
        outcomes = [row["outcome"] for row in rows]
        assert "success" in outcomes
        assert "failure" in outcomes
