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
