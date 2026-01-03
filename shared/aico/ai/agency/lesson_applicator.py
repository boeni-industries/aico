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
from datetime import datetime, UTC

from aico.core.logging import get_logger
from aico.core.config import ConfigurationManager

from .models import Lesson, LessonType, TargetKind, ChangeType
from .store import LessonStore
from .lesson_projector import LessonMemoryProjector


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
        kg_storage=None,  # PropertyGraphStorage for KG integration
    ):
        """
        Initialize lesson application service.
        
        Args:
            config: Configuration manager
            db_connection: Database connection
            lesson_store: Optional lesson store (created if not provided)
            kg_storage: Optional PropertyGraphStorage for KG integration
        """
        self.config = config
        self.db = db_connection
        self.lesson_store = lesson_store or LessonStore(db_connection)
        
        # Initialize projector for AMS/KG integration
        self.projector = LessonMemoryProjector(
            config=config,
            db_connection=db_connection,
            kg_storage=kg_storage,
        )
        
        # Get application thresholds
        self.min_confidence = config.get(
            "core.agency.lesson_application.min_confidence",
            0.7
        )
        self.dry_run = config.get(
            "core.agency.lesson_application.dry_run",
            False
        )
        
        # Policy amendment safety settings
        self.policy_amendment_limit = config.get(
            "core.agency.lesson_application.policy_amendment_limit_per_day",
            5  # Max 5 policy changes per day
        )
        self.policy_freeze = config.get(
            "core.agency.lesson_application.policy_freeze",
            False  # Emergency freeze mechanism
        )
        
        logger.debug(
            f"[LESSON_APPLICATOR] Initialized (min_confidence={self.min_confidence}, "
            f"dry_run={self.dry_run}, policy_amendment_limit={self.policy_amendment_limit}/day, "
            f"policy_freeze={self.policy_freeze})"
        )
    
    async def apply_lesson(self, lesson: Lesson, reflection_run=None) -> bool:
        """
        Apply a single lesson to the appropriate system.
        
        Args:
            lesson: Lesson to apply
            reflection_run: Optional reflection run for provenance tracking
            
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
            applied = False
            if lesson.target_kind == TargetKind.SKILL:
                applied = await self._apply_skill_lesson(lesson)
            elif lesson.target_kind == TargetKind.ARBITER_WEIGHT:
                applied = await self._apply_arbiter_weight_lesson(lesson)
            elif lesson.target_kind == TargetKind.PERSONA_TRAIT:
                applied = await self._apply_persona_lesson(lesson)
            elif lesson.target_kind == TargetKind.POLICY_RULE:
                applied = await self._apply_policy_lesson(lesson)
            else:
                logger.warning(
                    f"[LESSON_APPLICATOR] Unknown target_kind: {lesson.target_kind}"
                )
                return False
            
            # Project to Memory/AMS and KG if successfully applied
            if applied:
                await self.projector.project_lesson_to_memory(lesson)
                await self.projector.project_lesson_to_kg(lesson, reflection_run)
            
            return applied
                
        except Exception as e:
            logger.exception(f"[LESSON_APPLICATOR] Failed to apply lesson {lesson.lesson_id}: {e}")
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
            # Check if skill learning data exists
            row = self.db.execute(
                "SELECT skill_id, dimension_vector FROM agency_skill_learning_data WHERE skill_id = ?",
                (skill_id,)
            ).fetchone()
            
            if not row:
                # Initialize learning data for new skill
                logger.info(
                    f"[LESSON_APPLICATOR] Initializing learning data for skill {skill_id}"
                )
                dimension_vector = [0.0] * 11  # Default 11-dimensional vector
            else:
                # Parse existing dimension vector
                try:
                    dimension_vector = json.loads(row["dimension_vector"])
                except (json.JSONDecodeError, KeyError):
                    logger.warning(
                        f"[LESSON_APPLICATOR] Invalid dimension vector for skill {skill_id}, reinitializing"
                    )
                    dimension_vector = [0.0] * 11  # Default 11-dimensional vector
            
            # Apply adjustments
            for dim_idx, adjustment in change.items():
                if 0 <= dim_idx < len(dimension_vector):
                    dimension_vector[dim_idx] += adjustment
                    # Clamp to [-1, 1] range
                    dimension_vector[dim_idx] = max(-1.0, min(1.0, dimension_vector[dim_idx]))
            
            # Insert or update skill learning data
            now = datetime.now(UTC).isoformat()
            self.db.execute(
                """INSERT OR REPLACE INTO skill_learning_data 
                   (skill_id, dimension_vector, created_at, updated_at)
                   VALUES (?, ?, ?, ?)""",
                (skill_id, json.dumps(dimension_vector), now, now)
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
            logger.exception(f"[LESSON_APPLICATOR] Failed to apply skill performance lesson: {e}")
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
                    datetime.now(UTC).isoformat(),
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
            logger.exception(
                f"[LESSON_APPLICATOR] Failed to store arbiter adjustment: {e}"
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
            logger.exception(
                f"[LESSON_APPLICATOR] Failed to mark persona lesson as applied: {e}"
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
        
        # Check policy_mode configuration
        policy_mode = self.config.get(
            "core.agency.self_reflection.policy_mode",
            "observe_only"
        )
        
        if policy_mode == "observe_only":
            # Just log for review - do not modify policies
            logger.info(
                f"[LESSON_APPLICATOR] Policy suggestion logged (observe_only mode): "
                f"'{policy_key}' - {change.notes}"
            )
            
            # Mark as applied (logged for review)
            await self.lesson_store.mark_lesson_applied(
                lesson_id=lesson.lesson_id,
                applied_by="lesson_applicator_logged"
            )
            
            return True
        
        elif policy_mode == "allow_amend":
            # Actually apply policy amendment through Values & Ethics service
            return await self._apply_policy_amendment(lesson, policy_key, change)
        
        else:
            logger.error(f"[LESSON_APPLICATOR] Unknown policy_mode: {policy_mode}")
            return False
    
    async def _apply_policy_amendment(self, lesson: Lesson, policy_key: str, change) -> bool:
        """
        Apply policy amendment through Values & Ethics service (allow_amend mode).
        
        Args:
            lesson: Policy lesson
            policy_key: Policy rule ID
            change: Proposed change
            
        Returns:
            True if applied successfully
        """
        import json
        from datetime import datetime, timedelta
        
        logger.info(
            f"[LESSON_APPLICATOR] Applying policy amendment (allow_amend mode): "
            f"'{policy_key}' - {change.change_type.value}"
        )
        
        # Check emergency freeze
        if self.policy_freeze:
            logger.warning(
                f"[LESSON_APPLICATOR] Policy freeze active - amendment blocked"
            )
            return False
        
        # Check rate limiting
        if not await self._check_policy_amendment_rate_limit(lesson.user_id):
            logger.warning(
                f"[LESSON_APPLICATOR] Policy amendment rate limit exceeded for user {lesson.user_id}"
            )
            return False
        
        if self.dry_run:
            logger.info(f"[LESSON_APPLICATOR] [DRY_RUN] Would apply policy amendment")
            return False
        
        try:
            # Get current policy rule
            policy_row = self.db.execute(
                "SELECT * FROM agency_policy_rules WHERE rule_id = ?",
                (policy_key,)
            ).fetchone()
            
            if not policy_row:
                logger.warning(
                    f"[LESSON_APPLICATOR] Policy rule {policy_key} not found"
                )
                return False
            
            # Store old values for audit trail
            old_rule_data = dict(policy_row)
            
            # Apply change based on change_type
            if change.change_type == ChangeType.WEIGHT_TWEAK:
                # Update numeric field (e.g., priority, threshold)
                field = change.field
                new_value = change.new
                
                # Validate field exists
                if field not in old_rule_data:
                    logger.error(
                        f"[LESSON_APPLICATOR] Field '{field}' not found in policy rule"
                    )
                    return False
                
                # Update policy rule
                self.db.execute(
                    f"UPDATE agency_policy_rules SET {field} = ?, updated_at = ? WHERE rule_id = ?",
                    (new_value, datetime.now(UTC).isoformat(), policy_key)
                )
                
            elif change.change_type == ChangeType.THRESHOLD_TWEAK:
                # Update threshold in conditions JSON
                conditions = json.loads(policy_row["conditions"]) if policy_row["conditions"] else {}
                conditions[change.field] = change.new
                
                self.db.execute(
                    "UPDATE agency_policy_rules SET conditions = ?, updated_at = ? WHERE rule_id = ?",
                    (json.dumps(conditions), datetime.now(UTC).isoformat(), policy_key)
                )
                
            else:
                logger.warning(
                    f"[LESSON_APPLICATOR] Unsupported change_type for policy: {change.change_type.value}"
                )
                return False
            
            self.db.commit()
            
            # Create audit trail entry
            audit_entry = {
                "timestamp": datetime.now(UTC).isoformat(),
                "lesson_id": lesson.lesson_id,
                "policy_rule_id": policy_key,
                "change_type": change.change_type.value,
                "field": change.field,
                "old_value": change.old,
                "new_value": change.new,
                "initiator": "self_reflection",
                "confidence": lesson.confidence,
                "rationale": lesson.summary_text,
            }
            
            # Log audit entry
            logger.info(
                f"[LESSON_APPLICATOR] Policy amendment applied: {json.dumps(audit_entry, indent=2)}"
            )
            
            # Mark lesson as applied
            await self.lesson_store.mark_lesson_applied(
                lesson_id=lesson.lesson_id,
                applied_by="values_ethics_service"
            )
            
            # TODO: Emit audit event to message bus for external monitoring
            
            return True
            
        except Exception as e:
            logger.exception(
                f"[LESSON_APPLICATOR] Failed to apply policy amendment: {e}"
            )
            # Rollback on error
            self.db.rollback()
            return False
    
    async def _check_policy_amendment_rate_limit(self, user_id: str) -> bool:
        """
        Check if policy amendment rate limit has been exceeded.
        
        Args:
            user_id: User ID
            
        Returns:
            True if within rate limit, False if exceeded
        """
        from datetime import datetime, timedelta
        
        # Count policy amendments in last 24 hours
        yesterday = datetime.now(UTC) - timedelta(days=1)
        
        count = self.db.execute(
            """SELECT COUNT(*) as count FROM agency_lessons
               WHERE user_id = ? 
               AND lesson_type = 'policy_suggestion'
               AND applied_at > ?
               AND applied_by = 'values_ethics_service'""",
            (user_id, yesterday.isoformat())
        ).fetchone()["count"]
        
        if count >= self.policy_amendment_limit:
            logger.warning(
                f"[LESSON_APPLICATOR] Policy amendment rate limit: {count}/{self.policy_amendment_limit} in last 24h"
            )
            return False
        
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
