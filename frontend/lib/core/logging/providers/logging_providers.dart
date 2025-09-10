import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'package:aico_frontend/core/logging/models/log_entry.dart';
import 'package:aico_frontend/core/logging/services/aico_logger.dart';
import 'package:aico_frontend/core/logging/services/log_cache.dart';
import 'package:aico_frontend/core/logging/services/log_monitor.dart';
import 'package:aico_frontend/core/logging/services/log_transport.dart';

/// Logging configuration provider
final loggingConfigProvider = Provider<LoggingConfig>((ref) {
  // Load configuration from AICO defaults with environment overrides
  return const LoggingConfig(
    minimumLevel: LogLevel.info, // From core.yaml: logging.level
    enableConsoleOutput: true,   // From core.yaml: logging.console.enabled
    batchSize: 50,              // From core.yaml: logging.transport.batch_size
    batchTimeoutMs: 5000,       // From core.yaml: logging.transport.batch_timeout_ms
    maxRetries: 3,              // From core.yaml: logging.transport.max_retries
    retryDelayMs: 1000,         // From core.yaml: logging.transport.retry_delay_ms
    enableCompression: true,     // From core.yaml: logging.transport.compression.enabled
    compressionThreshold: 1024,  // From core.yaml: logging.transport.compression.threshold
  );
});

/// Log cache provider
final logCacheProvider = Provider<LogCache>((ref) {
  return LogCache(ref);
});

/// HTTP log transport provider
final httpLogTransportProvider = Provider<HttpLogTransport>((ref) {
  return HttpLogTransport(ref);
});

/// File log transport provider
final fileLogTransportProvider = Provider<FileLogTransport>((ref) {
  return FileLogTransport();
});

/// Fallback log transport provider with multiple transports
final logTransportProvider = Provider<FallbackLogTransport>((ref) {
  final httpTransport = ref.watch(httpLogTransportProvider);
  final fileTransport = ref.watch(fileLogTransportProvider);
  
  return FallbackLogTransport([httpTransport, fileTransport]);
});

/// Log monitor provider
final logMonitorProvider = Provider<LogMonitor>((ref) {
  return LogMonitor(ref);
});

/// AICO Logger provider with monitoring
final aicoLoggerProvider = Provider<AICOLogger?>((ref) {
  final config = ref.watch(loggingConfigProvider);
  final transport = ref.watch(logTransportProvider);
  final cache = ref.watch(logCacheProvider);
  
  AICOLogger.initialize(
    config: config,
    transport: transport,
    cache: cache,
  );
  
  return AICOLogger.instance;
});

/// Logger status provider for monitoring
final loggerStatusProvider = StreamProvider<Map<String, dynamic>>((ref) async* {
  final logger = ref.watch(aicoLoggerProvider);
  
  await for (final _ in Stream.periodic(const Duration(seconds: 10))) {
    if (logger != null) {
      yield await logger.getStats();
    } else {
      yield {'status': 'initializing'};
    }
  }
});
