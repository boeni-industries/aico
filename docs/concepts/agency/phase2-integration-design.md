---
title: Agency Phase 2: Memory, World Model & Relationship Integration
---

# Agency Phase 2: Memory, World Model & Relationship Integration

## Status

- **Implemented (v1)**: `WorldModelService` exists (`shared/aico/ai/world_model/service.py`) and provides basic context queries. Some sub-queries (e.g., open loops, recurring contexts) are placeholders.
- **Implemented (v1)**: `PersonalityService` exists (`shared/aico/ai/personality/service.py`) with Phase 2 defaults plus simple priority/proactivity heuristics.
- **Implemented (v1)**: `AgencyEngine` accepts optional `world_model` and `personality_service` and exposes Phase 2 goal creation helpers (see `shared/aico/ai/agency/engine.py`).
- **WIP**: deep end-to-end use of AMS summaries/open loops as first-class planning inputs.

## Overview

Phase 2 grounds the agency system in AICO's existing memory, knowledge graph, and personality systems to make goals and plans contextually aware and relationship-informed.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     AgencyEngine                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │ Goal System  │  │   Planner    │  │  Scheduler   │     │
│  └──────┬───────┘  └──────┬───────┘  └──────────────┘     │
│         │                  │                                 │
│         └──────────────────┴─────────────────┐              │
└───────────────────────────────────────────────┼──────────────┘
                                                │
                    ┌───────────────────────────┴───────────────────────┐
                    │                                                   │
          ┌─────────▼──────────┐                          ┌────────────▼─────────┐
          │  WorldModelService │                          │  PersonalityService  │
          │                    │                          │                      │
          │  • KG queries      │                          │  • Traits/values     │
          │  • Entity context  │                          │  • Relationship      │
          │  • Projects        │                          │    vectors           │
          │  • Open loops      │                          │  • Proactivity       │
          └─────────┬──────────┘                          │    preferences       │
                    │                                      └──────────────────────┘
          ┌─────────┴──────────┐
          │                    │
    ┌─────▼─────┐      ┌──────▼──────┐
    │    KG     │      │     AMS     │
    │ Storage   │      │   Memory    │
    └───────────┘      └─────────────┘
```

## Components

### 1. WorldModelService

**Purpose**: Unified API for querying knowledge graph and semantic memory.

**Location**: `shared/aico/ai/world_model/service.py`

**Key Methods**:
```python
class WorldModelService:
    async def get_user_context(user_id: str) -> UserContext
    async def get_entities_around_user(user_id: str, limit: int) -> List[Entity]
    async def get_active_projects(user_id: str) -> List[Project]
    async def get_open_loops(user_id: str) -> List[OpenLoop]
    async def get_recurring_contexts(user_id: str) -> List[Context]
    async def query_uncertain_areas(user_id: str) -> List[UncertainArea]
    async def get_world_context(user_id: str, include_entities: bool, include_projects: bool, include_open_loops: bool) -> WorldContext
```

**Dependencies**:
- `PropertyGraphStorage` (existing KG)
- `SemanticMemoryStore` (existing)
- `MemoryManager` (existing AMS)

### 2. AMS Integration in AgencyEngine

**AgencyEngine Phase 2 helpers (implemented)**:
```python
class AgencyEngine:
    async def create_goal_with_world_context(self, user_id: str, title: str, **kwargs):
        world_context = await self.world_model.get_world_context(
            user_id=user_id,
            include_entities=True,
            include_projects=True,
            include_open_loops=True,
        )
        # Enrich goal metadata with world_context (see engine implementation)

    async def create_goal_with_full_context(self, user_id: str, title: str, **kwargs):
        personality_context = await self.personality.get_personality_context(user_id)
        # Adjust priority and proactivity (Phase 2 heuristics)
        # Optionally also attach world_context
```

### 3. Personality Integration

**PersonalityService hooks (implemented)**:
```python
personality = await personality_service.get_personality_context(user_id)
adjusted_priority = personality_service.adjust_priority_for_personality(base_priority, personality)
proactivity = personality_service.calculate_proactivity_level(personality)
```

### 4. Planning with Context

**Changes to Planner**:
```python
class Planner:
    async def generate_plan_with_context(
        self,
        goal: Goal,
        world_context: WorldContext
    ) -> Plan:
        # Use world context to inform plan generation
        # - Check for related entities
        # - Consider active projects
        # - Respect user preferences
        # - Avoid uncertain areas unless exploring
        
        # Select shape based on context
        shape = self._select_shape_with_context(goal, world_context)
        
        return await self.generate_plan(goal, shape=shape)
```

## Implementation Steps

### Step 1: Create WorldModelService (Week 1)
- Implemented; see `shared/aico/ai/world_model/*`.

### Step 2: Integrate AMS into AgencyEngine (Week 1-2)
- Implemented in `AgencyEngine` as `create_goal_with_world_context` / `create_goal_with_full_context`.

### Step 3: Add Personality Hooks (Week 2)
- Implemented; see `shared/aico/ai/personality/service.py`.

### Step 4: Update Planner (Week 2-3)
- **WIP**: deeper planner integration with world context beyond attaching metadata.

### Step 5: Integration Testing (Week 3)
- [ ] End-to-end tests with real KG data
- [ ] Test goal creation with AMS context
- [ ] Test personality-informed behavior
- [ ] Performance testing

## Data Structures

### UserContext
```python
@dataclass
class UserContext:
    user_id: str
    active_projects: List[str]
    preferences: Dict[str, Any]
    recent_topics: List[str]
    relationship_closeness: float
    last_interaction: datetime
```

### OpenLoop
```python
@dataclass
class OpenLoop:
    id: str
    user_id: str
    description: str
    created_at: datetime
    priority: float
    related_entities: List[str]
```

### WorldContext
```python
@dataclass
class WorldContext:
    entities: List[Entity]
    projects: List[Project]
    open_loops: List[OpenLoop]
    recurring_contexts: List[Context]
    uncertain_areas: List[UncertainArea]
```

## Configuration

Add to `config.yaml`:
```yaml
agency:
  phase2:
    world_model:
      enabled: true
      max_entities_per_query: 20
      max_open_loops: 10
    personality:
      enabled: true
      adjust_priority: true
      adjust_proactivity: true
    ams:
      use_summaries: true
      use_open_loops: true
      context_window_days: 30
```

## Testing Strategy

1. **Unit Tests**: Each component in isolation
2. **Integration Tests**: AgencyEngine with WorldModelService
3. **End-to-End Tests**: Full goal creation with AMS + personality
4. **Performance Tests**: Query performance with large KG

## Success Metrics

- Goals include relevant AMS context in metadata
- Plans reference related entities from KG
- Personality traits influence goal priority
- Relationship vectors affect proactivity level
- Open loops are considered in goal creation

## Phase 2 Exit Condition

> "Goals and plans are meaningfully influenced by long-term memory, social context, and world structure; AICO feels more consistent and 'aware' over time."

**Verification**:
- Create a goal → Check it references user's active projects
- Generate a plan → Check it considers related entities
- Test with different personality traits → Verify different priorities
- Test with different relationship levels → Verify different proactivity
