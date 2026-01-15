# Database Migration Anti-Patterns to Fix

## Legacy Patterns Identified During AgencyEngine Refactoring

### 1. Direct `db_connection` Parameter in Service Constructors
**Pattern:**
```python
def __init__(self, db: Any, ...):
    self.db = db
```

**Fix:**
```python
def __init__(self, ...):
    # No db parameter - use UoW in methods
```

**Search:** `def __init__.*db.*:` in `shared/aico/ai/` and `shared/aico/services/`

---

### 2. Synchronous Database Methods Without UoW
**Pattern:**
```python
def method(self, param):
    row = self.db.fetch_one("SELECT ...", (param,))
```

**Fix:**
```python
async def method(self, param, uow: UnitOfWork):
    entity = await uow.repository.get_by_id(param)
```

**Search:** `self\.db\.(execute|fetch_one|fetch_all|commit)` in `shared/aico/`

---

### 3. Missing `uow` Parameter in Async Methods
**Pattern:**
```python
async def method(self, user_id: str):
    # Uses self.db or self.agency_service without uow
```

**Fix:**
```python
async def method(self, user_id: str, uow: UnitOfWork):
    # Pass uow to all repository/service calls
```

**Search:** `async def.*\).*:` without `uow.*UnitOfWork` in method signature

---

### 4. Services Calling Other Services Without UoW Propagation
**Pattern:**
```python
async def method(self, uow: UnitOfWork):
    result = await self.other_service.method(param)  # Missing uow!
```

**Fix:**
```python
async def method(self, uow: UnitOfWork):
    result = await self.other_service.method(param, uow)
```

**Search:** Service method calls within UoW context that don't pass uow

---

### 5. Engine Methods Creating UoW Internally (Should Be in Router)
**Pattern:**
```python
# In AgencyEngine
async def get_something(self, user_id):
    async with UnitOfWork(factory) as uow:
        return await self.service.method(user_id, uow)
```

**Fix:**
```python
# In Router
async def endpoint(uow: Annotated[UnitOfWork, Depends(get_uow)]):
    return await engine.get_something(user_id, uow)

# In Engine
async def get_something(self, user_id, uow: UnitOfWork):
    return await self.service.method(user_id, uow)
```

**Search:** `async with UnitOfWork` in `shared/aico/ai/`

---

### 6. Repositories Used Directly in Business Logic
**Pattern:**
```python
# In engine/service
entities = await uow.some_repository.list(filters)
```

**Fix:**
```python
# Create service method
# In SomeService
async def list_items(self, filters, uow):
    return await uow.some_repository.list(filters)

# In engine
items = await self.some_service.list_items(filters, uow)
```

**Note:** Engines should use services, not repositories directly

---

### 7. Missing Repository Import in UoW
**Pattern:**
```python
# UoW has _some_repository = None but no @property
```

**Fix:**
```python
@property
def some_repository(self):
    if self._some_repository is None:
        from .repositories.postgres.some_repository import PostgresSomeRepository
        self._some_repository = PostgresSomeRepository(self._session)
    return self._some_repository
```

**Search:** Repository usage without corresponding UoW property

---

### 8. Adaptive/Context Engines Still Using db_connection
**Pattern:**
```python
# In arbiter_adaptive.py, arbiter_context.py
class AdaptiveScoringEngine:
    def __init__(self, db, ...):
        self.db = db
```

**Fix:** Refactor to use UoW pattern like GoalArbiter

**Search:** `shared/aico/ai/agency/arbiter_adaptive.py`, `arbiter_context.py`

---

### 9. Skills Using db_connection
**Pattern:**
```python
# In skills/*.py
class SomeSkill:
    def __init__(self, db, ...):
        self.db = db
```

**Fix:** Skills should use services, not direct DB access

**Search:** `def __init__.*db.*:` in `shared/aico/ai/agency/skills/`

---

### 10. Reflection Engine Using db_connection
**Pattern:**
```python
# In reflection.py
class SelfReflectionEngine:
    def __init__(self, db_connection, ...):
        self.db = db_connection
```

**Fix:** Refactor to use AgencyService + UoW

**Search:** `shared/aico/ai/agency/reflection.py`

---

### 11. Pydantic Model Type Mismatches with Database Schema
**Pattern:**
```python
# Pydantic model expects one type
class EthicsValueProfile(BaseModel):
    sensitive_life_areas: Optional[List[str]] = None

# But database schema uses different type
Column('sensitive_life_areas', String)  # VARCHAR, not array

# Router creates with wrong type
profile = EthicsValueProfile(
    sensitive_life_areas=[],  # List, but model expects str
)
```

**Fix:**
```python
# Match Pydantic model to database schema
class EthicsValueProfile(BaseModel):
    sensitive_life_areas: Optional[str] = None  # String to match VARCHAR

# Router creates with correct type
profile = EthicsValueProfile(
    sensitive_life_areas=None,  # None or string, not list
)
```

**Root Cause:** Database migration changed column types but Pydantic models weren't updated, or vice versa.

**Search:** Compare Pydantic models in `shared/aico/data/*/models.py` with table definitions in `shared/aico/data/tables.py`

---

### 12. Inconsistent JSON Handling Between Storage and Retrieval
**Pattern:**
```python
# Storage: Converts dict to JSON string
async def create(self, entity):
    stmt = insert(table).values(
        conditions_json=json.dumps(entity.conditions_json)  # Dict → String
    )

# Retrieval: Tries to parse already-parsed JSONB
async def get(self, id):
    entity = await fetch_entity()
    return Model(
        conditions=json.loads(entity.conditions_json)  # Already dict from JSONB!
    )
```

**Fix:**
```python
# Storage: Pass dict directly (PostgreSQL JSONB handles it)
async def create(self, entity):
    stmt = insert(table).values(
        conditions_json=entity.conditions_json  # Dict → JSONB automatically
    )

# Retrieval: Use dict directly (asyncpg returns parsed JSONB as dict)
async def get(self, id):
    entity = await fetch_entity()
    return Model(
        conditions=entity.conditions_json  # Already dict, no parsing needed
    )
```

**Root Cause:** PostgreSQL JSONB columns are automatically parsed by asyncpg. Calling `json.loads()` on retrieval or `json.dumps()` on storage creates type mismatches.

**Key Insight:** With SQLAlchemy + asyncpg + PostgreSQL JSONB:
- **Storage**: Pass Python dict directly → SQLAlchemy handles JSONB conversion
- **Retrieval**: Use returned dict directly → asyncpg already parsed JSONB to dict
- **Never**: Call `json.loads()` or `json.dumps()` on JSONB columns

**Search:** `json.loads.*\..*_json` or `json.dumps.*\..*_json` in repository files

---

## Scan Commands

```bash
# Find all db_connection in constructors
rg "def __init__.*db.*:" shared/aico/ai/ shared/aico/services/

# Find all self.db usage
rg "self\.db\.(execute|fetch_one|fetch_all|commit)" shared/aico/

# Find async methods without uow parameter
rg "async def [^_].*\):" shared/aico/ai/ | grep -v "uow.*UnitOfWork"

# Find UoW creation in business logic
rg "async with UnitOfWork" shared/aico/ai/

# Find skills with db parameter
rg "def __init__.*db.*:" shared/aico/ai/agency/skills/
```

---

## Priority Order

1. **HIGH**: Reflection engine, adaptive scoring, context prioritization
2. **HIGH**: All skills in `shared/aico/ai/agency/skills/`
3. **MEDIUM**: Any remaining `self.db` usage in `shared/aico/ai/`
4. **MEDIUM**: Engine methods creating UoW internally
5. **LOW**: Missing UoW properties (add as needed)
