import 'dart:async';
import 'package:flutter/foundation.dart';
import 'package:aico_frontend/networking/services/websocket_service.dart';
import 'package:aico_frontend/networking/clients/websocket_client.dart';
import 'package:aico_frontend/core/services/encryption_service.dart';
import 'package:aico_frontend/networking/services/token_manager.dart';
import 'package:get_it/get_it.dart';

/// Manages WebSocket connections and provides high-level messaging interface
class WebSocketManager {
  WebSocketService? _webSocketService;
  final StreamController<WebSocketConnectionState> _connectionStateController = 
      StreamController.broadcast();
  final StreamController<Map<String, dynamic>> _messageController = 
      StreamController.broadcast();
  
  bool _isInitialized = false;
  Timer? _reconnectTimer;
  Timer? _heartbeatTimer;
  
  static const Duration _reconnectInterval = Duration(seconds: 5);
  static const Duration _heartbeatInterval = Duration(seconds: 30);

  /// Stream of connection state changes
  Stream<WebSocketConnectionState> get connectionState => _connectionStateController.stream;
  
  /// Stream of all incoming messages
  Stream<Map<String, dynamic>> get messages => _messageController.stream;
  
  /// Current connection state
  WebSocketConnectionState get currentState => 
      _webSocketService?.currentState ?? WebSocketConnectionState.disconnected;
  
  /// Whether the WebSocket is connected
  bool get isConnected => _webSocketService?.isConnected ?? false;

  /// Initialize the WebSocket manager
  Future<void> initialize(String baseUrl) async {
    if (_isInitialized) return;
    
    try {
      final encryptionService = GetIt.instance<EncryptionService>();
      final tokenManager = GetIt.instance<TokenManager>();
      
      _webSocketService = WebSocketService(
        encryptionService: encryptionService,
        tokenManager: tokenManager,
      );
      
      await _webSocketService!.initialize(baseUrl);
      
      // Set up message and state forwarding
      _webSocketService!.messages.listen(
        (message) => _messageController.add(message),
        onError: (error) => _messageController.addError(error),
      );
      
      _webSocketService!.connectionState.listen(
        (state) {
          _connectionStateController.add(state);
          _handleConnectionStateChange(state);
        },
        onError: (error) => _connectionStateController.addError(error),
      );
      
      _isInitialized = true;
      debugPrint('WebSocketManager initialized');
    } catch (e) {
      debugPrint('Failed to initialize WebSocketManager: $e');
      rethrow;
    }
  }

  /// Connect to the WebSocket server
  Future<void> connect() async {
    if (!_isInitialized || _webSocketService == null) {
      throw StateError('WebSocketManager not initialized. Call initialize() first.');
    }
    
    try {
      await _webSocketService!.connect();
    } catch (e) {
      debugPrint('WebSocket connection failed: $e');
      _scheduleReconnect();
    }
  }

  /// Disconnect from the WebSocket server
  Future<void> disconnect() async {
    _cancelReconnectTimer();
    _cancelHeartbeatTimer();
    
    if (_webSocketService != null) {
      await _webSocketService!.disconnect();
    }
  }

  /// Send a message through the WebSocket connection
  void sendMessage(Map<String, dynamic> message) {
    if (!isConnected) {
      debugPrint('Cannot send message: WebSocket not connected');
      return;
    }
    
    _webSocketService!.sendMessage(message);
  }

  /// Send a conversation message
  void sendConversationMessage({
    required String conversationId,
    required String content,
    String? messageId,
  }) {
    _webSocketService?.sendConversationMessage(
      conversationId: conversationId,
      content: content,
      messageId: messageId,
    );
  }

  /// Send typing indicator
  void sendTypingIndicator({
    required String conversationId,
    required bool isTyping,
  }) {
    _webSocketService?.sendTypingIndicator(
      conversationId: conversationId,
      isTyping: isTyping,
    );
  }

  /// Subscribe to conversation updates
  void subscribeToConversation(String conversationId) {
    _webSocketService?.subscribeToConversation(conversationId);
  }

  /// Unsubscribe from conversation updates
  void unsubscribeFromConversation(String conversationId) {
    _webSocketService?.unsubscribeFromConversation(conversationId);
  }

  /// Update user presence status
  void updatePresenceStatus({
    required String status,
    String? customMessage,
  }) {
    _webSocketService?.updatePresenceStatus(
      status: status,
      customMessage: customMessage,
    );
  }

  /// Get filtered message streams
  Stream<Map<String, dynamic>> getConversationMessages() {
    return _webSocketService?.getConversationMessages() ?? const Stream.empty();
  }

  Stream<Map<String, dynamic>> getTypingIndicators() {
    return _webSocketService?.getTypingIndicators() ?? const Stream.empty();
  }

  Stream<Map<String, dynamic>> getPresenceUpdates() {
    return _webSocketService?.getPresenceUpdates() ?? const Stream.empty();
  }

  Stream<Map<String, dynamic>> getSystemNotifications() {
    return _webSocketService?.getSystemNotifications() ?? const Stream.empty();
  }

  void _handleConnectionStateChange(WebSocketConnectionState state) {
    switch (state) {
      case WebSocketConnectionState.connected:
        _cancelReconnectTimer();
        _startHeartbeat();
        debugPrint('WebSocket connected successfully');
        break;
      case WebSocketConnectionState.disconnected:
        _cancelHeartbeatTimer();
        _scheduleReconnect();
        debugPrint('WebSocket disconnected');
        break;
      case WebSocketConnectionState.connecting:
      case WebSocketConnectionState.reconnecting:
        debugPrint('WebSocket connecting...');
        break;
    }
  }

  void _scheduleReconnect() {
    _cancelReconnectTimer();
    
    _reconnectTimer = Timer(_reconnectInterval, () async {
      if (!isConnected && _isInitialized) {
        debugPrint('Attempting WebSocket reconnection...');
        try {
          await connect();
        } catch (e) {
          debugPrint('Reconnection failed: $e');
          _scheduleReconnect(); // Schedule another attempt
        }
      }
    });
  }

  void _cancelReconnectTimer() {
    _reconnectTimer?.cancel();
    _reconnectTimer = null;
  }

  void _startHeartbeat() {
    _cancelHeartbeatTimer();
    
    _heartbeatTimer = Timer.periodic(_heartbeatInterval, (timer) {
      if (isConnected) {
        sendMessage({
          'type': WebSocketMessageTypes.ping,
          'timestamp': DateTime.now().toIso8601String(),
        });
      } else {
        _cancelHeartbeatTimer();
      }
    });
  }

  void _cancelHeartbeatTimer() {
    _heartbeatTimer?.cancel();
    _heartbeatTimer = null;
  }

  /// Dispose of the manager and clean up resources
  Future<void> dispose() async {
    _cancelReconnectTimer();
    _cancelHeartbeatTimer();
    
    await _webSocketService?.dispose();
    await _connectionStateController.close();
    await _messageController.close();
    
    _isInitialized = false;
  }
}

/// Singleton WebSocket manager for global access
class GlobalWebSocketManager {
  static WebSocketManager? _instance;
  
  static WebSocketManager get instance {
    _instance ??= WebSocketManager();
    return _instance!;
  }
  
  static Future<void> initialize(String baseUrl) async {
    await instance.initialize(baseUrl);
  }
  
  static Future<void> connect() async {
    await instance.connect();
  }
  
  static Future<void> disconnect() async {
    await instance.disconnect();
  }
  
  static void dispose() {
    _instance?.dispose();
    _instance = null;
  }
}
