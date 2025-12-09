# Agency Phase 2: Memory, World Model & Relationship Integration

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
```

**Dependencies**:
- `PropertyGraphStorage` (existing KG)
- `SemanticMemoryStore` (existing)
- `MemoryManager` (existing AMS)

### 2. AMS Integration in AgencyEngine

**Changes to AgencyEngine**:
```python
class AgencyEngine:
    def __init__(self, config, db_connection, world_model: WorldModelService):
        # ... existing init ...
        self.world_model = world_model
    
    async def create_goal_with_context(
        self,
        user_id: str,
        title: str,
        **kwargs
    ) -> Tuple[Goal, Optional[Plan]]:
        # NEW: Retrieve user context from AMS
        user_context = await self.world_model.get_user_context(user_id)
        open_loops = await self.world_model.get_open_loops(user_id)
        
        # Enrich goal metadata with context
        metadata = kwargs.get('metadata', {})
        metadata['context'] = {
            'open_loops': [loop.id for loop in open_loops],
            'active_projects': user_context.active_projects,
            'preferences': user_context.preferences,
        }
        
        # Create goal with enriched metadata
        return await self.create_goal_with_optional_plan(
            user_id=user_id,
            title=title,
            metadata=metadata,
            **kwargs
        )
```

### 3. Personality Integration

**Changes to Goal Creation**:
```python
async def create_goal_with_personality(
    self,
    user_id: str,
    title: str,
    personality_context: PersonalityContext,
    **kwargs
) -> Tuple[Goal, Optional[Plan]]:
    # Adjust priority based on personality traits
    priority = self._adjust_priority_for_personality(
        base_priority=kwargs.get('priority', GoalPriority.NORMAL),
        personality=personality_context
    )
    
    # Adjust goal type based on relationship vectors
    if personality_context.relationship_closeness < 0.3:
        # Low closeness = less proactive
        kwargs['proactivity_level'] = 'low'
    
    return await self.create_goal_with_context(
        user_id=user_id,
        title=title,
        priority=priority,
        **kwargs
    )
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
- [ ] Create `shared/aico/ai/world_model/` directory
- [ ] Implement `service.py` with basic queries
- [ ] Implement `models.py` for data structures
- [ ] Add tests for WorldModelService

### Step 2: Integrate AMS into AgencyEngine (Week 1-2)
- [ ] Add `world_model` parameter to AgencyEngine
- [ ] Implement `create_goal_with_context()` method
- [ ] Update goal metadata to include AMS context
- [ ] Add tests for AMS integration

### Step 3: Add Personality Hooks (Week 2)
- [ ] Create `PersonalityService` wrapper
- [ ] Implement priority adjustment based on traits
- [ ] Implement proactivity adjustment based on relationships
- [ ] Add tests for personality integration

### Step 4: Update Planner (Week 2-3)
- [ ] Add context-aware shape selection
- [ ] Use world model in plan generation
- [ ] Add tests for context-aware planning

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
