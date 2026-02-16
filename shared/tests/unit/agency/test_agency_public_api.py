import aico.ai.agency as agency


def test_agency_public_api_exports_are_stable():
    # Models (domain / persistence-facing)
    assert hasattr(agency, "Goal")
    assert hasattr(agency, "GoalOrigin")
    assert hasattr(agency, "GoalPriority")
    assert hasattr(agency, "GoalStatus")
    assert hasattr(agency, "Plan")
    assert hasattr(agency, "PlanStatus")
    assert hasattr(agency, "PlanStep")
    assert hasattr(agency, "StepStatus")
    assert hasattr(agency, "AgencyEvent")
    assert hasattr(agency, "ReflectionNote")

    # Arbiter (runtime decision/policy)
    assert hasattr(agency, "GoalArbiter")
    assert hasattr(agency, "Intention")
    assert hasattr(agency, "IntentionSet")
    assert hasattr(agency, "IntentionStatus")
    assert hasattr(agency, "PriorityBand")
    assert hasattr(agency, "ScoredGoal")

    # Stale export guard (previous startup failure)
    assert not hasattr(agency, "ActionIntent")


def test_agency_public_api_symbols_point_to_intended_modules():
    # Ensure we don't regress by accidentally re-exporting arbiter types from models.
    assert agency.Goal.__module__ == "aico.ai.agency.models"
    assert agency.Plan.__module__ == "aico.ai.agency.models"

    assert agency.Intention.__module__ == "aico.ai.agency.arbiter"
    assert agency.IntentionSet.__module__ == "aico.ai.agency.arbiter"
    assert agency.GoalArbiter.__module__ == "aico.ai.agency.arbiter"
