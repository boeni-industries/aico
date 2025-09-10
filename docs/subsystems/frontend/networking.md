# AICO Frontend Networking Client

## Architecture Overview

AICO's networking client provides a unified interface for communicating with the backend API Gateway across multiple protocols. The architecture prioritizes type safety, maintainability, and offline-first user experience while supporting REST, WebSocket, and future IPC communication.

The design follows a **layered approach** where high-level repositories abstract protocol details from business logic, while specialized clients handle the technical aspects of each communication method. This separation ensures the UI layer remains protocol-agnostic and testable.

## Core Structure

The networking layer is organized into focused modules within `lib/networking/`:

- **Clients**: Protocol-specific implementations (REST, WebSocket, IPC)
- **Interceptors**: Cross-cutting concerns like authentication and retry logic  
- **Models**: Shared data structures and error handling
- **Services**: Higher-level coordination like connection management and offline queuing

```
lib/networking/
├── clients/          # Protocol implementations
├── interceptors/     # Cross-cutting concerns
├── models/          # Shared data structures
└── services/        # Coordination layer
```

## Unified API Client

The frontend uses a **UnifiedApiClient** that intelligently routes requests between encrypted and unencrypted endpoints. This approach provides transparent encryption, automatic protocol selection, and robust error handling while maintaining a simple interface for the application layer.

The client combines **Dio** for primary HTTP communication with the standard **http** package as a fallback, ensuring maximum reliability across different network conditions and deployment scenarios.

Key features include automatic encryption detection, JWT token management, handshake protocol handling, and seamless fallback between transport mechanisms.

```dart
class UnifiedApiClient {
  final Dio _dio;
  final http.Client _httpClient;
  final EncryptionService _encryptionService;
  
  // Smart request routing based on endpoint encryption requirements
  Future<T> request<T>(
    String method,
    String endpoint, {
    Map<String, dynamic>? data,
    T Function(Map<String, dynamic>)? fromJson,
  }) async {
    final needsEncryption = _requiresEncryption(endpoint);
    
    if (needsEncryption) {
      // Handle encrypted endpoints with handshake protocol
      final encryptedPayload = data != null ? 
        _encryptionService.encryptPayload(data) : null;
      // ... encryption logic
    } else {
      // Use plain HTTP for public endpoints
      // ... standard HTTP logic
    }
  }
}
```

## WebSocket Client

WebSocket communication enables real-time features like live updates and bidirectional messaging. The client manages connection lifecycle, automatic reconnection, and message queuing during disconnections.

The implementation uses `IOWebSocketChannel` for robust connection handling and maintains an internal message queue to ensure no data is lost during temporary network issues. Messages are JSON-encoded for consistency with the REST API format.

Connection resilience is critical for user experience - the client automatically attempts reconnection with exponential backoff and queues outgoing messages until the connection is restored.

## Connection Management

### Current Implementation Status

**Implemented Protocols**:
- ✅ **HTTP/REST**: Primary protocol via Dio with comprehensive error handling
- ✅ **HTTP Fallback**: Secondary client using `http` package for reliability
- ⚠️ **WebSocket**: Basic implementation with limited functionality
- ❌ **ZeroMQ IPC**: Planned for future implementation

**Smart Protocol Selection**: The `UnifiedApiClient` currently focuses on HTTP reliability with dual client architecture rather than multi-protocol switching. Future versions will implement the full adaptive transport layer.

```dart
class ConnectionManager {
  // Current: Basic WebSocket + HTTP
  // Future: Full adaptive transport with IPC support
  Future<void> establishConnection() async {
    // Phase 1: HTTP-first approach (current)
    await _establishHttpConnection();
    
    // Phase 2: WebSocket enhancement (in progress)
    if (_wsClient.isAvailable) {
      await _wsClient.connect();
    }
    
    // Phase 3: IPC integration (planned)
    // if (_ipcClient.isAvailable) {
    //   await _ipcClient.connect();
    // }
  }
}
```

## Authentication & Security

Authentication is handled transparently through **interceptors** that automatically attach JWT tokens to outgoing requests. The system manages token lifecycle including automatic refresh when tokens expire, ensuring users never experience authentication interruptions.

When a token expires during a request, the interceptor automatically attempts to refresh it and retries the original request seamlessly. This provides a smooth user experience while maintaining security through short-lived tokens.

All authentication state is managed centrally, with secure token storage following platform best practices. The interceptor pattern ensures authentication logic is applied consistently across all API calls without requiring manual token management in business logic.
```

## Repository Pattern

The **repository pattern** provides a clean abstraction between business logic and network implementation. Repositories define domain-focused interfaces that hide protocol complexity, making the codebase more maintainable and testable.

Each repository handles data operations for a specific domain (users, admin, health) and can switch between different transport protocols transparently. This separation allows the UI layer to work with domain objects rather than network responses.

Repositories also coordinate **offline-first behavior** by implementing optimistic updates and operation queuing. When network requests fail, operations are queued for later execution while providing immediate feedback to users through optimistic UI updates.
```

## Offline-First Architecture

The networking client prioritizes **user experience over network reliability** through comprehensive offline support. When network operations fail, the system provides immediate optimistic feedback while queuing operations for background execution.

Operations are persisted locally and automatically retried when connectivity returns. This ensures users can continue working seamlessly regardless of network conditions, with changes synchronized transparently in the background.

The offline queue implements intelligent retry logic with exponential backoff and conflict resolution. Failed operations are preserved across app restarts, ensuring no user data is lost due to temporary network issues.
```

## Implementation Status & Roadmap

### ✅ **Completed (Phase 1)**
- **UnifiedApiClient**: Intelligent encrypted/unencrypted endpoint routing
- **Dual HTTP Architecture**: Dio primary + http package fallback
- **JWT Authentication**: Automatic token refresh and secure storage
- **Encryption Layer**: E2E encryption with handshake protocol
- **Error Handling**: Comprehensive error classification and recovery

### 🔄 **In Progress (Phase 2)**
- **WebSocket Enhancement**: Expanding real-time communication capabilities
- **Connection Resilience**: Improved reconnection and failure handling
- **Repository Pattern**: Completing domain-specific repository implementations

### 📋 **Planned (Phase 3+)**
- **ZeroMQ IPC**: High-performance local communication
- **Adaptive Transport**: Automatic protocol selection and failover
- **Advanced Offline**: Operation queuing and conflict resolution
- **Performance Optimization**: Connection pooling and request batching

## Key Benefits

### **Current Implementation**
- ✅ **Security-First**: Automatic encryption for sensitive endpoints
- ✅ **Reliability**: Dual HTTP client architecture with intelligent fallback
- ✅ **Maintainability**: Clean separation between transport and business logic
- ✅ **Testability**: Service locator pattern enables easy mocking
- ✅ **Performance**: Dio interceptors, connection pooling, and request optimization
- ✅ **Developer Experience**: Unified API with automatic error handling

### **Future Enhancements**
- 🔄 **Multi-Protocol**: WebSocket and IPC integration
- 🔄 **Offline-First**: Operation queuing and optimistic updates
- 📋 **Type Safety**: Enhanced compile-time safety via code generation
- 📋 **Adaptive Transport**: Intelligent protocol selection and failover
