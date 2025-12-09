from __future__ import annotations

import uuid
from typing import Any, Callable, Dict, Optional, Tuple, Awaitable
from datetime import datetime

from aico.core.config import ConfigurationManager
from aico.core.logging import get_logger
from aico.ai.base import BaseAIProcessor

from .models import (
    Goal,
    GoalOrigin,
    GoalPriority,
    GoalStatus,
    Plan,
    AgencyEvent,
)
from .store import GoalStore, PlanStore, AgencyEventStore, ReflectionStore
from .planner import Planner


logger = get_logger("shared", "ai.agency.engine")


class AgencyEngine(BaseAIProcessor):
    """Central orchestrator for autonomous agency.

    Coordinates goals, plans, events, and (later) proactive behaviours.
    This is the primary entrypoint that the AgencyPlugin should use.
    """

    def __init__(self, config: ConfigurationManager, db_connection) -> None:
        super().__init__()
        self.config = config
        self._db_connection = db_connection

        self.goal_store = GoalStore(db_connection)
        self.plan_store = PlanStore(db_connection)
        self.event_store = AgencyEventStore(db_connection)
        self.reflection_store = ReflectionStore(db_connection)
        self.planner = Planner()
        
        # Optional backend hook for LLM-based plan refinement (injected by backend)
        self._llm_plan_refiner: Optional[Callable[[Goal, Plan], Awaitable[Plan]]] = None

    async def initialize(self) -> None:  # type: ignore[override]
        """Placeholder for future initialization hooks."""
        return
    
    def set_llm_plan_refiner(self, refiner: Callable[[Goal, Plan], Awaitable[Plan]]) -> None:
        """Inject an LLM plan refinement callback from the backend layer.
        
        This allows the backend to provide LLM-enhanced planning without
        introducing backend dependencies into the shared agency code.
        """
        self._llm_plan_refiner = refiner
        logger.info("[AGENCY_ENGINE] LLM plan refiner injected")

    # ------------------------------------------------------------------
    # Goal & plan API (Phase 1 core)
    # ------------------------------------------------------------------

    async def create_goal_with_optional_plan(
        self,
        *,
        user_id: str,
        title: str,
        description: Optional[str] = None,
        origin: GoalOrigin = GoalOrigin.USER,
        goal_type: str = "project",
        priority: GoalPriority = GoalPriority.NORMAL,
        metadata: Optional[Dict[str, Any]] = None,
        auto_plan: bool = True,
    ) -> Tuple[Goal, Optional[Plan]]:
        """Create a new goal and (optionally) generate an initial plan."""

        goal = Goal(
            goal_id=str(uuid.uuid4()),
            user_id=user_id,
            origin=origin,
            goal_type=goal_type,
            title=title,
            description=description,
            status=GoalStatus.PENDING,
            priority=priority,
            metadata=metadata or {},
        )

        goal = await self.goal_store.create_goal(goal)

        await self.event_store.log_event(
            AgencyEvent(
                user_id=user_id,
                goal_id=goal.goal_id,
                plan_id=None,
                event_type="goal_created",
                source="agency_engine",
                payload={"title": title, "goal_type": goal_type},
            )
        )

        plan: Optional[Plan] = None
        if auto_plan:
            plan = await self._generate_and_store_plan(goal)

        return goal, plan

    async def create_hobby_goal_with_optional_plan(
        self,
        *,
        user_id: str,
        title: str,
        description: Optional[str] = None,
        goal_type: str = "hobby",
        priority: GoalPriority = GoalPriority.NORMAL,
        metadata: Optional[Dict[str, Any]] = None,
        auto_plan: bool = True,
    ) -> Tuple[Goal, Optional[Plan]]:
        """Convenience helper for creating agent-self hobby goals.

        Uses origin=HOBBY so these can be distinguished from direct user goals.
        """

        return await self.create_goal_with_optional_plan(
            user_id=user_id,
            title=title,
            description=description,
            origin=GoalOrigin.HOBBY,
            goal_type=goal_type,
            priority=priority,
            metadata=metadata,
            auto_plan=auto_plan,
        )

    async def create_maintenance_goal_with_optional_plan(
        self,
        *,
        user_id: str,
        title: str,
        description: Optional[str] = None,
        goal_type: str = "maintenance",
        priority: GoalPriority = GoalPriority.NORMAL,
        metadata: Optional[Dict[str, Any]] = None,
        auto_plan: bool = True,
    ) -> Tuple[Goal, Optional[Plan]]:
        """Convenience helper for creating system-maintenance goals."""

        return await self.create_goal_with_optional_plan(
            user_id=user_id,
            title=title,
            description=description,
            origin=GoalOrigin.MAINTENANCE,
            goal_type=goal_type,
            priority=priority,
            metadata=metadata,
            auto_plan=auto_plan,
        )

    async def _generate_and_store_plan(self, goal: Goal) -> Plan:
        """Generate an initial plan for a goal and persist it.
        
        Uses deterministic planner first, then optionally refines with LLM
        if a refiner callback has been injected by the backend.
        """

        # Generate base plan using deterministic planner
        plan = await self.planner.generate_initial_plan(goal)
        
        # Optionally refine with LLM if backend has injected a refiner
        if self._llm_plan_refiner:
            try:
                plan = await self._llm_plan_refiner(goal, plan)
            except Exception as e:
                logger.warning(f"[AGENCY_ENGINE] LLM plan refinement failed: {e}, using base plan")
        
        # Persist the plan (base or refined)
        plan = await self.plan_store.create_plan(plan)

        await self.event_store.log_event(
            AgencyEvent(
                user_id=goal.user_id,
                goal_id=goal.goal_id,
                plan_id=plan.plan_id,
                event_type="plan_generated",
                source="agency_engine",
                payload={
                    "step_count": len(plan.steps),
                    "llm_refined": plan.metadata.get("llm_refined", False),
                },
            )
        )

        return plan

    # ------------------------------------------------------------------
    # Goal lifecycle helpers (Phase 1)
    # ------------------------------------------------------------------

    async def get_goal(self, goal_id: str) -> Optional[Goal]:
        """Fetch a single goal by ID."""

        return await self.goal_store.get_goal(goal_id)

    async def list_goals_for_user(
        self,
        user_id: str,
        status: Optional[GoalStatus] = None,
    ) -> list[Goal]:
        """List goals for a user, optionally filtered by status."""

        return await self.goal_store.list_goals(user_id=user_id, status=status)

    async def _change_goal_status(
        self,
        *,
        goal_id: str,
        new_status: GoalStatus,
        event_type: str,
        source: str = "agency_engine",
        payload: Optional[Dict[str, Any]] = None,
    ) -> Optional[Goal]:
        """Internal helper to transition goal status and log telemetry."""

        goal = await self.goal_store.get_goal(goal_id)
        if not goal:
            logger.warning("[AGENCY_ENGINE] Attempted to change status of unknown goal", extra={"goal_id": goal_id})
            return None

        await self.goal_store.update_goal_status(goal_id, new_status)

        await self.event_store.log_event(
            AgencyEvent(
                user_id=goal.user_id,
                goal_id=goal.goal_id,
                plan_id=None,
                event_type=event_type,
                source=source,
                payload={
                    "from": goal.status.value,
                    "to": new_status.value,
                    **(payload or {}),
                },
            )
        )

        # Return updated goal snapshot (caller can ignore if not needed)
        updated = await self.goal_store.get_goal(goal_id)
        return updated

    async def activate_goal(self, goal_id: str) -> Optional[Goal]:
        """Mark a goal as active."""
        logger.info("[AGENCY_ENGINE] Activating goal", extra={"goal_id": goal_id})
        return await self._change_goal_status(
            goal_id=goal_id,
            new_status=GoalStatus.ACTIVE,
            event_type="goal_activated",
        )

    async def pause_goal(self, goal_id: str) -> Optional[Goal]:
        """Pause a goal (user-requested or system-initiated)."""
        logger.info("[AGENCY_ENGINE] Pausing goal", extra={"goal_id": goal_id})
        return await self._change_goal_status(
            goal_id=goal_id,
            new_status=GoalStatus.PAUSED,
            event_type="goal_paused",
        )

    async def complete_goal(self, goal_id: str) -> Optional[Goal]:
        """Mark a goal as completed."""
        logger.info("[AGENCY_ENGINE] Completing goal", extra={"goal_id": goal_id})
        return await self._change_goal_status(
            goal_id=goal_id,
            new_status=GoalStatus.COMPLETED,
            event_type="goal_completed",
        )

    async def retire_goal(self, goal_id: str) -> Optional[Goal]:
        """Retire a goal (abandoned, no longer relevant, etc.)."""
        logger.info("[AGENCY_ENGINE] Retiring goal", extra={"goal_id": goal_id})
        return await self._change_goal_status(
            goal_id=goal_id,
            new_status=GoalStatus.RETIRED,
            event_type="goal_retired",
        )

    # ------------------------------------------------------------------
    # Contract-style entrypoint for AgencyPlugin (Phase 1 stub)
    # ------------------------------------------------------------------

    async def analyze_conversation_turn(
        self,
        *,
        user_id: str,
        text: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Minimal contract-compatible analysis stub.

        Returns a structure compatible with AgencyPlugin's CapabilityContract.
        Later phases can hook goal detection and proactive triggers here.
        """

        analysis_timestamp = datetime.utcnow().isoformat()

        await self.event_store.log_event(
            AgencyEvent(
                user_id=user_id,
                goal_id=None,
                plan_id=None,
                event_type="turn_analyzed",
                source="agency_engine",
                payload={"text_length": len(text)},
            )
        )

        result: Dict[str, Any] = {
            "proactive_suggestions": [],
            "autonomous_goals": [],
            "behavioral_triggers": {},
            "confidence": 0.0,
            "analysis_timestamp": analysis_timestamp,
        }

        return result
