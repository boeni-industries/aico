"""
Agency Service

Replaces shared/aico/ai/agency/store.py with repository-based implementation.
Provides high-level agency operations using the 17 agency repositories.
"""

from __future__ import annotations

import json
from datetime import datetime, UTC
from typing import Any, Dict, List, Optional
from uuid import uuid4

from aico.core.logging import get_logger
from aico.data.uow import UnitOfWork
from aico.ai.agency.models import (
    Goal,
    GoalOrigin,
    GoalPriority,
    GoalStatus,
    Plan,
    PlanStatus,
)

logger = get_logger("shared.services.agency")


class AgencyService:
    """
    Service layer for agency operations.
    
    Replaces the legacy GoalStore, PlanStore, ReflectionStore, etc.
    Uses repositories through Unit of Work pattern.
    """

    def __init__(self, uow: UnitOfWork):
        self.uow = uow

    # ==================== Goal Operations ====================

    async def create_goal(self, goal: Goal) -> Goal:
        """Create a new goal."""
        try:
            now = datetime.now(UTC)
            goal.created_at = now
            goal.updated_at = now
            
            created = await self.uow.goals.create(goal)
            await self.uow.commit()
            
            logger.info("[AGENCY_SERVICE] Created goal", extra={"goal_id": goal.goal_id, "user_id": goal.user_id})
            return created
        except Exception as e:
            logger.error(f"[AGENCY_SERVICE] Failed to create goal: {e}", extra={"goal_id": goal.goal_id})
            await self.uow.rollback()
            raise

    async def get_goal(self, goal_id: str) -> Optional[Goal]:
        """Retrieve a goal by ID."""
        try:
            return await self.uow.goals.get_by_id(goal_id)
        except Exception as e:
            logger.error(f"[AGENCY_SERVICE] Failed to retrieve goal: {e}", extra={"goal_id": goal_id})
            raise

    async def list_goals(self, user_id: str, status: Optional[GoalStatus] = None) -> List[Goal]:
        """Retrieve a list of goals for a user."""
        try:
            filters = {"user_id": user_id}
            if status:
                filters["status"] = status.value
            
            return await self.uow.goals.list(filters=filters)
        except Exception as e:
            logger.error(f"[AGENCY_SERVICE] Failed to list goals: {e}", extra={"user_id": user_id})
            raise

    async def get_goals_by_status(self, status: GoalStatus | str, limit: int = 100) -> List[Goal]:
        """Retrieve goals across users filtered by status.

        This replaces legacy GoalStore.get_goals_by_status for scheduler tasks
        like AgencyArbiterTask.
        """
        try:
            if isinstance(status, GoalStatus):
                status_value = status.value
            else:
                status_value = status

            filters = {"status": status_value}
            return await self.uow.goals.list(filters=filters, limit=limit)
        except Exception as e:
            logger.error(
                f"[AGENCY_SERVICE] Failed to get goals by status: {e}",
                extra={"status": getattr(status, "value", status)},
            )
            raise

    async def update_goal(self, goal: Goal) -> Goal:
        """Update an existing goal."""
        try:
            goal.updated_at = datetime.now(UTC)
            updated = await self.uow.goals.update(goal)
            await self.uow.commit()
            
            logger.info("[AGENCY_SERVICE] Updated goal", extra={"goal_id": goal.goal_id})
            return updated
        except Exception as e:
            logger.error(f"[AGENCY_SERVICE] Failed to update goal: {e}", extra={"goal_id": goal.goal_id})
            await self.uow.rollback()
            raise

    async def delete_goal(self, goal_id: str) -> bool:
        """Delete a goal."""
        try:
            success = await self.uow.goals.delete(goal_id)
            await self.uow.commit()
            
            logger.info("[AGENCY_SERVICE] Deleted goal", extra={"goal_id": goal_id})
            return success
        except Exception as e:
            logger.error(f"[AGENCY_SERVICE] Failed to delete goal: {e}", extra={"goal_id": goal_id})
            await self.uow.rollback()
            raise

    async def get_active_goals(self, user_id: str) -> List[Goal]:
        """Get all active goals for a user."""
        return await self.list_goals(user_id, status=GoalStatus.ACTIVE)

    async def get_completed_goals(self, user_id: str) -> List[Goal]:
        """Get all completed goals for a user."""
        return await self.list_goals(user_id, status=GoalStatus.COMPLETED)

    # ==================== Plan Operations ====================

    async def create_plan(self, plan: Plan) -> Plan:
        """Create a new plan."""
        try:
            now = datetime.now(UTC)
            plan.created_at = now
            plan.updated_at = now
            
            created = await self.uow.plans.create(plan)
            await self.uow.commit()
            
            logger.info("[AGENCY_SERVICE] Created plan", extra={"plan_id": plan.plan_id, "goal_id": plan.goal_id})
            return created
        except Exception as e:
            logger.error(f"[AGENCY_SERVICE] Failed to create plan: {e}", extra={"plan_id": plan.plan_id})
            await self.uow.rollback()
            raise

    async def get_plan(self, plan_id: str) -> Optional[Plan]:
        """Retrieve a plan by ID."""
        try:
            return await self.uow.plans.get_by_id(plan_id)
        except Exception as e:
            logger.error(f"[AGENCY_SERVICE] Failed to retrieve plan: {e}", extra={"plan_id": plan_id})
            raise

    async def list_plans(self, goal_id: str, status: Optional[PlanStatus] = None) -> List[Plan]:
        """Retrieve plans for a goal."""
        try:
            filters = {"goal_id": goal_id}
            if status:
                filters["status"] = status.value
            
            return await self.uow.plans.list(filters=filters)
        except Exception as e:
            logger.error(f"[AGENCY_SERVICE] Failed to list plans: {e}", extra={"goal_id": goal_id})
            raise

    async def update_plan(self, plan: Plan) -> Plan:
        """Update an existing plan."""
        try:
            plan.updated_at = datetime.now(UTC)
            updated = await self.uow.plans.update(plan)
            await self.uow.commit()
            
            logger.info("[AGENCY_SERVICE] Updated plan", extra={"plan_id": plan.plan_id})
            return updated
        except Exception as e:
            logger.error(f"[AGENCY_SERVICE] Failed to update plan: {e}", extra={"plan_id": plan.plan_id})
            await self.uow.rollback()
            raise

    async def delete_plan(self, plan_id: str) -> bool:
        """Delete a plan."""
        try:
            success = await self.uow.plans.delete(plan_id)
            await self.uow.commit()
            
            logger.info("[AGENCY_SERVICE] Deleted plan", extra={"plan_id": plan_id})
            return success
        except Exception as e:
            logger.error(f"[AGENCY_SERVICE] Failed to delete plan: {e}", extra={"plan_id": plan_id})
            await self.uow.rollback()
            raise

    async def get_active_plan(self, goal_id: str) -> Optional[Plan]:
        """Get the active plan for a goal."""
        plans = await self.list_plans(goal_id, status=PlanStatus.ACTIVE)
        return plans[0] if plans else None

    # ==================== Reflection Operations ====================

    async def create_reflection_note(self, note_data: dict) -> dict:
        """Create a reflection note."""
        try:
            from aico.data.agency.models import AgencyReflectionNote
            note = AgencyReflectionNote(**note_data)
            created = await self.uow.agency_reflection_notes.create(note)
            await self.uow.commit()
            
            logger.info("[AGENCY_SERVICE] Created reflection note", extra={"note_id": created.note_id})
            return created
        except Exception as e:
            logger.error(f"[AGENCY_SERVICE] Failed to create reflection note: {e}")
            await self.uow.rollback()
            raise

    async def get_reflection_notes(self, goal_id: str) -> List[Any]:
        """Get reflection notes for a goal."""
        try:
            return await self.uow.agency_reflection_notes.list(filters={"goal_id": goal_id})
        except Exception as e:
            logger.error(f"[AGENCY_SERVICE] Failed to get reflection notes: {e}", extra={"goal_id": goal_id})
            raise

    # ==================== Execution Operations ====================

    async def create_plan_execution(self, execution_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a plan execution record."""
        try:
            from aico.data.agency.models import AgencyPlanExecution
            
            execution = AgencyPlanExecution(**execution_data)
            created = await self.uow.agency_plan_executions.create(execution)
            await self.uow.commit()
            
            logger.info("[AGENCY_SERVICE] Created plan execution", extra={"execution_id": created.execution_id})
            return created
        except Exception as e:
            logger.error(f"[AGENCY_SERVICE] Failed to create plan execution: {e}")
            await self.uow.rollback()
            raise

    async def get_plan_executions(self, plan_id: str) -> List[Any]:
        """Get executions for a plan."""
        try:
            return await self.uow.agency_plan_executions.list(filters={"plan_id": plan_id})
        except Exception as e:
            logger.error(f"[AGENCY_SERVICE] Failed to get plan executions: {e}", extra={"plan_id": plan_id})
            raise

    # ==================== Intention Set Operations ====================

    async def create_intention(self, intention_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create an intention."""
        try:
            from aico.data.agency.models import AgencyIntentionSet
            
            intention = AgencyIntentionSet(**intention_data)
            created = await self.uow.agency_intention_set.create(intention)
            await self.uow.commit()
            
            logger.info("[AGENCY_SERVICE] Created intention", extra={"intention_id": created.intention_id})
            return created
        except Exception as e:
            logger.error(f"[AGENCY_SERVICE] Failed to create intention: {e}")
            await self.uow.rollback()
            raise

    async def get_active_intentions(self, user_id: str) -> List[Any]:
        """Get active intentions for a user."""
        try:
            return await self.uow.agency_intention_set.list(filters={"user_id": user_id, "status": "active"})
        except Exception as e:
            logger.error(f"[AGENCY_SERVICE] Failed to get active intentions: {e}", extra={"user_id": user_id})
            raise
