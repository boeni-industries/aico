---
title: Agency Component – Planning & Decomposition
---

# Planning & Decomposition

## Status

- **Implemented (v1)**: `Planner.generate_initial_plan(goal, context)` in `shared/aico/ai/agency/planner.py` generates a `Plan` with ordered `PlanStep`s using LLM-first with template + simple fallbacks.
- **Implemented (v1)**: plan domain models exist in `shared/aico/ai/agency/models.py` (`Plan`, `PlanStep`, `PlanStatus`, `StepStatus`).
- **Implemented (v1)**: plans are persisted alongside goals (see `AgencyService.list_plans(...)` usage in `backend/api/agency/router.py`, e.g. `GET /api/v1/agency/goals/{goal_id}/plans`).
- **WIP**: fully hierarchical planning (goals → subgoals → plan steps) with explicit world-model pre/postconditions and ontology grounding per step.

## 1. Purpose

The Planning & Decomposition component turns abstract **goals and intentions** into **executable plans** that can be bound to skills/tools and scheduled.

## 2. Conceptual Model

- Takes a **target goal/intention** (from the Goal System / Arbiter).  
- Uses LLM-based reasoning plus templates to propose a **plan**: an ordered or conditional set of **plan steps/tasks**.  
- Each plan step has:
  - a natural-language description,  
  - links to ontology entities via the World Model (Persons, Activities, LifeAreas, WorldStateFacts),  
  - preconditions and expected postconditions,  
  - one or more candidate Skills from the Skill Registry that can realise it.

**Implementation note (v1):** `PlanStep` currently includes `description`, `status`, optional `skill_id` / `tool_id`, `depends_on`, and a free-form `metadata` dict. Explicit `linked_entities` and formal pre/postconditions are **WIP**.

Planning is **hierarchical**: goals → subgoals → plan steps → skills → tools (see `agency-component-skills-tools.md`).

**WIP**: subgoal trees as first-class objects; current implementation primarily creates linear steps for a single goal.

## 3. Data Model (Conceptual)

- **Plan**  
  - `plan_id`, `goal_id`, `status` (proposed/active/completed/abandoned).  
  - structure: list/tree of **PlanStep** objects with dependencies.

**Implementation note (v1):** statuses are `draft|active|completed|paused|abandoned` (see `PlanStatus` in `shared/aico/ai/agency/models.py`).

- **PlanStep**  
  - `step_id`, `plan_id`, `description`,  
  - `linked_entities` (IDs from WM: Persons, Activities, LifeAreas, etc.),  
  - `preconditions` / `postconditions` (expressed as desired WorldStateFacts or goal states),  
  - `candidate_skills` (list of `skill_id`s from the Skill Registry),  
  - `status` (pending/in_progress/success/partial/failure).

**Implementation note (v1):** step status values are `pending|in_progress|done|skipped` (`StepStatus` in `shared/aico/ai/agency/models.py`).

## 4. Operations / Behaviour

- **PlanFromGoal(goal)** – propose one or more candidate plans for a goal.  
- **SelectPlan(plan_candidates)** – choose a plan given Values & Ethics, resources, and user preferences.  
- **BindSkills(plan)** – use the Skill Registry (see Skills doc) to assign concrete skills to executable steps.  
- **UpdatePlan(step_results)** – mark steps as succeeded/partial/failed, trigger backtracking or replanning when necessary.

**Implementation note (v1):** plan generation is implemented; step execution bookkeeping and replanning policies are partially implemented / evolving (**WIP**) and depend on plan execution tooling.

Plans are **read/write objects** stored alongside goals so Scheduler, Skills, and Self-Reflection can inspect and evolve them over time.

## 5. Replanning and Failure Modes (Conceptual)

- **Local retries** – if a plan step fails due to transient issues (e.g., tool timeout), Planner may retry the same step/skill a limited number of times before marking it `failure`.
- **Alternative skills** – if a step repeatedly fails or yields only partial results, Planner can select a different Skill from the registry that satisfies the same pre/postconditions (e.g., different summarisation skill or data source).
- **Plan patching** – Planner may insert extra steps before a failing step (e.g., gather missing facts, clarify with the user) when preconditions are not met. These steps become part of the same `plan_id`.
- **Goal-level fallback** – if multiple key steps fail or partial results accumulate, Planner can:
  - downgrade the goal (e.g., from "fully organise" to "provide partial overview"), or  
  - raise a clarification/repair goal (e.g., "ask user to resolve conflicting data").

Replanning decisions are informed by step statuses, World Model hypotheses/conflicts, Values & Ethics decisions (what is allowed to retry or escalate), and user feedback.
