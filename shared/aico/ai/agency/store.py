from __future__ import annotations

import json
from datetime import datetime, UTC
from typing import Any, Dict, List, Optional

from aico.core.logging import get_logger

from .models import (
    Goal,
    GoalOrigin,
    GoalPriority,
    GoalStatus,
    Plan,
    PlanStatus,
    PlanStep,
    AgencyEvent,
    ReflectionNote,
)


logger = get_logger("shared", "ai.agency.store")


class GoalStore:
    """Persistence layer for agency_goals table."""

    def __init__(self, db_connection) -> None:
        self.db = db_connection

    async def create_goal(self, goal: Goal) -> Goal:
        """Create a new goal."""
        try:
            now = datetime.now(UTC)
            goal.created_at = now
            goal.updated_at = now

            self.db.execute(
                """INSERT INTO agency_goals (
                    goal_id, user_id, origin, goal_type, title,
                    description, status, priority, metadata_json,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    goal.goal_id,
                    goal.user_id,
                    goal.origin.value,
                    goal.goal_type,
                    goal.title,
                    goal.description,
                    goal.status.value,
                    goal.priority.value,
                    json.dumps(goal.metadata) if goal.metadata else None,
                    goal.created_at.isoformat(),
                    goal.updated_at.isoformat(),
                ),
            )
            self.db.commit()
            logger.info("[AGENCY_GOALS] Created goal", extra={"goal_id": goal.goal_id, "user_id": goal.user_id})
            return goal
        except Exception as e:
            logger.error(f"[AGENCY_GOALS] Failed to create goal: {e}", extra={"goal_id": goal.goal_id})
            raise

    async def get_goal(self, goal_id: str) -> Optional[Goal]:
        """Retrieve a goal by ID."""
        try:
            row = self.db.execute(
                "SELECT goal_id, user_id, origin, goal_type, title, description, status, priority, metadata_json, created_at, updated_at FROM agency_goals WHERE goal_id = ?",
                (goal_id,),
            ).fetchone()
            if not row:
                return None
            return Goal(
                goal_id=row[0],
                user_id=row[1],
                origin=GoalOrigin(row[2]),
                goal_type=row[3],
                title=row[4],
                description=row[5],
                status=GoalStatus(row[6]),
                priority=GoalPriority(row[7]),
                metadata=json.loads(row[8]) if row[8] else {},
                created_at=datetime.fromisoformat(row[9]).replace(tzinfo=UTC) if row[9] else datetime.now(UTC),
                updated_at=datetime.fromisoformat(row[10]).replace(tzinfo=UTC) if row[10] else datetime.now(UTC),
            )
        except Exception as e:
            logger.error(f"[AGENCY_GOALS] Failed to retrieve goal: {e}", extra={"goal_id": goal_id})
            raise

    async def list_goals(self, user_id: str, status: Optional[GoalStatus] = None) -> List[Goal]:
        """Retrieve a list of goals for a user."""
        try:
            if status:
                rows = self.db.execute(
                    """SELECT goal_id, user_id, origin, goal_type, title, description,
                               status, priority, metadata_json, created_at, updated_at
                       FROM agency_goals WHERE user_id = ? AND status = ?""",
                    (user_id, status.value),
                ).fetchall()
            else:
                rows = self.db.execute(
                    """SELECT goal_id, user_id, origin, goal_type, title, description,
                               status, priority, metadata_json, created_at, updated_at
                       FROM agency_goals WHERE user_id = ?""",
                    (user_id,),
                ).fetchall()

            goals: List[Goal] = []
            for row in rows:
                goals.append(
                    Goal(
                        goal_id=row[0],
                        user_id=row[1],
                        origin=GoalOrigin(row[2]),
                        goal_type=row[3],
                        title=row[4],
                        description=row[5],
                        status=GoalStatus(row[6]),
                        priority=GoalPriority(row[7]),
                        metadata=json.loads(row[8]) if row[8] else {},
                        created_at=datetime.fromisoformat(row[9]).replace(tzinfo=UTC) if row[9] else datetime.now(UTC),
                        updated_at=datetime.fromisoformat(row[10]).replace(tzinfo=UTC) if row[10] else datetime.now(UTC),
                    )
                )
            return goals
        except Exception as e:
            logger.error(f"[AGENCY_GOALS] Failed to retrieve goals: {e}", extra={"user_id": user_id})
            raise

    async def update_goal(self, goal: Goal) -> Goal:
        """Update an existing goal with all fields including metadata."""
        try:
            now = datetime.now(UTC)
            goal.updated_at = now
            
            self.db.execute(
                """UPDATE agency_goals SET 
                    title = ?, description = ?, status = ?, priority = ?,
                    metadata_json = ?, updated_at = ?
                WHERE goal_id = ?""",
                (
                    goal.title,
                    goal.description,
                    goal.status.value,
                    goal.priority.value,
                    json.dumps(goal.metadata) if goal.metadata else None,
                    goal.updated_at.isoformat(),
                    goal.goal_id,
                ),
            )
            self.db.commit()
            logger.info(
                "[AGENCY_GOALS] Updated goal",
                extra={"goal_id": goal.goal_id, "user_id": goal.user_id}
            )
            return goal
        except Exception as e:
            logger.error(f"[AGENCY_GOALS] Failed to update goal: {e}", extra={"goal_id": goal.goal_id})
            raise
    
    async def update_goal_status(self, goal_id: str, new_status: GoalStatus) -> None:
        """Update goal status."""
        try:
            now = datetime.now(UTC).isoformat()
            self.db.execute(
                "UPDATE agency_goals SET status = ?, updated_at = ? WHERE goal_id = ?",
                (new_status.value, now, goal_id),
            )
            self.db.commit()
            logger.info(
                "[AGENCY_GOALS] Updated goal status",
                extra={"goal_id": goal_id, "new_status": new_status.value}
            )
        except Exception as e:
            logger.error(f"[AGENCY_GOALS] Failed to update goal status: {e}", extra={"goal_id": goal_id})
            raise
    
    async def get_goals_by_status(self, user_id: str, statuses: List[GoalStatus]) -> List[Goal]:
        """
        Retrieve goals for a user filtered by multiple statuses.
        
        This is an alias/extension of list_goals() to support the intention set workflow
        which needs to query multiple statuses at once (e.g., PENDING and ACTIVE).
        
        Args:
            user_id: User ID
            statuses: List of goal statuses to filter by
            
        Returns:
            List of goals matching any of the specified statuses
        """
        try:
            if not statuses:
                return []
            
            # Build query with IN clause for multiple statuses
            placeholders = ','.join('?' * len(statuses))
            query = f"""
                SELECT goal_id, user_id, origin, goal_type, title, description,
                       status, priority, metadata_json, created_at, updated_at
                FROM agency_goals 
                WHERE user_id = ? AND status IN ({placeholders})
                ORDER BY priority DESC, created_at DESC
            """
            
            params = [user_id] + [s.value for s in statuses]
            rows = self.db.execute(query, tuple(params)).fetchall()
            
            goals: List[Goal] = []
            for row in rows:
                goals.append(
                    Goal(
                        goal_id=row[0],
                        user_id=row[1],
                        origin=GoalOrigin(row[2]),
                        goal_type=row[3],
                        title=row[4],
                        description=row[5],
                        status=GoalStatus(row[6]),
                        priority=GoalPriority(row[7]),
                        metadata=json.loads(row[8]) if row[8] else {},
                        created_at=datetime.fromisoformat(row[9]).replace(tzinfo=UTC) if row[9] else datetime.now(UTC),
                        updated_at=datetime.fromisoformat(row[10]).replace(tzinfo=UTC) if row[10] else datetime.now(UTC),
                    )
                )
            
            logger.info(
                "[AGENCY_GOALS] Retrieved goals by status",
                extra={"user_id": user_id, "statuses": [s.value for s in statuses], "count": len(goals)}
            )
            return goals
            
        except Exception as e:
            logger.error(
                f"[AGENCY_GOALS] Failed to retrieve goals by status: {e}",
                extra={"user_id": user_id, "statuses": [s.value for s in statuses]}
            )
            raise


class PlanStore:
    """Persistence layer for agency_plans table."""

    def __init__(self, db_connection) -> None:
        self.db = db_connection

    async def create_plan(self, plan: Plan) -> Plan:
        """Create a new plan."""
        try:
            now = datetime.now(UTC)
            plan.created_at = now
            plan.updated_at = now

            self.db.execute(
                """INSERT INTO agency_plans (
                    plan_id, goal_id, status, steps_json, metadata_json,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (
                    plan.plan_id,
                    plan.goal_id,
                    plan.status.value,
                    json.dumps([step.dict() for step in plan.steps]),
                    json.dumps(plan.metadata) if plan.metadata else None,
                    plan.created_at.isoformat(),
                    plan.updated_at.isoformat(),
                ),
            )
            self.db.commit()
            logger.info("[AGENCY_PLANS] Created plan", extra={"plan_id": plan.plan_id, "goal_id": plan.goal_id})
            return plan
        except Exception as e:
            logger.error(f"[AGENCY_PLANS] Failed to create plan: {e}", extra={"plan_id": plan.plan_id})
            raise

    async def get_plan(self, plan_id: str) -> Optional[Plan]:
        """Retrieve a plan by ID."""
        try:
            row = self.db.execute(
                "SELECT plan_id, goal_id, status, steps_json, metadata_json, created_at, updated_at FROM agency_plans WHERE plan_id = ?",
                (plan_id,),
            ).fetchone()
            if not row:
                return None
            steps_data = json.loads(row[3]) if row[3] else []
            steps = [PlanStep(**s) for s in steps_data]
            return Plan(
                plan_id=row[0],
                goal_id=row[1],
                status=PlanStatus(row[2]),
                steps=steps,
                metadata=json.loads(row[4]) if row[4] else {},
                created_at=datetime.fromisoformat(row[5]).replace(tzinfo=UTC) if row[5] else datetime.now(UTC),
                updated_at=datetime.fromisoformat(row[6]).replace(tzinfo=UTC) if row[6] else datetime.now(UTC),
            )
        except Exception as e:
            logger.error(f"[AGENCY_PLANS] Failed to retrieve plan: {e}", extra={"plan_id": plan_id})
            raise

    async def list_plans_for_goal(self, goal_id: str) -> List[Plan]:
        """Retrieve a list of plans for a goal."""
        try:
            rows = self.db.execute(
                "SELECT plan_id, goal_id, status, steps_json, metadata_json, created_at, updated_at FROM agency_plans WHERE goal_id = ?",
                (goal_id,),
            ).fetchall()
            plans: List[Plan] = []
            for row in rows:
                steps_data = json.loads(row[3]) if row[3] else []
                steps = [PlanStep(**s) for s in steps_data]
                plans.append(
                    Plan(
                        plan_id=row[0],
                        goal_id=row[1],
                        status=PlanStatus(row[2]),
                        steps=steps,
                        metadata=json.loads(row[4]) if row[4] else {},
                        created_at=datetime.fromisoformat(row[5]).replace(tzinfo=UTC) if row[5] else datetime.now(UTC),
                        updated_at=datetime.fromisoformat(row[6]).replace(tzinfo=UTC) if row[6] else datetime.now(UTC),
                    )
                )
            return plans
        except Exception as e:
            logger.error(f"[AGENCY_PLANS] Failed to retrieve plans: {e}", extra={"goal_id": goal_id})
            raise

    async def update_plan_status(self, plan_id: str, new_status: PlanStatus) -> None:
        """Update plan status."""
        try:
            now = datetime.now(UTC).isoformat()
            self.db.execute(
                "UPDATE agency_plans SET status = ?, updated_at = ? WHERE plan_id = ?",
                (new_status.value, now, plan_id),
            )
            self.db.commit()
            logger.info(
                "[AGENCY_PLANS] Updated plan status",
                extra={"plan_id": plan_id, "new_status": new_status.value}
            )
        except Exception as e:
            logger.error(f"[AGENCY_PLANS] Failed to update plan status: {e}", extra={"plan_id": plan_id})
            raise

    async def save_steps(self, plan_id: str, steps: List[PlanStep]) -> None:
        """Save plan steps."""
        try:
            now = datetime.now(UTC).isoformat()
            self.db.execute(
                "UPDATE agency_plans SET steps_json = ?, updated_at = ? WHERE plan_id = ?",
                (json.dumps([s.dict() for s in steps]), now, plan_id),
            )
            self.db.commit()
            logger.info(
                "[AGENCY_PLANS] Saved plan steps",
                extra={"plan_id": plan_id}
            )
        except Exception as e:
            logger.error(f"[AGENCY_PLANS] Failed to save plan steps: {e}", extra={"plan_id": plan_id})
            raise


class AgencyEventStore:
    """Append-only telemetry store for agency_events."""

    def __init__(self, db_connection) -> None:
        self.db = db_connection

    async def log_event(self, event: AgencyEvent) -> None:
        """Log an agency event."""
        try:
            self.db.execute(
                """
                INSERT INTO agency_events (user_id, goal_id, plan_id, event_type, source, payload_json, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    event.user_id,
                    event.goal_id,
                    event.plan_id,
                    event.event_type,
                    event.source,
                    json.dumps(event.payload),
                    event.created_at.isoformat() if event.created_at else datetime.now(UTC).isoformat(),
                ),
            )
            self.db.commit()
            logger.debug(
                "[AGENCY_EVENTS] Logged event",
                extra={"event_type": event.event_type, "goal_id": event.goal_id, "user_id": event.user_id}
            )
        except Exception as e:
            logger.error(f"[AGENCY_EVENTS] Failed to log event: {e}", extra={"event_type": event.event_type})
            raise


class ReflectionStore:
    """Persistence helper for agency_reflection_notes."""

    def __init__(self, db_connection) -> None:
        self.db = db_connection

    async def create_note(self, note: ReflectionNote) -> ReflectionNote:
        now = datetime.now(UTC)
        note.created_at = now
        note.updated_at = now

        self.db.execute(
            """INSERT INTO agency_reflection_notes (
                note_id, user_id, related_goal_id, related_plan_id,
                title, content, tags_json, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                note.note_id,
                note.user_id,
                note.related_goal_id,
                note.related_plan_id,
                note.title,
                note.content,
                json.dumps(note.tags) if note.tags else None,
                note.created_at.isoformat(),
                note.updated_at.isoformat(),
            ),
        )
        self.db.commit()
        return note


# Phase 5: Self-Reflection & Behavioral Learning Stores

class LessonStore:
    """Persistence helper for agency_lessons table (Phase 5)."""

    def __init__(self, db_connection) -> None:
        self.db = db_connection

    async def create_lesson(self, lesson: "Lesson") -> "Lesson":
        """Create a new lesson."""
        from .models import Lesson
        
        now = datetime.now(UTC)
        lesson.created_at = now
        lesson.updated_at = now

        self.db.execute(
            """INSERT INTO agency_lessons (
                lesson_id, user_id, lesson_type, target_kind, target_id,
                summary_text, proposed_change, confidence, metrics_basis,
                scope, status, superseded_by, applied_at, applied_by,
                source_reflection_run_id, evidence_window_start, evidence_window_end,
                related_goal_ids, related_trajectory_ids, related_event_ids,
                created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                lesson.lesson_id,
                lesson.user_id,
                lesson.lesson_type.value,
                lesson.target_kind.value,
                lesson.target_id,
                lesson.summary_text,
                json.dumps(lesson.proposed_change.dict()),
                lesson.confidence,
                json.dumps(lesson.metrics_basis.dict()) if lesson.metrics_basis else None,
                lesson.scope.value,
                lesson.status.value,
                lesson.superseded_by,
                lesson.applied_at.isoformat() if lesson.applied_at else None,
                lesson.applied_by,
                lesson.source_reflection_run_id,
                lesson.evidence_window_start.isoformat() if lesson.evidence_window_start else None,
                lesson.evidence_window_end.isoformat() if lesson.evidence_window_end else None,
                json.dumps(lesson.related_goal_ids) if lesson.related_goal_ids else None,
                json.dumps(lesson.related_trajectory_ids) if lesson.related_trajectory_ids else None,
                json.dumps(lesson.related_event_ids) if lesson.related_event_ids else None,
                lesson.created_at.isoformat(),
                lesson.updated_at.isoformat(),
            ),
        )
        self.db.commit()
        return lesson

    async def get_lesson(self, lesson_id: str) -> Optional["Lesson"]:
        """Get a lesson by ID."""
        from .models import Lesson, LessonType, TargetKind, LessonScope, LessonStatus, ProposedChange, MetricsBasis, ChangeType
        
        row = self.db.execute(
            "SELECT * FROM agency_lessons WHERE lesson_id = ?",
            (lesson_id,)
        ).fetchone()
        
        if not row:
            return None
        
        return Lesson(
            lesson_id=row["lesson_id"],
            user_id=row["user_id"],
            lesson_type=LessonType(row["lesson_type"]),
            target_kind=TargetKind(row["target_kind"]),
            target_id=row["target_id"],
            summary_text=row["summary_text"],
            proposed_change=ProposedChange(**json.loads(row["proposed_change"])),
            confidence=row["confidence"],
            metrics_basis=MetricsBasis(**json.loads(row["metrics_basis"])) if row["metrics_basis"] else None,
            scope=LessonScope(row["scope"]),
            status=LessonStatus(row["status"]),
            superseded_by=row["superseded_by"],
            applied_at=datetime.fromisoformat(row["applied_at"]).replace(tzinfo=UTC) if row["applied_at"] else None,
            applied_by=row["applied_by"],
            source_reflection_run_id=row["source_reflection_run_id"],
            evidence_window_start=datetime.fromisoformat(row["evidence_window_start"]).replace(tzinfo=UTC) if row["evidence_window_start"] else None,
            evidence_window_end=datetime.fromisoformat(row["evidence_window_end"]).replace(tzinfo=UTC) if row["evidence_window_end"] else None,
            related_goal_ids=json.loads(row["related_goal_ids"]) if row["related_goal_ids"] else [],
            related_trajectory_ids=json.loads(row["related_trajectory_ids"]) if row["related_trajectory_ids"] else [],
            related_event_ids=json.loads(row["related_event_ids"]) if row["related_event_ids"] else [],
            created_at=datetime.fromisoformat(row["created_at"]).replace(tzinfo=UTC),
            updated_at=datetime.fromisoformat(row["updated_at"]).replace(tzinfo=UTC),
        )

    async def get_active_lessons(
        self,
        user_id: str,
        lesson_type: Optional["LessonType"] = None,
        target_kind: Optional["TargetKind"] = None
    ) -> List["Lesson"]:
        """Get active lessons for a user, optionally filtered by type and target."""
        from .models import Lesson, LessonType, TargetKind, LessonStatus
        
        query = "SELECT * FROM agency_lessons WHERE user_id = ? AND status = ?"
        params = [user_id, LessonStatus.ACTIVE.value]
        
        if lesson_type:
            query += " AND lesson_type = ?"
            params.append(lesson_type.value)
        
        if target_kind:
            query += " AND target_kind = ?"
            params.append(target_kind.value)
        
        query += " ORDER BY created_at DESC"
        
        rows = self.db.execute(query, tuple(params)).fetchall()
        
        lessons = []
        for row in rows:
            lesson = await self.get_lesson(row["lesson_id"])
            if lesson:
                lessons.append(lesson)
        
        return lessons

    async def update_lesson_status(
        self,
        lesson_id: str,
        status: "LessonStatus",
        superseded_by: Optional[str] = None
    ) -> bool:
        """Update lesson status."""
        from .models import LessonStatus
        
        now = datetime.now(UTC)
        
        self.db.execute(
            """UPDATE agency_lessons 
               SET status = ?, superseded_by = ?, updated_at = ?
               WHERE lesson_id = ?""",
            (status.value, superseded_by, now.isoformat(), lesson_id)
        )
        self.db.commit()
        return True

    async def mark_lesson_applied(
        self,
        lesson_id: str,
        applied_by: str
    ) -> bool:
        """Mark a lesson as applied."""
        now = datetime.now(UTC)
        
        self.db.execute(
            """UPDATE agency_lessons 
               SET applied_at = ?, applied_by = ?, updated_at = ?
               WHERE lesson_id = ?""",
            (now.isoformat(), applied_by, now.isoformat(), lesson_id)
        )
        self.db.commit()
        return True


class SelfModelStore:
    """Persistence helper for agency_self_model table (Phase 5)."""

    def __init__(self, db_connection) -> None:
        self.db = db_connection

    async def upsert_entry(self, entry: "SelfModelEntry") -> "SelfModelEntry":
        """Create or update a self-model entry."""
        from .models import SelfModelEntry
        
        now = datetime.now(UTC)
        entry.last_updated = now
        
        # Check if entry exists
        existing = self.db.execute(
            """SELECT model_id FROM agency_self_model 
               WHERE user_id = ? AND entity_type = ? AND entity_id = ? AND window_start = ?""",
            (entry.user_id, entry.entity_type.value, entry.entity_id, entry.window_start.isoformat())
        ).fetchone()
        
        if existing:
            # Update
            self.db.execute(
                """UPDATE agency_self_model 
                   SET performance_summary = ?, window_end = ?, sample_size = ?,
                       confidence = ?, last_updated = ?
                   WHERE model_id = ?""",
                (
                    json.dumps(entry.performance_summary.dict()),
                    entry.window_end.isoformat(),
                    entry.sample_size,
                    entry.confidence,
                    entry.last_updated.isoformat(),
                    existing["model_id"]
                )
            )
        else:
            # Insert
            if not entry.created_at:
                entry.created_at = now
            
            self.db.execute(
                """INSERT INTO agency_self_model (
                    model_id, user_id, entity_type, entity_id,
                    performance_summary, window_start, window_end, sample_size,
                    confidence, last_updated, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    entry.model_id,
                    entry.user_id,
                    entry.entity_type.value,
                    entry.entity_id,
                    json.dumps(entry.performance_summary.dict()),
                    entry.window_start.isoformat(),
                    entry.window_end.isoformat(),
                    entry.sample_size,
                    entry.confidence,
                    entry.last_updated.isoformat(),
                    entry.created_at.isoformat(),
                )
            )
        
        self.db.commit()
        return entry

    async def get_latest_entry(
        self,
        user_id: str,
        entity_type: "EntityType",
        entity_id: str
    ) -> Optional["SelfModelEntry"]:
        """Get the most recent self-model entry for an entity."""
        from .models import SelfModelEntry, EntityType, PerformanceSummary
        
        row = self.db.execute(
            """SELECT * FROM agency_self_model 
               WHERE user_id = ? AND entity_type = ? AND entity_id = ?
               ORDER BY window_end DESC LIMIT 1""",
            (user_id, entity_type.value, entity_id)
        ).fetchone()
        
        if not row:
            return None
        
        return SelfModelEntry(
            model_id=row["model_id"],
            user_id=row["user_id"],
            entity_type=EntityType(row["entity_type"]),
            entity_id=row["entity_id"],
            performance_summary=PerformanceSummary(**json.loads(row["performance_summary"])),
            window_start=datetime.fromisoformat(row["window_start"]).replace(tzinfo=UTC),
            window_end=datetime.fromisoformat(row["window_end"]).replace(tzinfo=UTC),
            sample_size=row["sample_size"],
            confidence=row["confidence"],
            last_updated=datetime.fromisoformat(row["last_updated"]).replace(tzinfo=UTC),
            created_at=datetime.fromisoformat(row["created_at"]).replace(tzinfo=UTC),
        )


class ReflectionRunStore:
    """Persistence helper for agency_reflection_runs table (Phase 5)."""

    def __init__(self, db_connection) -> None:
        self.db = db_connection

    async def create_run(self, run: "ReflectionRun") -> "ReflectionRun":
        """Create a new reflection run."""
        from .models import ReflectionRun
        
        now = datetime.now(UTC)
        if not run.created_at:
            run.created_at = now

        self.db.execute(
            """INSERT INTO agency_reflection_runs (
                run_id, user_id, run_type, trigger_reason,
                analysis_window_start, analysis_window_end,
                lessons_generated, lessons_applied,
                started_at, completed_at, duration_seconds,
                status, error_message, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                run.run_id,
                run.user_id,
                run.run_type.value,
                run.trigger_reason,
                run.analysis_window_start.isoformat(),
                run.analysis_window_end.isoformat(),
                run.lessons_generated,
                run.lessons_applied,
                run.started_at.isoformat(),
                run.completed_at.isoformat() if run.completed_at else None,
                run.duration_seconds,
                run.status.value,
                run.error_message,
                run.created_at.isoformat(),
            ),
        )
        self.db.commit()
        return run

    async def update_run(
        self,
        run_id: str,
        status: "RunStatus",
        completed_at: Optional[datetime] = None,
        duration_seconds: Optional[float] = None,
        lessons_generated: Optional[int] = None,
        lessons_applied: Optional[int] = None,
        error_message: Optional[str] = None
    ) -> bool:
        """Update reflection run status and results."""
        from .models import RunStatus
        
        updates = ["status = ?"]
        params = [status.value]
        
        if completed_at:
            updates.append("completed_at = ?")
            params.append(completed_at.isoformat())
        
        if duration_seconds is not None:
            updates.append("duration_seconds = ?")
            params.append(duration_seconds)
        
        if lessons_generated is not None:
            updates.append("lessons_generated = ?")
            params.append(lessons_generated)
        
        if lessons_applied is not None:
            updates.append("lessons_applied = ?")
            params.append(lessons_applied)
        
        if error_message is not None:
            updates.append("error_message = ?")
            params.append(error_message)
        
        params.append(run_id)
        
        self.db.execute(
            f"UPDATE agency_reflection_runs SET {', '.join(updates)} WHERE run_id = ?",
            tuple(params)
        )
        self.db.commit()
        return True

    async def get_run(self, run_id: str) -> Optional["ReflectionRun"]:
        """Get a reflection run by ID."""
        from .models import ReflectionRun, RunType, RunStatus
        
        row = self.db.execute(
            "SELECT * FROM agency_reflection_runs WHERE run_id = ?",
            (run_id,)
        ).fetchone()
        
        if not row:
            return None
        
        return ReflectionRun(
            run_id=row["run_id"],
            user_id=row["user_id"],
            run_type=RunType(row["run_type"]),
            trigger_reason=row["trigger_reason"],
            analysis_window_start=datetime.fromisoformat(row["analysis_window_start"]).replace(tzinfo=UTC),
            analysis_window_end=datetime.fromisoformat(row["analysis_window_end"]).replace(tzinfo=UTC),
            lessons_generated=row["lessons_generated"],
            lessons_applied=row["lessons_applied"],
            started_at=datetime.fromisoformat(row["started_at"]).replace(tzinfo=UTC),
            completed_at=datetime.fromisoformat(row["completed_at"]).replace(tzinfo=UTC) if row["completed_at"] else None,
            duration_seconds=row["duration_seconds"],
            status=RunStatus(row["status"]),
            error_message=row["error_message"],
            created_at=datetime.fromisoformat(row["created_at"]).replace(tzinfo=UTC),
        )

    async def get_recent_runs(
        self,
        user_id: str,
        limit: int = 10
    ) -> List["ReflectionRun"]:
        """Get recent reflection runs for a user."""
        rows = self.db.execute(
            """SELECT run_id FROM agency_reflection_runs 
               WHERE user_id = ? 
               ORDER BY started_at DESC 
               LIMIT ?""",
            (user_id, limit)
        ).fetchall()
        
        runs = []
        for row in rows:
            run = await self.get_run(row["run_id"])
            if run:
                runs.append(run)
        
        return runs
