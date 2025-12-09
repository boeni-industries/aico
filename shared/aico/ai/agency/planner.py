from __future__ import annotations

import uuid
from datetime import datetime
from typing import List, Optional

from aico.core.logging import get_logger

from .models import Goal, Plan, PlanStatus, PlanStep, StepStatus
from .templates import PLAN_SHAPES, PlanShape


logger = get_logger("shared", "ai.agency.planner")


class Planner:
    """Phase 1 planning skeleton.

    Converts goals into simple linear plans with a small number of steps.
    LLM-backed planning can be added behind this interface in later phases.
    """

    def __init__(self) -> None:
        pass

    async def generate_initial_plan(self, goal: Goal) -> Plan:
        """Generate a very simple initial plan for a goal.

        For Phase 1 this uses deterministic placeholder steps so that
        persistence, scheduler integration, and telemetry can be built
        without depending on complex LLM behaviours.
        """

        plan_id = str(uuid.uuid4())

        # Try to use a hand-authored plan shape first
        steps: List[PlanStep] = []
        selected_shape: Optional[PlanShape] = None

        for shape in PLAN_SHAPES.values():
            if goal.goal_type in shape["applicable_goal_types"]:
                selected_shape = shape
                break

        if selected_shape:
            for index, abstract_step in enumerate(selected_shape["steps"], start=1):
                steps.append(
                    PlanStep(
                        step_id=str(uuid.uuid4()),
                        order=index,
                        description=abstract_step["description"].replace("this goal", goal.title),
                        status=StepStatus.PENDING,
                        metadata={
                            "shape_id": selected_shape["id"],
                            "shape_role": abstract_step["role"],
                            "abstract_step_id": abstract_step["id"],
                        },
                    )
                )
        else:
            # Fallback: minimal two-step linear plan as a starting point
            steps = [
                PlanStep(
                    step_id=str(uuid.uuid4()),
                    order=1,
                    description=f"Clarify details and constraints for goal: {goal.title}",
                    status=StepStatus.PENDING,
                    metadata={"phase": "intake"},
                ),
                PlanStep(
                    step_id=str(uuid.uuid4()),
                    order=2,
                    description=f"Take first concrete action towards: {goal.title}",
                    status=StepStatus.PENDING,
                    metadata={"phase": "action"},
                ),
            ]

        plan = Plan(
            plan_id=plan_id,
            goal_id=goal.goal_id,
            status=PlanStatus.DRAFT,
            steps=steps,
            metadata={"generated_at": datetime.utcnow().isoformat()},
        )

        logger.info(
            "[AGENCY_PLANNER] Generated initial plan",
            extra={
                "goal_id": goal.goal_id,
                "plan_id": plan_id,
                "step_count": len(steps),
                "shape_id": selected_shape["id"] if selected_shape else None,
            },
        )

        return plan
