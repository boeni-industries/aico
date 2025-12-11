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
from datetime import datetime, timedelta
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


logger = get_logger("agency", "reflection")


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
    ):
        """
        Initialize the Self-Reflection Engine.
        
        Args:
            config: Configuration manager
            db_connection: Database connection (encrypted)
            llm_client: Optional LLM client for lesson generation
        """
        self.config = config
        self.db = db_connection
        self.llm_client = llm_client
        
        # Initialize stores
        self.lesson_store = LessonStore(db_connection)
        self.self_model_store = SelfModelStore(db_connection)
        self.run_store = ReflectionRunStore(db_connection)
        
        # Initialize lesson applicator
        self.lesson_applicator = LessonApplicationService(
            config=config,
            db_connection=db_connection,
            lesson_store=self.lesson_store,
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
        
        logger.info(
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
        started_at = datetime.utcnow()
        
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
            
            # Combine all lessons
            all_lessons = skill_lessons + goal_lessons + feedback_lessons
            
            # Step 4: Apply lessons (if confidence threshold met)
            applied_count = 0
            for lesson in all_lessons:
                if lesson.confidence >= self.confidence_threshold:
                    if await self.lesson_applicator.apply_lesson(lesson):
                        applied_count += 1
            
            # Complete the run
            completed_at = datetime.utcnow()
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
            logger.error(f"[SELF_REFLECTION] Run {run_id} failed: {e}", exc_info=True)
            
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
