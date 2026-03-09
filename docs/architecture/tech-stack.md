---
title: Technology Stack
---

# Technology Stack

This document centralizes all technology decisions for the AICO system. It provides a comprehensive overview of the technologies selected for each layer of the architecture.

## Interface Layer

| Technology | Purpose | Justification |
|------------|---------|---------------|
| **Flutter 3.27+** | Cross-platform UI framework | Single codebase for macOS/iOS/Android/Linux/Windows, high performance, rich widget library |
| **Dart 3.8+** | Programming language | Modern, type-safe language with null safety and async/await |
| **Riverpod 3.0** | State management | Modern, compile-safe state management with code generation |
| **Drift 2.29** | Local database | Type-safe SQL with SQLCipher encryption support |
| **Dio 5.4** | HTTP client | Feature-rich HTTP client with interceptors and retry logic |
| **Go Router 16.2** | Navigation | Declarative routing with deep linking support |
| **Flutter Secure Storage** | Secure key storage | Platform-native secure storage (Keychain/Credential Manager) |
| **Sodium/libsodium** | Cryptography | NaCl-based encryption for frontend security |
| **flutter_inappwebview** | WebView with localhost server | Embeds web-based avatar with ES6 module support |
| **Three.js** | 3D graphics library | Industry standard for WebGL-based 3D rendering |
| **Ready Player Me** | Avatar creation | Customizable avatars with built-in animation support |
| **TalkingHead.js** | Lip-sync and expressions (planned) | Real-time lip-sync and facial expression capabilities |

## AI/ML Layer

### Foundation Models

| Technology | Purpose | Justification |
|------------|---------|---------------|
| **Ollama** | LLM management | Simplified model management, API, and lifecycle control |
| **Qwen3 Abliterated 8B** | Primary conversation model | Uncensored foundation model for character consistency |
| **Llama 3.2 Vision 11B** | Vision understanding (optional) | Scene understanding and emotional context from images |
| **Llama 3.2 1B** | Lightweight tasks (optional) | Ultra-fast model for simple operations |

### Entity Extraction & NLP

| Technology | Purpose | Justification |
|------------|---------|---------------|
| **GLiNER Medium v2.1** | Entity extraction | Zero-shot entity recognition without fine-tuning |
| **Transformers 4.50.3** | Model framework | Hugging Face transformers for NLP tasks |
| **PyTorch** | Deep learning backend | Required by transformers for model inference |
| **BERT Multilingual** | Sentiment analysis | Multilingual sentiment classification |
| **RoBERTa** | Emotion analysis | English emotion classification (6 emotions) |
| **XLM-RoBERTa Base** | Intent classification | Multilingual intent understanding |

### Embeddings & Search

| Technology | Purpose | Justification |
|------------|---------|---------------|
| **Sentence-Transformers** | Semantic embeddings | 768-dim multilingual embeddings for semantic search |
| **BM25 (Okapi)** | Keyword search | Statistical keyword matching with IDF weighting |
| **HNSW** | Approximate nearest neighbor | Fast similarity search for entity resolution |
| **Reciprocal Rank Fusion** | Score combination | Robust fusion of semantic and keyword scores |

### Knowledge Graph

| Technology | Purpose | Justification |
|------------|---------|---------------|
| **NetworkX** | Graph data structure | Python graph library for property graphs |
| **GrandCypher** | Graph query language | GQL/Cypher query execution on NetworkX graphs |
| **PageRank** | Importance scoring | Node importance calculation for entity ranking |
| **Louvain Algorithm** | Community detection | Relationship clustering and group identification |
| **Betweenness Centrality** | Key entity identification | Identifies critical nodes in relationship networks |

### Adaptive Learning

| Technology | Purpose | Justification |
|------------|---------|---------------|
| **Thompson Sampling** | Skill selection | Contextual bandit with Beta distribution for exploration/exploitation |
| **RLHF** | Behavioral learning | Reinforcement learning from human feedback |
| **Bayesian Optimization** | Memory strategy selection | Optimal strategy selection for memory operations |

### Planned/Future

| Technology | Purpose | Status |
|------------|---------|--------|
| **AppraisalCloudPCT** | Emotion simulation | Architecture defined, implementation planned |
| **MCTS** | Planning system | Architecture defined, implementation planned |
| **Behavior Trees** | Action modeling | Architecture defined, implementation planned |

## Data & Storage Layer

AICO employs a **specialized multi-database architecture** optimized for different data access patterns. See [Data Layer](../concepts/data/data-layer.md) for comprehensive details.

### Core Databases

| Technology | Purpose | Justification |
|------------|---------|---------------|
| **PostgreSQL 18.1** | Core application data | ACID transactions, referential integrity, JSON support. Stores users, conversations, knowledge graph, agency data |
| **Loki 2.9** | Log aggregation | Purpose-built log storage with LogQL queries. Stores structured application logs with 30-day retention |
| **InfluxDB 2.x (Pro/Enterprise)** | Time-series metrics | High-performance metrics storage. Stores system metrics, API latency, model performance data |
| **pgvector (PostgreSQL extension)** | Vector embeddings | Single-stack vector search in the same Postgres instance as core data; enables tenant-scoped semantic retrieval without dual-write |
| **DuckDB** | Analytics (planned) | OLAP queries for conversation analysis and reporting |

### Database Architecture Patterns

| Pattern | Technology | Purpose |
|---------|-----------|----------|
| **Repository Pattern** | SQLAlchemy Core | Data access abstraction for domain models |
| **UnitOfWork Pattern** | asyncpg/psycopg2 | Transaction management and connection pooling |
| **Domain Models** | Pydantic 2.11+ | Type-safe business entities |
| **Connection Pooling** | SQLAlchemy Engine | Efficient connection reuse for PostgreSQL |

### Database Drivers

| Driver | Use Case | Justification |
|--------|----------|---------------|
| **asyncpg** | Backend API (async) | High-performance async PostgreSQL driver |
| **psycopg2-binary** | CLI tools (sync) | Synchronous PostgreSQL driver for admin tools |
| **requests** | Loki log writes | HTTP client for Loki push API and LogQL queries |
| **influxdb-client** | Metrics writes | InfluxDB 2.x Python client for time-series metrics |
| **pgvector** | Vector operations | PostgreSQL extension used for embedding storage and similarity search |

### Encryption & Security

| Technology | Purpose | Justification |
|------------|---------|---------------|
| **Drift + SQLCipher** | Frontend database | Type-safe SQL with AES-256-GCM encryption for Flutter message cache |
| **Keyring** | Credential storage | Platform-native secure storage (Keychain/Credential Manager) for secrets |
| **PBKDF2** | Key derivation | Key derivation for encrypted secrets (100k iterations) |

## Communication Layer

| Technology | Purpose | Justification |
|------------|---------|---------------|
| **NATS** | Internal message bus | Single broker abstraction for pub/sub, request/reply, and streaming; supports local-first and enterprise deployments |
| **JetStream** | Durable messaging | Selectively used for correctness-critical flows (work queues, durable notifications, replay) |
| **FastAPI 0.116+** | API framework | Modern, fast Python web framework powering the service gateway |
| **Uvicorn 0.35+** | ASGI server | High-performance async server for FastAPI |
| **REST API** | UI/adapter protocol | Standard HTTP API for commands, queries, and configuration |
| **WebSocket API** | UI/adapter protocol | Real-time, bidirectional communication for streaming responses |
| **Protocol Buffers 6.32** | Message format | High-performance binary serialization with strong typing (backend) |
| **Protocol Buffers 5.0** | Message format | Wire-compatible protobuf for Flutter frontend |
| **protoc** | Code generation | Automatic code generation for Python and Dart |

## Security & Privacy Layer

| Technology | Purpose | Justification |
|------------|---------|---------------|
| **SQLCipher** | Frontend database encryption | AES-256-GCM encryption for Drift databases (Flutter message cache) |
| **Argon2id** | Key derivation | Memory-hard KDF for master key derivation from password |
| **PBKDF2** | Key derivation | Additional KDF for database encryption keys (100k iterations) |
| **NaCl/libsodium** | Frontend cryptography | Modern cryptographic library for Flutter (Ed25519, X25519) |
| **PyNaCl** | Backend cryptography | Python bindings for NaCl cryptographic operations |
| **Python-Cryptography** | Cryptographic primitives | Comprehensive library with Argon2id, AES, and key management |
| **Keyring** | Platform key storage | OS-native secure storage (Keychain, Credential Manager, Secret Service) |
| **Flutter Secure Storage** | Mobile key storage | Platform-native secure storage for Flutter apps |
| **JWT (HS256)** | Authentication tokens | Stateless authentication with 24-hour expiry |
| **BCrypt** | Password hashing | Secure password hashing for user authentication |

## Deployment & Distribution Layer

> **🐳 Docker Deployment**: AICO uses Docker containers for database services (PostgreSQL, InfluxDB) with plans to containerize additional components.

### Containerized Services

| Technology | Purpose | Status |
|------------|---------|--------|
| **Docker** | Container runtime | ✅ Required for database services |
| **PostgreSQL 18.1 (Docker)** | Core database container | ✅ Production deployment |
| **Loki 2.9 (Docker)** | Log aggregation container | ✅ Production deployment |
| **InfluxDB 2.x (Docker)** | Metrics database container | ✅ Pro/Enterprise deployments |
| **Docker Compose** | Multi-container orchestration | 🚧 Planned for full stack deployment |

### Application Runtime

| Technology | Purpose | Status |
|------------|---------|--------|
| **Local Python/uv env** | Backend/modelservice runtime | ✅ Current reference setup |
| **Flutter builds** | Frontend distribution | ✅ Native builds for desktop/mobile |
| **Electron** | Desktop packaging | 🚧 Planned wrapper for packaged desktop app |
| **Delta Updates** | Efficient updates | 🚧 Planned update mechanism |
| **Cryptographic Signatures** | Update verification | 🚧 Planned for packaged releases |

### Container Benefits

- **Consistent Environments**: Same database versions across dev/test/prod
- **Easy Version Management**: Pin specific PostgreSQL/InfluxDB versions
- **Isolated Dependencies**: No system-wide database installation required
- **Simple Cleanup**: Remove containers and volumes for fresh start
- **Cross-Platform**: Works identically on Windows, macOS, Linux

## Development & Testing Layer

| Technology      | Purpose           | Justification |
|-----------------|-------------------|---------------|
| **Python**      | Core development  | Primary language for AI components |
| **Dart/Flutter**| UI development    | Cross-platform UI framework |
| **JavaScript/TypeScript** | Avatar development | Web technologies for avatar system |
| **Pytest**      | Testing framework | Comprehensive Python testing |
| **GitHub Actions** | CI/CD           | Automated testing and deployment |
| **MkDocs**      | Documentation     | Markdown-based documentation system |
| **Material for MkDocs** | Documentation theme | Clean, responsive documentation UI |

### Command-Line Interface (CLI)

| Technology      | Purpose           | Justification |
|-----------------|-------------------|---------------|
| **Typer 0.12** | CLI framework     | Modern, maintainable, autocompleting command trees with 15 command groups |
| **Rich 13.7** | Output formatting  | Beautiful, readable, Unicode-rich CLI output with tables and progress bars |
| **PyInstaller** | Packaging         | Creates single-file, dependency-free, cross-platform executables |
| **Platformdirs 4.0** | Config management  | Cross-platform config/cache path handling |
| **Requests 2.31** | API communication | HTTP client for REST API integration |
| **Cron-Descriptor** | Cron parsing | Human-readable cron schedule descriptions |

**CLI Features:**
- **15 Command Groups**: security, database, gateway, ollama, kg, scheduler, logs, config, bus, dev, version, modelservice
- **100+ Subcommands**: Comprehensive admin tooling for all AICO subsystems
- **Cross-platform**: Windows, macOS, Linux with consistent UX
- **Production-ready**: v1.1.0 with extensive real-world testing

## Monitoring & Instrumentation Layer

| Technology | Purpose | Justification |
|------------|---------|---------------|
| **Custom Logging System** | Unified logging | AICO-specific logging with subsystem/module hierarchy |
| **Loki 2.9** | Log aggregation | Purpose-built log storage with LogQL queries and 30-day retention |
| **InfluxDB 2.x (Pro/Enterprise)** | Metrics storage | Time-series database for performance metrics and telemetry |
| **OpenTelemetry** | Instrumentation | Standardized metrics and tracing instrumentation |
| **Prometheus (optional)** | Metrics export | Optional Prometheus-compatible metrics endpoint |
| **Pydantic 2.11+** | Schema validation | Type-safe validation of API requests and responses |
| **LogQL** | Log querying | Loki's query language for filtering and aggregating logs |

## Module-Specific Technologies

### Task Scheduler

| Technology | Purpose | Justification |
|------------|---------|---------------|
| **Cron Parser** | Schedule parsing | High-performance cron expression parsing with caching |
| **Asyncio** | Task execution | Python async/await for concurrent task execution |
| **Resource Monitoring** | CPU/Memory tracking | Adaptive execution based on system resources |
| **Database Schema v4** | Task persistence | scheduled_tasks, task_executions, task_locks tables |

**Built-in Tasks:**
- **Maintenance**: Log cleanup, key rotation, health checks, database vacuum
- **AMS Tasks**: Consolidation, feedback classification, Thompson sampling, trajectory cleanup
- **KG Tasks**: Graph consolidation, entity resolution, relationship inference

### Memory Album

| Technology | Purpose | Justification |
|------------|---------|---------------|
| **Database Schema v6-7** | Memory storage | user_memories table with conversation-level support |
| **Feedback Events** | User interaction tracking | feedback_events table for memory curation |
| **Sentiment Classification** | Emotional tone | Automatic emotion detection for memory organization |

### Personality Simulation (Planned)

| Technology | Purpose | Status |
|------------|---------|--------|
| **Personality System** | Personality architecture | Architecture defined, implementation planned |
| **Big Five & HEXACO** | Trait models | Research complete, implementation planned |

### Emotion Simulation (Planned)

| Technology | Purpose | Status |
|------------|---------|--------|
| **C-CPM (Conversational Component Process Model)** | Emotion architecture | ✅ Phase 1 implemented (core appraisal engine, C-CPM pipeline) |
| **4-Stage Appraisal** | Emotion generation | ✅ Implemented (Relevance → Implication → Coping → Normative) |

### Autonomous Agency (Planned)

| Technology | Purpose | Status |
|------------|---------|--------|
| **MCTS** | Decision making | Architecture defined, implementation planned |
| **Behavior Trees** | Action execution | Architecture defined, implementation planned |

### Avatar System (Planned)

| Technology | Purpose | Status |
|------------|---------|--------|
| **flutter_inappwebview** | WebView + localhost server | ✅ Ready |
| **Three.js** | WebGL 3D rendering | ✅ Ready |
| **Ready Player Me** | Avatar models | ✅ Ready |
| **TalkingHead.js** | Facial animation | 🚧 Phase 2 |
