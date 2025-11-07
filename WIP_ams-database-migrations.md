# AMS Database Schema Migrations

**Date:** 2025-11-07  
**Status:** Migration Guide for AMS Phase 1  
**Target:** libSQL (SQLite) and ChromaDB

---

## Overview

This document provides SQL migration scripts and guidance for adding Adaptive Memory System (AMS) support to AICO's existing database schema. The migrations are **non-destructive** and **backward-compatible**.

### Migration Strategy

1. **Add columns** (don't modify existing schema)
2. **JSON storage** for temporal metadata (flexible, no future migrations needed)
3. **Indexes** for efficient temporal queries
4. **Backward compatible** (existing code continues to work)

---

## Phase 1: Temporal Metadata

### Working Memory (LMDB)

**No schema changes required** - LMDB is key-value store. Temporal metadata added to JSON values automatically by enhanced `working.py`.

**Verification:**
```python
# Check if temporal metadata is being stored
import lmdb
import json

env = lmdb.open('/path/to/working_memory')
with env.begin() as txn:
    cursor = txn.cursor()
    for key, value in cursor:
        data = json.loads(value)
        if 'temporal_metadata' in data:
            print("✅ Temporal metadata present")
            print(data['temporal_metadata'])
            break
```

### Semantic Memory (libSQL)

**Migration 001: Add temporal_metadata column**

```sql
-- Add temporal_metadata column to semantic_facts table
-- This stores TemporalMetadata as JSON for flexibility
ALTER TABLE semantic_facts 
ADD COLUMN temporal_metadata TEXT DEFAULT NULL;

-- Add index for temporal queries
CREATE INDEX IF NOT EXISTS idx_semantic_facts_temporal 
ON semantic_facts(
    json_extract(temporal_metadata, '$.last_accessed'),
    json_extract(temporal_metadata, '$.confidence')
);

-- Add index for superseded facts
CREATE INDEX IF NOT EXISTS idx_semantic_facts_superseded 
ON semantic_facts(
    json_extract(temporal_metadata, '$.superseded_by')
);
```

**Example temporal_metadata JSON:**
```json
{
  "created_at": "2025-11-07T18:00:00Z",
  "last_updated": "2025-11-07T18:30:00Z",
  "last_accessed": "2025-11-07T19:00:00Z",
  "access_count": 5,
  "confidence": 0.85,
  "version": 2,
  "superseded_by": null
}
```

### ChromaDB Metadata

**No migration required** - ChromaDB metadata is flexible. Enhanced `semantic.py` will add temporal fields to metadata automatically:

```python
# Temporal metadata in ChromaDB document metadata
metadata = {
    "user_id": "user_123",
    "created_at": "2025-11-07T18:00:00Z",
    "confidence": 0.9,
    "version": 1,
    "last_accessed": "2025-11-07T19:00:00Z",
    "access_count": 5
}
```

---

## Phase 2: Consolidation State

### Migration 002: Consolidation state tracking

```sql
-- Create consolidation_state table for tracking consolidation progress
CREATE TABLE IF NOT EXISTS consolidation_state (
    id TEXT PRIMARY KEY,
    state_json TEXT NOT NULL,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Create index for recent state queries
CREATE INDEX IF NOT EXISTS idx_consolidation_state_updated 
ON consolidation_state(updated_at DESC);
```

**Example state_json:**
```json
{
  "status": "completed",
  "progress": {
    "total_users": 100,
    "completed_users": 100,
    "failed_users": 0,
    "total_experiences": 5000,
    "processed_experiences": 5000,
    "started_at": "2025-11-07T02:00:00Z",
    "estimated_completion": null
  },
  "last_run": "2025-11-07T02:45:00Z",
  "next_scheduled": "2025-11-08T02:00:00Z",
  "errors": [],
  "metadata": {}
}
```

---

## Phase 3: Behavioral Learning (Future)

### Migration 003: Skills and preferences

```sql
-- Skills table (user-agnostic templates)
CREATE TABLE IF NOT EXISTS skills (
    skill_id TEXT PRIMARY KEY,
    skill_name TEXT NOT NULL,
    skill_type TEXT NOT NULL,  -- 'base', 'user_created'
    trigger_context TEXT NOT NULL,  -- JSON: {intent: [...], time_of_day: ...}
    procedure_template TEXT NOT NULL,
    dimensions TEXT NOT NULL,  -- JSON: [0.5, 0.7, ...] (16 floats)
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_skill_type (skill_type)
);

-- User-skill confidence mapping
CREATE TABLE IF NOT EXISTS user_skill_confidence (
    user_id TEXT NOT NULL,
    skill_id TEXT NOT NULL,
    confidence_score REAL DEFAULT 0.5,
    usage_count INTEGER DEFAULT 0,
    positive_count INTEGER DEFAULT 0,
    negative_count INTEGER DEFAULT 0,
    last_used_at DATETIME,
    PRIMARY KEY (user_id, skill_id),
    INDEX idx_user_confidence (user_id, confidence_score DESC)
);

-- Thompson Sampling context-skill statistics
CREATE TABLE IF NOT EXISTS context_skill_stats (
    user_id TEXT NOT NULL,
    context_bucket INTEGER NOT NULL,  -- Hash of (intent + sentiment + time_of_day) % 100
    skill_id TEXT NOT NULL,
    alpha REAL DEFAULT 1.0,  -- Beta distribution success parameter
    beta REAL DEFAULT 1.0,   -- Beta distribution failure parameter
    last_updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (user_id, context_bucket, skill_id),
    INDEX idx_user_context (user_id, context_bucket)
);

-- Context-aware preference vectors (16 explicit dimensions)
CREATE TABLE IF NOT EXISTS context_preference_vectors (
    user_id TEXT NOT NULL,
    context_bucket INTEGER NOT NULL,  -- Hash of (intent + sentiment + time_of_day) % 100
    dimensions TEXT NOT NULL,  -- JSON array: [0.5, 0.7, 0.3, ...] (16 floats)
    last_updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (user_id, context_bucket),
    INDEX idx_user_prefs (user_id)
);

-- Feedback events
CREATE TABLE IF NOT EXISTS feedback_events (
    event_id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    message_id TEXT NOT NULL,
    skill_id TEXT,
    reward INTEGER NOT NULL,  -- 1, 0, -1
    reason TEXT,  -- Dropdown selection
    free_text TEXT,  -- User's free text feedback (max 300 chars)
    classified_categories TEXT,  -- JSON: {"too_verbose": 0.85, ...}
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    processed BOOLEAN DEFAULT FALSE,
    INDEX idx_feedback_user (user_id),
    INDEX idx_feedback_skill (skill_id),
    INDEX idx_feedback_processed (processed)
);

-- Trajectories (conversation history for learning)
CREATE TABLE IF NOT EXISTS trajectories (
    trajectory_id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    conversation_id TEXT NOT NULL,
    turn_number INTEGER NOT NULL,
    user_input TEXT NOT NULL,
    selected_skill_id TEXT,
    ai_response TEXT NOT NULL,
    feedback_reward INTEGER,  -- 1, 0, -1, NULL
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    archived BOOLEAN DEFAULT FALSE,  -- For soft deletion
    INDEX idx_trajectory_user_feedback (user_id, feedback_reward),
    INDEX idx_trajectory_timestamp (timestamp)  -- For retention cleanup
);
```

---

## Migration Execution

### Using AICO CLI (Recommended)

```bash
# Run all pending migrations
aico db migrate

# Check migration status
aico db migrate --status

# Rollback last migration (if needed)
aico db migrate --rollback
```

### Manual Execution

```bash
# Connect to database
sqlite3 ~/.local/share/aico/data/aico.db

# Run migration SQL
.read migrations/001_temporal_metadata.sql
.read migrations/002_consolidation_state.sql

# Verify
.schema semantic_facts
.schema consolidation_state
```

### Python Migration Script

```python
# /backend/data/migrations/001_temporal_metadata.py
from aico.data.libsql import get_connection

async def migrate():
    """Add temporal metadata support to semantic_facts."""
    conn = await get_connection()
    
    # Add column
    await conn.execute("""
        ALTER TABLE semantic_facts 
        ADD COLUMN temporal_metadata TEXT DEFAULT NULL
    """)
    
    # Add indexes
    await conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_semantic_facts_temporal 
        ON semantic_facts(
            json_extract(temporal_metadata, '$.last_accessed'),
            json_extract(temporal_metadata, '$.confidence')
        )
    """)
    
    await conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_semantic_facts_superseded 
        ON semantic_facts(
            json_extract(temporal_metadata, '$.superseded_by')
        )
    """)
    
    print("✅ Migration 001 complete: temporal_metadata added")

async def rollback():
    """Rollback temporal metadata migration."""
    conn = await get_connection()
    
    # SQLite doesn't support DROP COLUMN, so we'd need to recreate table
    # For now, just drop indexes
    await conn.execute("DROP INDEX IF EXISTS idx_semantic_facts_temporal")
    await conn.execute("DROP INDEX IF EXISTS idx_semantic_facts_superseded")
    
    print("✅ Migration 001 rollback complete")
```

---

## Verification Queries

### Check Temporal Metadata

```sql
-- Check if temporal_metadata column exists
PRAGMA table_info(semantic_facts);

-- Check if any facts have temporal metadata
SELECT COUNT(*) FROM semantic_facts 
WHERE temporal_metadata IS NOT NULL;

-- View sample temporal metadata
SELECT 
    id,
    json_extract(temporal_metadata, '$.created_at') as created,
    json_extract(temporal_metadata, '$.confidence') as confidence,
    json_extract(temporal_metadata, '$.access_count') as accesses
FROM semantic_facts 
WHERE temporal_metadata IS NOT NULL
LIMIT 5;
```

### Check Consolidation State

```sql
-- Check if consolidation_state table exists
SELECT name FROM sqlite_master 
WHERE type='table' AND name='consolidation_state';

-- View current consolidation state
SELECT 
    id,
    json_extract(state_json, '$.status') as status,
    json_extract(state_json, '$.last_run') as last_run,
    updated_at
FROM consolidation_state
ORDER BY updated_at DESC
LIMIT 1;
```

### Performance Check

```sql
-- Check index usage
EXPLAIN QUERY PLAN
SELECT * FROM semantic_facts
WHERE json_extract(temporal_metadata, '$.confidence') > 0.5
ORDER BY json_extract(temporal_metadata, '$.last_accessed') DESC
LIMIT 10;

-- Should show: SEARCH using INDEX idx_semantic_facts_temporal
```

---

## Rollback Strategy

### Phase 1 Rollback

```sql
-- Drop temporal indexes (safe, doesn't affect data)
DROP INDEX IF EXISTS idx_semantic_facts_temporal;
DROP INDEX IF EXISTS idx_semantic_facts_superseded;

-- Note: Cannot drop column in SQLite without recreating table
-- Temporal metadata in column is harmless if unused
```

### Phase 2 Rollback

```sql
-- Drop consolidation state table
DROP TABLE IF EXISTS consolidation_state;
```

### Phase 3 Rollback

```sql
-- Drop behavioral learning tables
DROP TABLE IF EXISTS trajectories;
DROP TABLE IF EXISTS feedback_events;
DROP TABLE IF EXISTS context_preference_vectors;
DROP TABLE IF EXISTS context_skill_stats;
DROP TABLE IF EXISTS user_skill_confidence;
DROP TABLE IF EXISTS skills;
```

---

## Data Migration (Backfill)

### Backfill Temporal Metadata for Existing Facts

```python
# /scripts/backfill_temporal_metadata.py
from datetime import datetime
from aico.data.libsql import get_connection
from aico.ai.memory.temporal import TemporalMetadata
import json

async def backfill_temporal_metadata():
    """Add temporal metadata to existing semantic facts."""
    conn = await get_connection()
    
    # Get all facts without temporal metadata
    facts = await conn.execute("""
        SELECT id, created_at FROM semantic_facts
        WHERE temporal_metadata IS NULL
    """)
    
    updated = 0
    for fact in facts:
        # Create temporal metadata with existing created_at
        created = datetime.fromisoformat(fact['created_at'])
        temporal_meta = TemporalMetadata(
            created_at=created,
            last_updated=created,
            last_accessed=created,
            access_count=0,
            confidence=1.0,
            version=1
        )
        
        # Update fact
        await conn.execute("""
            UPDATE semantic_facts
            SET temporal_metadata = ?
            WHERE id = ?
        """, (json.dumps(temporal_meta.to_dict()), fact['id']))
        
        updated += 1
        if updated % 100 == 0:
            print(f"Updated {updated} facts...")
    
    print(f"✅ Backfill complete: {updated} facts updated")

# Run: python -m scripts.backfill_temporal_metadata
```

---

## Monitoring & Maintenance

### Temporal Metadata Health Check

```sql
-- Check temporal metadata coverage
SELECT 
    COUNT(*) as total_facts,
    COUNT(temporal_metadata) as with_temporal,
    ROUND(COUNT(temporal_metadata) * 100.0 / COUNT(*), 2) as coverage_percent
FROM semantic_facts;

-- Check confidence distribution
SELECT 
    CASE 
        WHEN json_extract(temporal_metadata, '$.confidence') >= 0.8 THEN 'high'
        WHEN json_extract(temporal_metadata, '$.confidence') >= 0.5 THEN 'medium'
        ELSE 'low'
    END as confidence_level,
    COUNT(*) as count
FROM semantic_facts
WHERE temporal_metadata IS NOT NULL
GROUP BY confidence_level;
```

### Consolidation Monitoring

```sql
-- Check consolidation history
SELECT 
    json_extract(state_json, '$.last_run') as last_run,
    json_extract(state_json, '$.progress.completed_users') as completed,
    json_extract(state_json, '$.progress.failed_users') as failed,
    json_extract(state_json, '$.progress.processed_experiences') as experiences
FROM consolidation_state
ORDER BY updated_at DESC
LIMIT 10;
```

---

## Troubleshooting

### Issue: Migration fails with "column already exists"

**Solution:** Migration already applied, safe to skip.

```sql
-- Check if column exists
PRAGMA table_info(semantic_facts);
```

### Issue: JSON queries are slow

**Solution:** Ensure indexes are created.

```sql
-- Recreate indexes
DROP INDEX IF EXISTS idx_semantic_facts_temporal;
CREATE INDEX idx_semantic_facts_temporal 
ON semantic_facts(
    json_extract(temporal_metadata, '$.last_accessed'),
    json_extract(temporal_metadata, '$.confidence')
);
```

### Issue: Temporal metadata not appearing

**Solution:** Check if enhanced working.py is being used.

```python
# Verify temporal metadata is being added
from aico.ai.memory import WorkingMemoryStore
store = WorkingMemoryStore(config)
await store.initialize()

# Store test message
await store.store_message("test_conv", {
    "message_type": "user_input",
    "content": "test"
})

# Retrieve and check
history = await store.retrieve_conversation_history("test_conv")
print(history[0].get('temporal_metadata'))  # Should not be None
```

---

## Next Steps

1. **Run Phase 1 migrations** (temporal metadata)
2. **Verify** temporal metadata is being stored
3. **Monitor** query performance with new indexes
4. **Backfill** existing data (optional, can be done gradually)
5. **Phase 2** migrations when consolidation is ready for testing
6. **Phase 3** migrations when behavioral learning is implemented

---

**Status:** Ready for Phase 1 migration execution
