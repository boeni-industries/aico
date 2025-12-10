from __future__ import annotations

import json
from datetime import datetime
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
            now = datetime.utcnow()
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
                created_at=datetime.fromisoformat(row[9]) if row[9] else datetime.utcnow(),
                updated_at=datetime.fromisoformat(row[10]) if row[10] else datetime.utcnow(),
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
                        created_at=datetime.fromisoformat(row[9]) if row[9] else datetime.utcnow(),
                        updated_at=datetime.fromisoformat(row[10]) if row[10] else datetime.utcnow(),
                    )
                )
            return goals
        except Exception as e:
            logger.error(f"[AGENCY_GOALS] Failed to retrieve goals: {e}", extra={"user_id": user_id})
            raise

    async def update_goal_status(self, goal_id: str, new_status: GoalStatus) -> None:
        """Update goal status."""
        try:
            now = datetime.utcnow().isoformat()
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
                        created_at=datetime.fromisoformat(row[9]) if row[9] else datetime.utcnow(),
                        updated_at=datetime.fromisoformat(row[10]) if row[10] else datetime.utcnow(),
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
            now = datetime.utcnow()
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
                created_at=datetime.fromisoformat(row[5]) if row[5] else datetime.utcnow(),
                updated_at=datetime.fromisoformat(row[6]) if row[6] else datetime.utcnow(),
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
                        created_at=datetime.fromisoformat(row[5]) if row[5] else datetime.utcnow(),
                        updated_at=datetime.fromisoformat(row[6]) if row[6] else datetime.utcnow(),
                    )
                )
            return plans
        except Exception as e:
            logger.error(f"[AGENCY_PLANS] Failed to retrieve plans: {e}", extra={"goal_id": goal_id})
            raise

    async def update_plan_status(self, plan_id: str, new_status: PlanStatus) -> None:
        """Update plan status."""
        try:
            now = datetime.utcnow().isoformat()
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
            now = datetime.utcnow().isoformat()
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
                    event.created_at.isoformat() if event.created_at else datetime.utcnow().isoformat(),
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
        now = datetime.utcnow()
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
