---
title: API Integration Patterns
---

# API Integration Patterns

## Overview

AICO's frontend integrates with the backend through multi-protocol API Gateway supporting REST, WebSocket, and ZeroMQ IPC. The thin client paradigm keeps presentation in frontend while backend handles AI processing, data persistence, and business logic.

## Design Philosophy

**Protocol Agnosticism**: Frontend abstracts transport details, enabling seamless transitions between deployment modes without application changes.

**Graceful Degradation**: Automatic fallback from IPC to WebSocket to HTTP ensures continuous functionality.

**Optimistic UX**: Immediate visual feedback while operations complete asynchronously maintains responsiveness.

**Resilient Communication**: Network failures are normal conditions handled through retry logic, connection management, and offline queuing.

### Communication Protocols

**Currently Implemented**:
- **REST API (HTTP/JSON)**: Primary protocol via Dio with comprehensive error handling and encryption support
- **HTTP Fallback**: Secondary client using `http` package for maximum reliability
- **WebSocket (JSON)**: Basic real-time communication (limited implementation)

**Planned for Future**:
- **ZeroMQ IPC (JSON)**: High-performance local communication for coupled deployments

**Current Protocol Selection**: The system uses HTTP-first approach with dual client architecture. Future versions will implement automatic protocol selection: IPC for local (lowest latency), WebSocket for real-time, HTTP for reliability.

### Security Architecture

- **End-to-End Encryption**: Automatic encryption for sensitive endpoints using X25519 + XSalsa20Poly1305
- **JWT Authentication**: Stateless token-based security with automatic refresh and secure storage
- **Handshake Protocol**: Secure session establishment with perfect forward secrecy
- **Platform Integration**: Native Keychain/Credential Manager for secure key storage
- **Smart Routing**: Automatic detection of encrypted vs unencrypted endpoints
- **Zero-Effort Security**: Transparent operation with comprehensive error handling

## Frontend Integration

### Architectural Patterns

- **Repository Pattern**: Abstracts data access behind clean interfaces, enabling testing and offline-first design
- **Adapter Pattern**: Protocol-specific clients implement common interfaces for uniform transport handling
- **Observer Pattern**: Real-time updates through reactive streams for automatic UI synchronization
- **Command Pattern**: User actions as queueable commands supporting offline operation

### Repository Implementation

Abstract repository interfaces define domain contracts while concrete implementations handle protocol-specific details. Repositories provide consistent data access regardless of transport mechanism.

```dart
abstract class ConversationRepository {
  Stream<Message> get messageStream;
  Future<void> sendMessage(Message message);
}

class ApiConversationRepository implements ConversationRepository {
  final UnifiedApiClient _apiClient;
  final StreamController<Message> _messageController = StreamController.broadcast();
  
  // Optimistic updates with automatic encryption
  Future<void> sendMessage(Message message) async {
    _messageController.add(message.copyWith(status: MessageStatus.sending));
    try {
      // UnifiedApiClient automatically handles encryption for /messages endpoint
      final response = await _apiClient.post<Map<String, dynamic>>(
        '/messages', 
        message.toJson(),
        fromJson: (json) => json,
      );
      _messageController.add(Message.fromJson(response));
    } catch (e) {
      _messageController.add(message.copyWith(status: MessageStatus.failed));
      rethrow;
    }
  }
}
```

### Protocol Clients

Each client handles transport-specific characteristics and failure modes:

- **HTTP Client**: Request-response with automatic token refresh and interceptor-based authentication
- **WebSocket Client**: Persistent connections with heartbeat, reconnection, and message queuing
- **IPC Client**: Local communication with minimal overhead and HTTP fallback

## Connection Management

### Adaptive Transport Layer
System attempts connections in preference order: IPC (local), WebSocket (real-time), HTTP (reliable). Intelligent failover analyzes failure types for informed protocol switching.

```dart
class ConnectionManager {
  final UnifiedApiClient _apiClient;
  final WebSocketClient _wsClient;
  ConnectionMode _currentMode = ConnectionMode.http;
  
  Future<void> establishConnection() async {
    // Phase 1: Initialize encryption for HTTP
    try {
      await _apiClient.initializeEncryption();
      _currentMode = ConnectionMode.http;
      debugPrint('✅ HTTP connection with encryption established');
    } catch (e) {
      debugPrint('⚠️ Encryption failed, using unencrypted HTTP: $e');
      _currentMode = ConnectionMode.httpFallback;
    }
    
    // Phase 2: Enhance with WebSocket (if available)
    try {
      await _wsClient.connect();
      _currentMode = ConnectionMode.websocket;
      debugPrint('✅ WebSocket connection established');
    } catch (e) {
      debugPrint('⚠️ WebSocket unavailable, using HTTP: $e');
    }
    
    // Phase 3: Future IPC integration
    // if (_ipcClient?.isAvailable == true) {
    //   await _ipcClient!.connect();
    //   _currentMode = ConnectionMode.ipc;
    // }
  }
}
```

## Error Handling

### Error Classification and Recovery
Errors are normal operating conditions handled through user-centric messaging, graceful degradation, and automatic recovery.

- **Network Errors**: Automatic retry with exponential backoff
- **Authentication Errors**: Transparent token refresh and retry
- **Server Errors**: Circuit breaker pattern prevents cascading failures
- **Validation Errors**: Immediate user feedback with correction guidance

## Offline Support

### Local-First Operations
User actions receive immediate local updates with background synchronization. Operation queue persists pending actions during offline periods.

- **Optimistic Updates**: Immediate UI feedback while operations complete asynchronously
- **Conflict Resolution**: Last-write-wins with user notification for critical data
- **Secure Offline**: Platform-native token storage enables offline operations with automatic validation on reconnection

## Data Models

### Serialization Strategy
JSON serialization provides human-readable, cross-platform compatibility. Strong typing with code generation ensures compile-time safety while supporting schema evolution through API versioning.

```dart
@freezed
class Message with _$Message {
  const factory Message({
    required String id,
    required String content,
    required DateTime timestamp,
    MessageStatus? status,
  }) = _Message;

  factory Message.fromJson(Map<String, dynamic> json) => _$MessageFromJson(json);
}
```

## Testing & Future Considerations

### Integration Testing
Multi-protocol testing validates consistent behavior across HTTP, WebSocket, and IPC transports. Failure scenario testing ensures reliable error handling and recovery mechanisms.

### Evolution Readiness
- **Protocol Extensibility**: Adapter pattern supports new transport protocols
- **Microservices Ready**: Domain-based organization enables backend decomposition
- **Performance Optimization**: Future binary protocols for high-frequency operations
- **Cross-Platform**: Clean separation supports easy platform expansion

This architecture ensures robust, performant communication supporting offline operation, multiple protocols, and comprehensive error handling while maintaining conceptual clarity for future evolution.
