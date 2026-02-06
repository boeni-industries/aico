from .models import (
    Goal,
    GoalOrigin,
    GoalPriority,
    GoalStatus,
    Plan,
    PlanStatus,
    PlanStep,
    StepStatus,
    AgencyEvent,
    ReflectionNote,
)
# GoalStore and PlanStore REMOVED - use aico.services.agency_service.AgencyService instead
# AgencyEventStore and ReflectionStore REMOVED - legacy storage code eliminated

import importlib
from typing import Any
from .arbiter import (
    GoalArbiter,
    IntentionSet,
    Intention,
    IntentionStatus,
    PriorityBand,
    ScoredGoal,
)


_LAZY_IMPORTS = {
    "Planner": (".planner", "Planner"),
    "AgencyEngine": (".engine", "AgencyEngine"),
    "ValuesEthicsService": (".values_ethics", "ValuesEthicsService"),
    "PolicyEffect": (".values_ethics", "PolicyEffect"),
    "PolicyRule": (".values_ethics", "PolicyRule"),
    "PolicyTargetType": (".values_ethics", "PolicyTargetType"),
    "ValueProfile": (".values_ethics", "ValueProfile"),
    "Consent": (".values_ethics", "Consent"),
    "ConsentDecision": (".values_ethics", "ConsentDecision"),
    "EvaluationResult": (".values_ethics", "EvaluationResult"),
    "PerceptualEvent": (".perceptual_events", "PerceptualEvent"),
    "PerceptType": (".perceptual_events", "PerceptType"),
    "GoalHorizon": (".perceptual_events", "GoalHorizon"),
    "GoalOriginType": (".perceptual_events", "GoalOriginType"),
    "UserGoalExtractor": (".goal_extractor", "UserGoalExtractor"),
    "get_goal_extractor": (".goal_extractor", "get_goal_extractor"),
}


def __getattr__(name: str) -> Any:
    lazy = _LAZY_IMPORTS.get(name)
    if lazy is None:
        raise AttributeError(f"module '{__name__}' has no attribute '{name}'")

    module_name, symbol_name = lazy
    module = importlib.import_module(module_name, __name__)
    value = getattr(module, symbol_name)
    globals()[name] = value
    return value

__all__ = [
    "Goal",
    "GoalOrigin",
    "GoalPriority",
    "GoalStatus",
    "Plan",
    "PlanStatus",
    "PlanStep",
    "StepStatus",
    "AgencyEvent",
    "ReflectionNote",
    "Planner",
    "AgencyEngine",
    "ValuesEthicsService",
    "PolicyEffect",
    "PolicyRule",
    "PolicyTargetType",
    "ValueProfile",
    "Consent",
    "ConsentDecision",
    "EvaluationResult",
    "GoalArbiter",
    "IntentionSet",
    "Intention",
    "IntentionStatus",
    "PriorityBand",
    "ScoredGoal",
    "PerceptualEvent",
    "PerceptType",
    "GoalHorizon",
    "GoalOriginType",
    "UserGoalExtractor",
    "get_goal_extractor",
]
