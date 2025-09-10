
/// Log levels following AICO logging standards
enum LogLevel {
  debug,
  info,
  warn,
  error,
  fatal,
}

/// Standardized log entry following AICO unified logging schema
class LogEntry {
  /// ISO8601 timestamp when log was created
  final String timestamp;
  
  /// Log severity level
  final LogLevel level;
  
  /// Module identifier (e.g., "frontend.conversation_ui")
  final String module;
  
  /// Function name where log originated
  final String function;
  
  /// Log topic for categorization (e.g., "ui.button.click")
  final String topic;
  
  /// Human-readable log message
  final String message;
  
  /// Optional source file name
  final String? file;
  
  /// Optional source line number
  final int? line;
  
  /// Optional trace ID for request correlation
  final String? traceId;
  
  /// Optional session ID for user session tracking
  final String? sessionId;
  
  /// Optional additional structured data
  final Map<String, dynamic>? extra;
  
  /// Optional error details for exception logging
  final Map<String, dynamic>? errorDetails;

  const LogEntry({
    required this.timestamp,
    required this.level,
    required this.module,
    required this.function,
    required this.topic,
    required this.message,
    this.file,
    this.line,
    this.traceId,
    this.sessionId,
    this.extra,
    this.errorDetails,
  });

  /// Create LogEntry from JSON
  factory LogEntry.fromJson(Map<String, dynamic> json) {
    return LogEntry(
      timestamp: json['timestamp'] as String,
      level: LogLevel.values.firstWhere(
        (l) => l.name.toUpperCase() == (json['level'] as String).toUpperCase(),
        orElse: () => LogLevel.info,
      ),
      module: json['module'] as String,
      function: json['function'] as String,
      topic: json['topic'] as String,
      message: json['message'] as String,
      file: json['file'] as String?,
      line: json['line'] as int?,
      traceId: json['trace_id'] as String?,
      sessionId: json['session_id'] as String?,
      extra: json['extra'] as Map<String, dynamic>?,
      errorDetails: json['error_details'] as Map<String, dynamic>?,
    );
  }

  /// Convert LogEntry to JSON
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
      if (traceId != null) 'trace_id': traceId,
      if (sessionId != null) 'session_id': sessionId,
      if (extra != null) 'extra': extra,
      if (errorDetails != null) 'error_details': errorDetails,
    };
  }

  /// Create a copy with modified fields
  LogEntry copyWith({
    String? timestamp,
    LogLevel? level,
    String? module,
    String? function,
    String? topic,
    String? message,
    String? file,
    int? line,
    String? traceId,
    String? sessionId,
    Map<String, dynamic>? extra,
    Map<String, dynamic>? errorDetails,
  }) {
    return LogEntry(
      timestamp: timestamp ?? this.timestamp,
      level: level ?? this.level,
      module: module ?? this.module,
      function: function ?? this.function,
      topic: topic ?? this.topic,
      message: message ?? this.message,
      file: file ?? this.file,
      line: line ?? this.line,
      traceId: traceId ?? this.traceId,
      sessionId: sessionId ?? this.sessionId,
      extra: extra ?? this.extra,
      errorDetails: errorDetails ?? this.errorDetails,
    );
  }

  @override
  String toString() {
    return '[$timestamp] ${level.name.toUpperCase()} $module.$function: $message';
  }

  @override
  bool operator ==(Object other) {
    if (identical(this, other)) return true;
    return other is LogEntry &&
        other.timestamp == timestamp &&
        other.level == level &&
        other.module == module &&
        other.function == function &&
        other.topic == topic &&
        other.message == message;
  }

  @override
  int get hashCode {
    return Object.hash(timestamp, level, module, function, topic, message);
  }
}

/// Extension methods for LogLevel
extension LogLevelExtension on LogLevel {
  /// Get numeric priority for level comparison
  int get priority {
    switch (this) {
      case LogLevel.debug:
        return 0;
      case LogLevel.info:
        return 1;
      case LogLevel.warn:
        return 2;
      case LogLevel.error:
        return 3;
      case LogLevel.fatal:
        return 4;
    }
  }

  /// Check if this level should be logged given a minimum level
  bool shouldLog(LogLevel minimumLevel) {
    return priority >= minimumLevel.priority;
  }
}
