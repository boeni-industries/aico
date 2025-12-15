"""
Behavioral Feedback Integration - Phase 6.6

Connects skill executions to behavioral feedback, implements automatic outcome
detection, and completes the feedback loop for behavioral learning.
"""

from __future__ import annotations

import json
import uuid
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta, UTC
from dataclasses import dataclass
from enum import Enum

from aico.data.libsql import EncryptedLibSQLConnection


# ============================================================================
# Enums & Data Models
# ============================================================================

class SkillOutcome(str, Enum):
    """Outcome of a skill execution."""
    SUCCESS = "success"
    FAILURE = "failure"
    TIMEOUT = "timeout"
    ERROR = "error"
    PARTIAL = "partial"


class FeedbackType(str, Enum):
    """Type of user feedback request."""
    SATISFACTION = "satisfaction"
    QUALITY = "quality"
    HELPFULNESS = "helpfulness"
    ACCURACY = "accuracy"


@dataclass
class SkillExecution:
    """Record of a skill execution."""
    execution_id: str
    skill_id: str
    user_id: str
    message_id: Optional[str]
    goal_id: Optional[str]
    execution_time_ms: Optional[int]
    outcome: SkillOutcome
    error_message: Optional[str]
    context: Dict[str, Any]
    created_at: datetime


@dataclass
class FeedbackRequest:
    """User feedback request."""
    request_id: str
    user_id: str
    goal_id: Optional[str]
    skill_id: Optional[str]
    execution_id: Optional[str]
    feedback_type: FeedbackType
    question: str
    response: Optional[str]
    rating: Optional[float]
    responded_at: Optional[datetime]
    created_at: datetime


# ============================================================================
# Behavioral Feedback Service
# ============================================================================

class BehavioralFeedbackService:
    """
    Manages behavioral feedback integration for Phase 6.6.
    
    Responsibilities:
    - Track skill executions
    - Link executions to goals
    - Record behavioral feedback with outcomes
    - Detect outcomes automatically
    - Collect user feedback
    """
    
    def __init__(
        self,
        db: EncryptedLibSQLConnection,
        logger=None
    ):
        self.db = db
        self.logger = logger
    
    # ========================================================================
    # Skill Execution Tracking
    # ========================================================================
    
    def record_skill_execution(
        self,
        skill_id: str,
        user_id: str,
        outcome: SkillOutcome,
        execution_time_ms: Optional[int] = None,
        message_id: Optional[str] = None,
        goal_id: Optional[str] = None,
        error_message: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Record a skill execution.
        
        Args:
            skill_id: ID of the skill executed
            user_id: User ID
            outcome: Execution outcome
            execution_time_ms: Execution time in milliseconds
            message_id: Associated message ID
            goal_id: Associated goal ID
            error_message: Error message if failed
            context: Execution context
            
        Returns:
            execution_id
        """
        execution_id = str(uuid.uuid4())
        context = context or {}
        
        try:
            self.db.execute(
                """
                INSERT INTO skill_executions (
                    execution_id, skill_id, user_id, message_id, goal_id,
                    execution_time_ms, outcome, error_message, context_json, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    execution_id,
                    skill_id,
                    user_id,
                    message_id,
                    goal_id,
                    execution_time_ms,
                    outcome.value,
                    error_message,
                    json.dumps(context),
                    datetime.now(UTC).isoformat()
                )
            )
            self.db.commit()
            
            if self.logger:
                self.logger.info(
                    f"[FEEDBACK] Recorded skill execution: {skill_id} -> {outcome.value} "
                    f"(execution_id: {execution_id})"
                )
            
            return execution_id
            
        except Exception as e:
            if self.logger:
                self.logger.error(f"[FEEDBACK] Failed to record skill execution: {e}")
            raise
    
    def link_execution_to_goal(
        self,
        goal_id: str,
        skill_id: str,
        execution_id: str,
        execution_order: Optional[int] = None
    ) -> None:
        """
        Link a skill execution to a goal.
        
        Args:
            goal_id: Goal ID
            skill_id: Skill ID
            execution_id: Execution ID
            execution_order: Order in goal execution sequence
        """
        try:
            link_id = str(uuid.uuid4())
            
            self.db.execute(
                """
                INSERT INTO goal_skill_executions (
                    link_id, goal_id, skill_id, execution_id, execution_order, created_at
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    link_id,
                    goal_id,
                    skill_id,
                    execution_id,
                    execution_order,
                    datetime.now(UTC).isoformat()
                )
            )
            self.db.commit()
            
            if self.logger:
                self.logger.debug(
                    f"[FEEDBACK] Linked execution {execution_id} to goal {goal_id}"
                )
                
        except Exception as e:
            if self.logger:
                self.logger.error(f"[FEEDBACK] Failed to link execution to goal: {e}")
            raise
    
    def get_goal_executions(self, goal_id: str) -> List[SkillExecution]:
        """Get all skill executions for a goal."""
        try:
            rows = self.db.fetch_all(
                """
                SELECT se.* FROM skill_executions se
                JOIN goal_skill_executions gse ON se.execution_id = gse.execution_id
                WHERE gse.goal_id = ?
                ORDER BY gse.execution_order, se.created_at
                """,
                (goal_id,)
            )
            
            return [
                SkillExecution(
                    execution_id=row["execution_id"],
                    skill_id=row["skill_id"],
                    user_id=row["user_id"],
                    message_id=row["message_id"],
                    goal_id=row["goal_id"],
                    execution_time_ms=row["execution_time_ms"],
                    outcome=SkillOutcome(row["outcome"]),
                    error_message=row["error_message"],
                    context=json.loads(row["context_json"]) if row["context_json"] else {},
                    created_at=datetime.fromisoformat(row["created_at"]).replace(tzinfo=UTC)
                )
                for row in rows
            ]
            
        except Exception as e:
            if self.logger:
                self.logger.error(f"[FEEDBACK] Failed to get goal executions: {e}")
            return []
    
    # ========================================================================
    # Behavioral Feedback Recording
    # ========================================================================
    
    def record_behavioral_feedback(
        self,
        user_id: str,
        message_id: str,
        skill_id: Optional[str],
        reward: int,
        outcome: Optional[SkillOutcome] = None,
        reason: Optional[str] = None,
        execution_time_ms: Optional[int] = None,
        context: Optional[Dict[str, Any]] = None,
        user_satisfaction: Optional[float] = None
    ) -> str:
        """
        Record behavioral feedback with outcome tracking.
        
        Args:
            user_id: User ID
            message_id: Message ID
            skill_id: Skill ID
            reward: Reward value (-1, 0, 1)
            outcome: Execution outcome
            reason: Feedback reason
            execution_time_ms: Execution time
            context: Execution context
            user_satisfaction: User satisfaction score (0.0-1.0)
            
        Returns:
            feedback_id
        """
        if reward not in [-1, 0, 1]:
            raise ValueError("Reward must be -1, 0, or 1")
        
        feedback_id = str(uuid.uuid4())
        
        try:
            self.db.execute(
                """
                INSERT INTO ams_behavioral_feedback (
                    feedback_id, user_id, message_id, skill_id, reward, reason,
                    timestamp, processed, outcome, execution_time_ms, context_json, user_satisfaction
                ) VALUES (?, ?, ?, ?, ?, ?, ?, 0, ?, ?, ?, ?)
                """,
                (
                    feedback_id,
                    user_id,
                    message_id,
                    skill_id,
                    reward,
                    reason,
                    datetime.now(UTC).isoformat(),
                    outcome.value if outcome else None,
                    execution_time_ms,
                    json.dumps(context) if context else None,
                    user_satisfaction
                )
            )
            self.db.commit()
            
            if self.logger:
                self.logger.info(
                    f"[FEEDBACK] Recorded behavioral feedback: skill={skill_id}, "
                    f"reward={reward}, outcome={outcome.value if outcome else 'N/A'}"
                )
            
            return feedback_id
            
        except Exception as e:
            if self.logger:
                self.logger.error(f"[FEEDBACK] Failed to record behavioral feedback: {e}")
            raise
    
    # ========================================================================
    # Automatic Outcome Detection
    # ========================================================================
    
    def detect_outcome_from_execution(
        self,
        execution_id: str
    ) -> Optional[SkillOutcome]:
        """
        Detect outcome from execution record.
        
        Args:
            execution_id: Execution ID
            
        Returns:
            Detected outcome or None
        """
        try:
            row = self.db.fetch_one(
                "SELECT outcome FROM skill_executions WHERE execution_id = ?",
                (execution_id,)
            )
            
            if row:
                return SkillOutcome(row["outcome"])
            
            return None
            
        except Exception as e:
            if self.logger:
                self.logger.warning(f"[FEEDBACK] Failed to detect outcome: {e}")
            return None
    
    def infer_outcome_from_reward(self, reward: int) -> SkillOutcome:
        """
        Infer outcome from reward value.
        
        Args:
            reward: Reward value (-1, 0, 1)
            
        Returns:
            Inferred outcome
        """
        if reward == 1:
            return SkillOutcome.SUCCESS
        elif reward == -1:
            return SkillOutcome.FAILURE
        else:
            return SkillOutcome.PARTIAL
    
    def update_feedback_with_outcome(
        self,
        feedback_id: str,
        outcome: SkillOutcome
    ) -> None:
        """
        Update existing feedback with detected outcome.
        
        Args:
            feedback_id: Feedback ID
            outcome: Detected outcome
        """
        try:
            self.db.execute(
                """
                UPDATE ams_behavioral_feedback
                SET outcome = ?
                WHERE feedback_id = ?
                """,
                (outcome.value, feedback_id)
            )
            self.db.commit()
            
            if self.logger:
                self.logger.debug(
                    f"[FEEDBACK] Updated feedback {feedback_id} with outcome: {outcome.value}"
                )
                
        except Exception as e:
            if self.logger:
                self.logger.error(f"[FEEDBACK] Failed to update feedback outcome: {e}")
            raise
    
    # ========================================================================
    # User Feedback Collection
    # ========================================================================
    
    def create_feedback_request(
        self,
        user_id: str,
        feedback_type: FeedbackType,
        question: str,
        goal_id: Optional[str] = None,
        skill_id: Optional[str] = None,
        execution_id: Optional[str] = None
    ) -> str:
        """
        Create a user feedback request.
        
        Args:
            user_id: User ID
            feedback_type: Type of feedback
            question: Question to ask user
            goal_id: Optional goal ID
            skill_id: Optional skill ID
            execution_id: Optional execution ID
            
        Returns:
            request_id
        """
        request_id = str(uuid.uuid4())
        
        try:
            self.db.execute(
                """
                INSERT INTO user_feedback_requests (
                    request_id, user_id, goal_id, skill_id, execution_id,
                    feedback_type, question, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    request_id,
                    user_id,
                    goal_id,
                    skill_id,
                    execution_id,
                    feedback_type.value,
                    question,
                    datetime.now(UTC).isoformat()
                )
            )
            self.db.commit()
            
            if self.logger:
                self.logger.info(
                    f"[FEEDBACK] Created feedback request: {feedback_type.value} for user {user_id}"
                )
            
            return request_id
            
        except Exception as e:
            if self.logger:
                self.logger.error(f"[FEEDBACK] Failed to create feedback request: {e}")
            raise
    
    def record_feedback_response(
        self,
        request_id: str,
        response: Optional[str] = None,
        rating: Optional[float] = None
    ) -> None:
        """
        Record user's response to feedback request.
        
        Args:
            request_id: Request ID
            response: Text response
            rating: Numeric rating
        """
        try:
            self.db.execute(
                """
                UPDATE user_feedback_requests
                SET response = ?, rating = ?, responded_at = ?
                WHERE request_id = ?
                """,
                (response, rating, datetime.now(UTC).isoformat(), request_id)
            )
            self.db.commit()
            
            if self.logger:
                self.logger.info(
                    f"[FEEDBACK] Recorded feedback response for request {request_id}"
                )
                
        except Exception as e:
            if self.logger:
                self.logger.error(f"[FEEDBACK] Failed to record feedback response: {e}")
            raise
    
    def get_pending_feedback_requests(self, user_id: str) -> List[FeedbackRequest]:
        """Get pending feedback requests for a user."""
        try:
            rows = self.db.fetch_all(
                """
                SELECT * FROM user_feedback_requests
                WHERE user_id = ? AND responded_at IS NULL
                ORDER BY created_at DESC
                LIMIT 10
                """,
                (user_id,)
            )
            
            return [
                FeedbackRequest(
                    request_id=row["request_id"],
                    user_id=row["user_id"],
                    goal_id=row["goal_id"],
                    skill_id=row["skill_id"],
                    execution_id=row["execution_id"],
                    feedback_type=FeedbackType(row["feedback_type"]),
                    question=row["question"],
                    response=row["response"],
                    rating=row["rating"],
                    responded_at=datetime.fromisoformat(row["responded_at"]).replace(tzinfo=UTC) if row["responded_at"] else None,
                    created_at=datetime.fromisoformat(row["created_at"]).replace(tzinfo=UTC)
                )
                for row in rows
            ]
            
        except Exception as e:
            if self.logger:
                self.logger.error(f"[FEEDBACK] Failed to get pending requests: {e}")
            return []
    
    # ========================================================================
    # Analytics & Reporting
    # ========================================================================
    
    def get_skill_success_rate(
        self,
        skill_id: str,
        user_id: Optional[str] = None,
        days: int = 30
    ) -> float:
        """
        Calculate success rate for a skill.
        
        Args:
            skill_id: Skill ID
            user_id: Optional user ID filter
            days: Number of days to analyze
            
        Returns:
            Success rate (0.0-1.0)
        """
        try:
            from_date = (datetime.now(UTC) - timedelta(days=days)).isoformat()
            
            if user_id:
                row = self.db.fetch_one(
                    """
                    SELECT 
                        SUM(CASE WHEN outcome = 'success' THEN 1 ELSE 0 END) as successes,
                        COUNT(*) as total
                    FROM skill_executions
                    WHERE skill_id = ? AND user_id = ? AND created_at >= ?
                    """,
                    (skill_id, user_id, from_date)
                )
            else:
                row = self.db.fetch_one(
                    """
                    SELECT 
                        SUM(CASE WHEN outcome = 'success' THEN 1 ELSE 0 END) as successes,
                        COUNT(*) as total
                    FROM skill_executions
                    WHERE skill_id = ? AND created_at >= ?
                    """,
                    (skill_id, from_date)
                )
            
            if row and row["total"] > 0:
                return row["successes"] / row["total"]
            
            return 0.5  # Default to neutral if no data
            
        except Exception as e:
            if self.logger:
                self.logger.error(f"[FEEDBACK] Failed to calculate success rate: {e}")
            return 0.5
    
    def get_user_satisfaction_trend(
        self,
        user_id: str,
        days: int = 30
    ) -> List[Dict[str, Any]]:
        """
        Get user satisfaction trend over time.
        
        Args:
            user_id: User ID
            days: Number of days to analyze
            
        Returns:
            List of satisfaction data points
        """
        try:
            from_date = (datetime.now(UTC) - timedelta(days=days)).isoformat()
            
            rows = self.db.fetch_all(
                """
                SELECT 
                    DATE(created_at) as date,
                    AVG(rating) as avg_rating,
                    COUNT(*) as count
                FROM user_feedback_requests
                WHERE user_id = ? AND responded_at IS NOT NULL AND created_at >= ?
                GROUP BY DATE(created_at)
                ORDER BY date
                """,
                (user_id, from_date)
            )
            
            return [
                {
                    "date": row["date"],
                    "avg_rating": row["avg_rating"],
                    "count": row["count"]
                }
                for row in rows
            ]
            
        except Exception as e:
            if self.logger:
                self.logger.error(f"[FEEDBACK] Failed to get satisfaction trend: {e}")
            return []
