import 'dart:async';
import 'dart:collection';
import 'dart:convert';
import 'package:flutter/foundation.dart';
import 'package:web_socket_channel/io.dart';
import '../models/error_models.dart';

enum WebSocketConnectionState {
  disconnected,
  connecting,
  connected,
  reconnecting,
}

class WebSocketClient {
  IOWebSocketChannel? _channel;
  final StreamController<Map<String, dynamic>> _messageController = 
      StreamController.broadcast();
  final StreamController<WebSocketConnectionState> _stateController = 
      StreamController.broadcast();
  
  Timer? _heartbeatTimer;
  Timer? _reconnectTimer;
  final Queue<Map<String, dynamic>> _messageQueue = Queue();
  
  String? _url;
  WebSocketConnectionState _state = WebSocketConnectionState.disconnected;
  int _reconnectAttempts = 0;
  
  static const int _maxReconnectAttempts = 5;
  static const Duration _heartbeatInterval = Duration(seconds: 30);
  static const Duration _reconnectBaseDelay = Duration(seconds: 2);

  Stream<Map<String, dynamic>> get messages => _messageController.stream;
  Stream<WebSocketConnectionState> get connectionState => _stateController.stream;
  WebSocketConnectionState get currentState => _state;
  bool get isConnected => _state == WebSocketConnectionState.connected;

  Future<void> connect(String url) async {
    _url = url;
    await _attemptConnection();
  }

  Future<void> disconnect() async {
    _setState(WebSocketConnectionState.disconnected);
    _stopHeartbeat();
    _stopReconnectTimer();
    
    await _channel?.sink.close();
    _channel = null;
    _reconnectAttempts = 0;
  }

  void sendMessage(Map<String, dynamic> message) {
    if (isConnected && _channel != null) {
      try {
        _channel!.sink.add(json.encode(message));
      } catch (e) {
        debugPrint('Failed to send message: $e');
        _queueMessage(message);
      }
    } else {
      _queueMessage(message);
    }
  }

  Future<void> _attemptConnection() async {
    if (_state == WebSocketConnectionState.connecting || 
        _state == WebSocketConnectionState.reconnecting) {
      return;
    }

    _setState(_reconnectAttempts == 0 
        ? WebSocketConnectionState.connecting 
        : WebSocketConnectionState.reconnecting);

    try {
      _channel = IOWebSocketChannel.connect(_url!);
      await _channel!.ready;
      
      _setState(WebSocketConnectionState.connected);
      _reconnectAttempts = 0;
      
      _setupMessageHandling();
      _startHeartbeat();
      _flushMessageQueue();
      
    } catch (e) {
      debugPrint('WebSocket connection failed: $e');
      _handleConnectionError();
    }
  }

  void _setupMessageHandling() {
    _channel!.stream.listen(
      (data) {
        try {
          final message = json.decode(data) as Map<String, dynamic>;
          _messageController.add(message);
        } catch (e) {
          debugPrint('Failed to parse WebSocket message: $e');
        }
      },
      onError: (error) {
        debugPrint('WebSocket stream error: $error');
        _handleConnectionError();
      },
      onDone: () {
        debugPrint('WebSocket connection closed');
        _handleConnectionError();
      },
    );
  }

  void _handleConnectionError() {
    _stopHeartbeat();
    _channel = null;
    
    if (_reconnectAttempts < _maxReconnectAttempts) {
      _scheduleReconnection();
    } else {
      _setState(WebSocketConnectionState.disconnected);
      _messageController.addError(
        const WebSocketException('Max reconnection attempts reached'),
      );
    }
  }

  void _scheduleReconnection() {
    _reconnectAttempts++;
    final delay = _calculateReconnectDelay();
    
    _reconnectTimer = Timer(delay, () {
      _attemptConnection();
    });
  }

  Duration _calculateReconnectDelay() {
    // Exponential backoff with jitter
    final exponentialDelay = _reconnectBaseDelay * (1 << _reconnectAttempts);
    final jitter = Duration(
      milliseconds: (exponentialDelay.inMilliseconds * 0.1).round(),
    );
    return exponentialDelay + jitter;
  }

  void _startHeartbeat() {
    _heartbeatTimer = Timer.periodic(_heartbeatInterval, (timer) {
      if (isConnected) {
        sendMessage({'type': 'ping', 'timestamp': DateTime.now().toIso8601String()});
      }
    });
  }

  void _stopHeartbeat() {
    _heartbeatTimer?.cancel();
    _heartbeatTimer = null;
  }

  void _stopReconnectTimer() {
    _reconnectTimer?.cancel();
    _reconnectTimer = null;
  }

  void _queueMessage(Map<String, dynamic> message) {
    _messageQueue.add(message);
    
    // Limit queue size to prevent memory issues
    if (_messageQueue.length > 100) {
      _messageQueue.removeFirst();
    }
  }

  void _flushMessageQueue() {
    while (_messageQueue.isNotEmpty && isConnected) {
      final message = _messageQueue.removeFirst();
      sendMessage(message);
    }
  }

  void _setState(WebSocketConnectionState newState) {
    if (_state != newState) {
      _state = newState;
      _stateController.add(_state);
    }
  }

  void dispose() {
    disconnect();
    _messageController.close();
    _stateController.close();
  }
}
