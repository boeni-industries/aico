import 'dart:async';
import 'dart:developer' as developer;

import 'package:flutter/foundation.dart';
import 'package:stack_trace/stack_trace.dart';

import 'package:aico_frontend/core/logging/models/log_entry.dart';
import 'package:aico_frontend/core/logging/services/log_cache.dart';
import 'package:aico_frontend/core/logging/services/log_transport.dart';

/// Configuration for the AICO logging system
class LoggingConfig {
  final LogLevel minimumLevel;
  final bool enableConsoleOutput;
  final int maxRetries;
  final int batchSize;
  final int batchTimeoutMs;
  final int retryDelayMs;
  final bool enableCompression;
  final int compressionThreshold;
  final bool enableRemoteLogging;
  final bool enableLocalCache;
  final Duration batchInterval;
  final int maxBatchSize;
  final Duration retryDelay;

  const LoggingConfig({
    this.minimumLevel = LogLevel.info,
    this.enableConsoleOutput = true,
    this.maxRetries = 3,
    this.batchSize = 50,
    this.batchTimeoutMs = 5000,
    this.retryDelayMs = 1000,
    this.enableCompression = true,
    this.compressionThreshold = 1024,
    this.enableRemoteLogging = true,
    this.enableLocalCache = true,
    this.batchInterval = const Duration(seconds: 5),
    this.maxBatchSize = 50,
    this.retryDelay = const Duration(seconds: 30),
  });
}

/// Main AICO logging service with Riverpod integration
class AICOLogger {
  final LoggingConfig _config;
  final LogTransport _transport;
  final LogCache _cache;
  
  final List<LogEntry> _pendingLogs = [];
  Timer? _batchTimer;
  Timer? _retryTimer;
  int _retryCount = 0;
  
  static AICOLogger? _instance;
  
  AICOLogger._({
    required LoggingConfig config,
    required LogTransport transport,
    required LogCache cache,
  }) : _config = config,
       _transport = transport,
       _cache = cache;

  /// Initialize the global logger instance
  static Future<void> initialize({
    required LoggingConfig config,
    required LogTransport transport,
    required LogCache cache,
  }) async {
    _instance = AICOLogger._(
      config: config,
      transport: transport,
      cache: cache,
    );
    
    await _instance!._initialize();
  }

  /// Get the global logger instance
  static AICOLogger? get instanceOrNull {
    return _instance;
  }

  /// Get the global logger instance
  static AICOLogger get instance {
    if (_instance == null) {
      throw StateError('AICOLogger not initialized. Call AICOLogger.initialize() first.');
    }
    return _instance!;
  }

  /// Internal initialization
  Future<void> _initialize() async {
    await _cache.initialize();
    await _transport.initialize();
    
    // Start batch processing timer
    _startBatchTimer();
    
    // Process any cached logs from previous sessions
    _processCachedLogs();
  }

  /// Start the batch processing timer
  void _startBatchTimer() {
    _batchTimer?.cancel();
    _batchTimer = Timer.periodic(_config.batchInterval, (_) => _processPendingLogs());
  }

  /// Process cached logs from previous sessions
  Future<void> _processCachedLogs() async {
    if (!_config.enableRemoteLogging) return;
    
    try {
      final cachedLogs = await _cache.getPendingLogs(limit: _config.maxBatchSize);
      if (cachedLogs.isNotEmpty) {
        final result = await _transport.sendBatch(cachedLogs);
        if (result.success) {
          await _cache.markAsUploaded(cachedLogs);
        }
      }
    } catch (e) {
      debugPrint('Failed to process cached logs: $e');
    }
  }

  /// Log a debug message
  static void debug(
    String message, {
    String? topic,
    String? traceId,
    String? sessionId,
    Map<String, dynamic>? extra,
  }) {
    _log(LogLevel.debug, message, topic: topic, traceId: traceId, sessionId: sessionId, extra: extra);
  }

  /// Log an info message
  static void info(
    String message, {
    String? topic,
    String? traceId,
    String? sessionId,
    Map<String, dynamic>? extra,
  }) {
    _log(LogLevel.info, message, topic: topic, traceId: traceId, sessionId: sessionId, extra: extra);
  }

  /// Log a warning message
  static void warn(
    String message, {
    String? topic,
    String? traceId,
    String? sessionId,
    Map<String, dynamic>? extra,
  }) {
    _log(LogLevel.warn, message, topic: topic, traceId: traceId, sessionId: sessionId, extra: extra);
  }

  /// Log an error message
  static void error(
    String message, {
    String? topic,
    String? traceId,
    String? sessionId,
    Map<String, dynamic>? extra,
    Object? error,
    StackTrace? stackTrace,
  }) {
    Map<String, dynamic>? errorDetails;
    if (error != null) {
      errorDetails = {
        'type': error.runtimeType.toString(),
        'message': error.toString(),
        if (stackTrace != null) 'stack': Trace.from(stackTrace).toString(),
      };
    }
    
    _log(
      LogLevel.error, 
      message, 
      topic: topic, 
      traceId: traceId, 
      sessionId: sessionId, 
      extra: extra,
      errorDetails: errorDetails,
    );
  }

  /// Log a fatal message
  static void fatal(
    String message, {
    String? topic,
    String? traceId,
    String? sessionId,
    Map<String, dynamic>? extra,
    Object? error,
    StackTrace? stackTrace,
  }) {
    Map<String, dynamic>? errorDetails;
    if (error != null) {
      errorDetails = {
        'type': error.runtimeType.toString(),
        'message': error.toString(),
        if (stackTrace != null) 'stack': Trace.from(stackTrace).toString(),
      };
    }
    
    _log(
      LogLevel.fatal, 
      message, 
      topic: topic, 
      traceId: traceId, 
      sessionId: sessionId, 
      extra: extra,
      errorDetails: errorDetails,
    );
  }

  /// Internal logging method with automatic context detection
  static void _log(
    LogLevel level,
    String message, {
    String? topic,
    String? traceId,
    String? sessionId,
    Map<String, dynamic>? extra,
    Map<String, dynamic>? errorDetails,
  }) {
    final logger = _instance;
    if (logger == null) {
      // Fallback to console if logger not initialized
      debugPrint('[$level] $message');
      return;
    }

    // Check if this level should be logged
    if (!level.shouldLog(logger._config.minimumLevel)) {
      return;
    }

    // Get caller context automatically
    final frame = Trace.current().frames[2]; // Skip _log and the public method
    final module = _extractModuleName(frame.uri);
    final function = frame.member ?? 'unknown';
    final file = frame.uri.pathSegments.isNotEmpty ? frame.uri.pathSegments.last : null;
    final line = frame.line;

    final entry = LogEntry(
      timestamp: DateTime.now().toIso8601String(),
      level: level,
      module: module,
      function: function,
      topic: topic ?? _generateTopic(module, function),
      message: message,
      file: file,
      line: line,
      traceId: traceId,
      sessionId: sessionId,
      extra: extra,
      errorDetails: errorDetails,
    );

    logger._processLogEntry(entry);
  }

  /// Extract module name from library URI
  static String _extractModuleName(Uri library) {
    final segments = library.pathSegments;
    if (segments.isEmpty) return 'frontend.unknown';
    
    // Find the lib segment and extract module path
    final libIndex = segments.indexOf('lib');
    if (libIndex == -1 || libIndex >= segments.length - 1) {
      return 'frontend.${segments.last}';
    }
    
    final moduleSegments = segments.sublist(libIndex + 1);
    // Remove .dart extension from last segment
    if (moduleSegments.isNotEmpty) {
      final lastSegment = moduleSegments.last;
      if (lastSegment.endsWith('.dart')) {
        moduleSegments[moduleSegments.length - 1] = lastSegment.substring(0, lastSegment.length - 5);
      }
    }
    
    return 'frontend.${moduleSegments.join('.')}';
  }

  /// Generate topic from module and function
  static String _generateTopic(String module, String function) {
    final moduleParts = module.split('.');
    if (moduleParts.length >= 2) {
      final category = moduleParts[1]; // e.g., 'ui', 'api', 'storage'
      return '$category.${function.toLowerCase()}';
    }
    return 'app.${function.toLowerCase()}';
  }

  /// Process a log entry through the pipeline
  void _processLogEntry(LogEntry entry) {
    // Console output if enabled
    if (_config.enableConsoleOutput) {
      _outputToConsole(entry);
    }

    // Add to local cache if enabled
    if (_config.enableLocalCache) {
      _cache.addLog(entry);
    }

    // Add to pending batch for remote logging
    if (_config.enableRemoteLogging) {
      _pendingLogs.add(entry);
      
      // Process immediately if batch is full
      if (_pendingLogs.length >= _config.maxBatchSize) {
        _processPendingLogs();
      }
    }
  }

  /// Output log entry to console
  void _outputToConsole(LogEntry entry) {
    final levelStr = entry.level.name.toUpperCase().padRight(5);
    final moduleStr = entry.module.padRight(25);
    final message = '[$levelStr] $moduleStr ${entry.function}: ${entry.message}';
    
    if (kDebugMode) {
      switch (entry.level) {
        case LogLevel.debug:
          debugPrint(message);
          break;
        case LogLevel.info:
          debugPrint(message);
          break;
        case LogLevel.warn:
          debugPrint('⚠️ $message');
          break;
        case LogLevel.error:
          debugPrint('❌ $message');
          break;
        case LogLevel.fatal:
          debugPrint('💀 $message');
          break;
      }
    }

    // Also log to developer console for better debugging
    developer.log(
      entry.message,
      name: entry.module,
      level: entry.level.priority * 200, // Convert to developer log levels
      error: entry.errorDetails?['message'],
      stackTrace: entry.errorDetails?['stack'] != null 
          ? StackTrace.fromString(entry.errorDetails!['stack'])
          : null,
    );
  }

  /// Process pending logs in batch
  Future<void> _processPendingLogs() async {
    if (_pendingLogs.isEmpty || !_config.enableRemoteLogging) return;

    final batch = List<LogEntry>.from(_pendingLogs);
    _pendingLogs.clear();

    try {
      final result = await _transport.sendBatch(batch);
      if (result.success) {
        _retryCount = 0;
        _retryTimer?.cancel();
        
        // Mark as uploaded in cache
        if (_config.enableLocalCache) {
          await _cache.markAsUploaded(batch);
        }
      } else {
        // Add back to cache for retry
        if (_config.enableLocalCache) {
          await _cache.addLogs(batch);
        }
        _scheduleRetry();
      }
    } catch (e) {
      // Add back to cache for retry
      if (_config.enableLocalCache) {
        await _cache.addLogs(batch);
      }
      _scheduleRetry();
    }
  }

  /// Schedule retry for failed log uploads
  void _scheduleRetry() {
    if (_retryCount >= _config.maxRetries) {
      debugPrint('Max retries reached for log upload');
      return;
    }

    _retryCount++;
    final delay = Duration(seconds: _config.retryDelay.inSeconds * _retryCount);
    
    _retryTimer?.cancel();
    _retryTimer = Timer(delay, () async {
      try {
        final cachedLogs = await _cache.getPendingLogs(limit: _config.maxBatchSize);
        if (cachedLogs.isNotEmpty) {
          final result = await _transport.sendBatch(cachedLogs);
          if (result.success) {
            await _cache.markAsUploaded(cachedLogs);
            _retryCount = 0;
          } else {
            _scheduleRetry();
          }
        }
      } catch (e) {
        _scheduleRetry();
      }
    });
  }

  /// Get logging statistics
  Future<Map<String, dynamic>> getStats() async {
    final cacheStats = await _cache.getStats();
    return {
      'transport_status': _transport.status.name,
      'pending_batch_size': _pendingLogs.length,
      'retry_count': _retryCount,
      'config': {
        'minimum_level': _config.minimumLevel.name,
        'console_output': _config.enableConsoleOutput,
        'remote_logging': _config.enableRemoteLogging,
        'local_cache': _config.enableLocalCache,
      },
      'cache': cacheStats,
    };
  }

  /// Cleanup and dispose resources
  Future<void> dispose() async {
    _batchTimer?.cancel();
    _retryTimer?.cancel();
    
    // Process any remaining logs
    if (_pendingLogs.isNotEmpty) {
      await _processPendingLogs();
    }
    
    await _transport.dispose();
    await _cache.dispose();
    
    _instance = null;
  }
}
