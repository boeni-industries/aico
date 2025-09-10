import 'dart:async';

import 'package:flutter/foundation.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'package:aico_frontend/core/logging/models/log_entry.dart';
import 'package:aico_frontend/core/logging/services/aico_logger.dart';
import 'package:aico_frontend/core/logging/services/log_transport.dart';
import 'package:aico_frontend/core/logging/providers/logging_providers.dart';

/// Statistics for logging system monitoring
class LoggingStats {
  final int totalLogsGenerated;
  final int logsInCache;
  final int logsSentSuccessfully;
  final int logsSentFailed;
  final int retryAttempts;
  final DateTime lastSuccessfulUpload;
  final DateTime lastFailedUpload;
  final TransportStatus transportStatus;
  final Map<LogLevel, int> logsByLevel;
  final Map<String, int> logsByModule;

  const LoggingStats({
    required this.totalLogsGenerated,
    required this.logsInCache,
    required this.logsSentSuccessfully,
    required this.logsSentFailed,
    required this.retryAttempts,
    required this.lastSuccessfulUpload,
    required this.lastFailedUpload,
    required this.transportStatus,
    required this.logsByLevel,
    required this.logsByModule,
  });

  Map<String, dynamic> toJson() => {
    'total_logs_generated': totalLogsGenerated,
    'logs_in_cache': logsInCache,
    'logs_sent_successfully': logsSentSuccessfully,
    'logs_sent_failed': logsSentFailed,
    'retry_attempts': retryAttempts,
    'last_successful_upload': lastSuccessfulUpload.toIso8601String(),
    'last_failed_upload': lastFailedUpload.toIso8601String(),
    'transport_status': transportStatus.name,
    'logs_by_level': logsByLevel.map((k, v) => MapEntry(k.name, v)),
    'logs_by_module': logsByModule,
  };
}

/// Health check result for logging system
class LoggingHealthCheck {
  final bool isHealthy;
  final String status;
  final List<String> issues;
  final DateTime checkedAt;

  const LoggingHealthCheck({
    required this.isHealthy,
    required this.status,
    required this.issues,
    required this.checkedAt,
  });

  Map<String, dynamic> toJson() => {
    'is_healthy': isHealthy,
    'status': status,
    'issues': issues,
    'checked_at': checkedAt.toIso8601String(),
  };
}

/// Monitoring service for the AICO logging system
class LogMonitor {
  final Ref _ref;
  
  // Statistics tracking
  int _totalLogsGenerated = 0;
  int _logsSentSuccessfully = 0;
  int _logsSentFailed = 0;
  int _retryAttempts = 0;
  DateTime _lastSuccessfulUpload = DateTime.fromMillisecondsSinceEpoch(0);
  DateTime _lastFailedUpload = DateTime.fromMillisecondsSinceEpoch(0);
  
  final Map<LogLevel, int> _logsByLevel = {};
  final Map<String, int> _logsByModule = {};
  
  Timer? _healthCheckTimer;
  
  LogMonitor(this._ref);

  /// Initialize monitoring
  Future<void> initialize() async {
    // Start periodic health checks
    _healthCheckTimer = Timer.periodic(
      const Duration(minutes: 5),
      (_) => _performHealthCheck(),
    );
  }

  /// Record a log entry being generated
  void recordLogGenerated(LogEntry entry) {
    _totalLogsGenerated++;
    
    // Track by level
    _logsByLevel[entry.level] = (_logsByLevel[entry.level] ?? 0) + 1;
    
    // Track by module
    _logsByModule[entry.module] = (_logsByModule[entry.module] ?? 0) + 1;
  }

  /// Record successful log upload
  void recordUploadSuccess(int count) {
    _logsSentSuccessfully += count;
    _lastSuccessfulUpload = DateTime.now();
  }

  /// Record failed log upload
  void recordUploadFailure(int count) {
    _logsSentFailed += count;
    _lastFailedUpload = DateTime.now();
  }

  /// Record retry attempt
  void recordRetryAttempt() {
    _retryAttempts++;
  }

  /// Get current logging statistics
  Future<LoggingStats> getStats() async {
    final cache = _ref.read(logCacheProvider);
    final cacheStats = await cache.getStats();
    
    // Get transport status from logger
    TransportStatus transportStatus = TransportStatus.disconnected;
    try {
      AICOLogger.instance;
      // Access transport status through logger
      transportStatus = TransportStatus.connected; // Simplified for now
    } catch (e) {
      transportStatus = TransportStatus.disconnected;
    }

    return LoggingStats(
      totalLogsGenerated: _totalLogsGenerated,
      logsInCache: cacheStats['pending_count'] ?? 0,
      logsSentSuccessfully: _logsSentSuccessfully,
      logsSentFailed: _logsSentFailed,
      retryAttempts: _retryAttempts,
      lastSuccessfulUpload: _lastSuccessfulUpload,
      lastFailedUpload: _lastFailedUpload,
      transportStatus: transportStatus,
      logsByLevel: Map.from(_logsByLevel),
      logsByModule: Map.from(_logsByModule),
    );
  }

  /// Perform health check on logging system
  Future<LoggingHealthCheck> performHealthCheck() async {
    return _performHealthCheck();
  }

  Future<LoggingHealthCheck> _performHealthCheck() async {
    final issues = <String>[];
    bool isHealthy = true;

    try {
      // Check if logger is initialized
      AICOLogger.instance;
      // Logger is available

      // Check cache health
      final cache = _ref.read(logCacheProvider);
      final cacheStats = await cache.getStats();
      final pendingCount = cacheStats['pending_count'] ?? 0;
      
      if (pendingCount > 1000) {
        issues.add('High number of pending logs in cache: $pendingCount');
        isHealthy = false;
      }

      // Check recent upload activity
      final now = DateTime.now();
      final timeSinceLastSuccess = now.difference(_lastSuccessfulUpload);
      
      if (timeSinceLastSuccess.inHours > 1 && _totalLogsGenerated > 0) {
        issues.add('No successful uploads in the last hour');
        isHealthy = false;
      }

      // Check retry rate
      if (_retryAttempts > _logsSentSuccessfully * 0.5) {
        issues.add('High retry rate detected');
        isHealthy = false;
      }

    } catch (e) {
      issues.add('Health check failed: $e');
      isHealthy = false;
    }

    final status = isHealthy ? 'healthy' : 'unhealthy';
    
    final healthCheck = LoggingHealthCheck(
      isHealthy: isHealthy,
      status: status,
      issues: issues,
      checkedAt: DateTime.now(),
    );

    // Log health check results if there are issues
    if (!isHealthy && kDebugMode) {
      debugPrint('Logging health check failed: ${issues.join(', ')}');
    }

    return healthCheck;
  }

  /// Reset statistics
  void resetStats() {
    _totalLogsGenerated = 0;
    _logsSentSuccessfully = 0;
    _logsSentFailed = 0;
    _retryAttempts = 0;
    _lastSuccessfulUpload = DateTime.fromMillisecondsSinceEpoch(0);
    _lastFailedUpload = DateTime.fromMillisecondsSinceEpoch(0);
    _logsByLevel.clear();
    _logsByModule.clear();
  }

  /// Dispose resources
  void dispose() {
    _healthCheckTimer?.cancel();
  }
}
