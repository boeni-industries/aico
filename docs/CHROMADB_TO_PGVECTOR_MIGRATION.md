# ChromaDB → pgvector Migration Guide

## Overview

AICO has migrated from ChromaDB to Postgres + pgvector for all vector storage needs (semantic memory and knowledge graph embeddings). This provides:

- **Unified data management**: All data in Postgres (no separate vector database)
- **Better performance**: HNSW indexes for fast similarity search
- **Simplified deployment**: One less service to manage
- **Transactional consistency**: Vector data participates in Postgres transactions
- **Data safety**: No risk of ChromaDB/Postgres data inconsistency

## Migration Status

✅ **COMPLETED** - All core systems migrated to pgvector

### What Changed

**Replaced:**
- ChromaDB collections → Postgres tables with pgvector columns
- ChromaDB HNSW indexes → Postgres HNSW indexes
- ChromaDB client service → Direct Postgres queries

**New Tables:**
- `aico_core.conversation_segments` - Semantic memory (replaces ChromaDB `conversation_segments` collection)
- `aico_core.kg_node_embeddings` - KG node vectors (replaces ChromaDB `kg_nodes` collection)
- `aico_core.kg_edge_embeddings` - KG edge vectors (replaces ChromaDB `kg_edges` collection)

**Removed:**
- `cli/commands/chroma.py` - ChromaDB CLI commands
- `cli/utils/chroma_utils.py` - ChromaDB utilities
- `backend/api/operations/chromadb_browser.py` - ChromaDB browser endpoints
- `backend/scheduler/tasks/kg_consolidation_chromadb.py` - ChromaDB cleanup task
- ChromaDB health/remediation tools
- `chromadb` dependency from `shared/pyproject.toml`

## Migration Process

### Prerequisites

1. **Postgres 18 with pgvector**: Already configured via `pgvector/pgvector:0.8.1-pg18` Docker image
2. **Existing ChromaDB data**: Located at `~/.local/share/aico/semantic_memory/`
3. **Postgres credentials**: Set up via `aico deploy pg`

### Step 1: Run Migration Script

The one-off migration script transfers all ChromaDB data to pgvector:

```bash
# From the aico root directory
python scripts/migrate_chroma_to_pgvector.py
```

**What it does:**
- Connects to existing ChromaDB
- Reads all collections (conversation_segments, kg_nodes, kg_edges)
- Creates corresponding pgvector tables in `aico_core` schema
- Bulk inserts all vectors with metadata
- Uses `ON CONFLICT DO UPDATE` for idempotency (safe to re-run)

**Output:**
```
ChromaDB → Postgres/pgvector Migration
================================================================================

✓ ChromaDB directory: /Users/you/.local/share/aico/semantic_memory
✓ Postgres: postgres@127.0.0.1:5432/aico
✓ Found 3 collections: ['conversation_segments', 'kg_nodes', 'kg_edges']
✓ Postgres connected, pgvector extension enabled

→ Migrating conversation_segments (1234 documents, 384d embeddings)
  ✓ 1234/1234 documents migrated
→ Migrating kg_nodes (567 documents, 384d embeddings)
  ✓ 567/567 documents migrated
→ Migrating kg_edges (890 documents, 384d embeddings)
  ✓ 890/890 documents migrated

================================================================================
✅ Migration completed: 2691 total documents migrated
================================================================================
```

### Step 2: Verify Migration

Check that data was migrated successfully:

```bash
# Connect to Postgres
psql -h 127.0.0.1 -U postgres -d aico

# Verify conversation segments
SELECT count(*) FROM aico_core.conversation_segments;

# Verify KG node embeddings
SELECT count(*) FROM aico_core.kg_node_embeddings;

# Verify KG edge embeddings
SELECT count(*) FROM aico_core.kg_edge_embeddings;

# Test vector search (should return results)
SELECT id, content, 1 - (embedding <=> '[0.1, 0.2, ...]'::vector) as similarity
FROM aico_core.conversation_segments
ORDER BY embedding <=> '[0.1, 0.2, ...]'::vector
LIMIT 5;
```

### Step 3: Restart Backend

The backend automatically uses pgvector after migration:

```bash
# Restart backend to pick up changes
aico dev restart backend
```

### Step 4: Clean Up (Optional)

After verifying the migration works:

```bash
# Remove ChromaDB data directory (ONLY after verification!)
rm -rf ~/.local/share/aico/semantic_memory/

# Uninstall chromadb package
uv pip uninstall chromadb
```

## Technical Details

### Schema Changes

All schema changes are **additive only** - no existing data is modified:

```sql
-- Enable pgvector extension (idempotent)
CREATE EXTENSION IF NOT EXISTS vector;

-- Conversation segments table
CREATE TABLE IF NOT EXISTS aico_core.conversation_segments (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    conversation_id TEXT NOT NULL,
    role TEXT NOT NULL,
    content TEXT NOT NULL,
    embedding vector(384) NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL,
    metadata JSONB,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- HNSW index for fast similarity search
CREATE INDEX IF NOT EXISTS idx_conversation_segments_embedding
    ON conversation_segments USING hnsw (embedding vector_cosine_ops);

-- KG node embeddings table
CREATE TABLE IF NOT EXISTS aico_core.kg_node_embeddings (
    node_id TEXT PRIMARY KEY REFERENCES kg_nodes(id) ON DELETE CASCADE,
    embedding vector(384) NOT NULL,
    document TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- KG edge embeddings table
CREATE TABLE IF NOT EXISTS aico_core.kg_edge_embeddings (
    edge_id TEXT PRIMARY KEY REFERENCES kg_edges(id) ON DELETE CASCADE,
    embedding vector(384) NOT NULL,
    document TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);
```

### Code Changes

**SemanticMemoryStore** (`shared/aico/ai/memory/semantic.py`):
- Now uses `uow_factory` for Postgres access
- Stores embeddings in `conversation_segments` table
- Queries using pgvector cosine similarity (`<=>` operator)

**PropertyGraphStorage** (`shared/aico/ai/knowledge_graph/storage.py`):
- Stores KG embeddings in `kg_node_embeddings` and `kg_edge_embeddings`
- Removed ChromaDB client dependency

**SemanticEntityRanker** (`shared/aico/ai/knowledge_graph/semantic_ranker.py`):
- Queries pgvector for semantic entity search
- Uses SQL joins for filtering

**MemoryManager** (`shared/aico/ai/memory/manager.py`):
- Passes `uow_factory` to all components
- Removed ChromaDB client initialization

## Data Safety

✅ **No data loss** - Migration is completely safe:

1. **Read-only ChromaDB access**: Migration script only reads from ChromaDB
2. **New tables only**: pgvector tables are brand new, don't touch existing data
3. **Idempotent operations**: Safe to re-run migration script
4. **Rollback capability**: ChromaDB data remains intact until manually deleted
5. **Postgres version protected**: Using `pgvector/pgvector:0.8.1-pg18` (Postgres 18)

## Performance

pgvector provides comparable or better performance than ChromaDB:

- **HNSW indexes**: Fast approximate nearest neighbor search
- **Cosine similarity**: Native operator (`<=>`) for vector distance
- **Batch operations**: Efficient bulk inserts with `ON CONFLICT`
- **Query optimization**: Postgres query planner optimizes vector + relational queries

## Troubleshooting

### Migration script fails with "ChromaDB directory not found"

**Solution**: Ensure ChromaDB data exists at `~/.local/share/aico/semantic_memory/`

### Migration script fails with "Postgres password not available"

**Solution**: Run `aico deploy pg` first to set up Postgres credentials

### Vector search returns no results

**Solution**: 
1. Verify data was migrated: `SELECT count(*) FROM aico_core.conversation_segments;`
2. Check HNSW index exists: `\d+ aico_core.conversation_segments`
3. Restart backend: `aico dev restart backend`

### "pgvector extension not found" error

**Solution**: Ensure using `pgvector/pgvector:0.8.1-pg18` Docker image (check `docker-compose.local.yml`)

## Rollback (Emergency Only)

If you need to rollback to ChromaDB:

1. **Stop backend**: `aico dev stop backend`
2. **Restore ChromaDB code**: `git checkout <previous-commit>`
3. **Reinstall chromadb**: `uv pip install chromadb>=1.0.16`
4. **Restart backend**: `aico dev start backend`

Note: This is only needed if the migration fails catastrophically. The migration is designed to be safe and reversible.

## Support

For issues or questions:
- Check logs: `aico dev logs backend`
- Verify Postgres: `aico pg status`
- Review schema: `psql -h 127.0.0.1 -U postgres -d aico -c "\d+ aico_core.conversation_segments"`
