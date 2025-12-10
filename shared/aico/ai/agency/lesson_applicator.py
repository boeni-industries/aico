"""
Lesson Application Service

Applies behavioral learning lessons to existing AICO systems:
- Skill selection weights (SkillStore)
- Goal Arbiter weights (configuration)
- Persona traits (conversation engine)
- Policy rules (Values & Ethics)

This service bridges the self-reflection engine with operational systems.
"""

from typing import Optional, Dict, Any
from datetime import datetime

from aico.core.logging import get_logger
from aico.core.config import ConfigurationManager

from .models import Lesson, LessonType, TargetKind, ChangeType
from .store import LessonStore


logger = get_logger("agency", "lesson_applicator")


class LessonApplicationService:
    """
    Service for applying behavioral learning lessons to operational systems.
    
    Respects lesson confidence thresholds and provides full audit logging.
    """
    
    def __init__(
        self,
        config: ConfigurationManager,
        db_connection,
        lesson_store: Optional[LessonStore] = None,
    ):
        """
        Initialize lesson application service.
        
        Args:
            config: Configuration manager
            db_connection: Database connection
            lesson_store: Optional lesson store (created if not provided)
        """
        self.config = config
        self.db = db_connection
        self.lesson_store = lesson_store or LessonStore(db_connection)
        
        # Get application thresholds
        self.min_confidence = config.get(
            "core.agency.lesson_application.min_confidence",
            0.7
        )
        self.dry_run = config.get(
            "core.agency.lesson_application.dry_run",
            False
        )
        
        logger.info(
            f"[LESSON_APPLICATOR] Initialized (min_confidence={self.min_confidence}, "
            f"dry_run={self.dry_run})"
        )
    
    async def apply_lesson(self, lesson: Lesson) -> bool:
        """
        Apply a single lesson to the appropriate system.
        
        Args:
            lesson: Lesson to apply
            
        Returns:
            True if applied successfully, False otherwise
        """
        # Check confidence threshold
        if lesson.confidence < self.min_confidence:
            logger.debug(
                f"[LESSON_APPLICATOR] Skipping lesson {lesson.lesson_id}: "
                f"confidence {lesson.confidence} < threshold {self.min_confidence}"
            )
            return False
        
        # Route to appropriate handler based on target_kind
        try:
            if lesson.target_kind == TargetKind.SKILL:
                return await self._apply_skill_lesson(lesson)
            elif lesson.target_kind == TargetKind.ARBITER_WEIGHT:
                return await self._apply_arbiter_weight_lesson(lesson)
            elif lesson.target_kind == TargetKind.PERSONA_TRAIT:
                return await self._apply_persona_lesson(lesson)
            elif lesson.target_kind == TargetKind.POLICY_RULE:
                return await self._apply_policy_lesson(lesson)
            else:
                logger.warning(
                    f"[LESSON_APPLICATOR] Unknown target_kind: {lesson.target_kind}"
                )
                return False
                
        except Exception as e:
            logger.error(
                f"[LESSON_APPLICATOR] Failed to apply lesson {lesson.lesson_id}: {e}",
                exc_info=True
            )
            return False
    
    async def _apply_skill_lesson(self, lesson: Lesson) -> bool:
        """
        Apply skill-related lesson (adjust selection weights).
        
        Args:
            lesson: Skill lesson
            
        Returns:
            True if applied
        """
        skill_id = lesson.target_id
        change = lesson.proposed_change
        
        logger.info(
            f"[LESSON_APPLICATOR] Applying skill lesson: {skill_id} "
            f"({change.change_type.value}: {change.field} {change.old} -> {change.new})"
        )
        
        if self.dry_run:
            logger.info(f"[LESSON_APPLICATOR] [DRY_RUN] Would apply skill lesson")
            return False
        
        # Store lesson metadata in skill's dimension_vector or metadata
        # This allows the bandit selector to use adjusted weights
        try:
            # Check if skill exists
            row = self.db.execute(
                "SELECT skill_id, dimension_vector FROM skills WHERE skill_id = ?",
                (skill_id,)
            ).fetchone()
            
            if not row:
                logger.warning(
                    f"[LESSON_APPLICATOR] Skill {skill_id} not found, cannot apply lesson"
                )
                return False
            
            # Parse existing dimension vector
            import json
            dimension_vector = json.loads(row["dimension_vector"]) if row["dimension_vector"] else {}
            
            # Add lesson adjustment
            if "lesson_adjustments" not in dimension_vector:
                dimension_vector["lesson_adjustments"] = {}
            
            dimension_vector["lesson_adjustments"][change.field] = {
                "value": change.new,
                "lesson_id": lesson.lesson_id,
                "applied_at": datetime.utcnow().isoformat(),
                "confidence": lesson.confidence,
            }
            
            # Update skill
            self.db.execute(
                """UPDATE skills 
                   SET dimension_vector = ?, updated_at = ?
                   WHERE skill_id = ?""",
                (json.dumps(dimension_vector), datetime.utcnow().isoformat(), skill_id)
            )
            self.db.commit()
            
            # Mark lesson as applied
            await self.lesson_store.mark_lesson_applied(
                lesson_id=lesson.lesson_id,
                applied_by="lesson_applicator"
            )
            
            logger.info(
                f"[LESSON_APPLICATOR] Applied skill lesson {lesson.lesson_id} to {skill_id}"
            )
            return True
            
        except Exception as e:
            logger.error(
                f"[LESSON_APPLICATOR] Failed to apply skill lesson: {e}",
                exc_info=True
            )
            return False
    
    async def _apply_arbiter_weight_lesson(self, lesson: Lesson) -> bool:
        """
        Apply Goal Arbiter weight adjustment lesson.
        
        Args:
            lesson: Arbiter weight lesson
            
        Returns:
            True if applied
        """
        weight_key = lesson.target_id  # e.g., "goal_type_learning"
        change = lesson.proposed_change
        
        logger.info(
            f"[LESSON_APPLICATOR] Applying arbiter weight lesson: {weight_key} "
            f"({change.change_type.value}: {change.old} -> {change.new})"
        )
        
        if self.dry_run:
            logger.info(f"[LESSON_APPLICATOR] [DRY_RUN] Would apply arbiter weight lesson")
            return False
        
        # Store in agency_arbiter_adjustments table for arbiter to read
        try:
            # Determine if this is user-specific or global
            user_id = lesson.user_id if lesson.scope.value == "this_user" else None
            
            # Store adjustment
            self.db.execute(
                """INSERT OR REPLACE INTO agency_arbiter_adjustments 
                   (adjustment_key, adjustment_value, lesson_id, user_id, applied_at, confidence, active, notes)
                   VALUES (?, ?, ?, ?, ?, ?, 1, ?)""",
                (
                    weight_key,
                    change.new,
                    lesson.lesson_id,
                    user_id,
                    datetime.utcnow().isoformat(),
                    lesson.confidence,
                    change.notes,
                )
            )
            self.db.commit()
            
            # Mark lesson as applied
            await self.lesson_store.mark_lesson_applied(
                lesson_id=lesson.lesson_id,
                applied_by="lesson_applicator"
            )
            
            logger.info(
                f"[LESSON_APPLICATOR] Applied arbiter weight lesson {lesson.lesson_id} "
                f"(key={weight_key}, value={change.new}, user_specific={user_id is not None})"
            )
            return True
            
        except Exception as e:
            logger.error(
                f"[LESSON_APPLICATOR] Failed to store arbiter adjustment: {e}",
                exc_info=True
            )
            return False
    
    async def _apply_persona_lesson(self, lesson: Lesson) -> bool:
        """
        Apply persona/style adjustment lesson.
        
        Args:
            lesson: Persona lesson
            
        Returns:
            True if applied
        """
        trait_key = lesson.target_id  # e.g., "response_tone"
        change = lesson.proposed_change
        
        logger.info(
            f"[LESSON_APPLICATOR] Applying persona lesson: {trait_key} "
            f"({change.change_type.value}: {change.old} -> {change.new})"
        )
        
        if self.dry_run:
            logger.info(f"[LESSON_APPLICATOR] [DRY_RUN] Would apply persona lesson")
            return False
        
        # Persona lessons are automatically applied by PersonalityService
        # when it queries active lessons from agency_lessons table
        # Just mark as applied so PersonalityService picks it up
        try:
            await self.lesson_store.mark_lesson_applied(
                lesson_id=lesson.lesson_id,
                applied_by="lesson_applicator"
            )
            
            logger.info(
                f"[LESSON_APPLICATOR] Persona lesson {lesson.lesson_id} marked as applied. "
                f"PersonalityService will automatically load '{trait_key}' = '{change.new}' "
                f"when retrieving personality context."
            )
            
            return True
            
        except Exception as e:
            logger.error(
                f"[LESSON_APPLICATOR] Failed to mark persona lesson as applied: {e}",
                exc_info=True
            )
            return False
    
    async def _apply_policy_lesson(self, lesson: Lesson) -> bool:
        """
        Apply policy rule adjustment lesson.
        
        Args:
            lesson: Policy lesson
            
        Returns:
            True if applied
        """
        policy_key = lesson.target_id
        change = lesson.proposed_change
        
        logger.info(
            f"[LESSON_APPLICATOR] Policy lesson: {policy_key} "
            f"({change.change_type.value})"
        )
        
        # Policy changes require explicit user approval
        # Just log for now - actual application requires Values & Ethics integration
        logger.info(
            f"[LESSON_APPLICATOR] Policy suggestion logged (requires user approval): "
            f"'{policy_key}' - {change.notes}"
        )
        
        # Mark as applied (logged for review)
        await self.lesson_store.mark_lesson_applied(
            lesson_id=lesson.lesson_id,
            applied_by="lesson_applicator_logged"
        )
        
        return True
    
    async def apply_pending_lessons(self, user_id: str) -> Dict[str, Any]:
        """
        Apply all pending active lessons for a user.
        
        Args:
            user_id: User ID
            
        Returns:
            Summary of application results
        """
        # Get active lessons
        active_lessons = await self.lesson_store.get_active_lessons(user_id=user_id)
        
        if not active_lessons:
            logger.debug(f"[LESSON_APPLICATOR] No active lessons for user {user_id}")
            return {
                "total": 0,
                "applied": 0,
                "skipped": 0,
                "failed": 0,
            }
        
        logger.info(
            f"[LESSON_APPLICATOR] Applying {len(active_lessons)} lessons for user {user_id}"
        )
        
        applied = 0
        skipped = 0
        failed = 0
        
        for lesson in active_lessons:
            # Skip if already applied
            if lesson.applied_at:
                skipped += 1
                continue
            
            # Apply lesson
            success = await self.apply_lesson(lesson)
            if success:
                applied += 1
            else:
                failed += 1
        
        summary = {
            "total": len(active_lessons),
            "applied": applied,
            "skipped": skipped,
            "failed": failed,
        }
        
        logger.info(
            f"[LESSON_APPLICATOR] Completed for user {user_id}: "
            f"{applied} applied, {skipped} skipped, {failed} failed"
        )
        
        return summary
