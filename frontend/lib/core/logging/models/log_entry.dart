// Simple data class without code generation dependencies

/// Log levels following AICO unified logging schema
enum LogLevel {
  debug,
  info,
  warning,
  error,
}

/// Log severity levels for prioritization
enum LogSeverity {
  low,
  medium,
  high,
}

/// Status of log entry in the system
enum LogStatus {
  pending,
  sending,
  sent,
  failed,
}

/// Unified log entry following AICO logging schema
class LogEntry {
  final String timestamp;
  final LogLevel level;
  final String module;
  final String function;
  final String topic;
  final String message;
  final String? file;
  final int? line;
  final String? userId;
  final String? traceId;
  final Map<String, dynamic>? extra;
  final LogSeverity? severity;
  final String? origin;
  final String? environment;
  final String? sessionId;
  final Map<String, dynamic>? errorDetails;
  
  // Local fields (not sent to backend)
  final LogStatus status;
  final DateTime? localTimestamp;
  final int? retryCount;

  const LogEntry({
    required this.timestamp,
    required this.level,
    required this.module,
    required this.function,
    required this.topic,
    required this.message,
    this.file,
    this.line,
    this.userId,
    this.traceId,
    this.extra,
    this.severity,
    this.origin,
    this.environment,
    this.sessionId,
    this.errorDetails,
    this.status = LogStatus.pending,
    this.localTimestamp,
    this.retryCount,
  });

  factory LogEntry.fromJson(Map<String, dynamic> json) {
    return LogEntry(
      timestamp: json['timestamp'] as String,
      level: LogLevel.values.firstWhere(
        (e) => e.name.toUpperCase() == (json['level'] as String).toUpperCase(),
        orElse: () => LogLevel.info,
      ),
      module: json['module'] as String,
      function: json['function'] as String,
      topic: json['topic'] as String,
      message: json['message'] as String,
      file: json['file'] as String?,
      line: json['line'] as int?,
      userId: json['user_id'] as String?,
      traceId: json['trace_id'] as String?,
      extra: json['extra'] as Map<String, dynamic>?,
      severity: json['severity'] != null 
        ? LogSeverity.values.firstWhere(
            (e) => e.name == json['severity'],
            orElse: () => LogSeverity.low,
          )
        : null,
      origin: json['origin'] as String?,
      environment: json['environment'] as String?,
      sessionId: json['session_id'] as String?,
      errorDetails: json['error_details'] as Map<String, dynamic>?,
    );
  }

  /// Create log entry with automatic timestamp and defaults
  factory LogEntry.create({
    required LogLevel level,
    required String module,
    required String function,
    required String topic,
    required String message,
    String? file,
    int? line,
    String? userId,
    String? traceId,
    Map<String, dynamic>? extra,
    LogSeverity? severity,
    String? origin,
    String? environment,
    String? sessionId,
  }) {
    return LogEntry(
      timestamp: DateTime.now().toIso8601String(),
      level: level,
      module: module,
      function: function,
      topic: topic,
      message: message,
      file: file,
      line: line,
      userId: userId,
      traceId: traceId,
      extra: extra,
      severity: severity,
      origin: origin ?? 'frontend',
      environment: environment,
      sessionId: sessionId,
      localTimestamp: DateTime.now(),
    );
  }

  /// Create error log entry with stack trace
  factory LogEntry.error({
    required String module,
    required String function,
    required String topic,
    required String message,
    String? file,
    int? line,
    required Object error,
    StackTrace? stackTrace,
    Map<String, dynamic>? extra,
    String? userId,
    String? sessionId,
    String? environment,
  }) {
    final errorDetails = <String, dynamic>{
      'error': error.toString(),
      'type': error.runtimeType.toString(),
      if (stackTrace != null) 'stackTrace': stackTrace.toString(),
    };

    return LogEntry(
      timestamp: DateTime.now().toIso8601String(),
      level: LogLevel.error,
      module: module,
      function: function,
      topic: topic,
      message: message,
      file: file,
      line: line,
      userId: userId,
      sessionId: sessionId,
      environment: environment,
      errorDetails: errorDetails,
      extra: extra,
      severity: LogSeverity.high,
      localTimestamp: DateTime.now(),
    );
  }

  /// Convert to JSON for backend transmission (excludes local fields)
  Map<String, dynamic> toBackendJson() {
    final json = toJson();
    // Remove local-only fields
    json.remove('status');
    json.remove('localTimestamp');
    json.remove('retryCount');
    return json;
  }

  /// Convert to JSON for serialization
  Map<String, dynamic> toJson() {
    return {
      'timestamp': timestamp,
      'level': level.name.toUpperCase(),
      'module': module,
      'function': function,
      'topic': topic,
      'message': message,
      if (file != null) 'file': file,
      if (line != null) 'line': line,
      if (userId != null) 'user_id': userId,
      if (traceId != null) 'trace_id': traceId,
      if (extra != null) 'extra': extra,
      if (severity != null) 'severity': severity!.name,
      if (origin != null) 'origin': origin,
      if (environment != null) 'environment': environment,
      if (sessionId != null) 'session_id': sessionId,
      if (errorDetails != null) 'error_details': errorDetails,
    };
  }

  /// Create copy with updated status
  LogEntry withStatus(LogStatus newStatus) {
    return LogEntry(
      timestamp: timestamp,
      level: level,
      module: module,
      function: function,
      topic: topic,
      message: message,
      file: file,
      line: line,
      userId: userId,
      traceId: traceId,
      extra: extra,
      severity: severity,
      origin: origin,
      environment: environment,
      sessionId: sessionId,
      errorDetails: errorDetails,
      status: newStatus,
      localTimestamp: localTimestamp,
      retryCount: retryCount,
    );
  }

  /// Create copy for retry with incremented count
  LogEntry withRetry() {
    return LogEntry(
      timestamp: timestamp,
      level: level,
      module: module,
      function: function,
      topic: topic,
      message: message,
      file: file,
      line: line,
      userId: userId,
      traceId: traceId,
      extra: extra,
      severity: severity,
      origin: origin,
      environment: environment,
      sessionId: sessionId,
      errorDetails: errorDetails,
      status: LogStatus.pending,
      localTimestamp: localTimestamp,
      retryCount: (retryCount ?? 0) + 1,
    );
  }

  /// Check if log entry should be retried
  bool get shouldRetry {
    const maxRetries = 3;
    return status == LogStatus.failed && (retryCount ?? 0) < maxRetries;
  }

  /// Get retry delay based on exponential backoff
  Duration get retryDelay {
    final attempt = retryCount ?? 0;
    return Duration(seconds: (1 << attempt).clamp(1, 30)); // 1s, 2s, 4s, 8s, max 30s
  }
}
