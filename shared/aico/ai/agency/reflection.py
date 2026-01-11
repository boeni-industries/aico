"""
Self-Reflection Engine for Agency Phase 5

Analyzes AICO's past behavior, outcomes, and user feedback to generate
structured lessons for behavioral improvement. Runs periodically during
sleep-like phases or triggered by significant events.

Design: See docs/concepts/agency/agency-component-self-reflection.md
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timedelta, UTC
from typing import Any, Dict, List, Optional, Tuple

from aico.core.logging import get_logger
from aico.core.config import ConfigurationManager

from .models import (
    Lesson, LessonType, TargetKind, ChangeType, LessonScope, LessonStatus,
    ProposedChange, MetricsBasis,
    SelfModelEntry, EntityType, PerformanceSummary,
    ReflectionRun, RunType, RunStatus,
)
from .store import LessonStore, SelfModelStore, ReflectionRunStore
from .lesson_applicator import LessonApplicationService
from .lesson_projector import LessonMemoryProjector


logger = get_logger("agency.reflection")


class SelfReflectionEngine:
    """
    Self-Reflection Engine for behavioral learning (Phase 5).
    
    Analyzes logs, trajectories, goals, and outcomes to generate lessons
    that improve AICO's behavior over time.
    """
    
    def __init__(
        self,
        config: ConfigurationManager,
        db_connection,
        llm_client: Optional[Any] = None,
        kg_storage=None,  # PropertyGraphStorage for World Model integration
    ):
        """
        Initialize the Self-Reflection Engine.
        
        Args:
            config: Configuration manager
            db_connection: Database connection (encrypted)
            llm_client: Optional LLM client for lesson generation
            kg_storage: Optional PropertyGraphStorage for World Model integration
        """
        self.config = config
        self.db = db_connection
        self.llm_client = llm_client
        self.kg_storage = kg_storage
        
        # Initialize stores
        self.lesson_store = LessonStore(db_connection)
        self.self_model_store = SelfModelStore(db_connection)
        self.run_store = ReflectionRunStore(db_connection)
        
        # Initialize projector for World Model integration
        self.projector = LessonMemoryProjector(
            config=config,
            db_connection=db_connection,
            kg_storage=kg_storage,
        )
        
        # Initialize lesson applicator
        self.lesson_applicator = LessonApplicationService(
            config=config,
            db_connection=db_connection,
            lesson_store=self.lesson_store,
            kg_storage=kg_storage,
        )
        
        # Get configuration
        self.policy_mode = config.get(
            "core.agency.self_reflection.policy_mode",
            "observe_only"  # Default: safest mode
        )
        self.min_sample_size = config.get(
            "core.agency.self_reflection.min_sample_size",
            10  # Minimum data points before generating lessons
        )
        self.confidence_threshold = config.get(
            "core.agency.self_reflection.confidence_threshold",
            0.7  # Minimum confidence to apply lessons
        )
        
        logger.debug(
            f"[SELF_REFLECTION] Initialized in '{self.policy_mode}' mode "
            f"(min_samples={self.min_sample_size}, confidence_threshold={self.confidence_threshold})"
        )
    
    async def run_reflection(
        self,
        user_id: str,
        run_type: RunType = RunType.SCHEDULED,
        trigger_reason: Optional[str] = None,
        analysis_window_days: int = 7,
    ) -> ReflectionRun:
        """
        Run a reflection job to analyze recent behavior and generate lessons.
        
        Args:
            user_id: User to reflect on
            run_type: Type of reflection run
            trigger_reason: Why this run was triggered
            analysis_window_days: How many days back to analyze
            
        Returns:
            ReflectionRun with results
        """
        run_id = str(uuid.uuid4())
        started_at = datetime.now(UTC)
        
        # Define analysis window
        window_end = started_at
        window_start = window_end - timedelta(days=analysis_window_days)
        
        logger.info(
            f"[SELF_REFLECTION] Starting reflection run {run_id} for user {user_id} "
            f"(window: {window_start.date()} to {window_end.date()})"
        )
        
        # Create run record
        run = ReflectionRun(
            run_id=run_id,
            user_id=user_id,
            run_type=run_type,
            trigger_reason=trigger_reason,
            analysis_window_start=window_start,
            analysis_window_end=window_end,
            started_at=started_at,
            status=RunStatus.RUNNING,
        )
        await self.run_store.create_run(run)
        
        try:
            # Step 1: Analyze skill performance
            skill_lessons = await self._analyze_skill_performance(
                user_id, window_start, window_end, run_id
            )
            
            # Step 2: Analyze goal completion patterns
            goal_lessons = await self._analyze_goal_patterns(
                user_id, window_start, window_end, run_id
            )
            
            # Step 3: Analyze user feedback and sentiment
            feedback_lessons = await self._analyze_user_feedback(
                user_id, window_start, window_end, run_id
            )
            
            # Step 4: Analyze emotion patterns
            emotion_lessons = await self._analyze_emotion_patterns(
                user_id, window_start, window_end, run_id
            )
            
            # Step 5: Analyze social relationship patterns
            social_lessons = await self._analyze_social_patterns(
                user_id, window_start, window_end, run_id
            )
            
            # Step 6: Analyze curiosity exploration outcomes
            curiosity_lessons = await self._analyze_curiosity_outcomes(
                user_id, window_start, window_end, run_id
            )
            
            # Combine all lessons
            all_lessons = (
                skill_lessons + goal_lessons + feedback_lessons + 
                emotion_lessons + social_lessons + curiosity_lessons
            )
            
            # Step 4: Apply lessons (if confidence threshold met)
            applied_count = 0
            for lesson in all_lessons:
                if lesson.confidence >= self.confidence_threshold:
                    if await self.lesson_applicator.apply_lesson(lesson, reflection_run=run):
                        applied_count += 1
            
            # Complete the run
            completed_at = datetime.now(UTC)
            duration = (completed_at - started_at).total_seconds()
            
            await self.run_store.update_run(
                run_id=run_id,
                status=RunStatus.COMPLETED,
                completed_at=completed_at,
                duration_seconds=duration,
                lessons_generated=len(all_lessons),
                lessons_applied=applied_count,
            )
            
            logger.info(
                f"[SELF_REFLECTION] Completed run {run_id}: "
                f"{len(all_lessons)} lessons generated, {applied_count} applied "
                f"(duration: {duration:.1f}s)"
            )
            
            # Return updated run
            return await self.run_store.get_run(run_id)
            
        except Exception as e:
            logger.exception(f"[SELF_REFLECTION] Run {run_id} failed: {e}")
            
            await self.run_store.update_run(
                run_id=run_id,
                status=RunStatus.FAILED,
                error_message=str(e),
            )
            
            raise
    
    async def _generate_llm_lesson(
        self,
        lesson_type: LessonType,
        context: Dict[str, Any],
    ) -> Optional[str]:
        """
        Use LLM to generate richer lesson insights.
        
        Args:
            lesson_type: Type of lesson being generated
            context: Context data (metrics, patterns, etc.)
            
        Returns:
            LLM-generated lesson text or None if LLM unavailable
        """
        if not self.llm_client:
            return None
        
        try:
            # Build prompt based on lesson type
            if lesson_type == LessonType.SKILL_TUNING:
                prompt = f"""Analyze this skill performance data and suggest a specific behavioral adjustment:

Skill: {context.get('skill_id')}
Success Rate: {context.get('success_rate', 0):.1%}
Total Uses: {context.get('total_uses', 0)}
Failures: {context.get('failures', 0)}

Provide a concise, actionable lesson (1-2 sentences) about how to improve or adjust usage of this skill."""

            elif lesson_type == LessonType.PLANNER_HEURISTIC:
                prompt = f"""Analyze this goal completion pattern and suggest a planning adjustment:

Goal Type: {context.get('goal_type')}
Completion Rate: {context.get('completion_rate', 0):.1%}
Retirement Rate: {context.get('retirement_rate', 0):.1%}
Total Goals: {context.get('total_goals', 0)}

Provide a concise, actionable lesson (1-2 sentences) about how to adjust goal prioritization or planning for this type."""

            elif lesson_type == LessonType.PERSONA_STYLE:
                prompt = f"""Analyze this user feedback pattern and suggest a communication adjustment:

Average Rating: {context.get('avg_rating', 0):.1f}/5
Low Ratings: {context.get('low_rating_count', 0)}
Total Feedback: {context.get('total_feedback', 0)}

Provide a concise, actionable lesson (1-2 sentences) about how to adjust communication style or tone."""

            else:
                return None
            
            # Call LLM (placeholder - actual implementation depends on LLM client interface)
            # response = await self.llm_client.generate(prompt, max_tokens=100)
            # return response.text
            
            # For now, return None to use statistical summaries
            logger.debug(f"[SELF_REFLECTION] LLM lesson generation not yet implemented for {lesson_type}")
            return None
            
        except Exception as e:
            logger.warning(f"[SELF_REFLECTION] LLM lesson generation failed: {e}")
            return None
    
    async def _analyze_skill_performance(
        self,
        user_id: str,
        window_start: datetime,
        window_end: datetime,
        run_id: str,
    ) -> List[Lesson]:
        """
        Analyze skill usage and outcomes to generate skill-tuning lessons.
        
        Returns:
            List of skill-related lessons
        """
        lessons = []
        
        # Query skill usage from behavioral feedback
        rows = self.db.execute(
            """SELECT skill_id, outcome, COUNT(*) as count
               FROM ams_behavioral_feedback
               WHERE user_id = ? AND timestamp BETWEEN ? AND ?
               GROUP BY skill_id, outcome""",
            (user_id, window_start.isoformat(), window_end.isoformat())
        ).fetchall()
        
        # Aggregate by skill
        skill_stats = {}
        for row in rows:
            skill_id = row["skill_id"]
            if skill_id not in skill_stats:
                skill_stats[skill_id] = {"success": 0, "failure": 0, "total": 0}
            
            outcome = row["outcome"]
            count = row["count"]
            skill_stats[skill_id][outcome] = count
            skill_stats[skill_id]["total"] += count
        
        # Generate lessons for skills with sufficient data
        for skill_id, stats in skill_stats.items():
            if stats["total"] < self.min_sample_size:
                continue
            
            success_rate = stats["success"] / stats["total"]
            
            # Update self-model
            performance_summary = PerformanceSummary(
                success_rate=success_rate,
                additional_metrics={"total_uses": stats["total"]}
            )
            
            model_entry = SelfModelEntry(
                model_id=str(uuid.uuid4()),
                user_id=user_id,
                entity_type=EntityType.SKILL,
                entity_id=skill_id,
                performance_summary=performance_summary,
                window_start=window_start,
                window_end=window_end,
                sample_size=stats["total"],
                confidence=min(0.9, stats["total"] / 50.0),  # More data = higher confidence
            )
            await self.self_model_store.upsert_entry(model_entry)
            
            # Project self-model entry to World Model KG
            if self.kg_storage:
                await self.projector.project_self_model_to_kg(model_entry)
            
            # Generate lesson if performance is poor
            if success_rate < 0.5 and stats["total"] >= self.min_sample_size:
                # Try to generate LLM-enhanced summary
                llm_summary = await self._generate_llm_lesson(
                    lesson_type=LessonType.SKILL_TUNING,
                    context={
                        "skill_id": skill_id,
                        "success_rate": success_rate,
                        "total_uses": stats["total"],
                        "failures": stats["failure"],
                    }
                )
                
                # Use LLM summary if available, otherwise use statistical summary
                summary_text = llm_summary if llm_summary else (
                    f"Skill '{skill_id}' has low success rate ({success_rate:.1%}). "
                    f"Consider reducing usage or improving implementation."
                )
                
                lesson = Lesson(
                    lesson_id=str(uuid.uuid4()),
                    user_id=user_id,
                    lesson_type=LessonType.SKILL_TUNING,
                    target_kind=TargetKind.SKILL,
                    target_id=skill_id,
                    summary_text=summary_text,
                    proposed_change=ProposedChange(
                        change_type=ChangeType.WEIGHT_TWEAK,
                        field="selection_weight",
                        old=1.0,
                        new=0.5,  # Reduce selection probability
                        notes=f"Based on {stats['total']} uses with {success_rate:.1%} success rate"
                    ),
                    confidence=min(0.8, stats["total"] / 30.0),
                    metrics_basis=MetricsBasis(
                        time_span=f"{(window_end - window_start).days} days",
                        sample_size=stats["total"],
                        outcome_counts={"success": stats["success"], "failure": stats["failure"]}
                    ),
                    scope=LessonScope.THIS_USER,
                    status=LessonStatus.ACTIVE,
                    source_reflection_run_id=run_id,
                    evidence_window_start=window_start,
                    evidence_window_end=window_end,
                )
                
                await self.lesson_store.create_lesson(lesson)
                lessons.append(lesson)
                
                logger.info(
                    f"[SELF_REFLECTION] Generated skill lesson for {skill_id}: "
                    f"success_rate={success_rate:.1%}, confidence={lesson.confidence:.2f}"
                )
        
        return lessons
    
    async def _analyze_goal_patterns(
        self,
        user_id: str,
        window_start: datetime,
        window_end: datetime,
        run_id: str,
    ) -> List[Lesson]:
        """
        Analyze goal completion patterns to generate planner heuristics.
        
        Returns:
            List of goal-related lessons
        """
        lessons = []
        
        # Query goal outcomes
        rows = self.db.execute(
            """SELECT goal_type, status, COUNT(*) as count
               FROM agency_goals
               WHERE user_id = ? AND created_at BETWEEN ? AND ?
               GROUP BY goal_type, status""",
            (user_id, window_start.isoformat(), window_end.isoformat())
        ).fetchall()
        
        # Aggregate by goal type
        goal_stats = {}
        for row in rows:
            goal_type = row["goal_type"]
            if goal_type not in goal_stats:
                goal_stats[goal_type] = {"completed": 0, "retired": 0, "active": 0, "total": 0}
            
            status = row["status"]
            count = row["count"]
            if status in goal_stats[goal_type]:
                goal_stats[goal_type][status] = count
            goal_stats[goal_type]["total"] += count
        
        # Generate lessons for goal types with patterns
        for goal_type, stats in goal_stats.items():
            if stats["total"] < self.min_sample_size:
                continue
            
            completion_rate = stats["completed"] / stats["total"]
            retirement_rate = stats["retired"] / stats["total"]
            
            # If many goals are retired, suggest deprioritizing this type
            if retirement_rate > 0.5 and stats["total"] >= self.min_sample_size:
                # Try to generate LLM-enhanced summary
                llm_summary = await self._generate_llm_lesson(
                    lesson_type=LessonType.PLANNER_HEURISTIC,
                    context={
                        "goal_type": goal_type,
                        "completion_rate": completion_rate,
                        "retirement_rate": retirement_rate,
                        "total_goals": stats["total"],
                    }
                )
                
                summary_text = llm_summary if llm_summary else (
                    f"Goal type '{goal_type}' has high retirement rate ({retirement_rate:.1%}). "
                    f"Consider lowering priority."
                )
                
                lesson = Lesson(
                    lesson_id=str(uuid.uuid4()),
                    user_id=user_id,
                    lesson_type=LessonType.PLANNER_HEURISTIC,
                    target_kind=TargetKind.ARBITER_WEIGHT,
                    target_id=f"goal_type_{goal_type}",
                    summary_text=summary_text,
                    proposed_change=ProposedChange(
                        change_type=ChangeType.WEIGHT_TWEAK,
                        field="goal_type_priority_weight",
                        old=1.0,
                        new=0.7,
                        notes=f"Based on {stats['total']} goals with {retirement_rate:.1%} retirement rate"
                    ),
                    confidence=min(0.75, stats["total"] / 20.0),
                    metrics_basis=MetricsBasis(
                        time_span=f"{(window_end - window_start).days} days",
                        sample_size=stats["total"],
                        outcome_counts={
                            "completed": stats["completed"],
                            "retired": stats["retired"],
                            "active": stats["active"]
                        }
                    ),
                    scope=LessonScope.THIS_USER,
                    status=LessonStatus.ACTIVE,
                    source_reflection_run_id=run_id,
                    evidence_window_start=window_start,
                    evidence_window_end=window_end,
                )
                
                await self.lesson_store.create_lesson(lesson)
                lessons.append(lesson)
                
                logger.info(
                    f"[SELF_REFLECTION] Generated goal pattern lesson for {goal_type}: "
                    f"retirement_rate={retirement_rate:.1%}"
                )
        
        return lessons
    
    async def _analyze_user_feedback(
        self,
        user_id: str,
        window_start: datetime,
        window_end: datetime,
        run_id: str,
    ) -> List[Lesson]:
        """
        Analyze user feedback and sentiment to generate persona/style lessons.
        
        Returns:
            List of feedback-related lessons
        """
        lessons = []
        
        # Query feedback events (reward is the rating in this table)
        try:
            rows = self.db.fetch_all(
                """SELECT reward, reason, classified_categories
                   FROM feedback_events
                   WHERE user_id = ? AND timestamp BETWEEN ? AND ?""",
                (user_id, window_start.isoformat(), window_end.isoformat())
            )
        except Exception as e:
            logger.debug(f"[SELF_REFLECTION] Could not query feedback_events: {e}")
            return lessons
        
        if len(rows) < self.min_sample_size:
            logger.debug(
                f"[SELF_REFLECTION] Insufficient feedback data for user {user_id}: "
                f"{len(rows)} events (need {self.min_sample_size})"
            )
            return lessons
        
        # Analyze ratings (reward column contains the rating)
        ratings = []
        for row in rows:
            if row["reward"] is not None:
                # Reward is stored as integer, convert to rating scale
                ratings.append(row["reward"])
        
        if ratings:
            avg_rating = sum(ratings) / len(ratings)
            
            # If average rating is low, suggest persona adjustment
            if avg_rating < 3.0:  # Assuming 1-5 scale
                # Try to generate LLM-enhanced summary
                low_rating_count = sum(1 for r in ratings if r < 3)
                llm_summary = await self._generate_llm_lesson(
                    lesson_type=LessonType.PERSONA_STYLE,
                    context={
                        "avg_rating": avg_rating,
                        "low_rating_count": low_rating_count,
                        "total_feedback": len(ratings),
                    }
                )
                
                summary_text = llm_summary if llm_summary else (
                    f"User feedback shows low satisfaction (avg rating: {avg_rating:.1f}/5). "
                    f"Consider adjusting communication style."
                )
                
                lesson = Lesson(
                    lesson_id=str(uuid.uuid4()),
                    user_id=user_id,
                    lesson_type=LessonType.PERSONA_STYLE,
                    target_kind=TargetKind.PERSONA_TRAIT,
                    target_id="response_style",
                    summary_text=summary_text,
                    proposed_change=ProposedChange(
                        change_type=ChangeType.TEMPLATE_UPDATE,
                        field="response_tone",
                        old="current",
                        new="more_empathetic",
                        notes=f"Based on {len(ratings)} ratings with average {avg_rating:.1f}/5"
                    ),
                    confidence=min(0.7, len(ratings) / 30.0),
                    metrics_basis=MetricsBasis(
                        time_span=f"{(window_end - window_start).days} days",
                        sample_size=len(ratings),
                        outcome_counts={"low_rating": sum(1 for r in ratings if r < 3)}
                    ),
                    scope=LessonScope.THIS_USER,
                    status=LessonStatus.ACTIVE,
                    source_reflection_run_id=run_id,
                    evidence_window_start=window_start,
                    evidence_window_end=window_end,
                )
                
                await self.lesson_store.create_lesson(lesson)
                lessons.append(lesson)
                
                logger.info(
                    f"[SELF_REFLECTION] Generated persona lesson: "
                    f"avg_rating={avg_rating:.1f}, confidence={lesson.confidence:.2f}"
                )
        
        return lessons
    
    async def get_active_lessons(
        self,
        user_id: str,
        lesson_type: Optional[LessonType] = None,
    ) -> List[Lesson]:
        """
        Get active lessons for a user.
        
        Args:
            user_id: User ID
            lesson_type: Optional filter by lesson type
            
        Returns:
            List of active lessons
        """
        return await self.lesson_store.get_active_lessons(
            user_id=user_id,
            lesson_type=lesson_type
        )
    
    async def get_self_model(
        self,
        user_id: str,
        entity_type: EntityType,
        entity_id: str,
    ) -> Optional[SelfModelEntry]:
        """
        Get the latest self-model entry for an entity.
        
        Args:
            user_id: User ID
            entity_type: Type of entity
            entity_id: Entity ID
            
        Returns:
            Latest self-model entry or None
        """
        return await self.self_model_store.get_latest_entry(
            user_id=user_id,
            entity_type=entity_type,
            entity_id=entity_id
        )
    
    async def get_skill_performance(self, user_id: str, skill_id: str) -> Optional[float]:
        """
        Get success rate for a skill (for use by Planner/Arbiter).
        
        Args:
            user_id: User ID
            skill_id: Skill ID
            
        Returns:
            Success rate (0.0-1.0) or None if no data
        """
        entry = await self.self_model_store.get_latest_entry(
            user_id=user_id,
            entity_type=EntityType.SKILL,
            entity_id=skill_id
        )
        
        if entry and entry.performance_summary:
            return entry.performance_summary.success_rate
        
        return None
    
    async def get_goal_type_performance(self, user_id: str, goal_type: str) -> Optional[Dict[str, Any]]:
        """
        Get performance metrics for a goal type (for use by Arbiter).
        
        Args:
            user_id: User ID
            goal_type: Goal type (e.g., "learning", "project")
            
        Returns:
            Dictionary with completion_rate, retirement_rate, sample_size
        """
        entry = await self.self_model_store.get_latest_entry(
            user_id=user_id,
            entity_type=EntityType.GOAL_TYPE,
            entity_id=goal_type
        )
        
        if entry and entry.performance_summary:
            return {
                "success_rate": entry.performance_summary.success_rate,
                "sample_size": entry.sample_size,
                "confidence": entry.confidence,
                "additional_metrics": entry.performance_summary.additional_metrics or {}
            }
        
        return None
    
    async def get_all_skill_performances(self, user_id: str) -> Dict[str, float]:
        """
        Get success rates for all skills with data (for use by Curiosity Engine).
        
        Args:
            user_id: User ID
            
        Returns:
            Dictionary of skill_id -> success_rate
        """
        # Query all skill entries for user
        rows = self.db.execute(
            """SELECT entity_id, performance_summary, sample_size
               FROM agency_self_model
               WHERE user_id = ? AND entity_type = 'skill'
               ORDER BY window_end DESC""",
            (user_id,)
        ).fetchall()
        
        performances = {}
        seen_skills = set()
        
        for row in rows:
            skill_id = row["entity_id"]
            
            # Only use most recent entry per skill
            if skill_id in seen_skills:
                continue
            seen_skills.add(skill_id)
            
            # Parse performance summary
            try:
                import json
                summary_data = json.loads(row["performance_summary"])
                success_rate = summary_data.get("success_rate")
                sample_size = row["sample_size"]
                
                # Only include if we have enough data
                if success_rate is not None and sample_size >= 5:
                    performances[skill_id] = success_rate
            except (json.JSONDecodeError, KeyError):
                continue
        
        return performances
    
    async def _analyze_emotion_patterns(
        self,
        user_id: str,
        window_start: datetime,
        window_end: datetime,
        run_id: str,
    ) -> List[Lesson]:
        """
        Analyze user emotional patterns to generate persona adjustment lessons.
        
        Examines emotion history to detect:
        - High-stress periods requiring more supportive interaction
        - Low-satisfaction patterns suggesting persona mismatch
        - Emotional trajectories indicating needed style changes
        
        Args:
            user_id: User to analyze
            window_start: Start of analysis window
            window_end: End of analysis window
            run_id: Reflection run ID for provenance
            
        Returns:
            List of emotion-based persona lessons
        """
        lessons = []
        
        try:
            # Query emotion history
            # Note: Some deployments only have valence/arousal columns. We
            # don't require richer fields for current analysis, so we select
            # only the stable subset.
            #
            # Emotion Simulation persists AICO's own emotional trajectory under
            # user_id = 'system' (single-agent emotion model).
            emotion_history_user_id = "system"
            rows = self.db.execute(
                """SELECT timestamp, valence, arousal
                   FROM emotion_history
                   WHERE user_id = ? AND timestamp BETWEEN ? AND ?
                   ORDER BY timestamp DESC""",
                (
                    emotion_history_user_id,
                    window_start.isoformat(),
                    window_end.isoformat(),
                )
            ).fetchall()
            
            if len(rows) < self.min_sample_size:
                # Degradation: not enough data to analyze emotion patterns
                logger.warning(
                    f"[SELF_REFLECTION] Emotion analysis degraded for user {user_id}: "
                    f"{len(rows)} entries (need {self.min_sample_size}) "
                    f"from emotion_history user_id='{emotion_history_user_id}'"
                )
                return lessons
            
            # Calculate average emotional metrics
            # Rows are tuples: (timestamp, valence, arousal)
            avg_valence = sum(row[1] for row in rows) / len(rows)
            avg_arousal = sum(row[2] for row in rows) / len(rows)
            
            # Detect high-stress pattern (low valence + high arousal)
            stress_score = (1.0 - avg_valence) * avg_arousal
            
            if stress_score > 0.6:  # Threshold for high stress
                # Generate lesson for more supportive interaction
                lesson = Lesson(
                    lesson_id=str(uuid.uuid4()),
                    user_id=user_id,
                    lesson_type=LessonType.PERSONA_STYLE,
                    target_kind=TargetKind.PERSONA_TRAIT,
                    target_id="supportiveness",
                    summary_text=(
                        f"Elevated stress detected in AICO emotion history (stress_score={stress_score:.2f}). "
                        "Increase supportiveness and empathy in interactions."
                    ),
                    proposed_change=ProposedChange(
                        change_type=ChangeType.WEIGHT_TWEAK,
                        field="supportiveness",
                        old=None,
                        new="+0.2",
                        notes="Increase supportiveness under sustained high-stress patterns.",
                    ),
                    confidence=min(0.9, stress_score),
                    metrics_basis=MetricsBasis(
                        time_span=f"{(window_end - window_start).days} days",
                        sample_size=len(rows),
                        outcome_counts={},
                        additional_metrics={
                            "stress_score": stress_score,
                            "avg_valence": avg_valence,
                            "avg_arousal": avg_arousal,
                        },
                    ),
                    scope=LessonScope.THIS_USER,
                    status=LessonStatus.ACTIVE,
                    source_reflection_run_id=run_id,
                    evidence_window_start=window_start,
                    evidence_window_end=window_end,
                )
                lessons.append(lesson)
                await self.lesson_store.create_lesson(lesson)
                
                logger.info(
                    f"[SELF_REFLECTION] Generated stress-response lesson for user {user_id}",
                    extra={"stress_score": stress_score, "avg_valence": avg_valence}
                )
            
            # Detect low satisfaction pattern (consistently low valence)
            if avg_valence < 0.3:  # Threshold for low satisfaction
                lesson = Lesson(
                    lesson_id=str(uuid.uuid4()),
                    user_id=user_id,
                    lesson_type=LessonType.PERSONA_STYLE,
                    target_kind=TargetKind.PERSONA_TRAIT,
                    target_id="interaction_style",
                    summary_text=(
                        f"Low average valence in AICO emotion history (avg_valence={avg_valence:.2f}). "
                        "Consider adjusting interaction style and tone."
                    ),
                    proposed_change=ProposedChange(
                        change_type=ChangeType.WEIGHT_TWEAK,
                        field="warmth",
                        old=None,
                        new="+0.15",
                        notes="Increase warmth when sustained low-valence patterns are observed.",
                    ),
                    confidence=0.7,
                    metrics_basis=MetricsBasis(
                        time_span=f"{(window_end - window_start).days} days",
                        sample_size=len(rows),
                        outcome_counts={},
                        additional_metrics={
                            "avg_valence": avg_valence,
                            "avg_arousal": avg_arousal,
                        },
                    ),
                    scope=LessonScope.THIS_USER,
                    status=LessonStatus.ACTIVE,
                    source_reflection_run_id=run_id,
                    evidence_window_start=window_start,
                    evidence_window_end=window_end,
                )
                lessons.append(lesson)
                await self.lesson_store.create_lesson(lesson)
                
                logger.info(
                    f"[SELF_REFLECTION] Generated low-satisfaction lesson for user {user_id}",
                    extra={"avg_valence": avg_valence}
                )
        
        except Exception as e:
            # Hard failure analyzing emotion patterns
            logger.exception(f"[SELF_REFLECTION] Failed to analyze emotion patterns: {e}")
        
        return lessons
    
    async def _analyze_social_patterns(
        self,
        user_id: str,
        window_start: datetime,
        window_end: datetime,
        run_id: str,
    ) -> List[Lesson]:
        """
        Analyze social relationship patterns to generate interaction lessons.
        
        Examines relationship data to detect:
        - Declining relationship strength requiring maintenance
        - Interaction frequency mismatches
        - Communication style preferences
        
        Args:
            user_id: User to analyze
            window_start: Start of analysis window
            window_end: End of analysis window
            run_id: Reflection run ID for provenance
            
        Returns:
            List of social relationship lessons
        """
        lessons = []
        
        try:
            # Query relationship data using actual schema columns
            # Current schema: uuid, user_uuid, related_user_uuid, relationship_type,
            # is_active, created_at, updated_at
            # 
            # NOTE: The full social analysis design requires richer metrics like
            # closeness, trust, interaction_frequency, last_interaction. Until those
            # are added to the schema, we degrade gracefully with a WARNING.
            rows = self.db.execute(
                """SELECT uuid, related_user_uuid, relationship_type, 
                          is_active, created_at, updated_at
                       FROM user_relationships
                       WHERE user_uuid = ?""",
                (user_id,),
            ).fetchall()
            
            if not rows:
                logger.debug(f"[SELF_REFLECTION] No relationship data for user {user_id}")
                return lessons
            
            # Degradation: current schema lacks closeness/trust/interaction metrics.
            # We log this once per run and skip rich social analysis until schema is extended.
            logger.warning(
                f"[SELF_REFLECTION] Social analysis degraded for user {user_id}: "
                f"relationship metrics (closeness, trust, interaction_frequency) not yet "
                f"in schema. Found {len(rows)} relationships but cannot analyze interaction patterns."
            )
            return lessons
        
        except Exception as e:
            logger.exception(f"[SELF_REFLECTION] Failed to analyze social patterns: {e}")
        
        return lessons
    
    async def _analyze_curiosity_outcomes(
        self,
        user_id: str,
        window_start: datetime,
        window_end: datetime,
        run_id: str,
    ) -> List[Lesson]:
        """
        Analyze curiosity exploration outcomes to generate policy adjustment lessons.
        
        Examines curiosity-driven goals to detect:
        - Successful explorations leading to skill improvements
        - Failed explorations indicating poor curiosity policies
        - Curiosity → learning → skill improvement pipeline effectiveness
        
        Args:
            user_id: User to analyze
            window_start: Start of analysis window
            window_end: End of analysis window
            run_id: Reflection run ID for provenance
            
        Returns:
            List of curiosity policy adjustment lessons
        """
        lessons = []
        
        try:
            # Query curiosity-driven goals
            # Use the actual agency_goals schema: metadata is stored as metadata_json.
            # We include it in the SELECT even if current analysis only uses status
            # and counts, to keep this query schema-accurate and future-safe.
            rows = self.db.execute(
                """SELECT goal_id, status, created_at, metadata_json
                   FROM agency_goals
                   WHERE user_id = ? 
                     AND origin = 'curiosity'
                     AND created_at BETWEEN ? AND ?
                   ORDER BY created_at DESC""",
                (user_id, window_start.isoformat(), window_end.isoformat())
            ).fetchall()
            
            if len(rows) < 3:  # Need at least a few curiosity goals to analyze
                logger.debug(
                    f"[SELF_REFLECTION] Insufficient curiosity goals for user {user_id}: "
                    f"{len(rows)} goals (need 3+)"
                )
                return lessons
            
            # Analyze completion rates
            total_goals = len(rows)
            completed_goals = sum(1 for row in rows if row["status"] == "completed")
            abandoned_goals = sum(1 for row in rows if row["status"] == "abandoned")
            
            completion_rate = completed_goals / total_goals if total_goals > 0 else 0
            abandonment_rate = abandoned_goals / total_goals if total_goals > 0 else 0
            
            # Detect poor curiosity policy (high abandonment rate)
            if abandonment_rate > 0.5 and total_goals >= 5:
                lesson = Lesson(
                    lesson_id=str(uuid.uuid4()),
                    user_id=user_id,
                    run_id=run_id,
                    lesson_type=LessonType.POLICY_SUGGESTION,
                    target_kind=TargetKind.POLICY_RULE,
                    target_id="curiosity_policy",
                    description=(
                        f"High curiosity goal abandonment rate ({abandonment_rate:.1%}). "
                        f"Curiosity policy may be generating goals that are too ambitious or "
                        "not aligned with user interests. Consider tightening curiosity filters."
                    ),
                    confidence=0.75,
                    metrics_basis=MetricsBasis(
                        sample_size=total_goals,
                        success_rate=completion_rate,
                        avg_duration_seconds=None,
                        error_rate=abandonment_rate,
                    ),
                    proposed_changes=[
                        ProposedChange(
                            change_type=ChangeType.ADJUST_WEIGHT,
                            target_field="curiosity_threshold",
                            old_value=None,
                            new_value="+0.1",  # Increase threshold (be more selective)
                        )
                    ],
                    created_at=datetime.now(UTC),
                )
                lessons.append(lesson)
                
                logger.info(
                    f"[SELF_REFLECTION] Generated curiosity policy adjustment lesson",
                    extra={
                        "abandonment_rate": abandonment_rate,
                        "total_goals": total_goals
                    }
                )
            
            # Detect successful curiosity → learning pipeline
            elif completion_rate > 0.7 and total_goals >= 5:
                lesson = Lesson(
                    lesson_id=str(uuid.uuid4()),
                    user_id=user_id,
                    run_id=run_id,
                    lesson_type=LessonType.POLICY_SUGGESTION,
                    target_kind=TargetKind.POLICY_RULE,
                    target_id="curiosity_policy",
                    description=(
                        f"High curiosity goal completion rate ({completion_rate:.1%}). "
                        "Curiosity policy is working well. Consider slightly loosening "
                        "filters to explore more opportunities."
                    ),
                    confidence=0.7,
                    metrics_basis=MetricsBasis(
                        sample_size=total_goals,
                        success_rate=completion_rate,
                        avg_duration_seconds=None,
                        error_rate=abandonment_rate,
                    ),
                    proposed_changes=[
                        ProposedChange(
                            change_type=ChangeType.ADJUST_WEIGHT,
                            target_field="curiosity_threshold",
                            old_value=None,
                            new_value="-0.05",  # Decrease threshold (be more exploratory)
                        )
                    ],
                    created_at=datetime.now(UTC),
                )
                lessons.append(lesson)
                
                logger.info(
                    f"[SELF_REFLECTION] Generated curiosity encouragement lesson",
                    extra={
                        "completion_rate": completion_rate,
                        "total_goals": total_goals
                    }
                )
        
        except Exception as e:
            logger.exception(f"[SELF_REFLECTION] Failed to analyze curiosity outcomes: {e}")
        
        return lessons
