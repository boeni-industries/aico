---
title: API Integration Patterns
---

# API Integration Patterns

## Overview

AICO's frontend integrates with the backend through a multi-protocol API Gateway that supports REST, WebSocket, and ZeroMQ IPC communication. The integration follows the thin client paradigm, with the frontend handling presentation while the backend manages all AI processing, data persistence, and business logic.

## Backend Architecture Context

### API Gateway Structure
The backend implements a domain-based API organization with the following structure:
- **Users Domain**: User management and authentication
- **Admin Domain**: Administrative functions and system management
- **Conversations Domain**: Chat and interaction management
- **Health Domain**: System monitoring and status

### Communication Protocols
- **REST API**: Standard HTTP/JSON for commands and queries
- **WebSocket**: Real-time bidirectional communication for live updates
- **ZeroMQ IPC**: High-performance local inter-process communication (coupled mode)
- **gRPC**: Optional high-performance binary protocol for advanced use cases

### Security Architecture
- **JWT Authentication**: Token-based authentication for REST and WebSocket
- **Role-based Access Control**: Granular permissions for different user types
- **Mutual TLS**: Certificate-based authentication for device communication
- **Request Validation**: Schema validation and input sanitization

## Frontend Integration Architecture

### Repository Pattern Implementation

#### Abstract Repository Interfaces
```dart
// Domain-agnostic repository contracts
abstract class ChatRepository {
  Stream<Message> get messageStream;
  Future<List<Message>> getConversationHistory({String? conversationId});
  Future<void> sendMessage(Message message);
  Future<void> markMessageAsRead(String messageId);
}

abstract class UserRepository {
  Future<User> getCurrentUser();
  Future<void> updateUserPreferences(UserPreferences preferences);
  Future<List<FamilyMember>> getFamilyMembers();
}

abstract class SystemRepository {
  Stream<SystemStatus> get statusStream;
  Future<SystemHealth> getSystemHealth();
  Future<void> requestSystemUpdate();
}
```

#### Concrete API Implementation
```dart
// REST + WebSocket implementation
class ApiChatRepository implements ChatRepository {
  final ApiClient _apiClient;
  final WebSocketClient _wsClient;
  final StreamController<Message> _messageController;

  @override
  Stream<Message> get messageStream => _messageController.stream;

  @override
  Future<List<Message>> getConversationHistory({String? conversationId}) async {
    final response = await _apiClient.get(
      '/conversations/${conversationId ?? 'current'}/messages',
    );
    return response.data.map<Message>((json) => Message.fromJson(json)).toList();
  }

  @override
  Future<void> sendMessage(Message message) async {
    // Optimistic update
    _messageController.add(message.copyWith(status: MessageStatus.sending));
    
    try {
      final response = await _apiClient.post(
        '/conversations/messages',
        data: message.toJson(),
      );
      
      // Update with server response
      final serverMessage = Message.fromJson(response.data);
      _messageController.add(serverMessage);
    } catch (e) {
      // Handle error and update message status
      _messageController.add(message.copyWith(status: MessageStatus.failed));
      rethrow;
    }
  }
}
```

### Protocol-Specific Clients

#### REST API Client
```dart
class ApiClient {
  final Dio _dio;
  final TokenManager _tokenManager;

  ApiClient({required String baseUrl}) : _dio = Dio(BaseOptions(baseUrl: baseUrl)) {
    _setupInterceptors();
  }

  void _setupInterceptors() {
    // Authentication interceptor
    _dio.interceptors.add(InterceptorsWrapper(
      onRequest: (options, handler) async {
        final token = await _tokenManager.getToken();
        if (token != null) {
          options.headers['Authorization'] = 'Bearer $token';
        }
        handler.next(options);
      },
      onError: (error, handler) async {
        if (error.response?.statusCode == 401) {
          await _tokenManager.refreshToken();
          // Retry request with new token
          final newToken = await _tokenManager.getToken();
          error.requestOptions.headers['Authorization'] = 'Bearer $newToken';
          final response = await _dio.fetch(error.requestOptions);
          handler.resolve(response);
        } else {
          handler.next(error);
        }
      },
    ));

    // Request/Response logging
    _dio.interceptors.add(LogInterceptor(
      requestBody: true,
      responseBody: true,
      logPrint: (object) => debugPrint(object.toString()),
    ));
  }

  Future<Response<T>> get<T>(String path, {Map<String, dynamic>? queryParameters}) {
    return _dio.get<T>(path, queryParameters: queryParameters);
  }

  Future<Response<T>> post<T>(String path, {dynamic data}) {
    return _dio.post<T>(path, data: data);
  }
}
```

#### WebSocket Client
```dart
class WebSocketClient {
  WebSocketChannel? _channel;
  final StreamController<Map<String, dynamic>> _messageController;
  final String _baseUrl;
  Timer? _heartbeatTimer;
  Timer? _reconnectTimer;

  Stream<Map<String, dynamic>> get messageStream => _messageController.stream;

  Future<void> connect() async {
    try {
      final token = await _tokenManager.getToken();
      final wsUrl = _baseUrl.replaceFirst('http', 'ws');
      
      _channel = WebSocketChannel.connect(
        Uri.parse('$wsUrl/ws?token=$token'),
      );

      _channel!.stream.listen(
        (data) {
          final message = json.decode(data) as Map<String, dynamic>;
          _messageController.add(message);
        },
        onError: (error) => _handleConnectionError(error),
        onDone: () => _handleConnectionClosed(),
      );

      _startHeartbeat();
    } catch (e) {
      _scheduleReconnect();
    }
  }

  void send(Map<String, dynamic> message) {
    if (_channel != null) {
      _channel!.sink.add(json.encode(message));
    }
  }

  void _startHeartbeat() {
    _heartbeatTimer = Timer.periodic(Duration(seconds: 30), (_) {
      send({'type': 'ping', 'timestamp': DateTime.now().toIso8601String()});
    });
  }

  void _scheduleReconnect() {
    _reconnectTimer = Timer(Duration(seconds: 5), () => connect());
  }
}
```

#### ZeroMQ IPC Client (Local Mode)
```dart
class ZmqIpcClient {
  late zmq.Socket _socket;
  final String _endpoint;
  bool _isConnected = false;

  ZmqIpcClient({required String endpoint}) : _endpoint = endpoint;

  Future<void> connect() async {
    try {
      _socket = zmq.Socket(zmq.SocketType.req);
      await _socket.connect(_endpoint);
      _isConnected = true;
    } catch (e) {
      // Fallback to HTTP if IPC fails
      throw IpcConnectionException('Failed to connect via IPC: $e');
    }
  }

  Future<Map<String, dynamic>> request(Map<String, dynamic> message) async {
    if (!_isConnected) await connect();
    
    final messageBytes = utf8.encode(json.encode(message));
    await _socket.send(messageBytes);
    
    final responseBytes = await _socket.receive();
    final responseString = utf8.decode(responseBytes);
    return json.decode(responseString) as Map<String, dynamic>;
  }
}
```

## Connection Management

### Adaptive Transport Layer
```dart
class ConnectionManager {
  final ApiClient _apiClient;
  final WebSocketClient _wsClient;
  final ZmqIpcClient? _ipcClient;
  
  ConnectionMode _currentMode = ConnectionMode.detecting;
  
  Future<void> establishConnection() async {
    // Try IPC first for local connections
    if (_ipcClient != null) {
      try {
        await _ipcClient!.connect();
        _currentMode = ConnectionMode.ipc;
        return;
      } catch (e) {
        debugPrint('IPC connection failed, falling back to HTTP: $e');
      }
    }
    
    // Fallback to HTTP/WebSocket
    try {
      await _wsClient.connect();
      _currentMode = ConnectionMode.websocket;
    } catch (e) {
      debugPrint('WebSocket connection failed: $e');
      _currentMode = ConnectionMode.http;
    }
  }
  
  Future<T> sendRequest<T>(ApiRequest request) async {
    switch (_currentMode) {
      case ConnectionMode.ipc:
        return await _sendViaIpc<T>(request);
      case ConnectionMode.websocket:
        return await _sendViaWebSocket<T>(request);
      case ConnectionMode.http:
        return await _sendViaHttp<T>(request);
      default:
        throw ConnectionException('No valid connection available');
    }
  }
}
```

### Connection State Management
```dart
class ConnectionBloc extends HydratedBloc<ConnectionEvent, ConnectionState> {
  final ConnectionManager _connectionManager;
  Timer? _healthCheckTimer;

  @override
  Stream<ConnectionState> mapEventToState(ConnectionEvent event) async* {
    if (event is ConnectRequested) {
      yield ConnectionState.connecting();
      
      try {
        await _connectionManager.establishConnection();
        yield ConnectionState.connected(
          mode: _connectionManager.currentMode,
          connectedAt: DateTime.now(),
        );
        _startHealthChecks();
      } catch (e) {
        yield ConnectionState.disconnected(reason: e.toString());
        _scheduleReconnect();
      }
    }
  }

  void _startHealthChecks() {
    _healthCheckTimer = Timer.periodic(Duration(seconds: 30), (_) async {
      try {
        await _connectionManager.healthCheck();
      } catch (e) {
        add(ConnectionLost(reason: e.toString()));
      }
    });
  }
}
```

## Data Models and Serialization

### Message Models
```dart
// Conversation message model
@freezed
class Message with _$Message {
  const factory Message({
    required String id,
    required String content,
    required MessageType type,
    required String senderId,
    required DateTime timestamp,
    MessageStatus? status,
    Map<String, dynamic>? metadata,
  }) = _Message;

  factory Message.fromJson(Map<String, dynamic> json) => _$MessageFromJson(json);
}

// System status model
@freezed
class SystemStatus with _$SystemStatus {
  const factory SystemStatus({
    required bool isHealthy,
    required String version,
    required DateTime timestamp,
    required Map<String, ServiceStatus> services,
  }) = _SystemStatus;

  factory SystemStatus.fromJson(Map<String, dynamic> json) => _$SystemStatusFromJson(json);
}
```

### API Response Handling
```dart
// Standardized API response wrapper
@freezed
class ApiResponse<T> with _$ApiResponse<T> {
  const factory ApiResponse.success({
    required T data,
    String? message,
  }) = ApiSuccess<T>;

  const factory ApiResponse.error({
    required String message,
    String? code,
    Map<String, dynamic>? details,
  }) = ApiError<T>;

  factory ApiResponse.fromJson(
    Map<String, dynamic> json,
    T Function(Object?) fromJsonT,
  ) {
    if (json['success'] == true) {
      return ApiResponse.success(
        data: fromJsonT(json['data']),
        message: json['message'],
      );
    } else {
      return ApiResponse.error(
        message: json['message'] ?? 'Unknown error',
        code: json['code'],
        details: json['details'],
      );
    }
  }
}
```

## Error Handling and Recovery

### API Error Classification
```dart
enum ApiErrorType {
  network,
  authentication,
  authorization,
  validation,
  serverError,
  timeout,
  unknown,
}

class ApiException implements Exception {
  final ApiErrorType type;
  final String message;
  final int? statusCode;
  final Map<String, dynamic>? details;

  const ApiException({
    required this.type,
    required this.message,
    this.statusCode,
    this.details,
  });

  factory ApiException.fromDioError(DioError error) {
    switch (error.type) {
      case DioErrorType.connectTimeout:
      case DioErrorType.sendTimeout:
      case DioErrorType.receiveTimeout:
        return ApiException(
          type: ApiErrorType.timeout,
          message: 'Request timeout',
        );
      case DioErrorType.response:
        final statusCode = error.response?.statusCode;
        if (statusCode == 401) {
          return ApiException(
            type: ApiErrorType.authentication,
            message: 'Authentication failed',
            statusCode: statusCode,
          );
        } else if (statusCode == 403) {
          return ApiException(
            type: ApiErrorType.authorization,
            message: 'Access denied',
            statusCode: statusCode,
          );
        }
        return ApiException(
          type: ApiErrorType.serverError,
          message: error.response?.data?['message'] ?? 'Server error',
          statusCode: statusCode,
        );
      default:
        return ApiException(
          type: ApiErrorType.network,
          message: 'Network error',
        );
    }
  }
}
```

### Retry Logic and Circuit Breaker
```dart
class RetryableApiClient {
  final ApiClient _apiClient;
  final Map<String, CircuitBreaker> _circuitBreakers = {};

  Future<T> executeWithRetry<T>(
    Future<T> Function() operation, {
    int maxRetries = 3,
    Duration delay = const Duration(seconds: 1),
    String? circuitBreakerKey,
  }) async {
    final circuitBreaker = circuitBreakerKey != null 
        ? _getCircuitBreaker(circuitBreakerKey)
        : null;

    if (circuitBreaker?.isOpen == true) {
      throw ApiException(
        type: ApiErrorType.serverError,
        message: 'Service temporarily unavailable',
      );
    }

    for (int attempt = 0; attempt <= maxRetries; attempt++) {
      try {
        final result = await operation();
        circuitBreaker?.recordSuccess();
        return result;
      } catch (e) {
        circuitBreaker?.recordFailure();
        
        if (attempt == maxRetries || !_shouldRetry(e)) {
          rethrow;
        }
        
        await Future.delayed(delay * (attempt + 1));
      }
    }
    
    throw ApiException(
      type: ApiErrorType.unknown,
      message: 'Max retries exceeded',
    );
  }

  bool _shouldRetry(dynamic error) {
    if (error is ApiException) {
      return error.type == ApiErrorType.network || 
             error.type == ApiErrorType.timeout ||
             (error.type == ApiErrorType.serverError && 
              error.statusCode != null && 
              error.statusCode! >= 500);
    }
    return false;
  }
}
```

## Offline Support and Caching

### Request Queue for Offline Operations
```dart
class OfflineRequestQueue {
  final List<PendingRequest> _queue = [];
  final LocalStorage _storage;

  Future<void> enqueue(PendingRequest request) async {
    _queue.add(request);
    await _storage.savePendingRequests(_queue);
  }

  Future<void> processQueue() async {
    final requests = List<PendingRequest>.from(_queue);
    
    for (final request in requests) {
      try {
        await _executeRequest(request);
        _queue.remove(request);
      } catch (e) {
        // Keep in queue for next attempt
        debugPrint('Failed to process queued request: $e');
      }
    }
    
    await _storage.savePendingRequests(_queue);
  }
}
```

### Response Caching Strategy
```dart
class CachedApiClient {
  final ApiClient _apiClient;
  final CacheManager _cacheManager;

  Future<T> get<T>(
    String path, {
    Duration? cacheMaxAge,
    bool forceRefresh = false,
  }) async {
    final cacheKey = _generateCacheKey(path);
    
    if (!forceRefresh && cacheMaxAge != null) {
      final cached = await _cacheManager.get<T>(cacheKey);
      if (cached != null && !_isCacheExpired(cached, cacheMaxAge)) {
        return cached.data;
      }
    }

    final response = await _apiClient.get<T>(path);
    
    if (cacheMaxAge != null) {
      await _cacheManager.put(cacheKey, CachedResponse(
        data: response.data,
        timestamp: DateTime.now(),
      ));
    }
    
    return response.data;
  }
}
```

This API integration architecture ensures robust, performant communication between the AICO frontend and backend while supporting offline operation, multiple transport protocols, and comprehensive error handling.
