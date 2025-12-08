# General Future Improvements (WIP)

## Scheduler & Resource Governance
- Implement real resource checks in TaskExecutor._check_resource_constraints (CPU, memory, battery, user-activity).
- Expose unified resource state to agency and Lifecycle for readiness gating of autonomous tasks.

## Memory / AMS / Unified Indexing
- Implement unified memory index (working, semantic, behavioral) and retrieval API as described in WIP_ams_future_improvements.md.
- Add memory lifecycle automation (promotion/demotion, TTLs) backed by existing stores and scheduler tasks.

## Skills & Behavioral Learning
- Standardize skill usage on shared.aico.ai.memory.behavioral.SkillStore and bandit selector for all agent tools.
- Extend Skill metadata (via existing JSON/metadata fields) with agency-specific attributes instead of creating new tables.
