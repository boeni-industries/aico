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

### 13. Router Accessing Deprecated Service Attributes Instead of UoW Pattern
**Pattern:**
```python
# Router directly accesses service internal attributes
@router.get("/tasks")
async def list_tasks(
    scheduler = Depends(get_task_scheduler),
    _auth = Depends(require_admin_access)
):
    tasks = scheduler.task_store.list_tasks()  # Direct attribute access
    return tasks

# Service was refactored but router wasn't updated
class TaskScheduler:
    def __init__(self):
        # self.task_store = TaskStore()  # REMOVED - now uses UoW
        self.task_registry = TaskRegistry()
```

**Fix:**
```python
# Router uses UoW pattern with service layer
@router.get("/tasks")
async def list_tasks(
    uow: Annotated[UnitOfWork, Depends(get_uow)],
    _auth = Depends(require_admin_access)
):
    scheduler_service = SchedulerService(uow)
    tasks = await scheduler_service.list_tasks()  # Proper service method
    return tasks

# Service uses UoW internally
class SchedulerService:
    def __init__(self, uow: UnitOfWork):
        self.uow = uow
    
    async def list_tasks(self):
        return await self.uow.scheduler_tasks.list()
```

**Root Cause:** Service layer was refactored to use UoW pattern (repository access via `uow.repository_name`), but API routers still try to access old internal attributes like `service.task_store` that no longer exist.

**Symptoms:**
- `AttributeError: 'ServiceClass' object has no attribute 'old_attribute'`
- 503 Service Unavailable errors from API endpoints
- Routers work in development but break after service refactoring

**Key Changes Required:**
1. Add `uow: Annotated[UnitOfWork, Depends(get_uow)]` to router function parameters
2. Create service instance: `service = ServiceClass(uow)`
3. Call async service methods instead of accessing attributes
4. Update data access from dict-style `task['id']` to object-style `task.id`
5. Add proper imports: `from aico.data.uow import UnitOfWork`, `from backend.core.postgres_dependencies import get_uow`

**Search:** `\.(task_store|execution_store|lock_store)\.` in `backend/api/` routers

---

### 14. Hardcoded User Roles Instead of Database Lookup

**Pattern:**
```python
# Authentication endpoint hardcodes roles
@router.post("/authenticate")
async def authenticate_user(
    request: AuthenticateRequest,
    uow: UnitOfWork = Depends(get_uow)
):
    user = await uow.users.get_by_id(request.user_uuid)
    
    # WRONG: Hardcoded roles - ignores database
    user_roles = ["user"]
    
    jwt_token = auth_manager.generate_jwt_token(
        user_uuid=user.uuid,
        roles=user_roles  # Always ["user"], never admin
    )
```

**Fix:**
```python
# Fetch actual roles from auth_access_policies table
@router.post("/authenticate")
async def authenticate_user(
    request: AuthenticateRequest,
    uow: UnitOfWork = Depends(get_uow)
):
    user = await uow.users.get_by_id(request.user_uuid)
    
    # CORRECT: Fetch roles from database
    access_policies = await uow.auth_access_policies.get_user_policies(
        user.uuid, 
        resource_type="role"
    )
    user_roles = [policy.permission for policy in access_policies] if access_policies else ["user"]
    
    # Default to "user" role if none found
    if not user_roles:
        user_roles = ["user"]
    
    logger.info(f"User roles loaded: {user_roles}", extra={"user_uuid": user.uuid, "roles": user_roles})
    
    jwt_token = auth_manager.generate_jwt_token(
        user_uuid=user.uuid,
        roles=user_roles  # Now includes admin, moderator, etc.
    )
```

**Root Cause:** Authentication endpoint was hardcoding `user_roles = ["user"]` instead of querying the `auth_access_policies` table where roles are stored. This caused all users to be authenticated with only the "user" role, even if they had "admin" role in the database.

**Symptoms:**
- User has admin role in `auth_access_policies` table but gets 403 Forbidden on admin endpoints
- JWT token payload contains `"roles": ["user"]` instead of `"roles": ["admin"]`
- Admin access checks fail with "Admin access required" error
- Works for regular user endpoints but fails for admin-only endpoints

**Key Changes Required:**
1. Use `uow.auth_access_policies.get_user_policies(user_uuid, resource_type="role")` to fetch roles
2. Extract `permission` field from policies: `[policy.permission for policy in access_policies]`
3. Keep default fallback to `["user"]` if no roles found
4. Log loaded roles for debugging: `logger.info(f"User roles loaded: {user_roles}")`

**Search:** `user_roles = \["user"\]` in authentication endpoints

---

### 15. Legacy get_db_connection Dependency in API Endpoints

**Pattern:**
```python
# API endpoint using legacy database connection dependency
from backend.api.system.dependencies import get_current_user, get_db_connection

@router.get("/databases")
async def get_database_stats(
    user: Annotated[dict, Depends(get_current_user)],
    db_connection: Annotated[object, Depends(get_db_connection)]  # WRONG: Legacy dependency
) -> DatabaseStatsResponse:
    # Endpoint tries to use old database service
    pass
```

**Fix:**
```python
# Use UoW pattern instead of legacy db_connection
from backend.api.system.dependencies import get_current_user
from backend.core.postgres_dependencies import get_uow
from aico.data.uow import UnitOfWork

@router.get("/databases")
async def get_database_stats(
    user: Annotated[dict, Depends(get_current_user)],
    uow: Annotated[UnitOfWork, Depends(get_uow)]  # CORRECT: UoW pattern
) -> DatabaseStatsResponse:
    # Use UoW to access repositories
    users = await uow.users.list(limit=1000)
    pass
```

**Root Cause:** After migrating to PostgreSQL with UoW pattern, some API endpoints still depend on the legacy `get_db_connection` dependency which tries to access the old database service. This service no longer exists, causing 503 errors.

**Symptoms:**
- HTTP 503 "Database not available" errors on certain endpoints
- Error: `raise HTTPException(status_code=503, detail="Database not available")`
- Endpoints fail during dependency injection before reaching handler code
- Works for endpoints using UoW, fails for those using `get_db_connection`

**Key Changes Required:**
1. Remove `get_db_connection` import from `backend.api.system.dependencies`
2. Add UoW imports: `from backend.core.postgres_dependencies import get_uow` and `from aico.data.uow import UnitOfWork`
3. Replace `db_connection: Annotated[object, Depends(get_db_connection)]` with `uow: Annotated[UnitOfWork, Depends(get_uow)]`
4. Update function signatures that accept `db_connection` parameter to accept `uow` instead
5. Use UoW repositories: `await uow.users.list()`, `await uow.sessions.get_by_id()`, etc.

**Files Commonly Affected:**
- `/backend/api/operations/router.py` - Operations/database stats endpoints
- `/backend/api/operations/database_routes.py` - Database admin routes
- `/backend/api/operations/database_admin.py` - Admin function implementations
- `/backend/api/operations/lmdb_browser.py` - LMDB browsing functions

**Example Migration:**
```python
# Before: Function using db_connection
async def find_orphaned_entries(database_name: str, db_connection) -> dict:
    # Had to create own UoW inside
    from aico.data.postgres.connection import get_session_factory
    from aico.data.uow import UnitOfWork
    
    session_factory = await get_session_factory()
    async with UnitOfWork(session_factory) as uow:
        users = await uow.users.list(limit=100000)

# After: Function using UoW parameter
async def find_orphaned_entries(database_name: str, uow) -> dict:
    # Use passed-in UoW directly
    users = await uow.users.list(limit=100000)
```

**Search:** `Depends\(get_db_connection\)` in `backend/api/` endpoints

---

### 16. Incomplete Pydantic Model Construction Missing Required Fields

**Pattern:**
```python
# Pydantic schema defines required fields
class UserCredentials(BaseModel):
    has_pin: bool = Field(..., description="Required field")
    failed_attempts: int = Field(..., description="Required field")
    is_locked: bool = Field(..., description="Required field")

# But router only provides some fields
credentials = UserCredentials(
    failed_attempts=cred.failed_attempts,
    # Missing has_pin and is_locked!
)
```

**Fix:**
```python
# Provide all required fields
credentials = UserCredentials(
    has_pin=bool(cred.pin_hash) if hasattr(cred, 'pin_hash') else False,
    failed_attempts=cred.failed_attempts,
    is_locked=bool(cred.locked_until and cred.locked_until > datetime.now(timezone.utc)),
    locked_until=cred.locked_until.isoformat() if cred.locked_until else None,
    last_login=cred.last_login.isoformat() if cred.last_login else None
)
```

**Root Cause:** Database schema was extended with new columns, Pydantic models were updated to include new required fields, but router code wasn't updated to provide values for those fields during model construction.

**Symptoms:**
- HTTP 500 errors with Pydantic validation messages
- Error: "Field required [type=missing, input_value={...}, input_type=dict]"
- Works in development but breaks after schema changes
- Multiple validation errors for different missing fields

**Key Changes Required:**
1. Check all required fields in Pydantic model (fields with `Field(...)` or no default)
2. Provide values for all required fields during construction
3. Use `hasattr()` checks for optional database fields
4. Provide sensible defaults for computed fields (e.g., `is_locked` based on `locked_until`)
5. Handle timezone-aware datetime comparisons properly

**Search:** Pydantic validation errors in logs, `Field\(\.\.\.,` in schema files without corresponding constructor parameters

---

### 17. Missing Computed/Derived Fields in Response Models

**Pattern:**
```python
# Response model expects computed statistics
class SessionStatistics(BaseModel):
    total_sessions: int
    active_sessions: int
    expired_sessions: int  # Required but not computed
    sessions_by_type: dict  # Required but not computed
    sessions_by_device_type: dict  # Required but not computed

# Router only provides basic counts
statistics = {
    "total_sessions": len(all_sessions),
    "active_sessions": sum(1 for s in all_sessions if s.is_active),
    # Missing expired_sessions, sessions_by_type, sessions_by_device_type
}
return SessionStatistics(**statistics)  # Validation error!
```

**Fix:**
```python
# Compute all required statistics
now = datetime.now(timezone.utc)
expired_count = sum(1 for s in all_sessions if not s.is_active or (s.expires_at and s.expires_at <= now))

# Group by type
sessions_by_type = {}
for sess in all_sessions:
    session_type = sess.session_type or 'unknown'
    sessions_by_type[session_type] = sessions_by_type.get(session_type, 0) + 1

# Group by device type
sessions_by_device_type = {}
for sess in all_sessions:
    device_type = get_device_type(sess.device_uuid) or 'unknown'
    sessions_by_device_type[device_type] = sessions_by_device_type.get(device_type, 0) + 1

statistics = SessionStatistics(
    total_sessions=len(all_sessions),
    active_sessions=sum(1 for s in all_sessions if s.is_active),
    expired_sessions=expired_count,
    sessions_by_type=sessions_by_type,
    sessions_by_device_type=sessions_by_device_type
)
```

**Root Cause:** Response models were enhanced with additional computed/aggregated fields for richer API responses, but endpoint logic wasn't updated to compute those values.

**Symptoms:**
- HTTP 500 errors with multiple Pydantic validation errors
- Error messages listing several missing required fields
- Frontend receives incomplete data structures
- Statistics or aggregations missing from API responses

**Key Changes Required:**
1. Identify all required fields in response models
2. Compute aggregations (counts, groupings, averages) from raw data
3. Handle edge cases (empty lists, null values, missing relationships)
4. Use proper timezone-aware datetime for time-based computations
5. Provide empty dicts/lists for collection fields rather than omitting them

**Search:** Response model classes with multiple required dict/list fields, endpoints returning those models

---

### 18. Async Methods in Legacy Components Not Awaited

**Pattern:**
```python
# Component migrated to async/UoW pattern
class AdaptiveScoringEngine:
    async def load_arms(self):  # Now async
        rows = await self.agency_service.get_bandit_arms()
        # ...
    
    async def _save_arm(self, arm):  # Now async
        await self.agency_service.save_bandit_arm(arm_data)

# But initialization doesn't await
class GoalArbiter:
    def __init__(self, ...):
        self.adaptive = AdaptiveScoringEngine(agency_service)
        # Missing: await self.adaptive.load_arms()
        
    def some_method(self):
        arm = self.adaptive.select_arm()  # Works (sync)
        self.adaptive.update_arm(arm_id, reward, success)  # ERROR: Not awaited!
```

**Fix:**
```python
# Make initialization async-aware
class GoalArbiter:
    def __init__(self, ...):
        self.adaptive = AdaptiveScoringEngine(agency_service)
        # Note: Must call await self.adaptive.load_arms() after construction
    
    async def initialize(self):
        """Async initialization - call after construction"""
        await self.adaptive.load_arms()
    
    async def some_method(self):  # Now async
        arm = self.adaptive.select_arm()  # Still sync
        await self.adaptive.update_arm(arm_id, reward, success)  # Properly awaited
```

**Root Cause:** Components were migrated from sync database access to async UoW pattern, but:
1. Callers weren't updated to await async methods
2. Initialization logic that loads data wasn't made async
3. Methods that call async sub-methods weren't converted to async

**Symptoms:**
- RuntimeWarning: "coroutine was never awaited"
- Methods return coroutine objects instead of actual values
- Database operations silently don't execute
- Data not persisted despite no errors

**Key Changes Required:**
1. Convert all methods calling async sub-methods to async
2. Add explicit async initialization methods for components needing data loading
3. Document initialization requirements (e.g., "call await load_arms() after construction")
4. Ensure all async method calls use `await`
5. Update calling code to be async and await properly

**Search:** `async def` methods in components, check all callers use `await`, look for `RuntimeWarning.*coroutine.*never awaited` in logs

---

### 19. Service Methods Missing AgencyService Parameter After Migration

**Pattern:**
```python
# Component migrated from db to agency_service
class BehavioralFeedbackService:
    def __init__(self, agency_service, logger=None):
        self.agency_service = agency_service  # ✓ Constructor updated
    
    # But methods still don't use it
    def record_skill_execution(self, execution_id, skill_id, ...):  # Not async!
        # Old code tried: self.db.execute(...)
        # New code should: await self.agency_service.record_skill_execution(...)
        pass
```

**Fix:**
```python
class BehavioralFeedbackService:
    def __init__(self, agency_service, logger=None):
        self.agency_service = agency_service
    
    async def record_skill_execution(self, execution_id, skill_id, ...):
        execution_data = {
            "execution_id": execution_id,
            "skill_id": skill_id,
            # ... all fields
        }
        await self.agency_service.record_skill_execution(execution_data)
```

**Root Cause:** Constructor was updated to accept `agency_service` instead of `db`, but method bodies weren't refactored to:
1. Convert to async
2. Use agency_service methods instead of direct DB calls
3. Prepare data in the format expected by service methods

**Symptoms:**
- Methods exist but do nothing (empty or incomplete)
- Constructor has `agency_service` but methods don't use it
- Mix of old `self.db` calls and new `self.agency_service` parameter
- Type errors when passing wrong parameter types

**Key Changes Required:**
1. Convert all methods to async
2. Replace `self.db.execute()` with `await self.agency_service.method()`
3. Prepare data dictionaries matching service method signatures
4. Remove all `self.db` references
5. Update all callers to await the async methods

**Search:** Classes with `self.agency_service` in `__init__` but methods not using it, `def .*\(self,` without `async` in migrated files

---

### 20. Legacy db=None Parameters Still Present After Migration

**Pattern:**
```python
# Component partially migrated
class SkillInvoker:
    def __init__(
        self,
        db: Any,  # Still here but set to None
        skill_registry: SkillRegistry,
        logger=None
    ):
        self.db = db  # Never used anymore
        self.skill_registry = skill_registry

# Called with db=None
self.skill_invoker = SkillInvoker(
    db=None,  # Legacy parameter
    skill_registry=self.skill_registry,
    logger=logger
)
```

**Fix:**
```python
# Remove legacy parameter completely
class SkillInvoker:
    def __init__(
        self,
        skill_registry: SkillRegistry,
        logger=None
    ):
        self.skill_registry = skill_registry

# Call without db parameter
self.skill_invoker = SkillInvoker(
    skill_registry=self.skill_registry,
    logger=logger
)
```

**Root Cause:** During migration, `db` parameters were set to `None` to fix immediate errors, but weren't fully removed. This creates:
1. Confusing API (why pass None?)
2. Risk of someone passing actual db connection
3. Code clutter
4. Incomplete migration

**Symptoms:**
- Constructor has `db: Any` parameter
- Parameter is always set to `None`
- Parameter is never used in the class
- Comments like "# Legacy parameter, not used"

**Key Changes Required:**
1. Remove `db` parameter from constructor signature
2. Remove `self.db = db` assignment
3. Update all callers to not pass `db=None`
4. Remove any comments about legacy parameters
5. Verify no code paths try to use `self.db`

**Search:** `db.*:.*Any.*=.*None` in constructors, `db=None` in method calls, `# Legacy.*db` comments

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

# NEW: Find incomplete Pydantic model construction
rg "Field\(\.\.\." backend/api/ -A 2 | grep "description"

# NEW: Find Pydantic validation errors in recent logs
rg "Field required.*type=missing" --type log

# NEW: Find legacy db=None parameters
rg "db.*:.*Any.*=.*None" shared/aico/

# NEW: Find db=None in method calls
rg "db=None" shared/aico/ai/

# NEW: Find methods not awaiting async calls
rg "self\.\w+\.\w+\(" shared/aico/ai/ | grep -v "await"

# NEW: Find classes with agency_service but sync methods
rg "self\.agency_service = agency_service" -A 20 | grep "def " | grep -v "async def"

# NEW: Find timezone-naive datetime comparisons
rg "datetime\.utcnow\(\)" backend/

# NEW: Find missing computed fields in statistics
rg "class.*Statistics.*BaseModel" backend/api/ -A 10

# NEW: Find legacy get_db_connection usage
rg "Depends\(get_db_connection\)" backend/api/

# NEW: Find coroutine never awaited warnings
rg "RuntimeWarning.*coroutine.*never awaited"
```

---

## Priority Order

1. **HIGH**: Reflection engine, adaptive scoring, context prioritization
2. **HIGH**: All skills in `shared/aico/ai/agency/skills/`
3. **MEDIUM**: Any remaining `self.db` usage in `shared/aico/ai/`
4. **MEDIUM**: Engine methods creating UoW internally
5. **LOW**: Missing UoW properties (add as needed)
