from __future__ import annotations

"""Planning templates and plan-shape patterns for the agency system.

This module centralises the hand-authored plan patterns that the Planner
can use, optionally combined with LLM calls, to generate concrete plans
from high-level goals.
"""

from typing import Dict, List, TypedDict


class PlanShapeStep(TypedDict):
    """Single abstract step in a plan shape pattern."""

    id: str
    role: str  # e.g. "research", "clarify", "act", "review"
    description: str


class PlanShape(TypedDict):
    """Pattern for a plan structure."""

    id: str
    name: str
    applicable_goal_types: List[str]
    steps: List[PlanShapeStep]


PLAN_SHAPES: Dict[str, PlanShape] = {
    "research_then_act": {
        "id": "research_then_act",
        "name": "Research then act",
        "applicable_goal_types": ["project", "learning", "decision"],
        "steps": [
            {
                "id": "clarify_goal",
                "role": "clarify",
                "description": "Clarify the specific question or outcome for this goal.",
            },
            {
                "id": "gather_information",
                "role": "research",
                "description": "Gather key information, examples, or constraints relevant to the goal.",
            },
            {
                "id": "synthesize_options",
                "role": "synthesize",
                "description": "Summarise options or approaches and choose a direction.",
            },
            {
                "id": "take_first_action",
                "role": "act",
                "description": "Take the first concrete action towards the chosen direction.",
            },
        ],
    },
    "implement_feature": {
        "id": "implement_feature",
        "name": "Implement a concrete feature or change",
        "applicable_goal_types": ["project", "feature", "development"],
        "steps": [
            {
                "id": "clarify_requirements",
                "role": "clarify",
                "description": "Clarify requirements, success criteria, and constraints.",
            },
            {
                "id": "design_solution",
                "role": "design",
                "description": "Sketch a simple design or approach for the change.",
            },
            {
                "id": "implement_minimum_slice",
                "role": "implement",
                "description": "Implement the smallest useful slice of the solution.",
            },
            {
                "id": "test_and_review",
                "role": "review",
                "description": "Test the change and review what should be done next.",
            },
        ],
    },
    "maintenance_cycle": {
        "id": "maintenance_cycle",
        "name": "Maintenance and cleanup cycle",
        "applicable_goal_types": ["maintenance", "cleanup", "refactor"],
        "steps": [
            {
                "id": "scan_and_list",
                "role": "scan",
                "description": "Scan for issues or areas that need maintenance and list them.",
            },
            {
                "id": "prioritize_items",
                "role": "prioritize",
                "description": "Prioritise the most important or impactful items.",
            },
            {
                "id": "fix_top_items",
                "role": "act",
                "description": "Work through the top one or two items in priority order.",
            },
            {
                "id": "verify_and_log",
                "role": "review",
                "description": "Verify changes and log what was done and what remains.",
            },
        ],
    },
}
