---
title: Agency Metrics & State Visibility
---

# Agency Metrics & State Visibility

This document lists key **metrics, states, and KPIs** of the Agency system.


- **User-Facing Metrics** – values that can be surfaced directly (or with light explanation) to end users, including non-technical users.
- **Engineering & Debug Metrics** – values primarily for developers, operators, and evaluators.

Each table uses these columns:

- **Name** – Metric/state identifier.
- **Type** – Counter, gauge, enum/state, list, time-series, etc.
- **Scope** – Per-user, per-agent (global), per-session, per-goal, etc.
- **Purpose** – Why we track it.

## 1. User-Facing Metrics

### 1.1 Goals, Intentions & Work in Progress

| Name | Type | Scope | Purpose |
| ---- | ---- | ----- | ------- |
| primary_focus_intention | single goal summary | per-user | Represent the intention AICO currently treats as primary focus (top-scored by Goal Arbiter, with temporal smoothing). |
| active_intentions | list of goal summaries | per-user | Show what AICO is currently working on (top goals/intentions). |
| open_goals_total | gauge (count) | per-user | Indicate how many open projects/threads exist. |
| hobby_goals_active | list of hobby summaries | per-user | Make AICO’s own hobbies and self-projects visible. |

### 1.2 Curiosity, Intrinsic Motivation & Hobbies

| Name | Type | Scope | Purpose |
| ---- | ---- | ----- | ------- |
| curiosity_level | scalar (e.g. low/medium/high) | per-user | Communicate how strong curiosity-driven behaviour is right now. |
| curiosity_opportunities | short list of themes | per-user | Show what AICO is currently curious about (1–3 human-readable items). |
| hobby_activity_time | coarse duration per hobby | per-user, per-hobby | Indicate recent engagement with each hobby (e.g., "spent time this week"). |
| hobby_state | enum + summary | per-hobby | Present the status of each hobby (active/paused/completed) with a short description. |

### 1.3 Memory, World Model & Open Loops

| Name | Type | Scope | Purpose |
| ---- | ---- | ----- | ------- |
| open_loops_count | gauge | per-user | Let users know how many unresolved threads AICO is tracking. |
| last_consolidation_time | timestamp | per-user | Indicate when the last sleep-like consolidation ran ("last night", "2h ago"). |
| life_area_coverage | coarse breakdown (e.g. low/medium/high per LifeArea) | per-user | Give the user a simple view of how well AICO understands different areas of their life (Health, Work, Relationships, etc.) based on World Model facts. |
| known_conflicts_present | boolean + short summary | per-user | Indicate whether the World Model currently has unresolved contradictions in important domains (e.g. job, relationship, routine) and, optionally, offer to clarify them. |

### 1.4 Emotion, Relationship & Style

| Name | Type | Scope | Purpose |
| ---- | ---- | ----- | ------- |
| emotional_state_current | enum + intensity | per-user | Provide a simple description of AICO’s current emotional stance, when appropriate. |
| relationship_strength | scalar (coarsened) | per-user | Optionally summarise how close/stable AICO perceives the relationship (only if UX-appropriate). |

### 1.5 Agency Style, Initiative & Safety

| Name | Type | Scope | Purpose |
| ---- | ---- | ----- | ------- |
| initiative_ratio | scalar (e.g. "rarely / sometimes / often") | per-user | Communicate how often AICO initiates interactions vs just responding. |
| agency_initiated_messages | count (aggregated over a period) | per-user | Provide history of how many conversations AICO started recently. |
| safety_profile | config snapshot (coarse mode) | per-user, per-deployment | Show current safety/value mode (e.g., cautious / balanced / experimental). |
| consent_required_actions | list of pending items | per-user | Surface actions waiting on explicit user approval/consent. |

### 1.6 Self-Reflection, Change & Lifecycle

| Name | Type | Scope | Purpose |
| ---- | ---- | ----- | ------- |
| reflection_runs | yes/no + last timestamp | per-user | Indicate that AICO has recently reflected on behaviour ("I recently reflected on our week"). |
| behaviour_adjustments | short list of changes | per-user | Summarise what AICO is trying to do differently (high-level strategy changes). |
| lifecycle_phase | enum (ACTIVE / FOCUSED_WORK / IDLE_LIGHT / SLEEP_LIKE / MAINTENANCE) | per-user, per-agent | Expose the current `LifecycleState` (from the Lifecycle component) and drive room/posture in the 3D flat. |
| embodiment_state | enum (room, posture, activity label) | per-user | Map internal state to visual representation in the avatar and flat. |

## 2. Engineering & Debug Metrics

The following metrics are primarily intended for developers, operators, and evaluation dashboards. They provide deeper visibility into internal dynamics and performance.

### 2.1 Goals, Planning & Execution

| Name | Type | Scope | Purpose |
| ---- | ---- | ----- | ------- |
| goals_by_origin | breakdown (user / curiosity / hobby / maintenance) | per-user | Analyse balance of goal sources. |
| goal_lifecycle_events | event log | per-goal | Debug why goals were created/paused/completed/dropped. |
| plans_active | list of plan IDs + goal IDs | per-user | Inspect which plans are currently executing. |
| plan_depth | gauge (avg steps per plan) | per-agent, time-series | Monitor complexity of planning over time. |
| plan_execution_success_rate | ratio (0-1) | per-user, per-goal type | Evaluate how often planned steps execute successfully. |
| replanning_events | count / log | per-user | Detect instability or frequent context shifts. |

### 2.2 Curiosity, World Model & AMS

| Name | Type | Scope | Purpose |
| ---- | ---- | ----- | ------- |
| curiosity_signals_total | count/time-series | per-user, per-agent | Track overall rate of CuriositySignals emitted by detectors. |
| curiosity_signals_by_type | breakdown by `curiosity_type` | per-user | Analyse which kinds of curiosity (knowledge_gap, novelty, self_performance, hobby_play) are most active. |
| curiosity_signals_promoted | count/time-series | per-user | Count signals that passed all gates and became CuriositySignalEvents. |
| curiosity_signals_deferred_or_rejected | breakdown (values/ethics / emotion / resources / low_score) | per-user | Understand why curiosity opportunities did not become events or goals. |
| curiosity_goals_created | count/time-series | per-user | Track frequency of intrinsically motivated goals created from CuriositySignalEvents. |
| curiosity_goals_active | gauge (count) | per-user | Monitor how many curiosity- or agent-self-origin goals are currently active. |
| curiosity_goal_outcomes | breakdown (completed / user_rejected / auto_dropped) | per-user | Evaluate how curiosity-driven goals fare and whether users accept or dismiss them. |
| world_model_nodes | gauge (count) | per-agent | Monitor size/growth of the world model. |
| world_model_edges | gauge (count) | per-agent | Track relational complexity of the world model. |
| world_model_facts_by_life_area | breakdown (fact counts per LifeArea) | per-user | Inspect how many WorldStateFacts exist per LifeArea to spot over- and under-represented domains. |
| world_model_conflicts_active | gauge (count) | per-user | Monitor how many conflicting WorldStateFacts are currently unresolved. |
| hypotheses_open | gauge (count) | per-user | Track how many open World Model hypotheses exist about the user. |
| hypothesis_lifecycle_events | event log | per-user, per-hypothesis | Debug how hypotheses move between open/confirmed/rejected and what evidence drove the change. |
| episodic_writes_rate | rate (events/time) | per-agent | Monitor memory write load. |
| semantic_summaries_created | count/time-series | per-user | Track consolidation of long-term summaries. |

### 2.3 Emotion, Personality & Social

| Name | Type | Scope | Purpose |
| ---- | ---- | ----- | ------- |
| emotion_transitions | event log | per-user | Debug emotional dynamics around key events. |
| relationship_stability | scalar | per-user | Capture volatility of relationship state. |

### 2.4 Arbiter, Values/Ethics & Safety

| Name | Type | Scope | Purpose |
| ---- | ---- | ----- | ------- |
| arbiter_decisions_log | event log (candidates + scores + chosen) | per-user | Debug why certain goals were selected or rejected. |
| goal_source_mix_over_time | time-series breakdown | per-user | Analyse balance of user vs agent-self vs maintenance goals over time. |
| actions_blocked_by_policy | count/time-series | per-user, per-agent | Monitor impact of value/ethics policies. |

### 2.5 Self-Reflection, Scheduler, Resources, Lifecycle & Embodiment

| Name | Type | Scope | Purpose |
| ---- | ---- | ----- | ------- |
| lessons_generated | count/time-series + list | per-user | Inspect how many lessons AICO is extracting and their content. |
| scheduled_agency_tasks | list + states | per-agent, per-user | See what background work is queued and its status. |
| agency_resource_usage | gauge (CPU/mem/battery share) | per-agent | Monitor resource cost of agency-related work. |
| lifecycle_state_time_distribution | breakdown (time spent per LifecycleState) | per-agent, time-series | Analyse how much time AICO spends in ACTIVE / FOCUSED_WORK / IDLE_LIGHT / SLEEP_LIKE / MAINTENANCE to tune daily rhythm and background work policies. |
| lifecycle_transitions | event log | per-agent | Debug when and why LifecycleState changed (including `reason` such as quiet_hours, manual_override, low_battery). |
| tasks_run_vs_deferred_by_lifecycle | breakdown (counts per state and task class) | per-agent | Inspect how often tasks (user_facing, background_light, background_heavy, maintenance) run or are deferred due to LifecycleState flags, to validate Scheduler/Lifecycle integration. |
| embodiment_state_changes | event log | per-user | Debug mapping between agency state transitions and visual updates. |

### 2.6 Conversation & Embodiment

| Name | Type | Scope | Purpose |
| ---- | ---- | ----- | ------- |
| agency_initiated_messages | count/time-series | per-user | Track how often AICO starts interactions. |
| embodiment_state | enum (room, posture, activity) | per-user | Map internal state to visual representation. |
| embodiment_state_changes | event log | per-user | Debug mapping between agency state and visuals. |
