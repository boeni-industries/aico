# API Gateway Architecture

---

## Admin Endpoints and Privileged Access

The API Gateway is also responsible for securely exposing all **administrative endpoints** (web UI and API) required for backend operation and maintenance:
- **Admin endpoints** (e.g., `/admin`, `/admin/config`, `/admin/logs`, etc.) are served as privileged, local-only interfaces by default.
- **Authentication & Authorization:** Strong authentication and role-based access control are enforced for all admin actions.
- **Routing:** Admin requests are routed to the corresponding backend admin modules in the Administration domain.
- **Separation:** Admin endpoints are strictly separated from user-facing APIs and are never exposed to regular users.
- **Extensibility:** As new admin modules are added to the backend, their endpoints become available via the gateway automatically.

This ensures that all administrative functionality—configuration, logs, plugin management, updates, audit, etc.—is securely accessible to developers and operators, while protecting regular users and maintaining system integrity.

---

## Overview

The API Gateway serves as the unified entry point for all external communication with the AICO backend services. It provides a consistent, secure, and protocol-agnostic interface that supports both coupled and detached roaming patterns while enforcing the system's security policies. Additionally, it plays a crucial role in AICO's federated device network, facilitating secure device-to-device communication and data synchronization.

## Core Principles

- **Single Entry Point**: All external requests to backend services must go through the API Gateway
- **Protocol Flexibility**: Support for REST, WebSocket, and gRPC protocols to accommodate different client capabilities
- **Security Enforcement**: Centralized authentication, authorization, and request validation
- **Roaming Support**: Seamless support for both coupled and detached roaming patterns
- **Local-First**: Designed to work in local-only environments without external dependencies
- **Zero-Trust**: Enforce security boundaries even for local communication
- **Federated Communication**: Support for P2P device communication in the federated device network
- **Selective Sync**: Facilitate different synchronization policies for various data types

## Architecture Components

### 1. Plugin-Based Architecture

The API Gateway uses a modular plugin-based architecture centered around the `GatewayCore` orchestrator:

- **GatewayCore**: Central orchestrator managing plugin lifecycle, protocol adapters, and configuration
- **PluginRegistry**: Discovers, loads, and manages plugins with dependency injection
- **ProtocolAdapterManager**: Manages protocol adapters as specialized plugins
- **Plugin System**: Extensible architecture allowing custom middleware, adapters, and services

### 2. Protocol Adapters (Plugin-Based)

Protocol adapters are implemented as plugins managed by the ProtocolAdapterManager:

- **REST Adapter**: HTTP/JSON interface integrated with FastAPI
  - Domain-based routing (`/api/v1/users/`, `/api/v1/admin/`, `/api/v1/logs/`)
  - OpenAPI 3.1 documentation and validation
  - Unified port design (single port 8771)

- **WebSocket Adapter**: Real-time bidirectional communication
  - Persistent connections for UI updates
  - Connection lifecycle management via plugin system
  - Message framing and serialization

- **ZeroMQ Adapter**: High-performance local communication
  - Cross-platform IPC transport with TCP fallback
  - Message bus integration for internal communication
  - Protocol Buffers for binary serialization

### 2. Domain-Based API Organization

The API Gateway organizes endpoints using a **domain-based module-functionality** pattern for improved maintainability and scalability:

- **Domain Separation**: Business functionality grouped by domain (users, admin, conversations, health)
- **Self-Contained Modules**: Each domain contains its own routers, schemas, dependencies, and exceptions
- **Consistent Structure**: Standardized file patterns across all domains following FastAPI best practices
- **Clean Architecture**: Clear separation between API layer, business logic, and infrastructure

**API Structure**:
```
api/
├── users/          # User management domain
│   ├── router.py   # User API endpoints
│   ├── schemas.py  # Pydantic request/response models
│   ├── dependencies.py  # User-specific auth and validation
│   └── exceptions.py    # User-specific error handling
├── admin/          # Administrative domain
│   ├── router.py   # Admin API endpoints
│   ├── schemas.py  # Admin Pydantic models
│   ├── dependencies.py  # Admin authentication
│   └── exceptions.py    # Admin-specific errors
├── conversations/ # Conversation management domain
└── health/        # System health and monitoring
```

This organization provides:
- **Scalability**: Easy addition of new domains (personality, emotion, etc.)
- **Maintainability**: Related functionality grouped together
- **Team Collaboration**: Clear ownership boundaries
- **Professional Standards**: Follows established FastAPI patterns

### 3. Middleware Stack (Plugin-Based)

The gateway implements a comprehensive middleware stack as plugins:

- **Encryption Middleware**: ASGI-level encryption wrapping the entire FastAPI app
  - Transparent encryption/decryption for all endpoints
  - Key management integration with `AICOKeyManager`
  - Unencrypted endpoint handling for health checks and handshake

- **Authentication Plugin**: JWT token validation and session management
  - Integration with backend authentication manager
  - Admin role enforcement for privileged endpoints
  - Device pairing and trust establishment

- **Rate Limiting Plugin**: Traffic management and abuse prevention
  - Per-client rate limiting with configurable policies
  - Graduated response to excessive requests
  - Integration with security monitoring

- **Request Logging Plugin**: Comprehensive request/response logging
  - Structured logging via Protocol Buffers
  - ZMQ transport to log consumer service
  - Performance metrics and audit trails

### 4. Core Services Integration

- **Message Bus Integration**: ZeroMQ-based internal communication
  - Protocol Buffers for high-performance binary serialization
  - Topic-based pub/sub for module communication
  - Log transport pipeline to database persistence

- **Database Connection Sharing**: Unified database access
  - Shared `EncryptedLibSQLConnection` across all plugins
  - Connection pooling and lifecycle management
  - Encrypted storage with key derivation

- **Configuration Management**: Centralized configuration system
  - YAML-based configuration with schema validation
  - Plugin-specific configuration sections
  - Runtime configuration updates

- **Process Management**: Service lifecycle coordination
  - PID file management for CLI integration
  - Graceful shutdown with signal handling
  - Background task coordination

### 5. Roaming and Federation Support

- **Device Registry**: Manages connected frontend devices
  - Tracks active connections and their capabilities
  - Maintains device trust relationships
  - Supports device capability discovery
  - Interfaces with the libSQL device registry database

- **Connection Manager**: Handles different connection modes
  - Local IPC connections for coupled mode
  - Secure network connections for detached mode
  - P2P connections for federated device communication
  - Automatic protocol selection based on deployment

- **Trust Establishment**: Manages secure device pairing
  - Implements secure pairing protocols
  - Manages trusted device certificates
  - Handles key exchange for secure communication
  - Supports device authorization and revocation

- **Federated Sync Gateway**: Facilitates device-to-device synchronization
  - Implements P2P encrypted mesh communication
  - Supports selective sync policies for different data types
  - Provides device discovery via mDNS/Bonjour and DHT
  - Handles conflict detection and resolution strategies

## Communication Patterns

### Local (Coupled) Mode

In coupled mode, where frontend and backend run on the same device:

1. API Gateway uses ZeroMQ's cross-platform IPC transport with automatic fallback:
   - Primary: ZeroMQ IPC using platform-appropriate mechanisms
   - Fallback: Localhost REST/WebSocket when IPC is unavailable
   - Automatic detection and switching between transport methods
   - Consistent API regardless of transport mechanism
2. Authentication leverages the device's security boundary
3. Communication remains encrypted but avoids network overhead
4. Connection manager optimizes for local performance

```
┌────────────┐      Local IPC      ┌────────────┐      ZeroMQ      ┌────────────┐
│  Frontend  │ ─────────────────── │ API Gateway│ ─────────────────│  Backend   │
│  (Flutter) │                     │            │                   │  Services  │
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

### Current Technology Stack

- **Core Framework**: FastAPI with ASGI middleware architecture
- **Plugin System**: Custom plugin registry with dependency injection
- **Security**: 
  - `AICOKeyManager` for key derivation and session management
  - ASGI-level encryption middleware
  - JWT authentication with admin role enforcement
- **Message Bus**: ZeroMQ with Protocol Buffers
  - Binary serialization for performance
  - Topic-based routing (`logs.*`, `events.*`)
  - Log consumer service for database persistence
- **Database**: Encrypted libSQL with shared connection pooling
- **Process Management**: 
  - Signal-based graceful shutdown
  - PID file management
  - Background task coordination
- **Configuration**: YAML-based with schema validation
- **Logging**: Structured logging with ZMQ transport pipeline

### Request Flow

#### Plugin-Based Request Processing

The current implementation uses a plugin-based middleware stack:

1. **ASGI Encryption Middleware**: Wraps entire FastAPI app
   - Handles encryption/decryption transparently
   - Manages unencrypted endpoints (health, handshake)
   - Key derivation and session management

2. **FastAPI Application**: Domain-based routing
   - `/api/v1/users/` - User management endpoints
   - `/api/v1/admin/` - Administrative endpoints  
   - `/api/v1/logs/` - Log management endpoints
   - `/api/v1/health` - System health checks

3. **Plugin Middleware Stack**: Applied via plugin system
   - Authentication validation (JWT tokens)
   - Rate limiting and abuse prevention
   - Request logging and metrics
   - Authorization enforcement

4. **Backend Integration**: Via shared services
   - Database connection sharing
   - Message bus communication
   - Configuration management
   - Process lifecycle coordination

#### Local Client Flow (Adaptive Transport)

1. Local client attempts connection via preferred transport:
   - First attempt: ZeroMQ IPC for optimal performance
   - Fallback: Localhost REST/WebSocket if IPC unavailable
2. Transport negotiation occurs automatically
3. Client sends message using negotiated transport (already in correct format)
4. Authentication uses local security context
5. Authorization enforcer checks access permissions
6. Request validator ensures message meets schema requirements
7. Message is routed directly to the internal message bus (zero transformation)
8. Response is received from message bus
9. Response is sent back through the negotiated transport (zero transformation)

## Security Considerations

### Authentication

- **Token-based**: JWT tokens for REST and WebSocket authentication
- **Certificate-based**: Mutual TLS for secure device communication
- **Device Pairing**: Secure pairing protocol for establishing trust

### Authorization

- **Role-based**: Access control based on user roles
- **Capability-based**: Fine-grained permissions for sensitive operations
- **Context-aware**: Authorization decisions consider request context

### Data Protection

- **In Transit**: All communications encrypted using TLS 1.3
- **At Rest**: All persistent data encrypted using gocryptfs (AES-256-GCM)
- **Key Management**: Secure key derivation with Argon2id and platform keyrings

## Rationale

The API Gateway architecture is designed to provide:

1. **Simplicity**: A single, unified entry point simplifies client integration
2. **Security**: Centralized security enforcement ensures consistent policy application
3. **Flexibility**: Multi-protocol support accommodates various client needs
4. **Scalability**: Decoupled design allows independent scaling of components
5. **Roaming Support**: Architecture works seamlessly in both coupled and detached modes
6. **Federation Support**: Facilitates secure P2P communication in the federated device network
7. **Selective Sync**: Enables different synchronization policies for various data types
8. **Cross-Platform Compatibility**: Works across desktop, mobile, and embedded platforms

This design aligns with AICO's core principles of local-first processing, privacy-focused security, flexible deployment across different device types, and federated device networking while maintaining a clean separation between frontend and backend components.
