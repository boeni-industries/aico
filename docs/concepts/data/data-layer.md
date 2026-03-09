---
title: Data Layer
---

# Data Layer Architecture

AICO's data layer implements **Clean Architecture** principles with a multi-database approach optimized for different data access patterns.

## Database Architecture

**Production Databases:**
- ✅ **PostgreSQL 18.1** (Docker): Core application data (users, conversations, knowledge graph, agency)
- ✅ **Loki 2.9** (Docker): Log aggregation with LogQL queries
- ✅ **InfluxDB 2.x (Pro/Enterprise)** (Docker): Time-series metrics (performance data, telemetry)
- ✅ **pgvector (PostgreSQL extension)**: Vector embeddings for semantic search

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
- **Loki**: Purpose-built log aggregation, LogQL queries, label-based indexing
- **InfluxDB**: High-performance time-series metrics, automatic downsampling
- **pgvector**: Vector similarity search inside Postgres

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

## Loki - Log Aggregation

**Purpose**: Purpose-built log storage and querying

**Deployment**: Docker container (`grafana/loki:2.9.0`) with persistent volume

**Data Organization**:
```
Storage: Filesystem (BoltDB + filesystem chunks)
Retention: 30 days (configurable)
Index: Label-based (service, level, logger_prefix)
```

**Data Stored**:
- **Application Logs**: Structured log events from all services
- **Labels**: service, level, logger_prefix for fast filtering
- **Metadata**: JSON-encoded metadata in log lines

**Technology Stack**:
- Loki 2.9 in Docker container
- requests library for HTTP push API
- LogQL query language
- Label-based indexing (not full-text)

**Access Pattern**:
```python
import requests
import json

# Push logs to Loki
loki_url = "http://localhost:3100/loki/api/v1/push"
payload = {
    "streams": [{
        "stream": {
            "service": "backend",
            "level": "INFO",
            "logger_prefix": "backend.api"
        },
        "values": [
            [str(int(time.time() * 1e9)), "Log message | {\"metadata\": \"json\"}"]
        ]
    }]
}
requests.post(loki_url, json=payload)

# Query logs with LogQL
query_url = "http://localhost:3100/loki/api/v1/query_range"
params = {
    "query": '{service="backend", level="ERROR"}',
    "limit": 100
}
response = requests.get(query_url, params=params)
```

**CLI Access**:
```bash
# Tail logs
aico logs tail --service backend --level ERROR --lines 50

# List logs
aico logs ls --service modelservice --limit 100
```

---

## InfluxDB - Time-Series Metrics

**Purpose**: High-performance metrics and telemetry data

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
- **Performance Data**: Time-series telemetry

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

## pgvector - Vector Embeddings

**Purpose**: Semantic search and similarity matching

**Technology Stack**:
- PostgreSQL extension
- Sentence-transformers via modelservice
- Cosine/inner-product distance (index-dependent)
- Tenant/user scoping enforced via standard relational filters

---

## Working Memory and Conversation History

**Purpose**: Authoritative storage for conversations and message history.

**Implementation**:
- Stored in PostgreSQL as the system of record.
- Tenant-scoped via `tenant_id` on authoritative tables.

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
1. **PostgreSQL**: Persist user message (source of truth; idempotent per request)
2. **Modelservice**: Generate embeddings as needed
3. **PostgreSQL + pgvector**: Store embeddings and metadata for semantic search

**Read Flow** (Retrieve relevant context):
1. **Query**: User asks question
2. **Modelservice**: Generate query embedding
3. **PostgreSQL + pgvector**: Semantic search returns top-N relevant items (tenant/user scoped)
4. **Fusion**: Combine semantic + recency + relationship scores

**Why This Architecture**:
- **PostgreSQL**: ACID guarantees for metadata, referential integrity for relationships
- **Loki**: Purpose-built for logs, label-based indexing, efficient storage
- **InfluxDB**: Optimized for time-series metrics, automatic retention policies
- **pgvector**: Optimized vector search inside Postgres
- **Separation**: Each database handles what it does best

---

## Performance Characteristics

**Resource Usage**:

| Database | Read/Write | Use Case | Latency |
|----------|-----------|----------|---------|
| **PostgreSQL** | High | Structured queries | ~1-10ms |
| **Loki** | Very High | Log writes | ~1-5ms |
| **InfluxDB** | Very High | Metrics writes | ~1-5ms |
| **pgvector** | High | Semantic search | ~5-50ms |

**Characteristics**:
- **PostgreSQL**: ACID transactions, connection pooling
- **Loki**: Label-based indexing, LogQL queries, 70% storage reduction vs InfluxDB
- **InfluxDB**: High-throughput writes, automatic downsampling
- **pgvector**: Cosine/inner-product similarity search with Postgres indexing

---

## Best Practices

### Database Selection

Choose the right database for your use case:
- **PostgreSQL**: User data, conversations, knowledge graph, agency data
- **Loki**: Application logs, structured logging, log queries
- **InfluxDB**: Metrics, performance data, time-series telemetry
- **pgvector**: Embeddings, semantic search, similarity matching

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

PostgreSQL, Loki, and InfluxDB run in Docker containers for consistent deployment.

**Deployment Commands**:
```bash
# Deploy PostgreSQL
aico deploy pg

# Deploy Loki (log aggregation)
aico deploy loki

# Deploy InfluxDB (metrics)
aico deploy influx

# Reset databases (⚠️ DANGEROUS - deletes all data)
aico deploy pg --nuke
aico deploy loki --nuke
aico deploy influx --nuke
```

**Container Details**:
- PostgreSQL: `postgres:18.1` on port 5432
- Loki: `grafana/loki:2.9.0` on port 3100
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
