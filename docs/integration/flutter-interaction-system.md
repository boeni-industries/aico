# Flutter Interaction System Integration Guide

## Overview

This guide provides complete instructions for integrating the AICO interaction system into the Flutter client application.

## Architecture

```
Flutter App
    ↓
WebSocket Connection (Real-time notifications)
    ↓
API Gateway (ws://host:8772/ws)
    ↓
Message Bus (interaction.notifications.<user_uuid>)
    ↓
Backend REST API (/api/v1/interactions/*)
    ↓
PostgreSQL (interaction_requests + interaction_events)
```

## Prerequisites

### Dependencies

Add to `pubspec.yaml`:

```yaml
dependencies:
  web_socket_channel: ^2.4.0
  json_annotation: ^4.8.1
  freezed_annotation: ^2.4.1
  
dev_dependencies:
  build_runner: ^2.4.6
  json_serializable: ^6.7.1
  freezed: ^2.4.5
```

## Data Models

### 1. InteractionRequest Model

```dart
import 'package:freezed_annotation/freezed_annotation.dart';

part 'interaction_request.freezed.dart';
part 'interaction_request.g.dart';

@freezed
class InteractionRequest with _$InteractionRequest {
  const factory InteractionRequest({
    required String interactionId,
    required String userId,
    required String correlationId,
    required InteractionType interactionType,
    required InteractionStatus status,
    required String prompt,
    String? title,
    required InteractionRequirement requirement,
    required InteractionSeverity severity,
    String? category,
    String? expectedAnswerType,
    List<String>? allowedOptions,
    String? answerText,
    Map<String, dynamic>? answerJson,
    DateTime? answeredAt,
    DateTime? expiresAt,
    required DateTime createdAt,
    required DateTime updatedAt,
  }) = _InteractionRequest;

  factory InteractionRequest.fromJson(Map<String, dynamic> json) =>
      _$InteractionRequestFromJson(json);
}

enum InteractionType {
  @JsonValue('question')
  question,
  @JsonValue('choice')
  choice,
  @JsonValue('dialogue')
  dialogue,
  @JsonValue('approval')
  approval,
  @JsonValue('ack')
  acknowledgement,
}

enum InteractionStatus {
  @JsonValue('pending')
  pending,
  @JsonValue('answered')
  answered,
  @JsonValue('approved')
  approved,
  @JsonValue('rejected')
  rejected,
  @JsonValue('dismissed')
  dismissed,
  @JsonValue('deferred')
  deferred,
  @JsonValue('expired')
  expired,
  @JsonValue('cancelled')
  cancelled,
}

enum InteractionRequirement {
  @JsonValue('required')
  required,
  @JsonValue('optional')
  optional,
}

enum InteractionSeverity {
  @JsonValue('low')
  low,
  @JsonValue('medium')
  medium,
  @JsonValue('high')
  high,
}
```

### 2. InteractionEvent Model

```dart
@freezed
class InteractionEvent with _$InteractionEvent {
  const factory InteractionEvent({
    required String eventId,
    required String interactionId,
    required String userId,
    required String correlationId,
    required String actor,
    required String eventType,
    String? fromStatus,
    String? toStatus,
    Map<String, dynamic>? payloadJson,
    required DateTime createdAt,
  }) = _InteractionEvent;

  factory InteractionEvent.fromJson(Map<String, dynamic> json) =>
      _$InteractionEventFromJson(json);
}
```

### 3. WebSocket Message Models

```dart
@freezed
class WebSocketMessage with _$WebSocketMessage {
  const factory WebSocketMessage.welcome({
    required String clientId,
    required String server,
    required String version,
  }) = WelcomeMessage;

  const factory WebSocketMessage.authSuccess({
    required String userUuid,
    required List<String> roles,
    String? sessionId,
  }) = AuthSuccessMessage;

  const factory WebSocketMessage.subscribed({
    required String topic,
  }) = SubscribedMessage;

  const factory WebSocketMessage.broadcast({
    required String topic,
    required InteractionBroadcastData data,
  }) = BroadcastMessage;

  const factory WebSocketMessage.error({
    required String error,
    String? detail,
  }) = ErrorMessage;

  factory WebSocketMessage.fromJson(Map<String, dynamic> json) {
    final type = json['type'] as String;
    switch (type) {
      case 'welcome':
        return WelcomeMessage(
          clientId: json['client_id'],
          server: json['server'],
          version: json['version'],
        );
      case 'auth_success':
        return AuthSuccessMessage(
          userUuid: json['user_uuid'],
          roles: List<String>.from(json['roles']),
          sessionId: json['session_id'],
        );
      case 'subscribed':
        return SubscribedMessage(topic: json['topic']);
      case 'broadcast':
        return BroadcastMessage(
          topic: json['topic'],
          data: InteractionBroadcastData.fromJson(json['data']),
        );
      case 'error':
        return ErrorMessage(
          error: json['error'],
          detail: json['detail'],
        );
      default:
        throw Exception('Unknown message type: $type');
    }
  }
}

@freezed
class InteractionBroadcastData with _$InteractionBroadcastData {
  const factory InteractionBroadcastData({
    required InteractionRequest interaction,
    required InteractionEvent event,
  }) = _InteractionBroadcastData;

  factory InteractionBroadcastData.fromJson(Map<String, dynamic> json) =>
      _$InteractionBroadcastDataFromJson(json);
}
```

## WebSocket Service

```dart
import 'dart:async';
import 'dart:convert';
import 'package:web_socket_channel/web_socket_channel.dart';

class InteractionWebSocketService {
  WebSocketChannel? _channel;
  StreamController<InteractionBroadcastData>? _broadcastController;
  StreamController<ConnectionState>? _stateController;
  
  String? _userUuid;
  String? _token;
  Timer? _reconnectTimer;
  int _reconnectAttempts = 0;
  
  static const int maxReconnectAttempts = 5;
  static const Duration initialReconnectDelay = Duration(seconds: 1);
  
  Stream<InteractionBroadcastData> get broadcasts => 
      _broadcastController?.stream ?? const Stream.empty();
  
  Stream<ConnectionState> get connectionState => 
      _stateController?.stream ?? const Stream.empty();

  Future<void> connect({
    required String wsUrl,
    required String token,
    required String userUuid,
  }) async {
    _token = token;
    _userUuid = userUuid;
    
    _broadcastController ??= StreamController<InteractionBroadcastData>.broadcast();
    _stateController ??= StreamController<ConnectionState>.broadcast();
    
    await _connectInternal(wsUrl);
  }

  Future<void> _connectInternal(String wsUrl) async {
    try {
      _stateController?.add(ConnectionState.connecting);
      
      // Connect to WebSocket
      _channel = WebSocketChannel.connect(Uri.parse(wsUrl));
      
      // Wait for welcome message
      final welcomeMsg = await _channel!.stream.first;
      final welcome = WebSocketMessage.fromJson(jsonDecode(welcomeMsg));
      
      if (welcome is! WelcomeMessage) {
        throw Exception('Expected welcome message, got: ${welcome.runtimeType}');
      }
      
      // Authenticate
      _channel!.sink.add(jsonEncode({
        'type': 'auth',
        'token': _token,
      }));
      
      // Wait for auth success
      final authMsg = await _channel!.stream.first;
      final authResponse = WebSocketMessage.fromJson(jsonDecode(authMsg));
      
      if (authResponse is! AuthSuccessMessage) {
        throw Exception('Authentication failed: $authResponse');
      }
      
      // Subscribe to user's interaction topic
      _channel!.sink.add(jsonEncode({
        'type': 'subscribe',
        'topic': 'interaction.notifications.$_userUuid',
      }));
      
      // Wait for subscription confirmation
      final subMsg = await _channel!.stream.first;
      final subResponse = WebSocketMessage.fromJson(jsonDecode(subMsg));
      
      if (subResponse is! SubscribedMessage) {
        throw Exception('Subscription failed: $subResponse');
      }
      
      _stateController?.add(ConnectionState.connected);
      _reconnectAttempts = 0;
      
      // Listen for broadcasts
      _channel!.stream.listen(
        _handleMessage,
        onError: _handleError,
        onDone: _handleDisconnect,
      );
      
    } catch (e) {
      _stateController?.add(ConnectionState.error);
      _scheduleReconnect(wsUrl);
    }
  }

  void _handleMessage(dynamic message) {
    try {
      final data = jsonDecode(message);
      final wsMessage = WebSocketMessage.fromJson(data);
      
      if (wsMessage is BroadcastMessage) {
        _broadcastController?.add(wsMessage.data);
      } else if (wsMessage is ErrorMessage) {
        print('WebSocket error: ${wsMessage.error} - ${wsMessage.detail}');
      }
    } catch (e) {
      print('Error parsing WebSocket message: $e');
    }
  }

  void _handleError(error) {
    print('WebSocket error: $error');
    _stateController?.add(ConnectionState.error);
  }

  void _handleDisconnect() {
    _stateController?.add(ConnectionState.disconnected);
    _scheduleReconnect(_channel?.closeCode == 1000 ? null : 'ws://localhost:8772/ws');
  }

  void _scheduleReconnect(String? wsUrl) {
    if (wsUrl == null || _reconnectAttempts >= maxReconnectAttempts) {
      return;
    }
    
    _reconnectAttempts++;
    final delay = initialReconnectDelay * (1 << (_reconnectAttempts - 1));
    
    _reconnectTimer?.cancel();
    _reconnectTimer = Timer(delay, () => _connectInternal(wsUrl));
  }

  void disconnect() {
    _reconnectTimer?.cancel();
    _channel?.sink.close();
    _broadcastController?.close();
    _stateController?.close();
  }
}

enum ConnectionState {
  disconnected,
  connecting,
  connected,
  error,
}
```

## REST API Client

```dart
class InteractionRepository {
  final Dio _dio;
  final String _baseUrl;

  InteractionRepository(this._dio, this._baseUrl);

  Future<InteractionRequest> getInteraction(String interactionId) async {
    final response = await _dio.get('$_baseUrl/api/v1/interactions/$interactionId');
    return InteractionRequest.fromJson(response.data['interaction']);
  }

  Future<List<InteractionRequest>> listInteractions({
    InteractionStatus? status,
    InteractionType? type,
    int? limit,
    int? offset,
  }) async {
    final response = await _dio.get(
      '$_baseUrl/api/v1/interactions',
      queryParameters: {
        if (status != null) 'status': status.name,
        if (type != null) 'type': type.name,
        if (limit != null) 'limit': limit,
        if (offset != null) 'offset': offset,
      },
    );
    
    return (response.data['interactions'] as List)
        .map((json) => InteractionRequest.fromJson(json))
        .toList();
  }

  Future<InteractionRequest> answerInteraction(
    String interactionId, {
    String? answerText,
    Map<String, dynamic>? answerJson,
  }) async {
    final response = await _dio.post(
      '$_baseUrl/api/v1/interactions/$interactionId/answer',
      data: {
        if (answerText != null) 'answer_text': answerText,
        if (answerJson != null) 'answer_json': answerJson,
      },
    );
    
    return InteractionRequest.fromJson(response.data['interaction']);
  }

  Future<InteractionRequest> approveInteraction(String interactionId) async {
    final response = await _dio.post(
      '$_baseUrl/api/v1/interactions/$interactionId/approve',
    );
    
    return InteractionRequest.fromJson(response.data['interaction']);
  }

  Future<InteractionRequest> rejectInteraction(String interactionId) async {
    final response = await _dio.post(
      '$_baseUrl/api/v1/interactions/$interactionId/reject',
    );
    
    return InteractionRequest.fromJson(response.data['interaction']);
  }

  Future<InteractionRequest> cancelInteraction(String interactionId) async {
    final response = await _dio.post(
      '$_baseUrl/api/v1/interactions/$interactionId/cancel',
    );
    
    return InteractionRequest.fromJson(response.data['interaction']);
  }
}
```

## State Management (Riverpod Example)

```dart
@riverpod
class InteractionNotifier extends _$InteractionNotifier {
  @override
  AsyncValue<List<InteractionRequest>> build() {
    _initWebSocket();
    return const AsyncValue.loading();
  }

  void _initWebSocket() async {
    final wsService = ref.read(webSocketServiceProvider);
    final token = await ref.read(authRepositoryProvider).getToken();
    final userUuid = await ref.read(authRepositoryProvider).getUserUuid();
    
    await wsService.connect(
      wsUrl: 'ws://localhost:8772/ws',
      token: token,
      userUuid: userUuid,
    );
    
    wsService.broadcasts.listen((broadcast) {
      _handleBroadcast(broadcast);
    });
    
    _loadInteractions();
  }

  void _handleBroadcast(InteractionBroadcastData broadcast) {
    state.whenData((interactions) {
      final index = interactions.indexWhere(
        (i) => i.interactionId == broadcast.interaction.interactionId,
      );
      
      if (index >= 0) {
        // Update existing
        final updated = List<InteractionRequest>.from(interactions);
        updated[index] = broadcast.interaction;
        state = AsyncValue.data(updated);
      } else {
        // Add new
        state = AsyncValue.data([broadcast.interaction, ...interactions]);
      }
    });
  }

  Future<void> _loadInteractions() async {
    state = const AsyncValue.loading();
    
    try {
      final repo = ref.read(interactionRepositoryProvider);
      final interactions = await repo.listInteractions(
        status: InteractionStatus.pending,
      );
      state = AsyncValue.data(interactions);
    } catch (e, st) {
      state = AsyncValue.error(e, st);
    }
  }

  Future<void> answerInteraction(String id, String answer) async {
    try {
      final repo = ref.read(interactionRepositoryProvider);
      await repo.answerInteraction(id, answerText: answer);
      // WebSocket will update state automatically
    } catch (e) {
      // Handle error
    }
  }

  Future<void> approveInteraction(String id) async {
    try {
      final repo = ref.read(interactionRepositoryProvider);
      await repo.approveInteraction(id);
    } catch (e) {
      // Handle error
    }
  }

  Future<void> rejectInteraction(String id) async {
    try {
      final repo = ref.read(interactionRepositoryProvider);
      await repo.rejectInteraction(id);
    } catch (e) {
      // Handle error
    }
  }
}
```

## UI Components

### Interaction List View

```dart
class InteractionListView extends ConsumerWidget {
  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final interactionsAsync = ref.watch(interactionNotifierProvider);
    
    return interactionsAsync.when(
      data: (interactions) => ListView.builder(
        itemCount: interactions.length,
        itemBuilder: (context, index) {
          final interaction = interactions[index];
          return InteractionCard(interaction: interaction);
        },
      ),
      loading: () => const Center(child: CircularProgressIndicator()),
      error: (error, stack) => Center(child: Text('Error: $error')),
    );
  }
}
```

### Interaction Dialog

```dart
class InteractionDialog extends ConsumerWidget {
  final InteractionRequest interaction;

  const InteractionDialog({required this.interaction});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return AlertDialog(
      title: Text(interaction.title ?? 'Interaction Request'),
      content: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(interaction.prompt),
          const SizedBox(height: 16),
          if (interaction.interactionType == InteractionType.question)
            _buildQuestionInput(context, ref),
          if (interaction.interactionType == InteractionType.choice)
            _buildChoiceInput(context, ref),
          if (interaction.interactionType == InteractionType.approval)
            _buildApprovalButtons(context, ref),
        ],
      ),
    );
  }

  Widget _buildQuestionInput(BuildContext context, WidgetRef ref) {
    final controller = TextEditingController();
    
    return Column(
      children: [
        TextField(
          controller: controller,
          decoration: const InputDecoration(
            hintText: 'Enter your answer...',
          ),
        ),
        const SizedBox(height: 16),
        ElevatedButton(
          onPressed: () {
            ref.read(interactionNotifierProvider.notifier)
                .answerInteraction(interaction.interactionId, controller.text);
            Navigator.of(context).pop();
          },
          child: const Text('Submit'),
        ),
      ],
    );
  }

  Widget _buildChoiceInput(BuildContext context, WidgetRef ref) {
    return Column(
      children: interaction.allowedOptions!.map((option) {
        return ListTile(
          title: Text(option),
          onTap: () {
            ref.read(interactionNotifierProvider.notifier)
                .answerInteraction(interaction.interactionId, option);
            Navigator.of(context).pop();
          },
        );
      }).toList(),
    );
  }

  Widget _buildApprovalButtons(BuildContext context, WidgetRef ref) {
    return Row(
      mainAxisAlignment: MainAxisAlignment.spaceEvenly,
      children: [
        ElevatedButton(
          onPressed: () {
            ref.read(interactionNotifierProvider.notifier)
                .approveInteraction(interaction.interactionId);
            Navigator.of(context).pop();
          },
          child: const Text('Approve'),
        ),
        OutlinedButton(
          onPressed: () {
            ref.read(interactionNotifierProvider.notifier)
                .rejectInteraction(interaction.interactionId);
            Navigator.of(context).pop();
          },
          child: const Text('Reject'),
        ),
      ],
    );
  }
}
```

## Testing

### Unit Tests

```dart
void main() {
  group('InteractionRequest', () {
    test('fromJson creates valid object', () {
      final json = {
        'interaction_id': 'test-id',
        'user_id': 'user-id',
        'correlation_id': 'corr-id',
        'interaction_type': 'question',
        'status': 'pending',
        'prompt': 'Test prompt',
        'requirement': 'required',
        'severity': 'medium',
        'created_at': '2026-02-08T00:00:00Z',
        'updated_at': '2026-02-08T00:00:00Z',
      };
      
      final interaction = InteractionRequest.fromJson(json);
      
      expect(interaction.interactionId, 'test-id');
      expect(interaction.interactionType, InteractionType.question);
      expect(interaction.status, InteractionStatus.pending);
    });
  });
}
```

## Next Steps

1. Implement data models with Freezed
2. Create WebSocket service with reconnection logic
3. Build REST API client with Dio
4. Set up state management (Riverpod/Bloc)
5. Create UI components for interaction inbox
6. Add notification handling for new interactions
7. Implement error handling and retry logic
8. Add integration tests

## Configuration

Add to your app configuration:

```dart
class AppConfig {
  static const String apiGatewayWsUrl = 'ws://localhost:8772/ws';
  static const String apiGatewayRestUrl = 'http://localhost:8772';
}
```

## Security Considerations

1. **JWT Token Storage**: Use `flutter_secure_storage` for token persistence
2. **WebSocket Reconnection**: Implement exponential backoff
3. **Error Handling**: Never expose sensitive data in error messages
4. **Input Validation**: Validate all user inputs before submission
5. **HTTPS/WSS**: Use secure protocols in production
