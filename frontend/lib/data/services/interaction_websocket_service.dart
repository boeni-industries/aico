import 'dart:async';
import 'dart:convert';

import 'package:aico_frontend/data/models/interaction_model.dart';
import 'package:flutter/foundation.dart';
import 'package:web_socket_channel/io.dart';
import 'package:web_socket_channel/web_socket_channel.dart';

/// WebSocket service for real-time interaction notifications
/// 
/// Handles connection lifecycle, authentication, subscription, and reconnection
/// following the backend WebSocket protocol documented in interaction-system-ux.md
class InteractionWebSocketService {
  final String wsUrl;
  final Future<String> Function() getToken;
  final Future<String> Function() getUserUuid;
  
  WebSocketChannel? _channel;
  StreamController<InteractionBroadcastData>? _broadcastController;
  Timer? _reconnectTimer;
  Timer? _heartbeatTimer;
  
  bool _isConnected = false;
  bool _isAuthenticated = false;
  bool _shouldReconnect = true;
  int _reconnectAttempts = 0;
  
  static const int _maxReconnectAttempts = 10;
  static const Duration _heartbeatInterval = Duration(seconds: 30);
  static const Duration _initialReconnectDelay = Duration(seconds: 1);
  
  InteractionWebSocketService({
    required this.wsUrl,
    required this.getToken,
    required this.getUserUuid,
  });
  
  /// Stream of interaction broadcasts
  Stream<InteractionBroadcastData> get broadcasts {
    _broadcastController ??= StreamController<InteractionBroadcastData>.broadcast();
    return _broadcastController!.stream;
  }
  
  /// Whether the WebSocket is currently connected and authenticated
  bool get isConnected => _isConnected && _isAuthenticated;
  
  /// Connect to WebSocket and authenticate
  Future<void> connect() async {
    if (_isConnected) {
      debugPrint('[InteractionWS] Already connected');
      return;
    }
    
    try {
      debugPrint('[InteractionWS] Connecting to $wsUrl');
      
      // Create WebSocket channel
      _channel = IOWebSocketChannel.connect(Uri.parse(wsUrl));
      _isConnected = true;
      _reconnectAttempts = 0;
      
      // Set up single message listener
      _channel!.stream.listen(
        _handleMessage,
        onError: _handleError,
        onDone: _handleDisconnect,
        cancelOnError: false,
      );
      
      // Send auth immediately (no welcome wait needed)
      final token = await getToken();
      final userUuid = await getUserUuid();
      
      _channel!.sink.add(jsonEncode({
        'type': 'auth',
        'token': token,
      }));
      
      // Wait a moment for auth to process
      await Future.delayed(const Duration(milliseconds: 500));
      
      // Subscribe to user's interaction topic
      final topic = 'interaction.notifications.$userUuid';
      _channel!.sink.add(jsonEncode({
        'type': 'subscribe',
        'topic': topic,
      }));
      
      debugPrint('[InteractionWS] Subscribed to $topic');
      
      // Start heartbeat
      _startHeartbeat();
      
      debugPrint('[InteractionWS] Connected and subscribed successfully');
    } catch (e) {
      debugPrint('[InteractionWS] Connection error: $e');
      _isConnected = false;
      _scheduleReconnect();
    }
  }
  
  /// Disconnect from WebSocket
  Future<void> disconnect() async {
    debugPrint('[InteractionWS] Disconnecting');
    _shouldReconnect = false;
    _reconnectTimer?.cancel();
    _heartbeatTimer?.cancel();
    
    await _channel?.sink.close();
    _channel = null;
    
    _isConnected = false;
    _isAuthenticated = false;
  }
  
  /// Dispose resources
  void dispose() {
    disconnect();
    _broadcastController?.close();
    _broadcastController = null;
  }
  
  // Private methods
  
  void _handleMessage(dynamic message) {
    try {
      final data = jsonDecode(message as String) as Map<String, dynamic>;
      final type = data['type'] as String?;
      
      if (type == 'broadcast') {
        _handleBroadcast(data);
      } else if (type == 'error') {
        debugPrint('[InteractionWS] Server error: ${data['error']}');
      }
      // Ignore welcome, auth_success, subscribed - handled in setup
    } catch (e) {
      debugPrint('[InteractionWS] Error handling message: $e');
    }
  }
  
  void _handleBroadcast(Map<String, dynamic> data) {
    try {
      final broadcastData = InteractionBroadcastData.fromJson(
        data['data'] as Map<String, dynamic>,
      );
      
      debugPrint('[InteractionWS] Received broadcast: ${broadcastData.interaction.interactionId}');
      _broadcastController?.add(broadcastData);
    } catch (e) {
      debugPrint('[InteractionWS] Error parsing broadcast: $e');
    }
  }
  
  void _handleError(Object error) {
    debugPrint('[InteractionWS] Stream error: $error');
    _isConnected = false;
    _isAuthenticated = false;
    _scheduleReconnect();
  }
  
  void _handleDisconnect() {
    debugPrint('[InteractionWS] Disconnected');
    _isConnected = false;
    _isAuthenticated = false;
    _heartbeatTimer?.cancel();
    
    if (_shouldReconnect) {
      _scheduleReconnect();
    }
  }
  
  void _scheduleReconnect() {
    if (!_shouldReconnect || _reconnectAttempts >= _maxReconnectAttempts) {
      debugPrint('[InteractionWS] Max reconnect attempts reached');
      return;
    }
    
    _reconnectAttempts++;
    
    // Exponential backoff: 1s, 2s, 4s, 8s, 16s, 32s (max)
    final delay = Duration(
      seconds: (_initialReconnectDelay.inSeconds * (1 << (_reconnectAttempts - 1)))
          .clamp(1, 32),
    );
    
    debugPrint('[InteractionWS] Reconnecting in ${delay.inSeconds}s (attempt $_reconnectAttempts)');
    
    _reconnectTimer?.cancel();
    _reconnectTimer = Timer(delay, () {
      if (_shouldReconnect) {
        connect();
      }
    });
  }
  
  void _startHeartbeat() {
    _heartbeatTimer?.cancel();
    _heartbeatTimer = Timer.periodic(_heartbeatInterval, (timer) {
      if (_isConnected) {
        try {
          _channel?.sink.add(jsonEncode({'type': 'ping'}));
        } catch (e) {
          debugPrint('[InteractionWS] Heartbeat error: $e');
          _handleDisconnect();
        }
      } else {
        timer.cancel();
      }
    });
  }
}
