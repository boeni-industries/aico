import 'package:flutter/foundation.dart';

import 'package:aico_frontend/core/logging/models/log_entry.dart';
import 'package:aico_frontend/core/logging/services/aico_logger.dart';

/// Developer-friendly logging API for AICO
/// 
/// Usage:
/// ```dart
/// AICOLog.info('User logged in successfully');
/// AICOLog.error('Failed to connect to server', error: e, stackTrace: stackTrace);
/// AICOLog.debug('Processing user data', extra: {'userId': user.id});
/// ```
class AICOLog {
  static AICOLogger? get _logger {
    return AICOLogger.instanceOrNull;
  }

  /// Log a debug message
  /// Used for detailed diagnostic information, typically only of interest when diagnosing problems
  static void debug(
    String message, {
    String? topic,
    Object? error,
    StackTrace? stackTrace,
    Map<String, dynamic>? extra,
  }) {
    _log(LogLevel.debug, message, topic, error, stackTrace, extra);
  }

  /// Log an info message
  /// Used for general information about application execution
  static void info(
    String message, {
    String? topic,
    Object? error,
    StackTrace? stackTrace,
    Map<String, dynamic>? extra,
  }) {
    _log(LogLevel.info, message, topic, error, stackTrace, extra);
  }

  /// Log a warning message
  /// Used for potentially harmful situations that don't prevent the application from continuing
  static void warn(
    String message, {
    String? topic,
    Object? error,
    StackTrace? stackTrace,
    Map<String, dynamic>? extra,
  }) {
    _log(LogLevel.warn, message, topic, error, stackTrace, extra);
  }

  /// Log an error message
  /// Used for error events that might still allow the application to continue running
  static void error(
    String message, {
    String? topic,
    Object? error,
    StackTrace? stackTrace,
    Map<String, dynamic>? extra,
  }) {
    _log(LogLevel.error, message, topic, error, stackTrace, extra);
  }

  /// Log a fatal message
  /// Used for very severe error events that will presumably lead the application to abort
  static void fatal(
    String message, {
    String? topic,
    Object? error,
    StackTrace? stackTrace,
    Map<String, dynamic>? extra,
  }) {
    _log(LogLevel.fatal, message, topic, error, stackTrace, extra);
  }

  /// Internal logging method
  static void _log(
    LogLevel level,
    String message,
    String? topic,
    Object? error,
    StackTrace? stackTrace,
    Map<String, dynamic>? extra,
  ) {
    final logger = _logger;
    if (logger == null) {
      // Fallback to debug print if logger not initialized
      if (kDebugMode) {
        debugPrint('[AICO-FALLBACK][${level.name.toUpperCase()}] $message');
        if (topic != null) {
          debugPrint('[AICO-FALLBACK] Topic: $topic');
        }
        if (extra != null) {
          debugPrint('[AICO-FALLBACK] Extra: $extra');
        }
        if (error != null) {
          debugPrint('[AICO-FALLBACK] Error: $error');
        }
        if (stackTrace != null) {
          debugPrint('[AICO-FALLBACK] Stack trace: $stackTrace');
        }
      }
      return;
    }

    // Use the appropriate logger method
    switch (level) {
      case LogLevel.debug:
        AICOLogger.debug(message, topic: topic, extra: extra);
        break;
      case LogLevel.info:
        AICOLogger.info(message, topic: topic, extra: extra);
        break;
      case LogLevel.warn:
        AICOLogger.warn(message, topic: topic, extra: extra);
        break;
      case LogLevel.error:
        AICOLogger.error(message, topic: topic, extra: extra);
        break;
      case LogLevel.fatal:
        AICOLogger.fatal(message, topic: topic, extra: extra);
        break;
    }
  }

  /// Check if a log level is enabled
  static bool isEnabled(LogLevel level) {
    final logger = _logger;
    if (logger == null) return false;
    return true; // Simplified for now
  }

  /// Get current logging statistics
  static Future<Map<String, dynamic>> getStats() async {
    final logger = _logger;
    if (logger == null) return {'status': 'not_initialized'};
    return await logger.getStats();
  }

  /// Flush pending logs immediately
  static Future<void> flush() async {
    final logger = _logger;
    if (logger == null) return;
    // Logger doesn't expose flush method, so we'll skip this for now
  }
}

/// Extension methods for easier logging with context
extension AICOLogContext on Object {
  /// Log a debug message with this object as context
  void logDebug(String message, {Map<String, dynamic>? extra}) {
    AICOLog.debug(message);
  }

  /// Log an info message with this object as context
  void logInfo(String message, {Map<String, dynamic>? extra}) {
    AICOLog.info(message);
  }

  /// Log a warning message with this object as context
  void logWarn(String message, {Object? error, StackTrace? stackTrace, Map<String, dynamic>? extra}) {
    AICOLog.warn(message, error: error, stackTrace: stackTrace);
  }

  /// Log an error message with this object as context
  void logError(String message, {Object? error, StackTrace? stackTrace, Map<String, dynamic>? extra}) {
    AICOLog.error(message, error: error, stackTrace: stackTrace);
  }
}

/// Mixin for classes that need logging capabilities
mixin AICOLoggingMixin {
  /// Log a debug message from this class
  void logDebug(String message, {Map<String, dynamic>? extra}) {
    AICOLog.debug(message);
  }

  /// Log an info message from this class
  void logInfo(String message, {Map<String, dynamic>? extra}) {
    AICOLog.info(message);
  }

  /// Log a warning message from this class
  void logWarn(String message, {Object? error, StackTrace? stackTrace, Map<String, dynamic>? extra}) {
    AICOLog.warn(message, error: error, stackTrace: stackTrace);
  }

  /// Log an error message from this class
  void logError(String message, {Object? error, StackTrace? stackTrace, Map<String, dynamic>? extra}) {
    AICOLog.error(message, error: error, stackTrace: stackTrace);
  }

  /// Log a fatal message from this class
  void logFatal(String message, {Object? error, StackTrace? stackTrace, Map<String, dynamic>? extra}) {
    AICOLog.fatal(message, error: error, stackTrace: stackTrace);
  }
}
