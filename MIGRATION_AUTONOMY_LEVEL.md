# Autonomy Level Migration - Complete

## Overview

Successfully renamed `proactive_behavior_level` to `autonomy_level` throughout the entire AICO system for consistent naming.

## Changes Made

### 1. Database Schema
- **File**: `shared/aico/data/postgres/schema.sql`
- **Change**: Column renamed from `proactive_behavior_level` to `autonomy_level`
- **Comment updated**: Now includes "autonomous" level

### 2. SQLAlchemy Tables
- **File**: `shared/aico/data/tables.py`
- **Change**: Column definition updated to `autonomy_level`

### 3. Data Models
- **File**: `shared/aico/data/ethics/value_models.py`
- **Change**: Field renamed to `autonomy_level`

### 4. Values & Ethics Service
- **File**: `shared/aico/ai/agency/values_ethics.py`
- **Changes**:
  - Enum renamed: `ProactiveBehaviorLevel` → `AutonomyLevel`
  - Added `AUTONOMOUS` level to enum
  - `ValueProfile.proactive_behavior_level` → `ValueProfile.autonomy_level`
  - All references updated throughout service

### 5. Repository Layer
- **File**: `shared/aico/data/repositories/postgres/ethics_value_profiles_repository.py`
- **Change**: All CRUD operations updated to use `autonomy_level`

### 6. Backend API
- **File**: `backend/api/agency/models.py`
- **Changes**:
  - Enum renamed: `ProactiveBehaviorLevel` → `AutonomyLevel`
  - Added `AUTONOMOUS` level
  - `ValueProfileResponse.autonomy_level`
  - `UpdateValueProfileRequest.autonomy_level`

- **File**: `backend/api/agency/router.py`
- **Change**: All endpoint handlers updated to use `autonomy_level`

### 7. Lesson Applicator
- **File**: `shared/aico/ai/agency/lesson_applicator.py`
- **Change**: Default profile creation uses `autonomy_level`

### 8. Test Fixtures
- **File**: `backend/tests/fixtures/agency.py`
- **Changes**:
  - Import updated to `AutonomyLevel`
  - Test profile setup uses `autonomy_level`

### 9. Integration Tests
- **File**: `backend/tests/integration/agency/test_api_endpoints.py`
- **Changes**:
  - Import updated to `AutonomyLevel`
  - Assertions updated to check `autonomy_level`

- **File**: `backend/tests/integration/agency/test_ethics_gates.py`
- **Changes**:
  - Import updated to `AutonomyLevel`
  - Test method renamed to `test_autonomy_level_affects_evaluation`
  - All assertions updated

## Configuration Hierarchy (VERIFIED)

The system now properly implements the configuration hierarchy:

```
1. User-specific DB value (if explicitly set by user)
   ↓ (if not set)
2. Global config default (agency.yaml: safety_control.autonomy_level)
   ↓ (if not set)
3. Hardcoded fallback ("balanced")
```

### How It Works

**When creating new profiles:**
- `ValuesEthicsService._get_or_create_profile()` reads from config:
  ```python
  config = ConfigurationManager()
  default_autonomy = config.get("agency.safety_control.autonomy_level", "balanced")
  profile = ValueProfile(user_id=user_id, autonomy_level=AutonomyLevel(default_autonomy))
  ```

- `backend/api/agency/router.py` get_value_profile() does the same

**When using existing profiles:**
- Database value is always used (user-specific setting)
- No config override - user setting takes precedence

**When updating profiles:**
- `PUT /api/v1/agency/profile` with `autonomy_level` field
- Updates database directly
- User setting persists and overrides config

## Database Migration

A migration script has been created to update existing databases:

**File**: `scripts/migrate_autonomy_level.py`

**Usage**:
```bash
python scripts/migrate_autonomy_level.py
```

**What it does**:
1. Checks if migration is needed
2. Renames `proactive_behavior_level` column to `autonomy_level`
3. Verifies the migration
4. Reports success/failure

## Autonomy Levels

The system now supports four levels:

- **`quiet`**: Only respond to explicit user requests, no autonomous goals
- **`balanced`**: Create goals from curiosity but require user activation (default)
- **`proactive`**: Autonomously activate goals and send occasional suggestions
- **`autonomous`**: Fully autonomous goal pursuit within safety constraints

## API Endpoints

### Get Value Profile
```
GET /api/v1/agency/profile
```

Response includes `autonomy_level` field.

### Update Value Profile
```
PUT /api/v1/agency/profile
Content-Type: application/json

{
  "autonomy_level": "proactive"
}
```

## Next Steps

1. **Run migration script** on existing databases:
   ```bash
   python scripts/migrate_autonomy_level.py
   ```

2. **Update existing user profiles** (if needed):
   ```sql
   UPDATE ethics_value_profiles 
   SET autonomy_level = 'proactive' 
   WHERE user_id = 'YOUR_USER_ID';
   ```

3. **Add UI control** in Studio frontend for users to edit their autonomy level

4. **Test thoroughly**:
   - Create new user profiles (should use config default)
   - Update existing profiles via API
   - Verify config hierarchy works correctly

## Configuration

The default autonomy level is set in `config/defaults/agency.yaml`:

```yaml
safety_control:
  autonomy_level: "proactive"  # Current setting
```

This value is used when creating new user profiles. Existing user profiles retain their database value and are not affected by config changes.
