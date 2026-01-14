---
title: Data Layer
---

# Data Layer Architecture

AICO's data layer implements **Clean Architecture** principles with a multi-database approach optimized for different data access patterns.

## Database Architecture

**Production Databases:**
- ✅ **PostgreSQL 18.1** (Docker): Core application data (users, conversations, knowledge graph, agency)
- ✅ **InfluxDB 2.x** (Docker): Time-series telemetry (metrics, logs, performance data)
- ✅ **ChromaDB**: Vector embeddings for semantic search
- ✅ **LMDB**: Working memory with 30-day TTL

**Planned:**
- ⏳ **DuckDB**: Analytics engine for conversation analysis

## Architecture Principles

### Clean Architecture Layers
1. **Domain Models**: Pure business logic (Pydantic models)
2. **Repositories**: Data access abstraction
3. **UnitOfWork**: Transaction and session management
4. **Database Adapters**: Technology-specific implementations

### Database Specialization
Each database serves a specific purpose optimized for its workload:
- **PostgreSQL**: ACID transactions, referential integrity, relational data
- **InfluxDB**: High-performance time-series data, automatic downsampling
- **ChromaDB**: Vector similarity search, semantic retrieval
- **LMDB**: Fast key-value working memory, sub-millisecond access

---

## PostgreSQL - Core Application Data

**Purpose**: Transactional application data requiring ACID guarantees

**Deployment**: Docker container (`postgres:18.1`) with persistent volume

**Schema Organization**:
```sql
Database: aico
Schema: aico_core  -- All application tables
```

**Data Stored**:
- **Users & Auth**: `user_profiles`, `auth_sessions`, `auth_user_credentials`
- **Conversations**: `conversations`, `messages`, `conversation_participants`
- **Knowledge Graph**: `kg_nodes`, `kg_edges`, `kg_node_properties`
- **Agency**: `agency_goals`, `agency_plans`, `agency_skill_executions`
- **Memory**: `semantic_memory_metadata`, `user_preferences`, `facts`

**Technology Stack**:
- PostgreSQL 18.1 in Docker container
- asyncpg for async operations (backend API)
- psycopg2 for sync operations (CLI tools)
- SQLAlchemy Core for query building
- Connection pooling via SQLAlchemy Engine

**Backend API Pattern (Repository + UnitOfWork)**:
```python
from aico.data.uow import UnitOfWork

async def create_conversation(user_id: str, title: str):
    async with UnitOfWork() as uow:
        conversation = await uow.conversations.create({
            "user_id": user_id,
            "title": title
        })
        await uow.commit()
        return conversation
```

**CLI Tools Pattern (Direct SQL)**:
```python
from cli.utils.pg_connection import get_pg_connection

def list_users():
    db = get_pg_connection()
    cursor = db.cursor()
    cursor.execute("SELECT uuid, full_name FROM aico_core.user_profiles")
    return cursor.fetchall()
```

---

## InfluxDB - Time-Series Telemetry

**Purpose**: High-performance metrics, logs, and observability data

**Deployment**: Docker container (`influxdb:2-alpine`) with persistent volume

**Data Organization**:
```
Organization: aico
Bucket: aico_telemetry
Retention: 30 days (configurable)
```

**Data Stored**:
- **System Metrics**: CPU, memory, disk usage
- **API Metrics**: Request/response times, error rates  
- **Model Metrics**: Inference latency, token counts
- **Application Logs**: Structured log events with timestamps

**Technology Stack**:
- InfluxDB 2.x in Docker container
- influxdb-client-python
- OpenTelemetry instrumentation
- Flux query language

**Access Pattern**:
```python
from influxdb_client import InfluxDBClient, Point

client = InfluxDBClient(url="http://localhost:8086", token=token, org="aico")
write_api = client.write_api()

point = Point("api_request") \
    .tag("endpoint", "/api/v1/conversation") \
    .field("duration_ms", 45.2) \
    .time(datetime.now(UTC))

write_api.write(bucket="aico_telemetry", record=point)
```

---

## ChromaDB - Vector Embeddings

**Purpose**: Semantic search and similarity matching

**Collections**:
- `conversation_segments`: Conversation history with embeddings
- `kg_node_embeddings`: Knowledge graph entity embeddings
- `kg_edge_embeddings`: Relationship embeddings

**Technology Stack**:
- ChromaDB (persistent mode)
- Sentence-transformers via modelservice
- Cosine similarity search
- Metadata filtering

**Access Pattern**:
```python
import chromadb

client = chromadb.PersistentClient(path="/path/to/chroma")
collection = client.get_or_create_collection("conversation_segments")

# Store with embeddings
collection.upsert(
    ids=["msg_123"],
    embeddings=[[0.1, 0.2, ...]],  # From modelservice
    documents=["User message text"],
    metadatas=[{"user_id": "uuid"}]
)

# Semantic search
results = collection.query(
    query_embeddings=[[0.1, 0.2, ...]],
    n_results=10
)
```

---

## LMDB - Working Memory

**Purpose**: High-performance ephemeral storage for active conversation context

**Features**:
- 30-day TTL for conversation continuity
- Sub-millisecond read/write latency
- Memory-mapped for performance
- Named databases for different data types

**Implementation**:
- Database: `session_memory`
- Storage: `/data/lmdb/`
- Integration: WorkingMemoryStore in `/shared/aico/ai/memory/working.py`
- Coordination: PostgreSQL tracks LMDB sessions via `session_metadata` table

---

## Repository Pattern

The Repository pattern abstracts data access, providing clean interfaces for domain operations.

**Base Repository**:
```python
class Repository:
    def __init__(self, connection, table):
        self.connection = connection
        self.table = table
    
    async def get_by_id(self, id: str):
        query = select(self.table).where(self.table.c.id == id)
        result = await self.connection.execute(query)
        return result.fetchone()
    
    async def create(self, data: dict):
        query = insert(self.table).values(**data).returning(self.table)
        result = await self.connection.execute(query)
        return result.fetchone()
```

**Specialized Repository**:
```python
class ConversationRepository(Repository):
    async def get_by_user(self, user_id: str):
        query = select(self.table).where(self.table.c.user_id == user_id)
        result = await self.connection.execute(query)
        return result.fetchall()
```

---

## UnitOfWork Pattern

Manages database transactions and repository lifecycle.

```python
class UnitOfWork:
    async def __aenter__(self):
        self.connection = await get_async_connection()
        self.transaction = await self.connection.begin()
        return self
    
    async def commit(self):
        await self.transaction.commit()
    
    @property
    def conversations(self):
        if not self._conversations:
            self._conversations = ConversationRepository(self.connection)
        return self._conversations
```

**Usage**:
```python
async with UnitOfWork() as uow:
    conversation = await uow.conversations.create(data)
    await uow.commit()
```

---

## Database Integration Flow

**Write Flow** (New conversation message):
1. **LMDB**: Store in working memory (immediate access)
2. **PostgreSQL**: Create metadata record with conversation_id, user_id, timestamp
3. **Modelservice**: Generate 768-dim embedding via sentence-transformers
4. **ChromaDB**: Store embedding with metadata for semantic search

**Read Flow** (Retrieve relevant context):
1. **Query**: User asks question
2. **Modelservice**: Generate query embedding
3. **ChromaDB**: Semantic search returns top-N similar segments
4. **PostgreSQL**: Fetch full metadata for returned segment IDs
5. **LMDB**: Check working memory for recent context
6. **Fusion**: Combine semantic + recency + relationship scores

**Why This Architecture**:
- **PostgreSQL**: ACID guarantees for metadata, referential integrity for relationships
- **InfluxDB**: Optimized for time-series data, automatic retention policies
- **ChromaDB**: Optimized for vector similarity search (cosine distance)
- **LMDB**: Ultra-fast access for active conversations
- **Separation**: Each database handles what it does best

---

## Performance Characteristics

**Resource Usage**:

| Database | Read/Write | Use Case | Latency |
|----------|-----------|----------|---------|
| **PostgreSQL** | High | Structured queries | ~1-10ms |
| **InfluxDB** | Very High | Time-series writes | ~1-5ms |
| **ChromaDB** | High | Semantic search | ~10-50ms |
| **LMDB** | Very High | Working memory | <1ms |

**Characteristics**:
- **PostgreSQL**: ACID transactions, connection pooling
- **InfluxDB**: High-throughput writes, automatic downsampling
- **ChromaDB**: Cosine similarity, hybrid search (BM25 + semantic)
- **LMDB**: Memory-mapped, multi-reader/single-writer

---

## Best Practices

### Database Selection

Choose the right database for your use case:
- **PostgreSQL**: User data, conversations, knowledge graph, agency data
- **InfluxDB**: Metrics, logs, performance data, time-series events
- **ChromaDB**: Embeddings, semantic search, similarity matching
- **LMDB**: Active session data, conversation context, temporary cache

### Repository Usage

```python
# ✅ Good - Repository pattern in backend
async with UnitOfWork() as uow:
    user = await uow.users.get_by_id(user_id)
    await uow.commit()

# ✅ Good - Direct SQL in CLI tools
db = get_pg_connection()
cursor = db.cursor()
cursor.execute("SELECT * FROM aico_core.user_profiles")
```

### Transaction Management

```python
# ✅ Good - Explicit commit for writes
async with UnitOfWork() as uow:
    await uow.conversations.create(data)
    await uow.commit()

# ✅ Good - No commit for read-only
async with UnitOfWork() as uow:
    conversations = await uow.conversations.list_all()
    return conversations
```

---

## Docker Deployment

PostgreSQL and InfluxDB run in Docker containers for consistent deployment.

**Deployment Commands**:
```bash
# Deploy PostgreSQL
aico deploy pg

# Deploy InfluxDB
aico deploy influx

# Reset databases (⚠️ DANGEROUS - deletes all data)
aico deploy pg --nuke
aico deploy influx --nuke
```

**Container Details**:
- PostgreSQL: `postgres:18.1` on port 5432
- InfluxDB: `influxdb:2-alpine` on port 8086
- Persistent volumes for data storage
- Docker bridge network for inter-container communication

See [Getting Started Guide](../../guides/developer/getting-started.md) for detailed deployment instructions.

---

## Related Documentation

- [Architecture Overview](../../architecture/architecture-overview.md) - System architecture
- [Tech Stack](../../architecture/tech-stack.md) - Technology decisions
- [Backend Patterns](../../guides/developer/backend-patterns.md) - Repository/UnitOfWork patterns
- [Getting Started](../../guides/developer/getting-started.md) - Database deployment
