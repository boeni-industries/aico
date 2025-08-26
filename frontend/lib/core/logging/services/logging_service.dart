import 'dart:async';
import 'dart:collection';
import 'dart:io';

import 'package:aico_frontend/core/logging/models/log_entry.dart';
import 'package:aico_frontend/core/logging/repositories/log_repository.dart';
import 'package:aico_frontend/core/utils/aico_paths.dart';
import 'package:flutter/foundation.dart';
import 'package:shared_preferences/shared_preferences.dart';

/// Configuration for logging service behavior
class LoggingConfig {
  final int maxBufferSize;
  final Duration batchInterval;
  final Duration retryInterval;
  final bool enableLocalFallback;
  final LogLevel minimumLevel;

  const LoggingConfig({
    this.maxBufferSize = 1000,
    this.batchInterval = const Duration(seconds: 5),
    this.retryInterval = const Duration(seconds: 30),
    this.enableLocalFallback = true,
    this.minimumLevel = LogLevel.info,
  });
}

/// Main logging service implementing AICO unified logging
class LoggingService {
  final LogRepository _repository;
  final LoggingConfig _config;
  
  // Local buffering
  final Queue<LogEntry> _buffer = Queue();
  final Queue<LogEntry> _failedLogs = Queue();
  
  // Timers and streams
  Timer? _batchTimer;
  Timer? _retryTimer;
  StreamSubscription? _statusSubscription;
  
  // Session and user context
  String? _sessionId;
  String? _userId;
  String? _environment;

  LoggingService({
    required LogRepository repository,
    LoggingConfig? config,
  })  : _repository = repository,
        _config = config ?? const LoggingConfig() {
    _initialize();
  }

  void _initialize() {
    // Listen to log status updates for retry logic
    _statusSubscription = _repository.logStatusStream.listen(_handleLogStatus);
    
    // Start batch timer
    _startBatchTimer();
    
    // Start retry timer
    _startRetryTimer();
    
    // Load session context
    _loadSessionContext();
  }

  Future<void> _loadSessionContext() async {
    try {
      final prefs = await SharedPreferences.getInstance();
      _sessionId = prefs.getString('session_id') ?? _generateSessionId();
      _userId = prefs.getString('user_id');
      _environment = prefs.getString('environment') ?? 'dev';
      
      // Save session ID if newly generated
      if (!prefs.containsKey('session_id')) {
        await prefs.setString('session_id', _sessionId!);
      }
    } catch (e) {
      _sessionId = _generateSessionId();
      _environment = 'dev';
    }
  }

  String _generateSessionId() {
    return 'session_${DateTime.now().millisecondsSinceEpoch}';
  }

  void _startBatchTimer() {
    _batchTimer?.cancel();
    _batchTimer = Timer.periodic(_config.batchInterval, (_) => _processBatch());
  }

  void _startRetryTimer() {
    _retryTimer?.cancel();
    _retryTimer = Timer.periodic(_config.retryInterval, (_) => _processRetries());
  }

  void _handleLogStatus(LogEntry logEntry) {
    if (logEntry.status == LogStatus.failed && logEntry.shouldRetry) {
      _failedLogs.add(logEntry.withRetry());
    }
  }

  /// Log a message with automatic function detection
  Future<void> log({
    required LogLevel level,
    required String module,
    required String topic,
    required String message,
    String? function,
    String? file,
    int? line,
    Map<String, dynamic>? extra,
    LogSeverity? severity,
    Object? error,
    StackTrace? stackTrace,
  }) async {
    // Check minimum level
    if (!_shouldLog(level)) return;

    // Auto-detect function name if not provided
    final detectedFunction = function ?? _detectFunctionName();

    final logEntry = error != null
        ? LogEntry.error(
            module: module,
            function: detectedFunction,
            topic: topic,
            message: message,
            file: file,
            line: line,
            error: error,
            stackTrace: stackTrace,
            extra: extra,
            userId: _userId,
            sessionId: _sessionId,
          )
        : LogEntry.create(
            level: level,
            module: module,
            function: detectedFunction,
            topic: topic,
            message: message,
            file: file,
            line: line,
            extra: extra,
            severity: severity,
            environment: _environment,
            userId: _userId,
            sessionId: _sessionId,
          );

    await _addToBuffer(logEntry);
  }

  /// Convenience methods for different log levels
  Future<void> debug(String module, String topic, String message, {
    String? function,
    Map<String, dynamic>? extra,
  }) => log(
    level: LogLevel.debug,
    module: module,
    topic: topic,
    message: message,
    function: function,
    extra: extra,
  );

  Future<void> info(String module, String topic, String message, {
    String? function,
    Map<String, dynamic>? extra,
  }) => log(
    level: LogLevel.info,
    module: module,
    topic: topic,
    message: message,
    function: function,
    extra: extra,
  );

  Future<void> warning(String module, String topic, String message, {
    String? function,
    Map<String, dynamic>? extra,
  }) => log(
    level: LogLevel.warning,
    module: module,
    topic: topic,
    message: message,
    function: function,
    extra: extra,
    severity: LogSeverity.medium,
  );

  Future<void> error(String module, String topic, String message, {
    String? function,
    Object? error,
    StackTrace? stackTrace,
    Map<String, dynamic>? extra,
    bool isRecursive = false, // Add flag to prevent recursive logging
  }) {
    if (isRecursive) return Future.value();

    return log(
      level: LogLevel.error,
      module: module,
      topic: topic,
      message: message,
      function: function,
      error: error,
      stackTrace: stackTrace,
      extra: extra,
      severity: LogSeverity.high,
    );
  }

  bool _shouldLog(LogLevel level) {
    const levelOrder = [LogLevel.debug, LogLevel.info, LogLevel.warning, LogLevel.error];
    return levelOrder.indexOf(level) >= levelOrder.indexOf(_config.minimumLevel);
  }

  String _detectFunctionName() {
    try {
      final stackTrace = StackTrace.current;
      final lines = stackTrace.toString().split('\n');
      
      // Skip the first few frames (this method, log method, etc.)
      for (int i = 2; i < lines.length && i < 6; i++) {
        final line = lines[i].trim();
        if (line.contains('.dart')) {
          // Extract function name from stack trace line
          final match = RegExp(r'#\d+\s+(.+?)\s+\(').firstMatch(line);
          if (match != null) {
            final fullName = match.group(1) ?? 'unknown';
            // Get just the function name, not the full class.method
            return fullName.split('.').last;
          }
        }
      }
    } catch (e) {
      // Ignore errors in function detection
    }
    return 'unknown';
  }

  Future<void> _addToBuffer(LogEntry logEntry) async {
    _buffer.add(logEntry);
    debugPrint('📝 LoggingService: Added log to buffer (${_buffer.length}/${_config.maxBufferSize}): ${logEntry.message}');
    
    // Enforce buffer size limit
    while (_buffer.length > _config.maxBufferSize) {
      final removed = _buffer.removeFirst();
      if (_config.enableLocalFallback) {
        await _writeToLocalFile(removed);
      }
    }
  }

  Future<void> _processBatch() async {
    if (_buffer.isEmpty) return;

    final batch = <LogEntry>[];
    final batchSize = 50; // Reasonable batch size
    
    while (_buffer.isNotEmpty && batch.length < batchSize) {
      batch.add(_buffer.removeFirst());
    }

    if (batch.isEmpty) return;

    debugPrint('📦 LoggingService: Processing batch of ${batch.length} log entries');
    try {
      await _repository.sendLogs(batch);
      debugPrint('✅ LoggingService: Batch processed successfully');
    } catch (e, s) {
      debugPrint('❌ LoggingService: Batch processing failed: $e');
      // Add failed logs back to failed queue for retry
      _failedLogs.addAll(batch.map((log) => log.withStatus(LogStatus.failed)));

      // Log the batch processing error itself, marking it as recursive
      error('logging_service', 'batch_error', 'Failed to send log batch', error: e, stackTrace: s, isRecursive: true);

      // Write to local file as fallback
      if (_config.enableLocalFallback) {
        for (final log in batch) {
          await _writeToLocalFile(log);
        }
      }
    }
  }

  Future<void> _processRetries() async {
    if (_failedLogs.isEmpty) return;

    final toRetry = <LogEntry>[];
    final now = DateTime.now();
    
    // Check which logs are ready for retry
    while (_failedLogs.isNotEmpty) {
      final log = _failedLogs.removeFirst();
      if (log.shouldRetry) {
        final timeSinceFailure = now.difference(log.localTimestamp ?? now);
        if (timeSinceFailure >= log.retryDelay) {
          toRetry.add(log);
        } else {
          // Put back in queue, not ready yet
          _failedLogs.addFirst(log);
          break;
        }
      }
    }

    // Retry logs
    for (final log in toRetry) {
      try {
        await _repository.sendLogs([log]);
      } catch (e) {
        // Will be handled by status stream
      }
    }
  }

  Future<void> _writeToLocalFile(LogEntry logEntry) async {
    if (!_config.enableLocalFallback) return;

    try {
      final logsPath = await AICOPaths.getLogsPath();
      final directory = await AICOPaths.ensureDirectory(logsPath);
      final file = File('${directory.path}/frontend_fallback.jsonl');
      
      final jsonLine = '${logEntry.toJson()}\n';
      await file.writeAsString(jsonLine, mode: FileMode.append);
    } catch (e) {
      // Ignore file write errors - this is best effort fallback
    }
  }

  /// Set user context for all future logs
  void setUserContext({String? userId, String? sessionId}) {
    _userId = userId;
    if (sessionId != null) {
      _sessionId = sessionId;
    }
  }

  /// Set environment for all future logs
  void setEnvironment(String environment) {
    _environment = environment;
  }

  /// Force flush all buffered logs
  Future<void> flush() async {
    await _processBatch();
    await _processRetries();
  }

  /// Get current buffer status
  Map<String, int> get bufferStatus => {
    'pending': _buffer.length,
    'failed': _failedLogs.length,
  };

  /// Dispose of the logging service
  Future<void> dispose() async {
    _batchTimer?.cancel();
    _retryTimer?.cancel();
    await _statusSubscription?.cancel();
    
    // Try to flush remaining logs
    await flush();
    
    await _repository.close();
  }
}
