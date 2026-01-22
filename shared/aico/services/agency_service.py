"""
Agency Service

Replaces shared/aico/ai/agency/store.py with repository-based implementation.
Provides high-level agency operations using the 17 agency repositories.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
from uuid import uuid4

# Python 3.9 compatibility
UTC = timezone.utc

from aico.core.logging import get_logger
from aico.data.uow import UnitOfWork
from aico.ai.agency.models import (
    Goal,
    GoalOrigin,
    GoalPriority,
    GoalStatus,
    Plan,
    PlanStatus,
    PlanStep,
)
from sqlalchemy.exc import IntegrityError

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
            # Narrow handling: duplicate open hobby/maintenance goals are expected in some
            # curiosity-driven flows. When the Postgres unique constraint
            # "uq_agency_goals_user_origin_title_open" fires, we treat it as
            # "goal already exists" and return the existing open goal instead of
            # propagating an error.

            if isinstance(e, IntegrityError):
                orig = getattr(e, "orig", None)
                constraint_name = getattr(orig, "constraint_name", None)

                if constraint_name == "uq_agency_goals_user_origin_title_open":
                    # Roll back the failed insert before running a lookup.
                    await self.uow.rollback()

                    origin_value = getattr(goal.origin, "value", goal.origin)

                    try:
                        existing = await self.uow.goals.find_open_goal_by_title(
                            goal.user_id,
                            origin_value,
                            goal.title,
                        )
                    except Exception as lookup_err:
                        logger.error(
                            "[AGENCY_SERVICE] Failed to resolve existing goal after unique constraint violation: "
                            f"{lookup_err}",
                            extra={
                                "goal_id": goal.goal_id,
                                "user_id": goal.user_id,
                                "origin": origin_value,
                                "title": goal.title,
                            },
                        )
                        # Fall back to the original error if lookup also fails.
                        raise e

                    if existing is not None:
                        logger.info(
                            "[AGENCY_SERVICE] Reusing existing open goal after uniqueness constraint "
                            "uq_agency_goals_user_origin_title_open",
                            extra={
                                "existing_goal_id": existing.goal_id,
                                "user_id": existing.user_id,
                                "origin": origin_value,
                                "title": existing.title,
                            },
                        )
                        return existing

                    # If we got the constraint but can't find the existing row, log and
                    # re-raise so we don't hide a deeper inconsistency.
                    logger.error(
                        "[AGENCY_SERVICE] Unique constraint triggered but no existing open goal found; "
                        "re-raising IntegrityError",
                        extra={
                            "goal_id": goal.goal_id,
                            "user_id": goal.user_id,
                            "origin": origin_value,
                            "title": goal.title,
                        },
                    )

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

    async def get_goal_by_curiosity_signal(self, signal_id: str) -> Optional[Goal]:
        """Retrieve a goal that was created from a specific curiosity signal, if any."""
        try:
            return await self.uow.goals.find_by_curiosity_signal_id(signal_id)
        except Exception as e:
            logger.error(
                f"[AGENCY_SERVICE] Failed to retrieve goal by curiosity signal: {e}",
                extra={"signal_id": signal_id},
            )
            raise

    async def find_open_goal_by_title(self, user_id: str, origin: GoalOrigin, title: str) -> Optional[Goal]:
        """Find an open goal for a user by origin and title.

        Open means status in (pending, active, in_progress).
        """
        try:
            return await self.uow.goals.find_open_goal_by_title(user_id, origin.value, title)
        except Exception as e:
            logger.error(
                f"[AGENCY_SERVICE] Failed to find open goal by title: {e}",
                extra={"user_id": user_id, "origin": origin.value, "title": title},
            )
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
            db_plan = await self.uow.plans.get_by_id(plan_id)
            if not db_plan:
                return None

            return self._to_domain_plan(db_plan)
        except Exception as e:
            logger.error(f"[AGENCY_SERVICE] Failed to retrieve plan: {e}", extra={"plan_id": plan_id})
            raise

    async def list_plans(self, goal_id: str, status: Optional[PlanStatus] = None) -> List[Plan]:
        """Retrieve plans for a goal."""
        try:
            filters = {"goal_id": goal_id}
            if status:
                filters["status"] = status.value
            
            db_plans = await self.uow.plans.list(filters=filters)
            return [self._to_domain_plan(p) for p in db_plans]
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

    # ==================== Internal Helpers ====================

    def _to_domain_plan(self, db_plan: Any) -> Plan:
        """Convert repository plan (with steps_json) to domain Plan with steps list.

        The repository model stores steps in steps_json (JSONB). This helper
        reconstructs PlanStep instances so that higher-level components like
        PlanExecutor can rely on plan.steps.
        """
        # Decode steps
        raw_steps = getattr(db_plan, "steps_json", None) or []

        # JSONB may already be a list of dicts or a JSON string
        if isinstance(raw_steps, str):
            try:
                raw_steps = json.loads(raw_steps)
            except Exception:
                raw_steps = []

        steps: List[PlanStep] = []
        for item in raw_steps:
            if isinstance(item, PlanStep):
                steps.append(item)
            elif isinstance(item, dict):
                # Best-effort reconstruction; missing fields fall back to PlanStep defaults
                steps.append(PlanStep.model_validate(item))

        # Decode metadata
        metadata = getattr(db_plan, "metadata", None) or {}

        # Status is stored as string in DB; map to PlanStatus enum if needed
        status_val = getattr(db_plan, "status", None)
        try:
            status_enum = PlanStatus(status_val) if isinstance(status_val, str) else status_val
        except Exception:
            status_enum = PlanStatus.DRAFT

        return Plan(
            plan_id=db_plan.plan_id,
            goal_id=db_plan.goal_id,
            title=getattr(db_plan, "title", None),
            description=getattr(db_plan, "description", None),
            status=status_enum,
            steps=steps,
            metadata=metadata,
            created_at=getattr(db_plan, "created_at", None),
            updated_at=getattr(db_plan, "updated_at", None),
        )

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
            from aico.data.agency.execution_models import AgencyPlanExecution
            
            execution = AgencyPlanExecution(**execution_data)
            created = await self.uow.agency_plan_executions.create(execution)
            await self.uow.commit()
            
            logger.info("[AGENCY_SERVICE] Created plan execution", extra={"execution_id": created.execution_id})
            return created
        except Exception as e:
            logger.error(f"[AGENCY_SERVICE] Failed to create plan execution: {e}")
            await self.uow.rollback()
            raise

    async def get_plan_executions(self, plan_id: str, limit: int = 10) -> List[Any]:
        """Get recent executions for a plan.

        By default this returns at most the last 10 executions to avoid
        loading unbounded history into API responses.
        """
        try:
            return await self.uow.agency_plan_executions.list(filters={"plan_id": plan_id}, limit=limit)
        except Exception as e:
            logger.error(
                f"[AGENCY_SERVICE] Failed to get plan executions: {e}",
                extra={"plan_id": plan_id, "limit": limit},
            )
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

    # ==================== Adaptive Arbiter Operations ====================

    async def save_bandit_arm(self, arm_data: Dict[str, Any]) -> None:
        """Save or update a bandit arm configuration."""
        try:
            from aico.data.agency.models import ArbiterBanditArm
            arm = ArbiterBanditArm(**arm_data)
            await self.uow.arbiter_bandit_arms.upsert(arm)
            await self.uow.commit()
            logger.debug(f"[AGENCY_SERVICE] Saved bandit arm: {arm_data.get('arm_id')}")
        except Exception as e:
            logger.error(f"[AGENCY_SERVICE] Failed to save bandit arm: {e}")
            await self.uow.rollback()
            raise

    async def get_bandit_arms(self) -> List[Dict[str, Any]]:
        """Get all bandit arm configurations."""
        try:
            arms = await self.uow.arbiter_bandit_arms.list()
            return [arm.to_dict() if hasattr(arm, 'to_dict') else arm for arm in arms]
        except Exception as e:
            logger.error(f"[AGENCY_SERVICE] Failed to get bandit arms: {e}")
            raise

    async def create_ab_test(self, test_data: Dict[str, Any]) -> None:
        """Create an A/B test for arbiter configurations."""
        try:
            from aico.data.agency.models import ArbiterABTest
            test = ArbiterABTest(**test_data)
            await self.uow.arbiter_ab_tests.create(test)
            await self.uow.commit()
            logger.info(f"[AGENCY_SERVICE] Created A/B test: {test_data.get('test_id')}")
        except Exception as e:
            logger.error(f"[AGENCY_SERVICE] Failed to create A/B test: {e}")
            await self.uow.rollback()
            raise

    async def get_ab_test(self, test_id: str) -> Optional[Dict[str, Any]]:
        """Get A/B test results."""
        try:
            test = await self.uow.arbiter_ab_tests.get_by_id(test_id)
            return test.to_dict() if test and hasattr(test, 'to_dict') else test
        except Exception as e:
            logger.error(f"[AGENCY_SERVICE] Failed to get A/B test: {e}")
            raise

    # ==================== Behavioral Feedback Operations ====================

    async def record_skill_execution(self, execution_data: Dict[str, Any]) -> str:
        """Record a skill execution."""
        try:
            from aico.data.agency.models import AgencySkillExecution
            execution = AgencySkillExecution(**execution_data)
            created = await self.uow.agency_skill_executions.create(execution)
            await self.uow.commit()
            logger.info(f"[AGENCY_SERVICE] Recorded skill execution: {created.execution_id}")
            return created.execution_id
        except Exception as e:
            logger.error(f"[AGENCY_SERVICE] Failed to record skill execution: {e}")
            await self.uow.rollback()
            raise

    async def link_goal_skill_execution(self, link_data: Dict[str, Any]) -> None:
        """Link a skill execution to a goal."""
        try:
            from aico.data.agency.models import AgencyGoalSkillExecution
            link = AgencyGoalSkillExecution(**link_data)
            await self.uow.agency_goal_skill_executions.create(link)
            await self.uow.commit()
            logger.debug(f"[AGENCY_SERVICE] Linked execution to goal: {link_data.get('goal_id')}")
        except Exception as e:
            logger.error(f"[AGENCY_SERVICE] Failed to link skill execution: {e}")
            await self.uow.rollback()
            raise

    async def get_goal_executions(self, goal_id: str) -> List[Dict[str, Any]]:
        """Get all skill executions for a goal."""
        try:
            # Use a join query through the repository
            executions = await self.uow.agency_skill_executions.get_by_goal(goal_id)
            return [e.to_dict() if hasattr(e, 'to_dict') else e for e in executions]
        except Exception as e:
            logger.error(f"[AGENCY_SERVICE] Failed to get goal executions: {e}")
            raise

    async def record_behavioral_feedback(self, feedback_data: Dict[str, Any]) -> str:
        """Record behavioral feedback."""
        try:
            from aico.data.agency.models import AMSBehavioralFeedback
            feedback = AMSBehavioralFeedback(**feedback_data)
            created = await self.uow.ams_behavioral_feedback.create(feedback)
            await self.uow.commit()
            logger.info(f"[AGENCY_SERVICE] Recorded behavioral feedback: {created.feedback_id}")
            return created.feedback_id
        except Exception as e:
            logger.error(f"[AGENCY_SERVICE] Failed to record behavioral feedback: {e}")
            await self.uow.rollback()
            raise

    async def get_skill_execution_outcome(self, execution_id: str) -> Optional[str]:
        """Get the outcome of a skill execution."""
        try:
            execution = await self.uow.agency_skill_executions.get_by_id(execution_id)
            return execution.outcome if execution else None
        except Exception as e:
            logger.error(f"[AGENCY_SERVICE] Failed to get execution outcome: {e}")
            raise

    async def update_feedback_outcome(self, feedback_id: str, outcome: str) -> None:
        """Update the outcome of a feedback record."""
        try:
            feedback = await self.uow.ams_behavioral_feedback.get_by_id(feedback_id)
            if feedback:
                feedback.outcome = outcome
                await self.uow.ams_behavioral_feedback.update(feedback)
                await self.uow.commit()
                logger.debug(f"[AGENCY_SERVICE] Updated feedback outcome: {feedback_id}")
        except Exception as e:
            logger.error(f"[AGENCY_SERVICE] Failed to update feedback outcome: {e}")
            await self.uow.rollback()
            raise

    async def create_feedback_request(self, request_data: Dict[str, Any]) -> str:
        """Create a user feedback request."""
        try:
            from aico.data.agency.models import UserFeedbackRequest
            request = UserFeedbackRequest(**request_data)
            created = await self.uow.user_feedback_requests.create(request)
            await self.uow.commit()
            logger.info(f"[AGENCY_SERVICE] Created feedback request: {created.request_id}")
            return created.request_id
        except Exception as e:
            logger.error(f"[AGENCY_SERVICE] Failed to create feedback request: {e}")
            await self.uow.rollback()
            raise

    async def respond_to_feedback_request(self, request_id: str, response: str, rating: Optional[float]) -> None:
        """Record user response to feedback request."""
        try:
            request = await self.uow.user_feedback_requests.get_by_id(request_id)
            if request:
                request.response = response
                request.rating = rating
                request.responded_at = datetime.now(UTC)
                await self.uow.user_feedback_requests.update(request)
                await self.uow.commit()
                logger.info(f"[AGENCY_SERVICE] Recorded feedback response: {request_id}")
        except Exception as e:
            logger.error(f"[AGENCY_SERVICE] Failed to respond to feedback request: {e}")
            await self.uow.rollback()
            raise

    async def get_pending_feedback_requests(self, user_id: str) -> List[Dict[str, Any]]:
        """Get pending feedback requests for a user."""
        try:
            requests = await self.uow.user_feedback_requests.list(
                filters={"user_id": user_id, "responded_at": None}
            )
            return [r.to_dict() if hasattr(r, 'to_dict') else r for r in requests]
        except Exception as e:
            logger.error(f"[AGENCY_SERVICE] Failed to get pending feedback requests: {e}")
            raise

    async def get_skill_performance_stats(self, skill_id: str, user_id: Optional[str] = None, days: int = 30) -> Dict[str, Any]:
        """Get performance statistics for a skill."""
        try:
            from_date = (datetime.now(UTC) - timedelta(days=days))
            stats = await self.uow.ams_behavioral_feedback.get_skill_stats(
                skill_id=skill_id,
                user_id=user_id,
                from_date=from_date
            )
            return stats
        except Exception as e:
            logger.error(f"[AGENCY_SERVICE] Failed to get skill performance stats: {e}")
            raise

    async def get_skill_trend_data(self, skill_id: str, days: int = 30) -> List[Dict[str, Any]]:
        """Get trend data for skill performance over time."""
        try:
            from_date = (datetime.now(UTC) - timedelta(days=days))
            trends = await self.uow.ams_behavioral_feedback.get_skill_trends(
                skill_id=skill_id,
                from_date=from_date
            )
            return trends
        except Exception as e:
            logger.error(f"[AGENCY_SERVICE] Failed to get skill trend data: {e}")
            raise

    # ==================== Step Execution Operations ====================

    async def create_step_execution(self, step_data: Dict[str, Any]) -> str:
        """Create a step execution record."""
        try:
            from aico.data.agency.execution_models import AgencyStepExecution
            step = AgencyStepExecution(**step_data)
            created = await self.uow.agency_step_executions.create(step)
            await self.uow.commit()
            logger.debug(f"[AGENCY_SERVICE] Created step execution: {created.step_execution_id}")
            return created.step_execution_id
        except Exception as e:
            logger.error(f"[AGENCY_SERVICE] Failed to create step execution: {e}")
            await self.uow.rollback()
            raise

    async def update_step_execution(self, step_execution_id: str, updates: Dict[str, Any]) -> None:
        """Update a step execution record."""
        try:
            step = await self.uow.agency_step_executions.get_by_id(step_execution_id)
            if step:
                for key, value in updates.items():
                    setattr(step, key, value)
                await self.uow.agency_step_executions.update(step)
                await self.uow.commit()
                logger.debug(f"[AGENCY_SERVICE] Updated step execution: {step_execution_id}")
        except Exception as e:
            logger.error(f"[AGENCY_SERVICE] Failed to update step execution: {e}")
            await self.uow.rollback()
            raise

    async def get_step_executions(self, execution_id: str) -> List[Dict[str, Any]]:
        """Get all step executions for a plan execution."""
        try:
            steps = await self.uow.agency_step_executions.list(
                filters={"execution_id": execution_id}
            )
            return [s.to_dict() if hasattr(s, 'to_dict') else s for s in steps]
        except Exception as e:
            logger.error(f"[AGENCY_SERVICE] Failed to get step executions: {e}")
            raise

    async def update_plan_execution(self, execution_id: str, updates: Dict[str, Any]) -> None:
        """Update a plan execution record."""
        try:
            execution = await self.uow.agency_plan_executions.get_by_id(execution_id)
            if execution:
                for key, value in updates.items():
                    setattr(execution, key, value)
                # Repository API expects (execution_id, entity)
                await self.uow.agency_plan_executions.update(execution_id, execution)
                await self.uow.commit()
                logger.debug(f"[AGENCY_SERVICE] Updated plan execution: {execution_id}")
        except Exception as e:
            logger.error(f"[AGENCY_SERVICE] Failed to update plan execution: {e}")
            await self.uow.rollback()
            raise

    async def create_plan_execution(self, execution_data: Dict[str, Any]) -> str:
        """Create a plan execution record."""
        try:
            from aico.data.agency.execution_models import AgencyPlanExecution
            execution = AgencyPlanExecution(**execution_data)
            created = await self.uow.agency_plan_executions.create(execution)
            await self.uow.commit()
            logger.info(f"[AGENCY_SERVICE] Created plan execution: {created.execution_id}")
            return created.execution_id
        except Exception as e:
            logger.error(f"[AGENCY_SERVICE] Failed to create plan execution: {e}")
            await self.uow.rollback()
            raise

    async def get_plan_execution(self, execution_id: str) -> Optional[Dict[str, Any]]:
        """Get a plan execution."""
        try:
            execution = await self.uow.agency_plan_executions.get_by_id(execution_id)
            if not execution:
                return None
            # Convert Pydantic model to dict
            return execution.model_dump() if hasattr(execution, 'model_dump') else dict(execution)
        except Exception as e:
            logger.error(f"[AGENCY_SERVICE] Failed to get plan execution: {e}")
            raise

    async def get_next_pending_step(self, execution_id: str) -> Optional[Dict[str, Any]]:
        """Get the next pending step for an execution."""
        try:
            steps = await self.uow.agency_step_executions.list(
                filters={"execution_id": execution_id, "status": "pending"},
                order_by="step_order",
                limit=1
            )
            if steps:
                step = steps[0]
                return step.to_dict() if hasattr(step, 'to_dict') else step
            return None
        except Exception as e:
            logger.error(f"[AGENCY_SERVICE] Failed to get next pending step: {e}")
            raise

    async def count_pending_steps(self, execution_id: str) -> int:
        """Count pending steps for an execution."""
        try:
            steps = await self.uow.agency_step_executions.list(
                filters={"execution_id": execution_id, "status": "pending"}
            )
            return len(steps)
        except Exception as e:
            logger.error(f"[AGENCY_SERVICE] Failed to count pending steps: {e}")
            return 0

    async def count_step_executions(self, execution_id: str) -> int:
        """Count total step executions for an execution."""
        try:
            steps = await self.uow.agency_step_executions.list(
                filters={"execution_id": execution_id}
            )
            return len(steps)
        except Exception as e:
            logger.error(f"[AGENCY_SERVICE] Failed to count step executions: {e}")
            return 0

    async def create_execution_snapshot(self, snapshot_data: Dict[str, Any]) -> str:
        """Create an execution snapshot."""
        try:
            from aico.data.agency.execution_models import AgencyExecutionSnapshot
            snapshot = AgencyExecutionSnapshot(**snapshot_data)
            created = await self.uow.agency_execution_snapshots.create(snapshot)
            await self.uow.commit()
            logger.debug(f"[AGENCY_SERVICE] Created execution snapshot: {created.snapshot_id}")
            return created.snapshot_id
        except Exception as e:
            logger.error(f"[AGENCY_SERVICE] Failed to create execution snapshot: {e}")
            await self.uow.rollback()
            raise
