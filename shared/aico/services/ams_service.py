"""
AMS (Adaptive Memory System) Service

Replaces shared/aico/ai/memory/behavioral/*.py with repository-based implementation.
Provides high-level AMS operations using the 10 AMS repositories.
"""

from __future__ import annotations

from datetime import datetime, UTC
from typing import Any, Dict, List, Optional

from aico.core.logging import get_logger
from aico.data.uow import UnitOfWork

logger = get_logger("shared.services.ams")


class AMSService:
    """
    Service layer for Adaptive Memory System operations.
    
    Handles trajectories, behavioral feedback, skills, preferences, and context.
    Uses AMS repositories through Unit of Work pattern.
    """

    def __init__(self, uow: UnitOfWork):
        self.uow = uow

    # ==================== Trajectory Operations ====================

    async def create_trajectory(self, trajectory_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new trajectory."""
        try:
            from aico.ai.ams.models import AMSTrajectory
            
            trajectory = AMSTrajectory(**trajectory_data)
            created = await self.uow.ams_trajectories.create(trajectory)
            await self.uow.commit()
            
            logger.info("[AMS_SERVICE] Created trajectory", extra={"trajectory_id": created.trajectory_id})
            return created
        except Exception as e:
            logger.error(f"[AMS_SERVICE] Failed to create trajectory: {e}")
            await self.uow.rollback()
            raise

    async def get_trajectory(self, trajectory_id: str) -> Optional[Any]:
        """Retrieve a trajectory by ID."""
        try:
            return await self.uow.ams_trajectories.get_by_id(trajectory_id)
        except Exception as e:
            logger.error(f"[AMS_SERVICE] Failed to retrieve trajectory: {e}", extra={"trajectory_id": trajectory_id})
            raise

    async def list_user_trajectories(self, user_id: str, limit: int = 100) -> List[Any]:
        """List recent trajectories for a user."""
        try:
            return await self.uow.ams_trajectories.list(filters={"user_id": user_id}, limit=limit)
        except Exception as e:
            logger.error(f"[AMS_SERVICE] Failed to list user trajectories: {e}", extra={"user_id": user_id})
            raise

    async def delete_trajectory(self, trajectory_id: str) -> bool:
        """Delete a trajectory."""
        try:
            success = await self.uow.ams_trajectories.delete(trajectory_id)
            await self.uow.commit()
            logger.info("[AMS_SERVICE] Deleted trajectory", extra={"trajectory_id": trajectory_id})
            return success
        except Exception as e:
            logger.error(f"[AMS_SERVICE] Failed to delete trajectory: {e}", extra={"trajectory_id": trajectory_id})
            await self.uow.rollback()
            raise

    async def update_trajectory(self, trajectory_data: Dict[str, Any]) -> Dict[str, Any]:
        """Update a trajectory."""
        try:
            from aico.ai.ams.models import AMSTrajectory
            
            trajectory = AMSTrajectory(**trajectory_data)
            updated = await self.uow.ams_trajectories.update(trajectory)
            await self.uow.commit()
            
            logger.info("[AMS_SERVICE] Updated trajectory", extra={"trajectory_id": trajectory.trajectory_id})
            return updated
        except Exception as e:
            logger.error(f"[AMS_SERVICE] Failed to update trajectory: {e}")
            await self.uow.rollback()
            raise

    # ==================== Behavioral Feedback Operations ====================

    async def create_feedback(self, feedback_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create behavioral feedback."""
        try:
            from aico.ai.ams.models import AMSBehavioralFeedback
            
            feedback = AMSBehavioralFeedback(**feedback_data)
            created = await self.uow.ams_behavioral_feedback.create(feedback)
            await self.uow.commit()
            
            logger.info("[AMS_SERVICE] Created feedback", extra={"feedback_id": created.feedback_id})
            return created
        except Exception as e:
            logger.error(f"[AMS_SERVICE] Failed to create feedback: {e}")
            await self.uow.rollback()
            raise

    async def get_user_feedback(self, user_id: str, limit: int = 50) -> List[Any]:
        """Get recent feedback for a user."""
        try:
            return await self.uow.ams_behavioral_feedback.list(filters={"user_id": user_id}, limit=limit)
        except Exception as e:
            logger.error(f"[AMS_SERVICE] Failed to get feedback: {e}", extra={"user_id": user_id})
            raise

    # ==================== Behavioral Skills Operations ====================

    async def create_skill(self, skill_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a behavioral skill."""
        try:
            from aico.ai.ams.models import AMSBehavioralSkill
            
            skill = AMSBehavioralSkill(**skill_data)
            created = await self.uow.ams_behavioral_skills.create(skill)
            await self.uow.commit()
            
            logger.info("[AMS_SERVICE] Created skill", extra={"skill_id": created.skill_id})
            return created
        except Exception as e:
            logger.error(f"[AMS_SERVICE] Failed to create skill: {e}")
            await self.uow.rollback()
            raise

    async def get_user_skills(self, user_id: str) -> List[Any]:
        """Get all skills for a user."""
        try:
            return await self.uow.ams_behavioral_skills.list(filters={"user_id": user_id})
        except Exception as e:
            logger.error(f"[AMS_SERVICE] Failed to get skills: {e}", extra={"user_id": user_id})
            raise

    async def update_skill_confidence(self, user_id: str, skill_id: str, confidence: float, usage_count: int) -> bool:
        """Update skill confidence level."""
        try:
            from aico.data.ams.models import UserSkillConfidence
            
            confidence_data = UserSkillConfidence(
                user_id=user_id,
                skill_id=skill_id,
                confidence_level=confidence,
                usage_count=usage_count,
                last_used=datetime.now(UTC).isoformat(),
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC)
            )
            
            await self.uow.user_skill_confidence.create(confidence_data)
            await self.uow.commit()
            
            logger.info("[AMS_SERVICE] Updated skill confidence", extra={"user_id": user_id, "skill_id": skill_id})
            return True
        except Exception as e:
            logger.error(f"[AMS_SERVICE] Failed to update skill confidence: {e}")
            await self.uow.rollback()
            raise

    # ==================== Context Preference Operations ====================

    async def create_context_preference_vector(self, user_id: str, context_bucket: int, dimensions: str) -> Dict[str, Any]:
        """Create a context preference vector."""
        try:
            from aico.data.ams.models import AMSContextPreferenceVector
            
            vector = AMSContextPreferenceVector(
                user_id=user_id,
                context_bucket=context_bucket,
                dimensions=dimensions,
                last_updated_at=datetime.now(UTC)
            )
            
            created = await self.uow.ams_context_preference_vectors.create(vector)
            await self.uow.commit()
            
            logger.info("[AMS_SERVICE] Created context preference vector", extra={"user_id": user_id, "context_bucket": context_bucket})
            return created
        except Exception as e:
            logger.error(f"[AMS_SERVICE] Failed to create context preference vector: {e}")
            await self.uow.rollback()
            raise

    async def get_user_context_vectors(self, user_id: str) -> List[Any]:
        """Get all context preference vectors for a user."""
        try:
            return await self.uow.ams_context_preference_vectors.list(filters={"user_id": user_id})
        except Exception as e:
            logger.error(f"[AMS_SERVICE] Failed to get context vectors: {e}", extra={"user_id": user_id})
            raise

    # ==================== Context Skill Stats Operations ====================

    async def update_context_skill_stats(self, user_id: str, context_bucket: int, skill_id: str, alpha: float, beta: float) -> Dict[str, Any]:
        """Update context-specific skill statistics."""
        try:
            from aico.data.ams.models import AMSContextSkillStats
            
            stats = AMSContextSkillStats(
                user_id=user_id,
                context_bucket=context_bucket,
                skill_id=skill_id,
                alpha=alpha,
                beta=beta,
                last_updated_at=datetime.now(UTC)
            )
            
            created = await self.uow.ams_context_skill_stats.create(stats)
            await self.uow.commit()
            
            logger.info("[AMS_SERVICE] Updated context skill stats", extra={"user_id": user_id, "skill_id": skill_id})
            return created
        except Exception as e:
            logger.error(f"[AMS_SERVICE] Failed to update context skill stats: {e}")
            await self.uow.rollback()
            raise

    async def get_user_context_stats(self, user_id: str, context_bucket: int) -> List[Any]:
        """Get context-specific skill stats for a user."""
        try:
            return await self.uow.ams_context_skill_stats.list(filters={"user_id": user_id, "context_bucket": context_bucket})
        except Exception as e:
            logger.error(f"[AMS_SERVICE] Failed to get context stats: {e}", extra={"user_id": user_id})
            raise

    # ==================== User Memory Operations ====================

    async def create_user_memory(self, memory_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a user memory entry."""
        try:
            from aico.data.ams.models import AMSUserMemory
            
            memory = AMSUserMemory(**memory_data)
            created = await self.uow.ams_user_memories.create(memory)
            await self.uow.commit()
            
            logger.info("[AMS_SERVICE] Created user memory", extra={"memory_id": created.memory_id})
            return created
        except Exception as e:
            logger.error(f"[AMS_SERVICE] Failed to create user memory: {e}")
            await self.uow.rollback()
            raise

    async def get_user_memories(self, user_id: str, memory_type: Optional[str] = None) -> List[Any]:
        """Get user memories, optionally filtered by type."""
        try:
            filters = {"user_id": user_id}
            if memory_type:
                filters["memory_type"] = memory_type
            
            return await self.uow.ams_user_memories.list(filters=filters)
        except Exception as e:
            logger.error(f"[AMS_SERVICE] Failed to get user memories: {e}", extra={"user_id": user_id})
            raise

    # ==================== Analytics Operations ====================

    async def get_trajectory_count(self, user_id: str) -> int:
        """Get total trajectory count for a user."""
        try:
            return await self.uow.ams_trajectories.count(filters={"user_id": user_id})
        except Exception as e:
            logger.error(f"[AMS_SERVICE] Failed to count trajectories: {e}", extra={"user_id": user_id})
            raise

    async def get_feedback_count(self, user_id: str) -> int:
        """Get total feedback count for a user."""
        try:
            return await self.uow.ams_behavioral_feedback.count(filters={"user_id": user_id})
        except Exception as e:
            logger.error(f"[AMS_SERVICE] Failed to count feedback: {e}", extra={"user_id": user_id})
            raise
