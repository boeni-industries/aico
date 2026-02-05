# World Model Implementation - Work In Progress

**Context**: Curiosity scan requires world model methods that are currently placeholders. This document tracks the conceptual design and implementation progress for the World Model component.

**Goal**: Build a hybrid world model combining Knowledge/Property Graph + Semantic Memory + LLM Simulator for social/everyday-life understanding.

---

## Conceptual Architecture (from docs/concepts/agency/agency-component-world-model.md)

### Core Components
1. **Knowledge/Property Graph** (PostgreSQL) - Canonical entity/relation store
   - Entities: Person, Activity, Project, Routine, LifeArea, Place, Device
   - Relations: WorldStateFact (subject/predicate/object triples)
   - Attributes: confidence, validity_interval, provenance

2. **Semantic Memory** (ChromaDB) - Embeddings for similarity queries
   - Similar days, projects, people, patterns
   - Soft generalizations and clustering

3. **LLM Simulator** - Consumes graph for reasoning
   - Counterfactuals and plausible futures
   - Explanations grounded in graph facts
   - Hypothesis proposals

### Key Operations
- **Ingestion**: PerceptualEvent → WorldStateFacts + provenance
- **Query**: Graph neighborhood, life-area summaries, fact lookup, similarity
- **Hypothesis**: Track uncertain beliefs, confidence updates, drift detection
- **Consistency**: Detect conflicts, favor recent/high-confidence evidence

### Design Principles
- Multiple facts with validity intervals (not silent overwrites)
- Confidence and temporal awareness on all facts
- Provenance tracking for explainability
- Surface conflicts, don't hide them
- Safety-aware exposure for sensitive domains

---

## Implementation Phases

### Phase 1: Unblock Curiosity Engine ✅ COMPLETED
**Goal**: Implement placeholder methods with lightweight KG queries using existing tables

- [x] `detect_anomalies()` - Query KG for contradictory facts
  - ✅ Detects duplicate open goals with same title
  - ✅ Identifies stuck goals with failed plan executions
  - ✅ Returns structured anomaly reports with severity levels

- [x] `query_uncertain_areas()` - Query facts with low confidence or staleness
  - ✅ Finds goals with low completion rates (<30%)
  - ✅ Identifies unexplored goals (no plans created)
  - ✅ Returns UncertainArea objects with confidence gaps and questions

- [x] `query_aico_self_assessment()` - Query self-model facts
  - ✅ Analyzes goal completion rates by origin (curiosity, hobby, user, maintenance)
  - ✅ Calculates execution success rates as skill proficiency proxy
  - ✅ Returns self-assessment facts with confidence based on data volume

**Implementation**: Uses existing tables (goals, plans, executions) via UnitOfWork pattern with SQLAlchemy queries.

**Test Results** (2026-02-05 12:06):
- Curiosity scan executed successfully in 1.6s (5 users, 30 signals, 30 goals)
- World model methods integrated without errors
- Performance: Total scan 0.02s, Goal creation 1.58s, Avg per user 0.32s

### Phase 2: Foundation Infrastructure
**Goal**: Build core WorldStateFact storage and ingestion pipeline

- [ ] Create `WorldStateFact` table schema
  - subject_id, predicate, object (JSON), confidence, validity_start, validity_end
  - provenance fields (source_component, percept_ids, memory_ids)
  - status (current, superseded, hypothesis)

- [ ] Implement fact assertion/retraction operations
  - `assert_fact()` with provenance tracking
  - `retract_fact()` with reason and audit trail
  - Consistency checking on high-impact predicates

- [ ] Build PerceptualEvent ingestion pipeline
  - Extract entities and relations from events
  - Create/update WorldStateFacts with provenance
  - Trigger consistency checks

- [ ] Implement hypothesis tracking
  - `Hypothesis` table (id, description, affected_entities, status, confidence)
  - Open/update/confirm/reject operations
  - Link to CuriositySignals and Goals

### Phase 3: Intelligence & Integration
**Goal**: Add advanced reasoning and bidirectional AMS integration

- [ ] Drift detection
  - Temporal pattern analysis for routines/habits
  - Confidence shift detection
  - Emit CuriositySignals for significant drifts

- [ ] Consistency checker
  - Domain-specific invariants (one employer, mutually exclusive states)
  - Conflict resolution strategies (recent/high-confidence wins)
  - User confirmation for sensitive domains

- [ ] AMS consolidation integration
  - Bidirectional flow: AMS memories → WorldStateFacts → AMS queries
  - Sleep-like consolidation cycles
  - Routine/LifeArea recomputation

- [ ] Embedding indices for similarity queries
  - Similar days, projects, people
  - Pattern-based recommendations

---

## Current Status

**Last Updated**: 2026-02-05 12:08 UTC+01:00
**Phase**: Phase 1 - Completed ✅
**Blockers**: None

### Completed
- ✅ Conceptual design documented
- ✅ Implementation phases defined
- ✅ Phase 1: All three world model methods implemented
  - ✅ `detect_anomalies()` - Detects duplicate goals and stuck goals
  - ✅ `query_uncertain_areas()` - Identifies low-completion and unexplored goals
  - ✅ `query_aico_self_assessment()` - Analyzes performance by goal type and skills
- ✅ Integration tested with curiosity scan (1.6s execution, 30 signals generated)

### Next Steps
1. Monitor curiosity scan in production for signal quality
2. Gather feedback on anomaly/uncertainty detection accuracy
3. Begin Phase 2 planning for WorldStateFact infrastructure
4. Design PerceptualEvent ingestion pipeline
5. Create WorldStateFact table schema

---

## Technical Notes

### Placeholder Method Locations
- `shared/aico/ai/world_model/service.py:509-516` - `detect_anomalies()`
- `shared/aico/ai/world_model/service.py:263-266` - `query_uncertain_areas()`
- `shared/aico/ai/world_model/service.py:554-558` - `query_aico_self_assessment()`

### Dependencies
- PostgreSQL for graph storage
- ChromaDB for embeddings (already available)
- UnitOfWork pattern for database access
- AgencyService for goal/plan queries

### Safety Considerations
- Sensitive domain handling (health, finance, relationships)
- User confirmation for high-impact changes
- Provenance tracking for explainability
- Audit trail for critical changes
