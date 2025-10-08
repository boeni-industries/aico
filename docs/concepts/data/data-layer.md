---
title: Data Layer
---

# Data Layer

AICO's data layer provides local-first, privacy-preserving storage for the AI companion system. Currently implemented with libSQL, with additional databases planned for specialized workloads.

## Current Implementation vs. Future Plans

**Currently Implemented:**
- ✅ **libSQL**: Primary encrypted storage for all structured data

**Planned for Future:**
- ⏳ **ChromaDB**: Vector database for AI embeddings and semantic search
- ⏳ **DuckDB**: Analytics engine for conversation analysis
- ⏳ **LMDB**: High-performance cache for session data

## Architecture Overview

```mermaid
classDiagram
    class AICO_DATA_LAYER {
        <<Current + Planned>>
    }
    
    class libSQL {
        ✅ PRIMARY STORAGE
        Encrypted structured data
        Schema management
        ACID transactions
    }
    
    class ChromaDB {
        ⏳ VECTOR DATABASE
        AI embeddings
        Semantic search
    }
    
    class DuckDB {
        ⏳ ANALYTICS ENGINE
        Conversation analysis
        OLAP queries
    }
    
    class LMDB {
        ⏳ CACHE LAYER
        Session data
        High-performance KV
    }
    
    AICO_DATA_LAYER --> libSQL
    AICO_DATA_LAYER -.-> ChromaDB
    AICO_DATA_LAYER -.-> DuckDB
    AICO_DATA_LAYER -.-> LMDB
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
- Plugin metadata and state

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

### 3. Vector Database: ChromaDB ⏳

**Status**: Planned for future implementation.

**Planned Purpose**: Storage and retrieval of AI embeddings for semantic search and long-term memory.

**Future Capabilities**:
- Conversation embeddings for semantic search
- Long-term memory storage and retrieval
- Context-aware information lookup
- Similarity-based content recommendations

**Integration Plan**:
- Embed conversation content using local AI models
- Store embeddings with metadata in ChromaDB
- Provide semantic search API for conversation history

### 4. Cache Layer: LMDB ⏳

**Status**: Planned for future implementation.

**Planned Purpose**: High-performance caching for frequently accessed data and session state.

**Future Capabilities**:
- Session state and active context caching
- Frequently accessed configuration data
- Temporary computation results
- Real-time interaction state

**Integration Plan**:
- Cache hot data from libSQL for faster access
- Store ephemeral session data
- Provide microsecond-latency key-value operations

## Current Data Integration

**libSQL Integration** (Currently Implemented):
- Direct database connections through `EncryptedLibSQLConnection`
- Schema management via `SchemaRegistry` with automatic migrations
- Repository pattern for clean data access
- Message bus integration for log persistence

**Future Multi-Database Integration** (Planned):
- Event-driven updates across multiple databases
- Unified data access layer abstracting database specifics
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

**Current (libSQL)**:
- **Read/Write**: High performance for structured queries
- **Memory**: Low footprint, file-based storage
- **Encryption**: Minimal overhead with hardware acceleration
- **Concurrency**: Multi-reader, single-writer model

**Future Multi-Database Performance**:
- **Specialized Workloads**: Each database optimized for specific use cases
- **Query Routing**: Automatic selection of optimal database for each query type
- **Caching Strategy**: Hot data in LMDB, analytical queries in DuckDB

## Architecture Rationale

**Current Single-Database Approach**:
- **Simplicity**: Single libSQL database reduces complexity
- **Reliability**: Proven SQLite foundation with encryption
- **Development Speed**: Faster initial implementation

**Future Multi-Database Benefits**:
- **Performance Optimization**: Specialized databases for different workloads
- **Scalability**: Independent scaling of different data types
- **Feature Specialization**: Vector search, analytics, and caching capabilities

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


