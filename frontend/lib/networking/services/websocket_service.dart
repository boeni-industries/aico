import 'dart:async';

import 'package:aico_frontend/core/services/encryption_service.dart';
import 'package:aico_frontend/networking/clients/websocket_client.dart';
import 'package:aico_frontend/networking/services/token_manager.dart';
import 'package:flutter/foundation.dart';

/// High-level WebSocket service for real-time communication
class WebSocketService {
  final WebSocketClient _client;
  final StreamController<Map<String, dynamic>> _messageController = 
      StreamController.broadcast();
  final StreamController<WebSocketConnectionState> _connectionController = 
      StreamController.broadcast();
  
  String? _currentUrl;
  bool _isInitialized = false;
  
  WebSocketService({
    required EncryptionService encryptionService,
    required TokenManager tokenManager,
  }) : _client = WebSocketClient(
         encryptionService: encryptionService,
         tokenManager: tokenManager,
       );

  /// Stream of incoming messages
  Stream<Map<String, dynamic>> get messages => _messageController.stream;
  
  /// Stream of connection state changes
  Stream<WebSocketConnectionState> get connectionState => _connectionController.stream;
  
  /// Current connection state
  WebSocketConnectionState get currentState => _client.currentState;
  
  /// Whether the service is connected
  bool get isConnected => _client.isConnected;

  /// Initialize the WebSocket service
  Future<void> initialize(String baseUrl, {bool enableEncryption = true}) async {
    if (_isInitialized) return;
    
    _currentUrl = _buildWebSocketUrl(baseUrl);
    
    // Set up message forwarding
    _client.messages.listen(
      (message) => _messageController.add(message),
      onError: (error) => _messageController.addError(error),
    );
    
    // Set up connection state forwarding
    _client.connectionState.listen(
      (state) => _connectionController.add(state),
      onError: (error) => _connectionController.addError(error),
    );
    
    _isInitialized = true;
    debugPrint('WebSocketService initialized with URL: $_currentUrl');
  }

  /// Connect to the WebSocket server
  Future<void> connect() async {
    if (!_isInitialized || _currentUrl == null) {
      throw StateError('WebSocketService not initialized. Call initialize() first.');
    }
    
    await _client.connect(_currentUrl!, enableEncryption: true);
  }

  /// Disconnect from the WebSocket server
  Future<void> disconnect() async {
    await _client.disconnect();
  }

  /// Send a message through the WebSocket connection
  void sendMessage(Map<String, dynamic> message) {
    if (!_isInitialized) {
      throw StateError('WebSocketService not initialized. Call initialize() first.');
    }
    
    _client.sendMessage(message);
  }

  /// Send a conversation message
  void sendConversationMessage({
    required String conversationId,
    required String content,
    String? messageId,
  }) {
    final message = {
      'type': 'conversation_message',
      'conversation_id': conversationId,
      'message_id': messageId ?? _generateMessageId(),
      'content': content,
      'timestamp': DateTime.now().toIso8601String(),
    };
    
    sendMessage(message);
  }

  /// Send a typing indicator
  void sendTypingIndicator({
    required String conversationId,
    required bool isTyping,
  }) {
    final message = {
      'type': 'typing_indicator',
      'conversation_id': conversationId,
      'is_typing': isTyping,
      'timestamp': DateTime.now().toIso8601String(),
    };
    
    sendMessage(message);
  }

  /// Subscribe to conversation updates
  void subscribeToConversation(String conversationId) {
    final message = {
      'type': 'subscribe',
      'channel': 'conversation:$conversationId',
      'timestamp': DateTime.now().toIso8601String(),
    };
    
    sendMessage(message);
  }

  /// Unsubscribe from conversation updates
  void unsubscribeFromConversation(String conversationId) {
    final message = {
      'type': 'unsubscribe',
      'channel': 'conversation:$conversationId',
      'timestamp': DateTime.now().toIso8601String(),
    };
    
    sendMessage(message);
  }

  /// Subscribe to user presence updates
  void subscribeToPresence() {
    final message = {
      'type': 'subscribe',
      'channel': 'presence',
      'timestamp': DateTime.now().toIso8601String(),
    };
    
    sendMessage(message);
  }

  /// Update user presence status
  void updatePresenceStatus({
    required String status, // online, away, busy, offline
    String? customMessage,
  }) {
    final message = {
      'type': 'presence_update',
      'status': status,
      if (customMessage != null) 'custom_message': customMessage,
      'timestamp': DateTime.now().toIso8601String(),
    };
    
    sendMessage(message);
  }

  /// Send a system command
  void sendSystemCommand({
    required String command,
    Map<String, dynamic>? parameters,
  }) {
    final message = {
      'type': 'system_command',
      'command': command,
      if (parameters != null) 'parameters': parameters,
      'timestamp': DateTime.now().toIso8601String(),
    };
    
    sendMessage(message);
  }

  /// Filter messages by type
  Stream<Map<String, dynamic>> getMessagesByType(String messageType) {
    return messages.where((message) => message['type'] == messageType);
  }

  /// Get conversation messages stream
  Stream<Map<String, dynamic>> getConversationMessages() {
    return getMessagesByType('conversation_message');
  }

  /// Get typing indicator stream
  Stream<Map<String, dynamic>> getTypingIndicators() {
    return getMessagesByType('typing_indicator');
  }

  /// Get presence updates stream
  Stream<Map<String, dynamic>> getPresenceUpdates() {
    return getMessagesByType('presence_update');
  }

  /// Get system notifications stream
  Stream<Map<String, dynamic>> getSystemNotifications() {
    return getMessagesByType('system_notification');
  }

  String _buildWebSocketUrl(String baseUrl) {
    // Convert HTTP(S) URL to WebSocket URL
    final uri = Uri.parse(baseUrl);
    final scheme = uri.scheme == 'https' ? 'wss' : 'ws';
    
    return '$scheme://${uri.host}:${uri.port}/ws';
  }

  String _generateMessageId() {
    return '${DateTime.now().millisecondsSinceEpoch}_${_generateRandomString(8)}';
  }

  String _generateRandomString(int length) {
    const chars = 'abcdefghijklmnopqrstuvwxyz0123456789';
    final random = DateTime.now().millisecondsSinceEpoch;
    return List.generate(length, (index) => chars[(random + index) % chars.length]).join();
  }

  /// Dispose of the service and clean up resources
  Future<void> dispose() async {
    await _client.dispose();
    await _messageController.close();
    await _connectionController.close();
  }
}

/// WebSocket message types for type-safe message handling
class WebSocketMessageTypes {
  static const String conversationMessage = 'conversation_message';
  static const String typingIndicator = 'typing_indicator';
  static const String presenceUpdate = 'presence_update';
  static const String systemNotification = 'system_notification';
  static const String systemCommand = 'system_command';
  static const String subscribe = 'subscribe';
  static const String unsubscribe = 'unsubscribe';
  static const String ping = 'ping';
  static const String pong = 'pong';
  static const String error = 'error';
}

/// User presence status constants
class PresenceStatus {
  static const String online = 'online';
  static const String away = 'away';
  static const String busy = 'busy';
  static const String offline = 'offline';
}
