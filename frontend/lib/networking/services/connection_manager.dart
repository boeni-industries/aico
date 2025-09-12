import 'dart:async';
import 'dart:io';
import 'dart:math';

import 'package:aico_frontend/core/logging/aico_log.dart';
import 'package:aico_frontend/core/services/encryption_service.dart';
import 'package:aico_frontend/networking/clients/websocket_client.dart';
import 'package:aico_frontend/networking/exceptions/api_exceptions.dart';
import 'package:connectivity_plus/connectivity_plus.dart';

enum ConnectionMode {
  http,
  websocket,
  ipc, // Future implementation
}

enum InternalConnectionStatus {
  connected,
  connecting,
  disconnected,
  offline,
  error,
}

class ConnectionHealth {
  final InternalConnectionStatus status;
  final DateTime lastSuccessful;
  final int consecutiveFailures;
  final String? lastError;
  final Duration? latency;

  const ConnectionHealth({
    required this.status,
    required this.lastSuccessful,
    this.consecutiveFailures = 0,
    this.lastError,
    this.latency,
  });

  bool get isHealthy => status == InternalConnectionStatus.connected && consecutiveFailures < 3;
  bool get needsReconnection => consecutiveFailures >= 3 || status == InternalConnectionStatus.error;
}

class ConnectionManager {
  final WebSocketClient _wsClient;
  final EncryptionService _encryptionService;
  final Connectivity _connectivity = Connectivity();
  
  ConnectionMode _currentMode = ConnectionMode.http; // REST-first architecture
  bool _isInitialized = false;
  
  // Connection health monitoring
  ConnectionHealth _health = ConnectionHealth(
    status: InternalConnectionStatus.disconnected,
    lastSuccessful: DateTime.now(),
  );
  
  // Retry configuration
  static const int _maxRetries = 5;
  static const Duration _baseRetryDelay = Duration(seconds: 1);
  static const Duration _healthCheckInterval = Duration(seconds: 15);
  static const Duration _maxRetryDelay = Duration(seconds: 30);
  
  // Connection monitoring
  Timer? _healthCheckTimer;
  Timer? _reconnectTimer;
  StreamSubscription? _connectivitySubscription;
  
  // Status streams
  final StreamController<ConnectionHealth> _healthController = StreamController<ConnectionHealth>.broadcast();
  final StreamController<bool> _offlineController = StreamController<bool>.broadcast();
  
  static const String _defaultWsUrl = 'ws://localhost:8772';
  static const String _defaultHttpUrl = 'http://localhost:8771';

  ConnectionManager(this._wsClient, this._encryptionService) {
    _initializeConnectivityMonitoring();
  }

  ConnectionMode get currentMode => _currentMode;
  bool get isInitialized => _isInitialized;
  ConnectionHealth get health => _health;
  Stream<ConnectionHealth> get healthStream => _healthController.stream;
  Stream<bool> get offlineStream => _offlineController.stream;
  bool get isOnline => _health.status != InternalConnectionStatus.offline;
  bool get isConnected => _health.status == InternalConnectionStatus.connected;

  Future<void> initialize() async {
    if (_isInitialized) return;

    updateHealth(InternalConnectionStatus.connecting);
    
    // Check network connectivity first
    final connectivityResult = await _connectivity.checkConnectivity();
    if (connectivityResult.contains(ConnectivityResult.none)) {
      updateHealth(InternalConnectionStatus.offline);
      _isInitialized = true;
      return;
    }

    // Try protocols in REST-first preference order with retry logic
    bool connected = false;
    
    for (int attempt = 0; attempt < _maxRetries && !connected; attempt++) {
      // REST/HTTP first for primary communication
      if (await _tryHttpConnection()) {
        _currentMode = ConnectionMode.http;
        connected = true;
      } else if (await _tryWebSocketConnection()) {
        _currentMode = ConnectionMode.websocket;
        connected = true;
      } else if (await _tryIpcConnection()) {
        _currentMode = ConnectionMode.ipc;
        connected = true;
      }
      
      if (!connected && attempt < _maxRetries - 1) {
        final delay = _calculateRetryDelay(attempt);
        AICOLog.warn('Connection attempt ${attempt + 1} failed, retrying in ${delay.inSeconds}s',
          topic: 'network/connection/retry');
        await Future.delayed(delay);
      }
    }

    if (connected) {
      updateHealth(InternalConnectionStatus.connected);
      _startHealthMonitoring();
    } else {
      updateHealth(InternalConnectionStatus.error, 'All connection attempts failed');
    }

    _isInitialized = true;
    AICOLog.info('Connection manager initialized', 
      topic: 'network/connection/init',
      extra: {
        'mode': _currentMode.toString(),
        'status': _health.status.toString(),
        'connected': connected
      });
  }

  Future<T> executeWithRetry<T>(Future<T> Function() operation, {
    int maxRetries = 3,
    Duration? timeout,
  }) async {
    if (!_isInitialized) {
      await initialize();
    }

    // Check if we're offline
    if (_health.status == InternalConnectionStatus.offline) {
      throw const OfflineException('Device is offline');
    }

    Exception? lastException;
    
    for (int attempt = 0; attempt <= maxRetries; attempt++) {
      try {
        final Future<T> future = operation();
        final T result = await future;
        
        // Success - update health
        if (_health.consecutiveFailures > 0) {
          updateHealth(InternalConnectionStatus.connected);
        }
        
        return result;
        
      } catch (e) {
        lastException = e is Exception ? e : Exception(e.toString());
        
        // Gracefully handle connection errors - update status immediately
        InternalConnectionStatus newStatus = InternalConnectionStatus.error;
        if (e is SocketException || e.toString().contains('connection refused')) {
          newStatus = InternalConnectionStatus.disconnected;
          // Schedule background reconnection
          _scheduleReconnect();
        }
        
        updateHealth(newStatus, e.toString(), _health.consecutiveFailures + 1);
        
        AICOLog.warn('Operation attempt ${attempt + 1} failed',
          topic: 'network/connection/retry',
          extra: {
            'error': e.toString(),
            'attempt': attempt + 1,
            'max_retries': maxRetries
          });
        
        // Check if we should fallback or retry
        if (_shouldFallback(e)) {
          if (await _fallbackToNextProtocol()) {
            // Fallback successful, try operation again
            continue;
          }
        }
        
        // If this isn't the last attempt, wait before retrying
        if (attempt < maxRetries) {
          final delay = _calculateRetryDelay(attempt);
          await Future.delayed(delay);
        }
      }
    }
    
    // All attempts failed - gracefully handle without throwing
    final finalStatus = lastException.toString().contains('connection refused') 
        ? InternalConnectionStatus.disconnected 
        : InternalConnectionStatus.error;
    updateHealth(finalStatus, lastException?.toString());
    
    // Return a graceful failure instead of throwing
    throw lastException ?? Exception('Operation failed after all retries');
  }

  Future<bool> _tryIpcConnection() async {
    // TODO: Implement IPC connection testing
    // For now, IPC is not available
    return false;
  }

  Future<bool> _tryWebSocketConnection() async {
    try {
      final stopwatch = Stopwatch()..start();
      final completer = Completer<bool>();
      Timer? timeoutTimer;

      // Set up connection state listener
      StreamSubscription? stateSubscription;
      stateSubscription = _wsClient.connectionState.listen((state) {
        if (state == WebSocketConnectionState.connected) {
          stopwatch.stop();
          timeoutTimer?.cancel();
          stateSubscription?.cancel();
          
          // Update health with latency info
          updateHealth(
            InternalConnectionStatus.connected,
            null,
            0,
            stopwatch.elapsed,
          );
          
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
      timeoutTimer = Timer(const Duration(seconds: 10), () {
        stateSubscription?.cancel();
        if (!completer.isCompleted) {
          completer.complete(false);
        }
      });

      // Attempt connection
      await _wsClient.connect(_defaultWsUrl);
      
      return await completer.future;
    } catch (e) {
      AICOLog.debug('WebSocket connection test failed', 
        topic: 'network/connection/websocket_test',
        extra: {'error': e.toString()});
      return false;
    }
  }
  
  Future<bool> _tryHttpConnection() async {
    HttpClient? client;
    try {
      final stopwatch = Stopwatch()..start();
      
      // Use HttpClient directly to avoid Dio's debugger exception issues
      client = HttpClient();
      client.connectionTimeout = const Duration(seconds: 3);
      
      final request = await client.getUrl(Uri.parse('$_defaultHttpUrl/api/v1/health'));
      final response = await request.close();
      
      stopwatch.stop();
      
      if (response.statusCode == 200) {
        updateHealth(
          InternalConnectionStatus.connected,
          null,
          0,
          stopwatch.elapsed,
        );
        return true;
      }
      
      return false;
    } catch (e) {
      // Gracefully handle ALL connection errors including timeouts
      updateHealth(InternalConnectionStatus.error, e.toString());
      AICOLog.debug('HTTP connection test failed',
        topic: 'network/connection/http_test', 
        extra: {'error': e.toString()});
      return false;
    } finally {
      client?.close(force: true);
    }
  }

  bool _shouldFallback(dynamic error) {
    if (error is ApiException) {
      // Fallback on connection errors, but not on auth errors
      return error is ConnectionException || 
             error is ServerException ||
             error is OfflineException;
    }
    
    // Handle SocketException and connection refused errors
    if (error is SocketException || error.toString().contains('connection refused')) {
      return true;
    }
    
    return false;
  }

  Future<bool> _fallbackToNextProtocol() async {
    AICOLog.info('Attempting protocol fallback',
      topic: 'network/connection/fallback',
      extra: {'current_mode': _currentMode.toString()});
      
    switch (_currentMode) {
      case ConnectionMode.ipc:
        if (await _tryWebSocketConnection()) {
          _currentMode = ConnectionMode.websocket;
          AICOLog.info('Fell back to WebSocket mode', topic: 'network/connection/fallback');
          return true;
        } else if (await _tryHttpConnection()) {
          _currentMode = ConnectionMode.http;
          AICOLog.info('Fell back to HTTP mode', topic: 'network/connection/fallback');
          return true;
        }
        break;
        
      case ConnectionMode.websocket:
        await _wsClient.disconnect();
        if (await _tryHttpConnection()) {
          _currentMode = ConnectionMode.http;
          AICOLog.info('Fell back to HTTP mode', topic: 'network/connection/fallback');
          return true;
        }
        break;
        
      case ConnectionMode.http:
        // Already at lowest fallback level
        AICOLog.error('All connection methods failed', topic: 'network/connection/fallback');
        return false;
    }
    
    return false;
  }

  Future<void> reconnect() async {
    AICOLog.info('Initiating reconnection', topic: 'network/connection/reconnect');
    
    _stopHealthMonitoring();
    _isInitialized = false;
    
    // Disconnect current connections
    if (_currentMode == ConnectionMode.websocket) {
      await _wsClient.disconnect();
    }
    
    await initialize();
  }
  
  void _initializeConnectivityMonitoring() {
    _connectivitySubscription = _connectivity.onConnectivityChanged.listen((result) {
      if (result.contains(ConnectivityResult.none)) {
        updateHealth(InternalConnectionStatus.offline);
        _offlineController.add(true);
      } else {
        _offlineController.add(false);
        // If we were offline and now have connectivity, try to reconnect
        if (_health.status == InternalConnectionStatus.offline) {
          _scheduleReconnect();
        }
      }
    });
  }
  
  void _startHealthMonitoring() {
    _healthCheckTimer?.cancel();
    _healthCheckTimer = Timer.periodic(_healthCheckInterval, (_) {
      _performHealthCheck();
    });
  }
  
  void _stopHealthMonitoring() {
    _healthCheckTimer?.cancel();
    _reconnectTimer?.cancel();
  }
  
  Future<void> _performHealthCheck() async {
    if (_health.status == InternalConnectionStatus.offline) return;
    
    try {
      bool isHealthy = false;
      
      switch (_currentMode) {
        case ConnectionMode.websocket:
          isHealthy = _wsClient.currentState == WebSocketConnectionState.connected;
          break;
        case ConnectionMode.http:
          isHealthy = await _tryHttpConnection();
          break;
        case ConnectionMode.ipc:
          isHealthy = await _tryIpcConnection();
          break;
      }
      
      if (!isHealthy && _health.status == InternalConnectionStatus.connected) {
        updateHealth(InternalConnectionStatus.disconnected, 'Health check failed - backend unavailable');
        _scheduleReconnect();
      } else if (isHealthy && _health.status != InternalConnectionStatus.connected) {
        // Backend came back online - reset encryption session since backend lost all sessions
        if (_encryptionService.isSessionActive) {
          AICOLog.info('Backend reconnected - resetting encryption session', 
            topic: 'network/connection/encryption_reset');
          _encryptionService.resetSession();
        }
        updateHealth(InternalConnectionStatus.connected, null, 0);
      }
    } catch (e) {
      // Gracefully handle health check failures
      updateHealth(InternalConnectionStatus.disconnected, 'Health check failed: ${e.toString()}');
      _scheduleReconnect();
      AICOLog.warn('Health check failed', 
        topic: 'network/connection/health_check',
        extra: {'error': e.toString()});
    }
  }
  
  void _scheduleReconnect() {
    if (_reconnectTimer?.isActive == true) return;
    
    final delay = _calculateRetryDelay(_health.consecutiveFailures);
    AICOLog.info('Scheduling reconnection',
      topic: 'network/connection/schedule_reconnect',
      extra: {'delay_seconds': delay.inSeconds});
      
    _reconnectTimer = Timer(delay, () {
      reconnect();
    });
  }
  
  Duration _calculateRetryDelay(int attempt) {
    // Exponential backoff with jitter
    final baseDelay = _baseRetryDelay.inMilliseconds;
    final exponentialDelay = baseDelay * pow(2, attempt).toInt();
    final jitter = Random().nextInt(1000); // 0-1000ms jitter
    final totalDelay = exponentialDelay + jitter;
    
    return Duration(
      milliseconds: totalDelay.clamp(baseDelay, _maxRetryDelay.inMilliseconds)
    );
  }
  
  void updateHealth(
    InternalConnectionStatus status, [
    String? error,
    int? consecutiveFailures,
    Duration? latency,
  ]) {
    _health = ConnectionHealth(
      status: status,
      lastSuccessful: status == InternalConnectionStatus.connected 
        ? DateTime.now() 
        : _health.lastSuccessful,
      consecutiveFailures: consecutiveFailures ?? 
        (status == InternalConnectionStatus.connected ? 0 : _health.consecutiveFailures),
      lastError: error,
      latency: latency ?? _health.latency,
    );
    
    _healthController.add(_health);
    
    AICOLog.debug('Connection health updated',
      topic: 'network/connection/health',
      extra: {
        'status': status.toString(),
        'consecutive_failures': _health.consecutiveFailures,
        'last_error': error,
        'latency_ms': latency?.inMilliseconds,
      });
  }

  void dispose() {
    _stopHealthMonitoring();
    _connectivitySubscription?.cancel();
    _healthController.close();
    _offlineController.close();
    _wsClient.dispose();
  }
}
