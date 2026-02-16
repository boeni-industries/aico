---
title: AICO Testing Concepts & Strategy
---

# AICO Testing Concepts & Strategy

This document defines the comprehensive testing strategy for the AICO project, covering all subsystems (Python backend/shared/modelservice, Flutter frontend, and Studio).

## Philosophy

**Progressive Testing**: Test each phase/feature as it's built, not after the entire system is complete.

**Test Pyramid**: Balance unit tests (fast, isolated), integration tests (realistic, cross-component), and system tests (end-to-end, user scenarios).

**Observability-First**: All tests validate both behavior AND telemetry (logs, events, metrics).

## Project Structure

```
aico/
├── shared/tests/          # Shared library tests (models, stores, AI processors)
├── backend/tests/         # Backend service tests (API, plugins, lifecycle)
├── modelservice/tests/    # Model service tests (handlers, inference)
├── frontend/test/         # Flutter widget and integration tests
└── scripts/               # Ad-hoc test scripts (to be migrated to proper tests)
```

## Testing Tiers

### Tier 1: Unit Tests

**Purpose**: Test individual functions, classes, and modules in isolation.

**Characteristics**:
- Fast (<10ms per test)
- No external dependencies (DB, network, filesystem)
- Use mocks/stubs for dependencies
- High code coverage (aim for 80%+)

**Examples**:
- `Goal` model validation
- `Planner.generate_initial_plan()` with different goal types
- JSON serialization/deserialization
- Utility functions (date parsing, string formatting)

**Location**: `*/tests/unit/`

### Tier 2: Integration Tests

**Purpose**: Test component interactions within a subsystem.

**Characteristics**:
- Medium speed (100ms-1s per test)
- Use test database (in-memory PostgreSQL or test instance)
- Real component interactions, minimal mocking
- Test cross-component contracts

**Examples**:
- `AgencyEngine` → `GoalStore` → Database
- `AgencyFollowUpTask` → `TaskScheduler` → `TaskExecutor`
- `ConversationEngine` → `AgencyPlugin` → `ai_registry`
- LLM planning helper → ModelServiceClient (mocked)

**Location**: `*/tests/integration/`

### Tier 3: System Tests

**Purpose**: Test end-to-end user scenarios across multiple subsystems.

**Characteristics**:
- Slow (1s-10s per test)
- Full stack running (backend + modelservice + DB)
- Real or realistic data
- Test user-facing behaviors

**Examples**:
- User creates goal → plan generated → scheduler triggers → follow-up sent
- Multi-day agency lifecycle simulation
- Conversation with memory retrieval and agency suggestions

**Location**: `*/tests/system/` or `scripts/` (for now)

### Tier 4: Performance Tests

**Purpose**: Validate performance characteristics and resource usage.

**Characteristics**:
- Measure latency, throughput, memory usage
- Detect regressions
- Stress testing under load

**Examples**:
- Scheduler handles 1000+ tasks
- Memory retrieval <100ms p95
- Agency follow-up scan completes in <5s

**Location**: `scripts/benchmarks/` or `*/tests/performance/`

## Python Testing Stack

### Core Tools

- **pytest**: Test framework
- **pytest-asyncio**: Async test support
- **pytest-cov**: Code coverage
- **pytest-mock**: Mocking utilities
- **pytest-timeout**: Prevent hanging tests

### Test Database Strategy

**Shared & Backend**:
- Use in-memory PostgreSQL for unit/integration tests
- Apply schema migrations in test fixtures
- Isolated DB per test (via fixtures)

**Example**:
```python
@pytest.fixture
async def test_db():
    """Provide isolated test database."""
    db = UnitOfWork()  # PostgreSQL with connection pooling
    # Apply schema
    from aico.data.schemas.core import apply_schema
    apply_schema(db, target_version=20)
    yield db
    db.close()
```

### Mocking Strategy

**Mock external services**:
- ModelService LLM calls (use recorded responses)
- Message bus (use in-memory queue)
- Filesystem (use `tmp_path` fixture)

**Don't mock internal components** in integration tests:
- Real `GoalStore`, `PlanStore`, `AgencyEngine`
- Real database interactions
- Real scheduler logic

### Fixtures Organization

```
tests/fixtures/
├── __init__.py
├── database.py        # DB fixtures (test_db, migrations)
├── agency.py          # Agency fixtures (goals, plans, events)
├── config.py          # Config fixtures (test config manager)
├── modelservice.py    # Mock LLM responses
└── users.py           # Test user data
```

## Test Naming Conventions

### File Names
- `test_<module>.py` for unit tests
- `test_<feature>_integration.py` for integration tests
- `test_<scenario>_e2e.py` for system tests

### Test Function Names
```python
# Pattern: test_<what>_<condition>_<expected>
def test_create_goal_with_valid_data_succeeds()
def test_activate_goal_when_not_found_returns_none()
def test_scheduler_respects_quiet_hours()
```

### Test Structure (AAA Pattern)
```python
async def test_example():
    # Arrange: Set up test data and state
    goal = Goal(...)
    engine = AgencyEngine(config, test_db)
    
    # Act: Execute the behavior being tested
    result = await engine.create_goal_with_optional_plan(...)
    
    # Assert: Verify expected outcomes
    assert result[0].status == GoalStatus.PENDING
    assert len(result[1].steps) == 4
    
    # Assert telemetry (observability)
    events = test_db.execute("SELECT * FROM agency_events").fetchall()
    assert len(events) == 2  # goal_created + plan_generated
```

## Coverage Requirements

### Minimum Coverage Targets

- **Shared library**: 80% line coverage
- **Backend services**: 75% line coverage
- **Critical paths**: 95% coverage
  - Authentication & authorization
  - Data persistence (stores)
  - Agency lifecycle operations
  - Scheduler task execution

### Coverage Exclusions

- Generated code (protobuf)
- Third-party integrations (test with mocks)
- UI/presentation layer (test with Flutter tests)
- Debug/development utilities

## Continuous Integration

### Pre-commit Checks
```bash
# Run before committing
pytest shared/tests backend/tests --cov --cov-report=term-missing
```

### CI Pipeline (GitHub Actions)
1. **Lint**: `ruff check`, `mypy`
2. **Unit Tests**: Fast, parallel execution
3. **Integration Tests**: Sequential, with test DB
4. **Coverage Report**: Fail if below threshold
5. **Performance Tests**: Weekly, track trends

## Testing by Subsystem

### Agency System (Phase 1 - Reference Implementation)

**Unit Tests** (`shared/tests/unit/agency/`):
- `test_models.py`: Goal, Plan, PlanStep validation
- `test_store.py`: GoalStore, PlanStore CRUD
- `test_planner.py`: Plan generation with shapes
- `test_engine.py`: AgencyEngine lifecycle methods

**Integration Tests** (`backend/tests/integration/agency/`):
- `test_phase1_goal_lifecycle.py`: Create → activate → pause → complete
- `test_phase1_planning.py`: Goal → plan → LLM refinement
- `test_phase1_scheduler.py`: Task discovery → execution → follow-ups
- `test_phase1_proactive_behavior.py`: Candidate selection → follow-up sending
- `test_phase1_resource_constraints.py`: CPU/memory limits, quiet hours

**System Tests** (`scripts/agency/` or `backend/tests/system/`):
- `test_agency_multi_day_lifecycle.py`: Simulate days of agency behavior
- `test_agency_with_conversation.py`: Full conversation + agency integration

### Memory System

**Unit Tests**:
- Semantic memory CRUD
- Embedding generation
- Fact extraction

**Integration Tests**:
- AMS consolidation
- Memory retrieval with context
- Cross-tier lifecycle

### Conversation Engine

**Unit Tests**:
- Message formatting
- Context assembly
- Plugin contract validation

**Integration Tests**:
- Full conversation flow
- Plugin integration (agency, emotion, personality)
- Memory context injection

### Scheduler

**Unit Tests**:
- Cron parsing
- Task registry
- Resource constraint checks

**Integration Tests**:
- Task discovery and registration
- Task execution lifecycle
- Lock management

### ModelService

**Unit Tests**:
- Request/response parsing
- Handler routing
- Error handling

**Integration Tests**:
- LLM inference (with mock model)
- Embeddings generation
- NER/sentiment analysis

## Flutter Testing

### Widget Tests
- Individual widget behavior
- State management
- User interactions

### Integration Tests
- Multi-widget flows
- Navigation
- State persistence

### Golden Tests
- Visual regression testing
- Screenshot comparison

## Test Data Management

### Fixtures
- Reusable test data in `fixtures/`
- JSON files for complex scenarios
- Factories for generating test objects

### Seeding
```python
@pytest.fixture
def sample_goals():
    return [
        Goal(goal_id="g1", title="Learn Python", ...),
        Goal(goal_id="g2", title="Build AICO", ...),
    ]
```

### Cleanup
- Use fixtures with `yield` for setup/teardown
- Ensure test isolation (no shared state)
- Clean up temp files, DB connections

## Debugging Tests

### Running Tests
```bash
# All tests
pytest

# Specific module
pytest shared/tests/unit/agency/

# Specific test
pytest shared/tests/unit/agency/test_models.py::test_goal_validation

# With output
pytest -v -s

# With coverage
pytest --cov=aico --cov-report=html

# Failed tests only
pytest --lf

# Stop on first failure
pytest -x
```

### Debugging
```python
# Add breakpoint
import pdb; pdb.set_trace()

# Or use pytest's built-in
pytest --pdb  # Drop into debugger on failure
```

### Logging in Tests
```python
# Enable logging output
pytest -v -s --log-cli-level=DEBUG
```

## Best Practices

### DO
✅ Write tests as you build features (TDD or test-alongside)
✅ Test both happy paths and error cases
✅ Validate telemetry (logs, events, metrics)
✅ Use descriptive test names
✅ Keep tests fast and isolated
✅ Mock external dependencies
✅ Test edge cases and boundaries

### DON'T
❌ Write tests after the entire system is built
❌ Test implementation details (test behavior, not internals)
❌ Share state between tests
❌ Use real external services in unit/integration tests
❌ Ignore flaky tests (fix or remove them)
❌ Test third-party library behavior

## Migration Plan

### Phase 1: Agency System (Current)
- ✅ Set up test infrastructure
- ✅ Write Phase 1 integration test suite
- ✅ Achieve 80%+ coverage for agency components

### Phase 2: Core Systems
- Memory system tests
- Conversation engine tests
- Scheduler tests

### Phase 3: Migrate Ad-hoc Scripts
- Convert `scripts/test_*.py` to proper tests
- Organize into unit/integration/system tiers

### Phase 4: CI/CD Integration
- GitHub Actions workflow
- Coverage reporting
- Performance tracking

## Resources

- [pytest documentation](https://docs.pytest.org/)
- [pytest-asyncio](https://pytest-asyncio.readthedocs.io/)
- [Test-Driven Development](https://en.wikipedia.org/wiki/Test-driven_development)
- AICO Agency Roadmap: `/docs/concepts/agency/agency-roadmap.md`

## Appendix: Example Test Files

See:
- `backend/tests/integration/agency/test_phase1_goal_lifecycle.py` (reference implementation)
- `shared/tests/unit/agency/test_models.py` (unit test example)
- `backend/tests/fixtures/agency.py` (fixture examples)
