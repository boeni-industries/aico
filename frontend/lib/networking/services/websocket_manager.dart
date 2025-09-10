import 'dart:async';
import 'dart:convert';

import 'package:flutter/foundation.dart';
import 'package:web_socket_channel/web_socket_channel.dart';

/// Simple WebSocket state enum
enum WebSocketState {
  disconnected,
  connecting,
  connected,
  reconnecting,
}

/// Simplified WebSocket manager for Riverpod architecture
class WebSocketManager {
  WebSocketChannel? _channel;
  final StreamController<WebSocketState> _stateController = StreamController.broadcast();
  final StreamController<Map<String, dynamic>> _messageController = StreamController.broadcast();
  
  WebSocketState _currentState = WebSocketState.disconnected;
  Timer? _reconnectTimer;
  Timer? _heartbeatTimer;
  
  static const Duration _reconnectInterval = Duration(seconds: 5);
  static const Duration _heartbeatInterval = Duration(seconds: 30);

  /// Stream of connection state changes
  Stream<WebSocketState> get connectionState => _stateController.stream;
  
  /// Stream of incoming messages
  Stream<Map<String, dynamic>> get messages => _messageController.stream;
  
  /// Current connection state
  WebSocketState get currentState => _currentState;

  /// Connect to WebSocket server
  Future<void> connect(String url) async {
    if (_currentState == WebSocketState.connected || _currentState == WebSocketState.connecting) {
      return;
    }

    _updateState(WebSocketState.connecting);
    
    try {
      _channel = WebSocketChannel.connect(Uri.parse(url));
      
      // Listen for messages
      _channel!.stream.listen(
        _handleMessage,
        onError: _handleError,
        onDone: _handleDisconnect,
      );
      
      _updateState(WebSocketState.connected);
      _startHeartbeat();
      
      debugPrint('[WebSocket] Connected to $url');
    } catch (e) {
      debugPrint('[WebSocket] Connection failed: $e');
      _updateState(WebSocketState.disconnected);
      _scheduleReconnect(url);
    }
  }

  /// Disconnect from WebSocket server
  Future<void> disconnect() async {
    _reconnectTimer?.cancel();
    _heartbeatTimer?.cancel();
    
    await _channel?.sink.close();
    _channel = null;
    
    _updateState(WebSocketState.disconnected);
    debugPrint('[WebSocket] Disconnected');
  }

  /// Send message to WebSocket server
  void sendMessage(Map<String, dynamic> message) {
    if (_currentState != WebSocketState.connected || _channel == null) {
      debugPrint('[WebSocket] Cannot send message - not connected');
      return;
    }

    try {
      final jsonMessage = jsonEncode(message);
      _channel!.sink.add(jsonMessage);
      debugPrint('[WebSocket] Sent: $jsonMessage');
    } catch (e) {
      debugPrint('[WebSocket] Failed to send message: $e');
    }
  }

  /// Handle incoming messages
  void _handleMessage(dynamic data) {
    try {
      final Map<String, dynamic> message = jsonDecode(data.toString());
      _messageController.add(message);
      debugPrint('[WebSocket] Received: $message');
    } catch (e) {
      debugPrint('[WebSocket] Failed to parse message: $e');
    }
  }

  /// Handle connection errors
  void _handleError(error) {
    debugPrint('[WebSocket] Error: $error');
    _updateState(WebSocketState.disconnected);
  }

  /// Handle disconnection
  void _handleDisconnect() {
    debugPrint('[WebSocket] Connection closed');
    _updateState(WebSocketState.disconnected);
  }

  /// Update connection state and notify listeners
  void _updateState(WebSocketState newState) {
    if (_currentState != newState) {
      _currentState = newState;
      _stateController.add(newState);
    }
  }

  /// Schedule reconnection attempt
  void _scheduleReconnect(String url) {
    _reconnectTimer?.cancel();
    _reconnectTimer = Timer(_reconnectInterval, () {
      debugPrint('[WebSocket] Attempting reconnection...');
      connect(url);
    });
  }

  /// Start heartbeat to keep connection alive
  void _startHeartbeat() {
    _heartbeatTimer?.cancel();
    _heartbeatTimer = Timer.periodic(_heartbeatInterval, (timer) {
      if (_currentState == WebSocketState.connected) {
        sendMessage({'type': 'ping', 'timestamp': DateTime.now().millisecondsSinceEpoch});
      } else {
        timer.cancel();
      }
    });
  }

  /// Dispose resources
  void dispose() {
    _reconnectTimer?.cancel();
    _heartbeatTimer?.cancel();
    _channel?.sink.close();
    _stateController.close();
    _messageController.close();
  }
}
