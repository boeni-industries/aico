import 'package:aico_frontend/core/logging/models/log_entry.dart';

/// Abstract repository for log operations
abstract class LogRepository {
  /// Send multiple log entries in batch
  Future<void> sendLogs(List<LogEntry> logEntries);

  /// Get stream of log send status updates
  Stream<LogEntry> get logStatusStream;

  /// Check if repository is available/connected
  Future<bool> get isAvailable;

  /// Close repository and cleanup resources
  Future<void> close();
}
