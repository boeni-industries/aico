# API Gateway Architecture

## Overview

The API Gateway serves as the unified entry point for all external communication with the AICO backend services. It provides a consistent, secure interface supporting REST, WebSocket, and ZeroMQ protocols while enforcing security policies and managing device connections.

## Core Principles

- **Single Entry Point**: All external requests go through the API Gateway
- **Protocol Support**: REST (primary), WebSocket (real-time), ZeroMQ (internal)
- **Security Enforcement**: JWT authentication, ASGI-level encryption, role-based access
- **Local-First**: Works in local-only environments without external dependencies
- **Plugin Architecture**: Extensible via standardized plugin system

## Architecture Components

### 1. Plugin-Based Architecture ✅

**Current Implementation**:
- **ServiceContainer**: Manages service registration and dependency injection
- **BasePlugin**: Standardized base class with lifecycle management (`initialize()`, `start()`, `stop()`)
- **Plugin Types**: InfrastructurePlugin, SecurityPlugin, MiddlewarePlugin
- **Priority System**: Infrastructure (10) → Security (20) → Middleware (30) → Business (40)

**Active Plugins**:
- Message Bus Plugin (infrastructure)
- Encryption Plugin (security) 
- Log Consumer Plugin (infrastructure)
- Rate Limiting Plugin (middleware)

### 2. Protocol Support ✅

**REST API** (Primary):
- FastAPI framework on port 8771
- Domain-based routing: `/api/v1/{domain}/`
- JWT authentication with admin role enforcement
- OpenAPI documentation at `/docs`

**WebSocket** (Real-time):
- Thread-specific connections: `/api/v1/conversation/ws/{thread_id}`
- Real-time AI response delivery
- Heartbeat support for connection management

**ZeroMQ** (Internal):
- Message bus integration for backend communication
- Protocol Buffers serialization
- CurveZMQ encryption for security

### 3. Domain-Based API Organization ✅

**Current Domains**:
- **`/api/v1/conversation/`** - Thread and message management
- **`/api/v1/admin/`** - Administrative endpoints
- **`/api/v1/logs/`** - Log management and retrieval
- **`/api/v1/scheduler/`** - Task scheduling operations
- **`/api/v1/health`** - System health monitoring

**Structure Pattern**:
```
api/{domain}/
├── router.py      # FastAPI endpoints
├── schemas.py     # Pydantic models
├── dependencies.py # Auth and validation
└── exceptions.py   # Domain-specific errors
```

### 4. Middleware Stack ✅

**ASGI Encryption Middleware**:
- Wraps entire FastAPI application
- AES-256-GCM encryption using `AICOKeyManager`
- Unencrypted endpoints: `/health`, `/docs`, `/handshake`

**Authentication**:
- JWT token validation via `HTTPBearer`
- Admin role enforcement for privileged endpoints
- Token storage in `~/.aico/gateway_token`

**Request Logging**:
- Structured logging via Protocol Buffers
- ZMQ transport to log consumer service
- Performance metrics and audit trails

### 5. Core Services Integration ✅

**Message Bus Integration**:
- ZeroMQ with CurveZMQ encryption
- Protocol Buffers serialization
- Topic-based routing (`logs.*`, `conversation.*`)

**Database Access**:
- Shared `EncryptedLibSQLConnection` (libSQL with AES-256-GCM)
- Single database file: `data/aico.db`
- Key derivation via `AICOKeyManager`

**Configuration Management**:
- YAML-based configuration with schema validation
- Plugin-specific sections in `core.yaml`
- Runtime updates via `ConfigurationManager`

**Process Management**:
- PID file management for CLI integration
- Signal-based graceful shutdown
- Background task coordination

### 6. Device Connection Support 🚧

**Current Implementation**:
- Local connections via REST/WebSocket on port 8771
- JWT-based authentication for device trust
- Single-device deployment model

**Planned Features**:
- Multi-device federation with P2P sync
- Device registry and trust management
- mDNS/Bonjour device discovery
- Selective sync policies

## Communication Patterns ✅

### Current Implementation (Local Mode)

**Frontend ↔ API Gateway**:
- REST API on `localhost:8771`
- WebSocket for real-time updates
- JWT authentication
- ASGI-level encryption

**API Gateway ↔ Backend Services**:
- ZeroMQ message bus with CurveZMQ encryption
- Protocol Buffers serialization
- Topic-based routing

```
┌────────────┐   REST/WebSocket   ┌────────────┐      ZeroMQ      ┌────────────┐
│  Frontend  │ ─────────────────── │ API Gateway│ ─────────────────│  Backend   │
│  (Flutter) │    localhost:8771   │            │   CurveZMQ+PB    │  Services  │
└────────────┘                     └────────────┘                   └────────────┘
```

### Detached Mode

In detached mode, where frontend and backend run on separate devices:

1. API Gateway uses secure network protocols (HTTPS, WSS)
2. Mutual TLS authentication ensures bidirectional trust
3. End-to-end encryption protects all communications
4. Connection manager handles network reliability challenges

```
┌────────────┐    HTTPS/WSS/gRPC   ┌────────────┐      ZeroMQ      ┌────────────┐
│  Frontend  │ ─────────────────── │ API Gateway│ ─────────────────│  Backend   │
│  (Flutter) │      Encrypted      │            │                   │  Services  │
└────────────┘                     └────────────┘                   └────────────┘
```

### Federated Device Network Mode

In federated mode, where multiple devices synchronize data across the network:

1. API Gateway facilitates P2P encrypted communication between trusted devices
2. Device discovery uses mDNS/Bonjour (local) or DHT (remote)
3. Selective sync policies determine what data is synchronized and when
4. Conflict resolution strategies are applied based on data types

```
┌────────────┐                     ┌────────────┐                     ┌────────────┐
│  Device A  │◄───P2P Encrypted────►  Device B  │◄───P2P Encrypted────►  Device C  │
│            │       Sync          │            │       Sync          │            │
└────────────┘                     └────────────┘                     └────────────┘
      │                                  │                                  │
      └──────────────┐     ┌─────────────┘                                  │
                     ▼     ▼                                                ▼
               ┌─────────────────┐                                   ┌────────────┐
               │ Encrypted Cloud │◄──────────Fallback Only──────────►│  Device D  │
               │     Relay       │                                   │            │
               └─────────────────┘                                   └────────────┘
```

## Implementation Details

### Technology Stack

**Core Framework**:
- FastAPI with ASGI middleware
- Plugin system with `ServiceContainer`
- Port 8771 (unified REST/WebSocket)

**Security**:
- `AICOKeyManager` for key derivation
- ASGI-level AES-256-GCM encryption
- JWT authentication with admin roles
- CurveZMQ for internal communication

**Data Layer**:
- Encrypted libSQL database (`data/aico.db`)
- Protocol Buffers for message serialization
- ZeroMQ message bus (ports 5555/5556)

**Configuration**:
- YAML-based configuration (`config/defaults/core.yaml`)
- Schema validation
- Runtime updates via `ConfigurationManager`

### Request Processing Flow ✅

**Incoming Request Pipeline**:
1. **ASGI Encryption Middleware** - Decrypt request if encrypted
2. **FastAPI Router** - Route to domain-specific endpoint
3. **JWT Authentication** - Validate token and extract user context
4. **Domain Handler** - Process request (conversation, admin, logs, etc.)
5. **Backend Integration** - Communicate via ZeroMQ message bus
6. **Response Assembly** - Format response and encrypt if needed

**Example: Conversation Message Flow**:
1. Client sends POST to `/api/v1/conversation/messages`
2. Encryption middleware decrypts request
3. JWT middleware validates authentication
4. Conversation router processes message
5. ThreadManager resolves appropriate thread
6. Message published to `conversation/user/input` topic
7. Response returned immediately with message ID
8. AI response delivered via WebSocket when ready

## Security Implementation ✅

**Authentication**:
- JWT tokens with HS256 signing
- Admin role enforcement for privileged endpoints
- Token storage in `~/.aico/gateway_token`

**Encryption**:
- ASGI-level AES-256-GCM for HTTP requests
- CurveZMQ for internal ZeroMQ communication
- Key derivation via `AICOKeyManager` with Argon2id

**Data Protection**:
- Encrypted libSQL database with AES-256-GCM
- Protocol Buffers for structured message serialization
- Local-only processing (no external data transmission)

## Design Rationale ✅

**Unified Entry Point**: Single port (8771) simplifies client integration and deployment

**Security-First**: ASGI-level encryption ensures all communication is protected by default

**Plugin Architecture**: Extensible design allows adding new capabilities without core changes

**Local-First**: Designed for local deployment with encrypted storage and processing

**Performance**: ZeroMQ + Protocol Buffers provide high-performance internal communication

**Maintainability**: Domain-based organization and standardized patterns improve code quality
