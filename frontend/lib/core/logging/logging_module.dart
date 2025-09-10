import 'package:aico_frontend/core/di/modules/di_module.dart';
import 'package:aico_frontend/core/logging/models/log_entry.dart';
import 'package:aico_frontend/core/logging/repositories/http_log_repository.dart';
import 'package:aico_frontend/core/logging/repositories/log_repository.dart';
import 'package:aico_frontend/core/logging/services/logging_service.dart';
import 'package:aico_frontend/networking/clients/unified_api_client.dart';
import 'package:get_it/get_it.dart';
// import 'package:aico_frontend/core/logging/repositories/websocket_log_repository.dart'; // Available for future use

/// Dependency injection setup for logging module
class LoggingModule implements DIModule {
  @override
  String get name => 'LoggingModule';

  @override
  Future<void> register(GetIt getIt) async {
    // Register repository based on configuration
    getIt.registerLazySingleton<LogRepository>(() {
      final apiClient = getIt<UnifiedApiClient>();
      
      // Primary: HTTP repository with fallback capability
      return HttpLogRepository(apiClient: apiClient);
      
      // Alternative: WebSocket repository
      // return WebSocketLogRepository(wsUrl: 'ws://localhost:8772/ws/logs');
    });

    // Register logging service
    getIt.registerLazySingleton<LoggingService>(() {
      return LoggingService(
        repository: getIt<LogRepository>(),
        config: const LoggingConfig(
          maxBufferSize: 1000,
          batchInterval: Duration(seconds: 5),
          retryInterval: Duration(seconds: 30),
          enableLocalFallback: true,
          minimumLevel: LogLevel.info,
        ),
      );
    });
  }

  @override
  Future<void> dispose(GetIt getIt) async {
    if (getIt.isRegistered<LoggingService>()) {
      await getIt<LoggingService>().dispose();
    }
  }
}

/// Global logging helper functions
class Log {
  static LoggingService get _service => GetIt.instance<LoggingService>();

  /// Debug level logging
  static Future<void> d(String module, String topic, String message, {
    String? function,
    Map<String, dynamic>? extra,
  }) => _service.debug(module, topic, message, function: function, extra: extra);

  /// Info level logging
  static Future<void> i(String module, String topic, String message, {
    String? function,
    Map<String, dynamic>? extra,
  }) => _service.info(module, topic, message, function: function, extra: extra);

  /// Warning level logging
  static Future<void> w(String module, String topic, String message, {
    String? function,
    Map<String, dynamic>? extra,
  }) => _service.warning(module, topic, message, function: function, extra: extra);

  /// Error level logging
  static Future<void> e(String module, String topic, String message, {
    String? function,
    Object? error,
    StackTrace? stackTrace,
    Map<String, dynamic>? extra,
  }) => _service.error(
    module, 
    topic, 
    message, 
    function: function, 
    error: error, 
    stackTrace: stackTrace, 
    extra: extra,
  );

  /// Set user context
  static void setUser({String? userId, String? sessionId}) {
    _service.setUserContext(userId: userId, sessionId: sessionId);
  }

  /// Set environment
  static void setEnvironment(String environment) {
    _service.setEnvironment(environment);
  }

  /// Flush all logs
  static Future<void> flush() => _service.flush();

  /// Get buffer status
  static Map<String, int> get bufferStatus => _service.bufferStatus;
}
