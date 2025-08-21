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

- **REST API (HTTP/JSON)**: Foundation protocol for stateful operations requiring confirmation
- **WebSocket (JSON)**: Real-time bidirectional communication for live updates and notifications  
- **ZeroMQ IPC (JSON)**: High-performance local communication for coupled deployments

System automatically selects optimal protocol: IPC for local (lowest latency), WebSocket for real-time, HTTP for reliability.

### Security Architecture

- **JWT Authentication**: Stateless token-based security across all protocols with automatic refresh
- **RBAC**: Granular permissions mapping user roles to specific endpoints and operations
- **Transport Security**: TLS encryption for network, OS-level security for IPC
- **Zero-Effort Security**: Transparent operation using platform-native secure storage

## Frontend Integration

### Architectural Patterns

- **Repository Pattern**: Abstracts data access behind clean interfaces, enabling testing and offline-first design
- **Adapter Pattern**: Protocol-specific clients implement common interfaces for uniform transport handling
- **Observer Pattern**: Real-time updates through reactive streams for automatic UI synchronization
- **Command Pattern**: User actions as queueable commands supporting offline operation

### Repository Implementation

Abstract repository interfaces define domain contracts while concrete implementations handle protocol-specific details. Repositories provide consistent data access regardless of transport mechanism.

```dart
abstract class ChatRepository {
  Stream<Message> get messageStream;
  Future<void> sendMessage(Message message);
}

class ApiChatRepository implements ChatRepository {
  // Optimistic updates with error handling
  Future<void> sendMessage(Message message) async {
    _messageController.add(message.copyWith(status: sending));
    try {
      final response = await _apiClient.post('/messages', data: message.toJson());
      _messageController.add(Message.fromJson(response.data));
    } catch (e) {
      _messageController.add(message.copyWith(status: failed));
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
  Future<void> establishConnection() async {
    try {
      if (_ipcClient != null) {
        await _ipcClient!.connect();
        _currentMode = ConnectionMode.ipc;
        return;
      }
    } catch (e) {
      // Fallback to WebSocket/HTTP
    }
    
    try {
      await _wsClient.connect();
      _currentMode = ConnectionMode.websocket;
    } catch (e) {
      _currentMode = ConnectionMode.http;
    }
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
