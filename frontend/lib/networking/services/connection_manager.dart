import 'dart:async';

import 'package:aico_frontend/networking/clients/websocket_client.dart';
import 'package:aico_frontend/networking/models/error_models.dart';
import 'package:flutter/foundation.dart';

enum ConnectionMode {
  http,
  websocket,
  ipc, // Future implementation
}

class ConnectionManager {
  // final AicoApiClient _apiClient;
  final WebSocketClient _wsClient;
  
  ConnectionMode _currentMode = ConnectionMode.http;
  bool _isInitialized = false;
  
  static const String _defaultWsUrl = 'ws://localhost:8772';

  ConnectionManager(this._wsClient);

  ConnectionMode get currentMode => _currentMode;
  bool get isInitialized => _isInitialized;

  Future<void> initialize() async {
    if (_isInitialized) return;

    // Try protocols in preference order: IPC -> WebSocket -> HTTP
    if (await _tryIpcConnection()) {
      _currentMode = ConnectionMode.ipc;
    } else if (await _tryWebSocketConnection()) {
      _currentMode = ConnectionMode.websocket;
    } else {
      _currentMode = ConnectionMode.http;
    }

    _isInitialized = true;
    debugPrint('Connection manager initialized with mode: $_currentMode');
  }

  Future<T> execute<T>(Future<T> Function() operation) async {
    if (!_isInitialized) {
      await initialize();
    }

    try {
      return await operation();
    } catch (e) {
      if (_shouldFallback(e)) {
        await _fallbackToNextProtocol();
        return await operation();
      }
      rethrow;
    }
  }

  Future<bool> _tryIpcConnection() async {
    // TODO: Implement IPC connection testing
    // For now, IPC is not available
    return false;
  }

  Future<bool> _tryWebSocketConnection() async {
    try {
      final completer = Completer<bool>();
      Timer? timeoutTimer;

      // Set up connection state listener
      StreamSubscription? stateSubscription;
      stateSubscription = _wsClient.connectionState.listen((state) {
        if (state == WebSocketConnectionState.connected) {
          timeoutTimer?.cancel();
          stateSubscription?.cancel();
          completer.complete(true);
        } else if (state == WebSocketConnectionState.disconnected) {
          timeoutTimer?.cancel();
          stateSubscription?.cancel();
          if (!completer.isCompleted) {
            completer.complete(false);
          }
        }
      });

      // Set connection timeout
      timeoutTimer = Timer(const Duration(seconds: 5), () {
        stateSubscription?.cancel();
        if (!completer.isCompleted) {
          completer.complete(false);
        }
      });

      // Attempt connection
      await _wsClient.connect(_defaultWsUrl);
      
      return await completer.future;
    } catch (e) {
      debugPrint('WebSocket connection test failed: $e');
      return false;
    }
  }

  bool _shouldFallback(dynamic error) {
    if (error is NetworkException) {
      // Fallback on connection errors, but not on auth errors
      return error is ConnectionException || 
             error is ServerException ||
             error is OfflineException;
    }
    return false;
  }

  Future<void> _fallbackToNextProtocol() async {
    switch (_currentMode) {
      case ConnectionMode.ipc:
        if (await _tryWebSocketConnection()) {
          _currentMode = ConnectionMode.websocket;
          debugPrint('Fell back to WebSocket mode');
        } else {
          _currentMode = ConnectionMode.http;
          debugPrint('Fell back to HTTP mode');
        }
        break;
        
      case ConnectionMode.websocket:
        await _wsClient.disconnect();
        _currentMode = ConnectionMode.http;
        debugPrint('Fell back to HTTP mode');
        break;
        
      case ConnectionMode.http:
        // Already at lowest fallback level
        throw const OfflineException('All connection methods failed');
    }
  }

  Future<void> reconnect() async {
    _isInitialized = false;
    
    // Disconnect current connections
    if (_currentMode == ConnectionMode.websocket) {
      await _wsClient.disconnect();
    }
    
    await initialize();
  }

  void dispose() {
    _wsClient.dispose();
  }
}
