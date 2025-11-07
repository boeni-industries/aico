# Database Init Command Fix - Root Cause Analysis

**Date:** 2025-11-07  
**Issue:** `aico db init` not applying new schema versions (12 & 13)  
**Status:** ✅ RESOLVED

---

## Root Cause Analysis

### Problem 1: Schema Registry Caching
**Issue:** `SchemaRegistry` uses class-level `_schemas` dictionary that persists across module reloads.

**Flow:**
1. `database.py` imports `aico.data.schemas.core` at module load time
2. Decorator `register_schema()` populates `SchemaRegistry._schemas`
3. Later, `db init` command tries to reload schemas with `importlib.reload()`
4. Module code re-executes, decorator runs again
5. **BUT** `SchemaRegistry` class itself is NOT reloaded (different module)
6. Registry cache may contain stale references

**Solution:**
```python
# Step 1: Clear the registry cache
SchemaRegistry.clear_registry()

# Step 2: Remove schema modules from sys.modules
schema_modules_to_clear = [
    key for key in list(sys.modules.keys()) 
    if key.startswith('aico.data.schemas')
]
for module_name in schema_modules_to_clear:
    del sys.modules[module_name]

# Step 3: Fresh import - re-runs decorators
import aico.data.schemas.core

# Step 4: Apply schemas with fresh definitions
SchemaRegistry.apply_core_schemas(conn)
```

### Problem 2: Database State Inconsistency
**Issue:** Version 11 already applied manually but not recorded in migration history.

**Symptoms:**
- Database at version 10
- Schema registry has versions 1-13
- Version 11 tries to rename `facts_metadata` → `user_memories`
- Table `user_memories` already exists
- Migration fails silently

**Detection:**
```bash
$ uv run aico db ls | grep memories
  user_memories             5

$ uv run aico db exec "SELECT version FROM _aico_migration_history WHERE version=11"
# No results - version 11 not recorded!
```

**Solution:**
Added special case handling in `database.py`:
```python
if version == 11:
    # Check if user_memories table exists
    result = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='user_memories'"
    ).fetchone()
    
    if result:
        # Migration already applied manually - record it
        conn.execute("""
            INSERT INTO _aico_migration_history 
            (version, name, description, rollback_sql, checksum)
            VALUES (?, ?, ?, ?, ?)
        """, (version, schema_v.name, schema_v.description, rollback_sql, "manual_fix"))
        
        conn.execute("""
            UPDATE _aico_schema_metadata 
            SET value = ? WHERE key = 'schema_version'
        """, (str(version),))
        
        conn.commit()
        continue  # Proceed to next version
```

---

## Implementation Changes

### File: `/cli/commands/database.py`

**Changes Made:**
1. **Removed premature schema import** at module level (line 40-42)
   - Was causing schemas to register before command execution
   - Now imports lazily inside command

2. **Added comprehensive schema reload logic** (lines 319-342)
   - Clears registry cache
   - Removes schema modules from `sys.modules`
   - Fresh import to re-register schemas
   - Debug output showing registered versions

3. **Added detailed migration logging** (lines 350-430)
   - Loops through each version individually
   - Shows success/failure for each version
   - Catches and displays exceptions with traceback
   - Special handling for version 11 inconsistency

4. **Added version 11 fix logic** (lines 383-419)
   - Detects if `user_memories` table exists
   - Records version 11 in migration history
   - Updates schema_version metadata
   - Continues to next version

---

## Verification

### Before Fix:
```bash
$ uv run aico db status
Current Version: 10
Latest Version: 13
Status: ⚠️ Update available

$ uv run aico db init
ℹ️ Database is up to date - no missing schemas  # ❌ WRONG!
```

### After Fix:
```bash
$ uv run aico db init
🔄 Clearing schema registry cache...
🔄 Removing 2 schema modules from cache...
🔄 Re-importing schema definitions...
📋 Registered schema versions: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13]
📊 Current DB version: 10, Latest: 13
🔄 Applying schema migrations...
  ▶️  Applying version 11...
    ⚠️  Table 'user_memories' already exists - migration was applied manually
    🔧 Recording version 11 in migration history...
    ✅ Version 11 recorded in migration history
  ▶️  Applying version 12...
    ✅ Version 12 applied successfully
  ▶️  Applying version 13...
    ✅ Version 13 applied successfully
📊 Final DB version: 13

$ uv run aico db status
Current Version: 13
Latest Version: 13
Status: ✅ Up to date
```

### Schema Verification:
```bash
$ uv run aico db desc user_memories | grep temporal
  temporal_metadata        TEXT        YES    NULL  # ✅ Version 12

$ uv run aico db ls | grep consolidation
  consolidation_state       0  # ✅ Version 13
```

---

## AMS Schema Versions Applied

### Version 12: Temporal Metadata Support
- **Table:** `user_memories`
- **Changes:** Added `temporal_metadata` TEXT column
- **Indexes:** 
  - `idx_user_memories_temporal` (last_accessed, confidence)
  - `idx_user_memories_superseded` (superseded_by)
- **Purpose:** Enable AMS temporal intelligence tracking

### Version 13: Consolidation State Tracking
- **Table:** `consolidation_state` (new)
- **Columns:**
  - `id` TEXT PRIMARY KEY
  - `state_json` TEXT NOT NULL
  - `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP
- **Index:** `idx_consolidation_state_updated` (updated_at DESC)
- **Purpose:** Track memory consolidation progress

---

## Lessons Learned

### 1. Module-Level Imports Can Cause Caching Issues
- **Problem:** Importing at module level caches class-level state
- **Solution:** Use lazy imports inside commands for dynamic content
- **Pattern:** Clear registry + clear sys.modules + fresh import

### 2. Silent Failures Are Hard to Debug
- **Problem:** `apply_core_schemas()` returned empty list without explanation
- **Solution:** Added detailed per-version logging
- **Pattern:** Loop through versions individually, log each step

### 3. Database State Can Diverge from Migration History
- **Problem:** Manual schema changes bypass migration tracking
- **Solution:** Detect and reconcile state inconsistencies
- **Pattern:** Check actual DB state vs expected state, record fixes

### 4. `importlib.reload()` Is Not Sufficient
- **Problem:** Only reloads target module, not dependent class state
- **Solution:** Explicitly clear class-level caches before reload
- **Pattern:** `clear_cache()` + `del sys.modules[...]` + `import`

---

## Future Improvements

### 1. Idempotent Migrations
Make all migrations idempotent by checking current state:
```sql
-- Instead of:
ALTER TABLE facts_metadata RENAME TO user_memories

-- Use:
ALTER TABLE IF EXISTS facts_metadata RENAME TO user_memories
```

### 2. Migration State Validation
Add `aico db validate` command to check:
- Migration history completeness
- Actual schema vs expected schema
- Detect manual changes

### 3. Dry-Run Mode
Add `aico db init --dry-run` to show what would be applied without executing.

### 4. Better Error Messages
Include specific SQL that failed and suggested fixes.

---

## Status: ✅ RESOLVED

The `aico db init` command now properly:
- ✅ Reloads schema definitions from disk
- ✅ Detects new schema versions
- ✅ Applies migrations sequentially
- ✅ Handles state inconsistencies gracefully
- ✅ Provides detailed logging for debugging
- ✅ Successfully applied AMS Phase 1.5 migrations (v12, v13)

**Database Version:** 10 → 13  
**AMS Status:** Ready for Phase 1.5 integration
