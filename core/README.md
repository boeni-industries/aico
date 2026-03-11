# AICO Core

## Purpose

The Core is the business logic engine of the AICO system. It handles:

- **NATS Request Handlers** - Processes all requests from Gateway
- **Business Logic** - Agency orchestration, memory management, conversation processing
- **Data Access** - PostgreSQL, MinIO, ChromaDB, InfluxDB operations
- **Service Orchestration** - Coordinates modelservice, scheduler, and external services
- **Background Jobs** - Scheduled tasks, memory consolidation, cleanup

## Architecture

```
Gateway
    ↓ NATS Request
Core NATS Handlers
    ↓
Business Logic (API modules)
    ↓
Data Layer (Postgres, MinIO, ChromaDB)
```

## Key Components

### `/api`
- **`/admin`** - Admin security and user management
- **`/agency`** - Agency orchestration and arbiter logic
- **`/ams`** - Agency Management System
- **`/operations`** - System operations (backups, databases, topology)
- **`/system`** - System health, metrics, configuration
- **`dependencies.py`** - Service container, UnitOfWork, database dependencies
- **`errors.py`** - Business logic error handling

### `/handlers`
- **`nats_handlers.py`** - NATS request/reply handlers for all Core operations

### `/services`
- **`lifecycle_manager.py`** - Service initialization and shutdown
- **`version_detector.py`** - Database version detection
- **Agency services** - Agency-specific business logic
- **Memory services** - Memory consolidation and management

## Running

```bash
# Development
cd core
python -m core.main

# Docker
docker compose up aico-core
```

## NATS Subjects

### Operations
- `operations.topology` - System topology
- `operations.backup.create` - Create backup
- `operations.backup.delete` - Soft-delete backup
- `operations.backup.purge` - Hard-delete backup
- `operations.databases.postgresql.details` - PostgreSQL schema details

### Agency
- `agency.arbiter.adjust` - Arbiter adjustments
- `agency.proactive.execute` - Proactive agency execution

### System
- `system.health` - Health check
- `system.metrics` - System metrics

## Environment Variables

```bash
NATS_URL=nats://localhost:4222
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=aico_core
MINIO_ENDPOINT=localhost:9000
MINIO_ACCESS_KEY=<key>
MINIO_SECRET_KEY=<secret>
INFLUXDB_URL=http://localhost:8086
```

## Dependencies

- **FastAPI** - Internal HTTP (health checks only, not exposed)
- **NATS** - Message bus server
- **asyncpg** - PostgreSQL async driver
- **boto3/aioboto3** - MinIO S3 client
- **influxdb-client** - InfluxDB client
- **ChromaDB** - Vector database (via shared)

## Architecture Principles

1. **NATS-Only External Interface** - No HTTP endpoints exposed to clients
2. **Domain-Driven Design** - Clear separation of concerns by domain
3. **Repository Pattern** - Data access via repositories and UnitOfWork
4. **Async-First** - All I/O operations are async
5. **Observable** - Comprehensive logging, metrics, and tracing
6. **Idempotent** - All operations designed for safe retries
