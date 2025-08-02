# API Gateway Architecture

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

### 1. Protocol Adapters

The API Gateway implements multiple protocol adapters to support various client communication patterns:

- **REST Adapter**: HTTP/JSON interface for standard request-response interactions
  - Supports standard CRUD operations
  - Uses OpenAPI 3.1 for documentation and validation
  - Handles request/response transformation

- **WebSocket Adapter**: Bidirectional communication for real-time interactions
  - Supports persistent connections for UI updates
  - Handles connection lifecycle management
  - Provides message framing and serialization

- **ZeroMQ IPC Adapter**: Cross-platform local inter-process communication
  - Uses ZeroMQ's native IPC transport (Unix sockets on Unix/Linux/macOS, named pipes on Windows)
  - Provides high-performance, low-latency local communication
  - Maintains consistent API across all platforms
  - Supports various messaging patterns (request-reply, pub-sub, push-pull)
  - Automatically falls back to localhost TCP when IPC is unavailable

- **gRPC Adapter** (Optional): High-performance binary protocol
  - Supports streaming communication patterns
  - Provides efficient binary serialization
  - Enables strong typing through Protocol Buffers

### 2. Core Gateway Services

- **Request Router**: Maps external endpoints to internal message bus topics
  - Handles URL routing for REST requests
  - Maps WebSocket events to appropriate handlers
  - Translates gRPC service methods to internal commands

- **Message Normalizer**: Standardizes all messages to a unified format
  - Uses a common message schema across all protocols
  - Minimal transformation between external and internal formats
  - Leverages Protocol Buffers as the canonical message definition

- **Response Aggregator**: Combines results from multiple backend services when needed
  - Supports request fan-out and response aggregation
  - Handles timeouts and partial responses
  - Manages response transformation back to client format

### 3. Security Layer

- **Authentication Handler**: Verifies client identity
  - JWT token validation for REST and WebSocket
  - Certificate validation for mutual TLS
  - Device pairing validation for trusted devices

- **Authorization Enforcer**: Enforces access control policies
  - Role-based access control for API endpoints
  - Capability-based security for sensitive operations
  - Context-aware authorization decisions

- **Request Validator**: Ensures requests meet schema and security requirements
  - Schema validation for all incoming requests
  - Input sanitization and normalization
  - Protection against common attack vectors

- **Rate Limiter**: Prevents abuse through traffic management
  - Per-client rate limiting
  - Graduated response to excessive requests
  - Configurable limits based on endpoint sensitivity

### 4. Roaming and Federation Support

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

### Technology Stack

- **Core Framework**: Python with FastAPI for REST and WebSocket support
- **gRPC Support**: gRPC Python with gRPC API Gateway for protocol translation
- **Security**: PyJWT for token handling, Python-TLS for mutual TLS
- **Message Bus Integration**: ZeroMQ with CurveZMQ for secure messaging
- **P2P Communication**: libp2p for peer-to-peer networking and DHT
- **Local Discovery**: mDNS/Bonjour for same-network device discovery
- **Data Synchronization**: Merkle tree-based change detection and CRDTs
- **Cross-Platform Communication**: Adaptive transport layer
  - Primary: ZeroMQ's native IPC transport for optimal performance
  - Fallback: Localhost HTTP/WebSocket for restricted environments
  - Automatic transport negotiation at connection time
  - Consistent API regardless of underlying transport
  - Supports secure communication with CurveZMQ or TLS
- **Unified Message Schema**: Protocol Buffers for consistent message definitions
  - Single source of truth for all message types
  - Automatic code generation for multiple languages
  - Versioning support for backward compatibility

### Request Flow

#### Unified Message Approach

To simplify message handling and reduce translation overhead, we use a unified message schema approach:

1. All messages (external and internal) share a common schema defined in Protocol Buffers
2. Frontend libraries provide native language bindings that match the schema
3. Protocol adapters handle only transport concerns, not message transformation
4. Message structure remains consistent throughout the system

#### External Client Flow (REST/WebSocket/gRPC)

1. Client sends request through external protocol (REST/WebSocket/gRPC)
2. Protocol adapter extracts the message payload (minimal transformation)
3. Authentication handler verifies client identity
4. Authorization enforcer checks access permissions
5. Request validator ensures request meets schema requirements
6. Rate limiter checks for request quota
7. Request router maps to appropriate internal message topic
8. Request is published directly to the message bus (no format conversion)
9. Response is received from message bus
10. Response is wrapped in appropriate protocol envelope (minimal transformation)
11. Response is sent back to client

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
