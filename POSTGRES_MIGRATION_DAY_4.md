# PostgreSQL Migration - Day 4: API Endpoint Migration

## Status: IN PROGRESS

**Date:** January 13, 2026  
**Phase:** API Endpoint Migration to Repository Pattern

---

## Day 1-3 Summary: Foundation Complete ✅

### Repositories Implemented (5 total)
1. **UserRepository** - 15 tests ✅
2. **SessionRepository** - 5 tests ✅
3. **CredentialsRepository** - 6 tests ✅
4. **GoalRepository** - 8 tests ✅
5. **PlanRepository** - 9 tests ✅

**Total: 43/43 integration tests passing, zero errors, zero warnings**

### Architecture Validated
- ✅ Repository pattern working across all repositories
- ✅ Unit of Work managing atomic transactions
- ✅ SQLAlchemy Core + asyncpg integration
- ✅ Connection pooling optimized (min=10, max=50)
- ✅ Production-grade PostgreSQL configuration
- ✅ Password authentication via AICOKeyManager

---

## Day 4 Objectives

### Primary Goal
Migrate API endpoints from LibSQL/UserService to PostgreSQL repositories.

### Approach
**Incremental Migration** - Replace endpoints one at a time while maintaining backward compatibility.

### Target Endpoints

#### Users API (`/api/users`)
- [ ] `POST /` - Create user
- [ ] `GET /{uuid}` - Get user by ID (✅ already in router_postgres.py)
- [ ] `PUT /{uuid}` - Update user
- [ ] `DELETE /{uuid}` - Delete user
- [ ] `GET /` - List users (✅ already in router_postgres.py)
- [ ] `GET /{uuid}/stats` - Get user stats
- [ ] `POST /authenticate` - Authenticate user

#### Auth API (`/api/auth`)
- [ ] `POST /login` - User login (SessionRepository)
- [ ] `POST /logout` - User logout (SessionRepository)
- [ ] `GET /sessions` - List active sessions (SessionRepository)
- [ ] `POST /pin/set` - Set PIN (CredentialsRepository)
- [ ] `POST /pin/verify` - Verify PIN (CredentialsRepository)

#### Agency API (`/api/agency`)
- [ ] `POST /goals` - Create goal (GoalRepository)
- [ ] `GET /goals` - List goals (GoalRepository)
- [ ] `GET /goals/{id}` - Get goal (GoalRepository)
- [ ] `PUT /goals/{id}` - Update goal (GoalRepository)
- [ ] `DELETE /goals/{id}` - Delete goal (GoalRepository)
- [ ] `POST /plans` - Create plan (PlanRepository)
- [ ] `GET /plans` - List plans (PlanRepository)

---

## Migration Pattern

### Before (LibSQL + UserService)
```python
@router.get("/{user_uuid}")
async def get_user(user_uuid: str):
    user_service = get_user_service()
    user = await user_service.get_user(user_uuid)
    return UserResponse(...)
```

### After (PostgreSQL + Repository)
```python
@router.get("/{user_uuid}")
async def get_user(
    user_uuid: str,
    uow: UnitOfWork = Depends(get_uow)
):
    user = await uow.users.get_by_id(user_uuid)
    return UserResponse(...)
```

### Key Changes
1. **Dependency Injection:** `uow: UnitOfWork = Depends(get_uow)`
2. **Repository Access:** `uow.users.get_by_id()` instead of `user_service.get_user()`
3. **Transaction Management:** Automatic via UoW context manager
4. **Type Safety:** SQLAlchemy Core provides compile-time type checking

---

## Implementation Strategy

### Phase 1: Users API (Current)
1. Update main `router.py` to use repositories
2. Keep `router_postgres.py` as reference implementation
3. Test each endpoint individually
4. Maintain backward compatibility

### Phase 2: Auth API
1. Implement session management endpoints
2. Implement credentials/PIN endpoints
3. Update authentication flow

### Phase 3: Agency API
1. Implement goal management endpoints
2. Implement plan management endpoints
3. Update agency workflows

---

## Testing Strategy

### Integration Tests
- ✅ Repository tests complete (43/43 passing)
- [ ] API endpoint tests with repositories
- [ ] End-to-end workflow tests

### Manual Testing
- [ ] Test user CRUD via API
- [ ] Test authentication flow
- [ ] Test agency goal/plan creation

---

## Success Criteria

### Day 4 Complete When:
- [ ] All Users API endpoints use repositories
- [ ] All Auth API endpoints use repositories
- [ ] All Agency API endpoints use repositories
- [ ] All API tests passing
- [ ] No regressions in existing functionality

---

## Notes

### Existing Patterns
- `router_postgres.py` demonstrates the pattern with 2 endpoints
- `postgres_dependencies.py` provides `get_uow()` dependency
- All repositories support async operations

### Dependencies
- FastAPI dependency injection for UoW
- Automatic transaction management
- Clean separation of concerns

### Next Steps After Day 4
- Expand to remaining repositories (KG, AMS, Scheduler)
- Update remaining API endpoints
- Performance optimization
- Documentation updates
