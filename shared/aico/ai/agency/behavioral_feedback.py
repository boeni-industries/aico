"""
Behavioral Feedback Integration - Phase 6.6

Connects skill executions to behavioral feedback, implements automatic outcome
detection, and completes the feedback loop for behavioral learning.
"""

from __future__ import annotations

import json
import uuid
from typing import Dict, List, Optional, Any, TYPE_CHECKING
from datetime import datetime, timedelta, UTC
from dataclasses import dataclass
from enum import Enum

if TYPE_CHECKING:
    from aico.services.agency_service import AgencyService



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
        agency_service: "AgencyService",
        logger=None
    ):
        self.agency_service = agency_service
        self.logger = logger
    
    # ========================================================================
    # Skill Execution Tracking
    # ========================================================================
    
    async def record_skill_execution(
        self,
        execution_id: str,
        skill_id: str,
        user_id: str,
        message_id: Optional[str] = None,
        goal_id: Optional[str] = None,
        execution_time_ms: Optional[int] = None,
        outcome: SkillOutcome = SkillOutcome.SUCCESS,
        error_message: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Record a skill execution.
        
        Args:
            execution_id: ID of the skill execution
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
        execution_id = execution_id or str(uuid.uuid4())
        context = context or {}
        
        try:
            execution_data = {
                "execution_id": execution_id,
                "skill_id": skill_id,
                "user_id": user_id,
                "message_id": message_id,
                "goal_id": goal_id,
                "execution_time_ms": execution_time_ms,
                "outcome": outcome.value,
                "error_message": error_message,
                "context_json": context,
                "created_at": datetime.now(UTC)
            }
            
            await self.agency_service.record_skill_execution(execution_data)
            
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
    
    async def link_execution_to_goal(
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
            link_data = {
                "link_id": str(uuid.uuid4()),
                "goal_id": goal_id,
                "skill_id": skill_id,
                "execution_id": execution_id,
                "execution_order": execution_order,
                "created_at": datetime.now(UTC)
            }
            
            await self.agency_service.link_goal_skill_execution(link_data)
            
            if self.logger:
                self.logger.debug(
                    f"[FEEDBACK] Linked execution {execution_id} to goal {goal_id}"
                )
                
        except Exception as e:
            if self.logger:
                self.logger.error(f"[FEEDBACK] Failed to link execution to goal: {e}")
            raise
    
    async def get_goal_executions(self, goal_id: str) -> List[SkillExecution]:
        """Get all skill executions for a goal."""
        try:
            rows = await self.agency_service.get_goal_executions(goal_id)
            
            return [
                SkillExecution(
                    execution_id=row["execution_id"],
                    skill_id=row["skill_id"],
                    user_id=row["user_id"],
                    message_id=row.get("message_id"),
                    goal_id=row.get("goal_id"),
                    execution_time_ms=row.get("execution_time_ms"),
                    outcome=SkillOutcome(row["outcome"]),
                    error_message=row.get("error_message"),
                    context=row.get("context_json", {}),
                    created_at=row["created_at"] if isinstance(row["created_at"], datetime) else datetime.fromisoformat(row["created_at"]).replace(tzinfo=UTC)
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
    
    async def record_behavioral_feedback(
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
            feedback_data = {
                "feedback_id": feedback_id,
                "user_id": user_id,
                "message_id": message_id,
                "skill_id": skill_id,
                "reward": reward,
                "reason": reason,
                "timestamp": datetime.now(UTC),
                "processed": False,
                "outcome": outcome.value if outcome else None,
                "execution_time_ms": execution_time_ms,
                "context_json": context,
                "user_satisfaction": user_satisfaction
            }
            
            await self.agency_service.record_behavioral_feedback(feedback_data)
            
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
    
    async def detect_outcome_from_execution(
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
            outcome_str = await self.agency_service.get_skill_execution_outcome(execution_id)
            
            if outcome_str:
                return SkillOutcome(outcome_str)
            
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
    
    async def update_feedback_with_outcome(
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
            await self.agency_service.update_feedback_outcome(feedback_id, outcome.value)
            
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
    
    async def create_feedback_request(
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
            request_data = {
                "request_id": request_id,
                "user_id": user_id,
                "goal_id": goal_id,
                "skill_id": skill_id,
                "execution_id": execution_id,
                "feedback_type": feedback_type.value,
                "question": question,
                "created_at": datetime.now(UTC)
            }
            
            await self.agency_service.create_feedback_request(request_data)
            
            if self.logger:
                self.logger.info(
                    f"[FEEDBACK] Created feedback request: {feedback_type.value} for user {user_id}"
                )
            
            return request_id
            
        except Exception as e:
            if self.logger:
                self.logger.error(f"[FEEDBACK] Failed to create feedback request: {e}")
            raise
    
    async def record_feedback_response(
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
            await self.agency_service.respond_to_feedback_request(request_id, response, rating)
            
            if self.logger:
                self.logger.info(
                    f"[FEEDBACK] Recorded feedback response for request {request_id}"
                )
                
        except Exception as e:
            if self.logger:
                self.logger.error(f"[FEEDBACK] Failed to record feedback response: {e}")
            raise
    
    async def get_pending_feedback_requests(self, user_id: str) -> List[FeedbackRequest]:
        """Get pending feedback requests for a user."""
        try:
            rows = await self.agency_service.get_pending_feedback_requests(user_id)
            
            return [
                FeedbackRequest(
                    request_id=row["request_id"],
                    user_id=row["user_id"],
                    goal_id=row.get("goal_id"),
                    skill_id=row.get("skill_id"),
                    execution_id=row.get("execution_id"),
                    feedback_type=FeedbackType(row["feedback_type"]),
                    question=row["question"],
                    response=row.get("response"),
                    rating=row.get("rating"),
                    responded_at=row["responded_at"] if isinstance(row.get("responded_at"), datetime) else (datetime.fromisoformat(row["responded_at"]).replace(tzinfo=UTC) if row.get("responded_at") else None),
                    created_at=row["created_at"] if isinstance(row["created_at"], datetime) else datetime.fromisoformat(row["created_at"]).replace(tzinfo=UTC)
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
    
    async def get_skill_success_rate(
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
            stats = await self.agency_service.get_skill_performance_stats(skill_id, user_id, days)
            
            if stats and stats.get("total", 0) > 0:
                return stats["successes"] / stats["total"]
            
            return 0.5  # Default to neutral if no data
            
        except Exception as e:
            if self.logger:
                self.logger.error(f"[FEEDBACK] Failed to calculate success rate: {e}")
            return 0.5
    
    async def get_user_satisfaction_trend(
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
            # Note: This would need a new AgencyService method for trend data
            # For now, return empty list as this is analytics/reporting
            # TODO: Add get_user_satisfaction_trend to AgencyService
            if self.logger:
                self.logger.warning("[FEEDBACK] get_user_satisfaction_trend not yet implemented in AgencyService")
            return []
            
        except Exception as e:
            if self.logger:
                self.logger.error(f"[FEEDBACK] Failed to get satisfaction trend: {e}")
            return []
