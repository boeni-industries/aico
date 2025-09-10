import 'dart:async';
import 'dart:collection';
import 'dart:convert';

import 'package:aico_frontend/core/services/encryption_service.dart';
import 'package:aico_frontend/networking/models/error_models.dart';
import 'package:aico_frontend/networking/services/token_manager.dart';
import 'package:flutter/foundation.dart';
import 'package:web_socket_channel/io.dart';

enum WebSocketConnectionState {
  disconnected,
  connecting,
  connected,
  reconnecting,
}

class WebSocketClient {
  final EncryptionService _encryptionService;
  final TokenManager _tokenManager;
  
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
  bool _encryptionEnabled = false;
  
  WebSocketClient({
    required EncryptionService encryptionService,
    required TokenManager tokenManager,
  }) : _encryptionService = encryptionService,
       _tokenManager = tokenManager;
  
  static const int _maxReconnectAttempts = 5;
  static const Duration _heartbeatInterval = Duration(seconds: 30);
  static const Duration _reconnectBaseDelay = Duration(seconds: 2);

  Stream<Map<String, dynamic>> get messages => _messageController.stream;
  Stream<WebSocketConnectionState> get connectionState => _stateController.stream;
  WebSocketConnectionState get currentState => _state;
  bool get isConnected => _state == WebSocketConnectionState.connected;

  Future<void> connect(String url, {bool enableEncryption = true}) async {
    _url = url;
    _encryptionEnabled = enableEncryption;
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
        final messageToSend = _encryptionEnabled 
            ? _encryptMessage(message)
            : message;
        _channel!.sink.add(json.encode(messageToSend));
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
      final headers = await _buildHeaders();
      _channel = IOWebSocketChannel.connect(_url!, headers: headers);
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
          final rawMessage = json.decode(data) as Map<String, dynamic>;
          final message = _encryptionEnabled 
              ? _decryptMessage(rawMessage)
              : rawMessage;
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

  Future<Map<String, String>> _buildHeaders() async {
    final headers = <String, String>{};
    
    // Add authentication token if available
    final token = await _tokenManager.getAccessToken();
    if (token != null) {
      headers['Authorization'] = 'Bearer $token';
    }
    
    // Add encryption capability header
    if (_encryptionEnabled && _encryptionService.isInitialized) {
      headers['X-Encryption-Supported'] = 'true';
      final publicKey = _encryptionService.getPublicKey();
      if (publicKey != null) {
        headers['X-Public-Key'] = publicKey;
      }
    }
    
    return headers;
  }
  
  Map<String, dynamic> _encryptMessage(Map<String, dynamic> message) {
    if (!_encryptionService.isInitialized) {
      return message;
    }
    
    try {
      final encryptedData = _encryptionService.encryptPayload(message);
      return {
        'encrypted': true,
        'data': encryptedData,
        'timestamp': DateTime.now().toIso8601String(),
      };
    } catch (e) {
      debugPrint('Failed to encrypt WebSocket message: $e');
      return message;
    }
  }
  
  Map<String, dynamic> _decryptMessage(Map<String, dynamic> message) {
    if (!message.containsKey('encrypted') || message['encrypted'] != true) {
      return message;
    }
    
    if (!_encryptionService.isInitialized) {
      throw Exception('Received encrypted message but encryption service not initialized');
    }
    
    try {
      final encryptedData = message['data'] as String;
      return _encryptionService.decryptPayload(encryptedData);
    } catch (e) {
      debugPrint('Failed to decrypt WebSocket message: $e');
      throw Exception('Failed to decrypt message: $e');
    }
  }
  
  Future<void> dispose() async {
    await disconnect();
    await _messageController.close();
    await _stateController.close();
  }
}
