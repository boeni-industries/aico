import 'dart:async';
import 'dart:io';
import 'dart:math' as math;

import 'package:aico_frontend/core/logging/aico_log.dart';
import 'package:aico_frontend/core/providers/networking_providers.dart';
import 'package:aico_frontend/networking/services/connection_manager.dart';
import 'package:riverpod_annotation/riverpod_annotation.dart';
import 'package:shared_preferences/shared_preferences.dart';

part 'startup_connection_provider.g.dart';

enum StartupConnectionPhase {
  initializing,
  connecting,      // Initial attempt only (purple ring)
  retryMode,      // All retry attempts (amber ring)
  connected,
  failed,
}

class StartupConnectionState {
  final StartupConnectionPhase phase;
  final int currentAttempt;
  final int maxAttempts;
  final String? message;
  final String? error;
  final bool canRetry;

  const StartupConnectionState({
    this.phase = StartupConnectionPhase.initializing,
    this.currentAttempt = 0,
    this.maxAttempts = 3,
    this.message,
    this.error,
    this.canRetry = false,
  });

  StartupConnectionState copyWith({
    StartupConnectionPhase? phase,
    int? currentAttempt,
    int? maxAttempts,
    String? message,
    String? error,
    bool? canRetry,
  }) {
    return StartupConnectionState(
      phase: phase ?? this.phase,
      currentAttempt: currentAttempt ?? this.currentAttempt,
      maxAttempts: maxAttempts ?? this.maxAttempts,
      message: message ?? this.message,
      error: error,
      canRetry: canRetry ?? this.canRetry,
    );
  }

  bool get isConnected => phase == StartupConnectionPhase.connected;
  bool get isFailed => phase == StartupConnectionPhase.failed;
  bool get isInProgress => phase == StartupConnectionPhase.connecting || 
                          phase == StartupConnectionPhase.retryMode;
}

@riverpod
class StartupConnectionNotifier extends _$StartupConnectionNotifier {
  late final ConnectionManager _connectionManager;
  Timer? _retryTimer;
  Timer? _phaseTimer;

  static const String _defaultApiBaseUrl = 'http://localhost:8771/api/v1';
  static const String _settingsApiBaseUrlKey = 'settings_api_base_url';

  @override
  StartupConnectionState build() {
    _connectionManager = ref.watch(connectionManagerProvider);
    
    // Schedule initialization after build completes
    Future.microtask(() => _initializeConnection());
    
    return const StartupConnectionState(
      phase: StartupConnectionPhase.initializing,
      message: 'Initializing connection...',
    );
  }

  void _initializeConnection() {
    AICOLog.info('Starting startup connection flow', topic: 'startup/connection/init');

    // Start the connection attempt after brief initialization
    _phaseTimer = Timer(const Duration(milliseconds: 800), () {
      _attemptConnection();
    });
  }

  Future<void> _attemptConnection() async {
    try {
      AICOLog.info('Connection attempt ${state.currentAttempt}/${state.maxAttempts}', 
        topic: 'startup/connection/attempt');

      // For initial attempt, show connecting state
      if (state.currentAttempt == 0) {
        state = state.copyWith(
          phase: StartupConnectionPhase.connecting,
          message: 'Connecting to AICO...',
        );

        // Fixed 4-second duration for initial attempt
        final connectingStart = DateTime.now();
        const initialAttemptDuration = Duration(seconds: 4);

        // Test connection with isolated HTTP request
        final isConnected = await _testConnection();
        
        // Ensure full 4 seconds for visual feedback
        final elapsed = DateTime.now().difference(connectingStart);
        if (elapsed < initialAttemptDuration) {
          await Future.delayed(initialAttemptDuration - elapsed);
        }

        if (isConnected) {
          // Initialize ConnectionManager on successful connection
          await _connectionManager.initialize();
          _handleConnectionSuccess();
        } else {
          // Move to retry mode after initial failure
          _handleConnectionFailure('Initial connection failed');
        }
      } else {
        // For retry attempts, we're already in retryMode
        final isConnected = await _testConnection();
        
        if (isConnected) {
          await _connectionManager.initialize();
          _handleConnectionSuccess();
        } else {
          _handleConnectionFailure('Connection attempt failed');
        }
      }
    } catch (e) {
      if (state.currentAttempt == 0) {
        _handleConnectionError(e.toString());
      } else {
        _handleConnectionError(e.toString());
      }
    }
  }

  /// Test connection with HttpClient (original approach that worked)
  Future<bool> _testConnection() async {
    HttpClient? client;
    try {
      client = HttpClient();
      client.connectionTimeout = const Duration(seconds: 2);

      final prefs = await SharedPreferences.getInstance();
      final rawBaseUrl = (prefs.getString(_settingsApiBaseUrlKey) ?? _defaultApiBaseUrl).trim();
      final baseUrl = rawBaseUrl.replaceAll(RegExp(r'/+$'), '');
      final healthUrl = '$baseUrl/health';

      final request = await client.getUrl(Uri.parse(healthUrl));
      final response = await request.close();

      return response.statusCode == 200;
    } catch (e) {
      return false;
    } finally {
      client?.close(force: true);
    }
  }


  void _handleConnectionSuccess() {
    AICOLog.info('Startup connection successful', topic: 'startup/connection/success');
    
    _cancelRetryTimer();
    state = state.copyWith(
      phase: StartupConnectionPhase.connected,
      message: 'Connected to AICO',
    );
  }

  void _handleConnectionFailure(String error) {
    if (state.currentAttempt < state.maxAttempts) {
      _scheduleRetry(error);
    } else {
      _handleFinalFailure(error);
    }
  }

  void _handleConnectionError(String error) {
    _handleConnectionFailure(error);
  }

  void _scheduleRetry(String error) {
    final nextAttempt = state.currentAttempt + 1;
    AICOLog.info('Scheduling retry $nextAttempt/${state.maxAttempts}', 
      topic: 'startup/connection/retry');

    state = state.copyWith(
      phase: StartupConnectionPhase.retryMode,
      currentAttempt: nextAttempt,
      message: 'Connection failed. Retrying ($nextAttempt/${state.maxAttempts})...',
      error: error,
    );

    // Show retry state for guaranteed duration (amber ring)
    final retryDelay = _calculateRetryDelay(nextAttempt - 2);
    _retryTimer = Timer(retryDelay, () {
      if (state.phase == StartupConnectionPhase.retryMode) {
        _attemptConnection();
      }
    });
  }

  /// Calculate retry delays using ConnectionManager's exponential backoff pattern
  Duration _calculateRetryDelay(int attempt) {
    // Use ConnectionManager's pattern but with startup-friendly base delay
    const baseDelayMs = 3000; // 3 second base for startup UX
    const maxDelayMs = 12000; // 12 seconds max for reasonable startup time
    
    // Exponential backoff with jitter (following ConnectionManager pattern)
    final exponentialDelay = (baseDelayMs * math.pow(2, attempt)).toInt();
    final jitter = math.Random().nextInt(1000); // 0-1000ms jitter
    final totalDelay = exponentialDelay + jitter;
    
    return Duration(
      milliseconds: totalDelay.clamp(baseDelayMs, maxDelayMs)
    );
  }

  void _handleFinalFailure(String error) {
    AICOLog.error('All startup connection attempts failed', 
      topic: 'startup/connection/failed', 
      error: error);

    _cancelRetryTimer();
    state = state.copyWith(
      phase: StartupConnectionPhase.failed,
      message: 'Unable to connect to AICO backend',
      error: error,
      canRetry: true,
    );
  }

  void retry() {
    AICOLog.info('Manual retry requested', topic: 'startup/connection/manual_retry');
    
    _cancelRetryTimer();
    state = state.copyWith(
      phase: StartupConnectionPhase.connecting,
      currentAttempt: 0, // Reset to 0 so first attempt shows as attempt 1
      message: 'Connecting to AICO...',
      error: null,
      canRetry: false,
    );

    _attemptConnection();
  }

  void _cancelRetryTimer() {
    _retryTimer?.cancel();
    _retryTimer = null;
    _phaseTimer?.cancel();
    _phaseTimer = null;
  }
}
