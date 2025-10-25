---
title: Data Layer
---

# Data Layer

AICO's data layer provides local-first, privacy-preserving storage for the AI companion system. Currently implemented with libSQL, with additional databases planned for specialized workloads.

## Current Implementation vs. Future Plans

**Currently Implemented:**
- ✅ **libSQL**: Primary encrypted storage for all structured data
- ✅ **ChromaDB**: Vector database for conversation embeddings and semantic search
- ✅ **LMDB**: High-performance key-value store for session data

**Planned for Future:**
- ⏳ **DuckDB**: Analytics engine for conversation analysis

## Architecture Overview

```mermaid
classDiagram
    class AICO_DATA_LAYER {
        <<Current + Planned>>
    }
    
    class libSQL {
        ✅ PRIMARY STORAGE
        Encrypted structured data
        Facts, feedback, users, logs
        ACID transactions
    }
    
    class ChromaDB {
        ✅ VECTOR DATABASE
        Conversation embeddings
        Semantic search
    }
    
    class LMDB {
        ✅ WORKING MEMORY
        Active session data
        Sub-ms latency
    }
    
    class DuckDB {
        ⏳ ANALYTICS ENGINE
        Conversation analysis
        OLAP queries
    }
    
    AICO_DATA_LAYER --> libSQL
    AICO_DATA_LAYER --> ChromaDB
    AICO_DATA_LAYER --> LMDB
    AICO_DATA_LAYER -.-> DuckDB
```

**Current Architecture Principles:**
- **Local-first**: All data stored locally by default
- **Privacy-first**: Encryption at rest for sensitive data
- **File-based**: No daemon processes required
- **Cross-platform**: Works on Windows, macOS, and Linux
- **Single-user**: Optimized for personal AI companion use

## Database Components

### 1. Primary Storage: libSQL ✅

**Status**: Currently implemented and fully functional.

**Key Features**:
- SQLite-compatible with encryption at rest
- Schema management with automatic migrations
- ACID transactions for data consistency
- Cross-platform file-based storage

**Current Data Storage**:
- System logs and audit trails
- User authentication and security data
- Configuration settings and preferences
- Facts metadata (user-curated and AI-extracted)
- Feedback events (user actions, signals, ratings)
- Task scheduling and execution history

**Implementation Example**:
```python
from aico.data import EncryptedLibSQLConnection

# Connect with encryption
conn = EncryptedLibSQLConnection(
    db_path="~/.aico/user.db",
    encryption_key=derived_key
)

# Execute queries with automatic encryption
conn.execute("INSERT INTO logs (timestamp, level, message) VALUES (?, ?, ?)",
            [timestamp, "INFO", "User logged in"])
```

### 2. Analytics Engine: DuckDB ⏳

**Status**: Planned for future implementation.

**Planned Purpose**: Analytical processing of conversation data and user interaction patterns.

**Future Capabilities**:
- Conversation pattern analysis and insights
- User behavior analytics and trends
- Performance metrics and system statistics
- Advanced aggregations and time-series analysis

**Integration Plan**:
- Export data from libSQL for analysis
- Columnar storage for analytical workloads
- Integration with AI model training pipelines

### 3. Vector Database: ChromaDB ✅

**Status**: Currently implemented.

**Purpose**: Storage and retrieval of conversation embeddings for semantic search.

**Current Capabilities**:
- Conversation segment embeddings with cosine similarity
- Hybrid search (BM25 + semantic)
- Context-aware conversation history retrieval
- Configurable relevance thresholds

**Implementation**:
- Collection: `conversation_segments`
- Embeddings: Generated via ModelService (paraphrase-multilingual)
- Storage: `/data/chroma/`
- Integration: SemanticMemoryStore in `/shared/aico/ai/memory/semantic.py`

### 4. Cache Layer: LMDB ✅

**Status**: Currently implemented.

**Purpose**: High-performance ephemeral storage for active conversation context.

**Current Capabilities**:
- Working memory for active conversations
- Recent message caching (TTL: 24 hours)
- Sub-millisecond read/write latency
- Named databases for different data types

**Implementation**:
- Database: `session_memory`
- Storage: `/data/lmdb/`
- Integration: WorkingMemoryStore in `/shared/aico/ai/memory/working.py`
- Coordination: `session_metadata` table in libSQL tracks LMDB sessions

## Current Data Integration

**Three-Tier Architecture** (Currently Implemented):

1. **libSQL** - Structured data with ACID guarantees
   - Facts metadata (user-curated and AI-extracted)
   - Feedback events (actions, signals, ratings)
   - Users, auth, logs, tasks
   - Schema v6: Extended for Memory Album

2. **ChromaDB** - Vector embeddings for semantic search
   - Conversation segments with embeddings
   - Hybrid search (BM25 + semantic)
   - Managed by SemanticMemoryStore

3. **LMDB** - Fast ephemeral working memory
   - Active conversation context
   - Recent messages (24h TTL)
   - Managed by WorkingMemoryStore

**Coordination**:
- `session_metadata` table in libSQL coordinates LMDB sessions
- MemoryManager orchestrates all three stores
- Shared modules in `/shared/aico/ai/memory/`

**Future Multi-Database Integration** (Planned):
- DuckDB for analytical queries
- Event-driven updates across databases
- Cross-database consistency with eventual consistency model

## Federated Device Sync ⏳

**Status**: Not yet implemented - see [Data Federation](data-federation.md) for planned architecture.

**Current**: Single-device operation only
**Future**: Multi-device sync with encrypted data replication

## Security and Privacy

**Current Implementation**:
- **libSQL Encryption**: AES-256-GCM encryption at rest with Argon2id key derivation
- **Local Storage**: All data stored locally on user's device
- **Master Key**: Stored securely in system keyring
- **Zero Cloud Dependencies**: No external services required

**Future Security**:
- **Multi-Database Encryption**: Consistent encryption across all databases
- **Federated Sync**: End-to-end encryption for device synchronization
- **Zero-Knowledge**: No third-party access to user data

## Performance Characteristics

**Current Performance**:

| Database | Read/Write | Use Case | Latency |
|----------|-----------|----------|---------|
| **libSQL** | High | Structured queries | ~1-10ms |
| **ChromaDB** | High | Semantic search | ~10-50ms |
| **LMDB** | Very High | Working memory | <1ms |

**Characteristics**:
- **libSQL**: ACID transactions, encryption overhead minimal
- **ChromaDB**: Cosine similarity, hybrid search (BM25 + semantic)
- **LMDB**: Memory-mapped, multi-reader/single-writer

**Future Multi-Database Performance**:
- **DuckDB**: Analytical queries on exported data
- **Query Routing**: Automatic selection of optimal database
- **Caching Strategy**: Hot data in LMDB, cold data in libSQL

## Architecture Rationale

**Current Three-Database Approach**:
- **Specialization**: Each database optimized for its workload
- **Performance**: LMDB for speed, ChromaDB for search, libSQL for structure
- **Reliability**: Proven technologies (SQLite, LMDB, ChromaDB)
- **Coordination**: MemoryManager orchestrates across all three

**Future Benefits with DuckDB**:
- **Analytics**: Dedicated engine for conversation analysis
- **Separation**: Analytical queries don't impact operational databases
- **Columnar Storage**: Optimized for aggregations and time-series

## Current Database Architecture

**Repository Pattern**: AICO uses the repository pattern for clean data access:

```python
from aico.data.logs import LogRepository
from aico.data.user import UserService

# Domain-specific repositories
log_repo = LogRepository(connection)
user_service = UserService(connection)

# Clean API for data operations
log_repo.insert_log(level="INFO", message="User action")
user_profile = user_service.get_profile(user_id)
```

**Current Implementation Layers**:
1. **Domain Services**: Business logic (UserService, LogRepository)
2. **Data Access**: Database connections and transactions
3. **Database Layer**: libSQL with encryption and schema management

**Benefits**:
- **Clean Separation**: Business logic separated from database details
- **Testability**: Easy to mock repositories for unit testing
- **Maintainability**: Schema changes isolated to data layer
- **Future-Ready**: Easy to add new databases when implemented

## Schema Management ✅

**Current Implementation**: AICO uses a decorator-based schema registry for automatic schema discovery and application:

```python
from aico.data import register_schema, SchemaVersion

@register_schema("core", "core", priority=1)
CORE_SCHEMA = {
    1: SchemaVersion(
        version=1,
        name="Core System",
        description="Logs, users, and system tables",
        sql_statements=[
            "CREATE TABLE logs (...)",
            "CREATE TABLE users (...)"
        ]
    )
}
```

**Features**:
- **Automatic Discovery**: Schemas registered via decorators
- **Version Management**: Incremental migrations with rollback support
- **Transaction Safety**: All migrations wrapped in transactions
- **Plugin Support**: Plugin schemas isolated from core schemas

**Usage**:
```python
# Automatic schema application on startup
from aico.data.libsql.registry import SchemaRegistry

# Apply all core schemas
applied = SchemaRegistry.apply_core_schemas(connection)
print(f"Applied schemas: {applied}")
```


