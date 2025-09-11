import 'dart:async';
import 'dart:convert';
import 'dart:io';

import 'package:aico_frontend/core/logging/models/log_entry.dart';
import 'package:aico_frontend/core/logging/services/log_compression.dart';
import 'package:aico_frontend/core/providers/networking_providers.dart';
import 'package:aico_frontend/core/utils/aico_paths.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

/// Transport status for monitoring connectivity
enum TransportStatus {
  connected,
  disconnected,
  error,
  retrying,
}

/// Result of a log transport operation
class TransportResult {
  final bool success;
  final String? error;
  final int? statusCode;

  const TransportResult({
    required this.success,
    this.error,
    this.statusCode,
  });

  factory TransportResult.success() => const TransportResult(success: true);
  
  factory TransportResult.failure(String error, [int? statusCode]) => 
      TransportResult(success: false, error: error, statusCode: statusCode);
}

/// Abstract base class for log transport implementations
abstract class LogTransport {
  /// Current transport status
  TransportStatus get status;
  
  /// Stream of status changes
  Stream<TransportStatus> get statusStream;
  
  /// Send a single log entry
  Future<TransportResult> sendLog(LogEntry entry);
  
  /// Send multiple log entries in batch
  Future<TransportResult> sendBatch(List<LogEntry> entries);
  
  /// Initialize the transport
  Future<void> initialize();
  
  /// Cleanup resources
  Future<void> dispose();
}

/// HTTP-based log transport using UnifiedApiClient with encryption
class HttpLogTransport extends LogTransport {
  final Ref _ref;
  final StreamController<TransportStatus> _statusController = StreamController.broadcast();
  TransportStatus _status = TransportStatus.disconnected;

  HttpLogTransport(this._ref);

  @override
  TransportStatus get status => _status;

  @override
  Stream<TransportStatus> get statusStream => _statusController.stream;

  void _updateStatus(TransportStatus newStatus) {
    if (_status != newStatus) {
      _status = newStatus;
      _statusController.add(newStatus);
    }
  }

  @override
  Future<void> initialize() async {
    try {
      final apiClient = _ref.read(unifiedApiClientProvider);
      await apiClient.initialize();
      _updateStatus(TransportStatus.connected);
    } catch (e) {
      _updateStatus(TransportStatus.error);
      rethrow;
    }
  }

  @override
  Future<TransportResult> sendLog(LogEntry entry) async {
    return sendBatch([entry]);
  }

  @override
  Future<TransportResult> sendBatch(List<LogEntry> entries) async {
    if (entries.isEmpty) return TransportResult.success();

    try {
      _updateStatus(TransportStatus.connected);
      
      final apiClient = _ref.read(unifiedApiClientProvider);
      
      // Use compression for large batches
      Map<String, dynamic> payload;
      if (LogCompression.shouldCompress(entries)) {
        final compressed = LogCompression.compressBatch(entries);
        payload = {
          'compressed_logs': base64Encode(compressed),
          'batch_size': entries.length,
          'timestamp': DateTime.now().toIso8601String(),
          'compression': 'gzip',
        };
      } else {
        payload = {
          'logs': entries.map((e) => e.toJson()).toList(),
          'batch_size': entries.length,
          'timestamp': DateTime.now().toIso8601String(),
        };
      }

      final response = await apiClient.post('/logs/batch', data: payload);
      
      if (response != null) {
        return TransportResult.success();
      } else {
        _updateStatus(TransportStatus.error);
        return TransportResult.failure('No response from server');
      }
    } catch (e) {
      _updateStatus(TransportStatus.error);
      return TransportResult.failure('HTTP transport failed: $e');
    }
  }

  @override
  Future<void> dispose() async {
    await _statusController.close();
  }
}

/// File-based fallback transport for offline logging
class FileLogTransport extends LogTransport {
  final StreamController<TransportStatus> _statusController = StreamController.broadcast();
  TransportStatus _status = TransportStatus.disconnected;
  String? _logFilePath;

  @override
  TransportStatus get status => _status;

  @override
  Stream<TransportStatus> get statusStream => _statusController.stream;

  void _updateStatus(TransportStatus newStatus) {
    if (_status != newStatus) {
      _status = newStatus;
      _statusController.add(newStatus);
    }
  }

  @override
  Future<void> initialize() async {
    try {
      // Web platform doesn't support file operations
      if (kIsWeb) {
        _updateStatus(TransportStatus.error);
        return;
      }

      final logsPath = await AICOPaths.getLogsPath();
      await AICOPaths.ensureDirectory(logsPath);
      
      final now = DateTime.now();
      final dateStr = '${now.year}-${now.month.toString().padLeft(2, '0')}-${now.day.toString().padLeft(2, '0')}';
      _logFilePath = '$logsPath/frontend-$dateStr.jsonl';
      
      _updateStatus(TransportStatus.connected);
    } catch (e) {
      _updateStatus(TransportStatus.error);
      rethrow;
    }
  }

  @override
  Future<TransportResult> sendLog(LogEntry entry) async {
    return sendBatch([entry]);
  }

  @override
  Future<TransportResult> sendBatch(List<LogEntry> entries) async {
    if (entries.isEmpty) return TransportResult.success();
    if (kIsWeb) return TransportResult.failure('File operations not supported on web');
    if (_logFilePath == null) return TransportResult.failure('Transport not initialized');

    try {
      final file = File(_logFilePath!);
      final sink = file.openWrite(mode: FileMode.append);
      
      for (final entry in entries) {
        final jsonLine = jsonEncode(entry.toJson());
        sink.writeln(jsonLine);
      }
      
      await sink.flush();
      await sink.close();
      
      _updateStatus(TransportStatus.connected);
      return TransportResult.success();
    } catch (e) {
      _updateStatus(TransportStatus.error);
      return TransportResult.failure('File transport failed: $e');
    }
  }

  @override
  Future<void> dispose() async {
    await _statusController.close();
  }
}

/// Multi-transport with fallback strategy
class FallbackLogTransport extends LogTransport {
  final List<LogTransport> _transports;
  final StreamController<TransportStatus> _statusController = StreamController.broadcast();
  TransportStatus _status = TransportStatus.disconnected;

  FallbackLogTransport(this._transports);

  @override
  TransportStatus get status => _status;

  @override
  Stream<TransportStatus> get statusStream => _statusController.stream;

  void _updateStatus(TransportStatus newStatus) {
    if (_status != newStatus) {
      _status = newStatus;
      _statusController.add(newStatus);
    }
  }

  @override
  Future<void> initialize() async {
    for (final transport in _transports) {
      try {
        await transport.initialize();
      } catch (e) {
        // Continue with next transport
        debugPrint('Transport initialization failed: $e');
      }
    }
    
    // Update status based on available transports
    final hasConnected = _transports.any((t) => t.status == TransportStatus.connected);
    _updateStatus(hasConnected ? TransportStatus.connected : TransportStatus.error);
  }

  @override
  Future<TransportResult> sendLog(LogEntry entry) async {
    return sendBatch([entry]);
  }

  @override
  Future<TransportResult> sendBatch(List<LogEntry> entries) async {
    if (entries.isEmpty) return TransportResult.success();

    // Try each transport in order until one succeeds
    for (final transport in _transports) {
      if (transport.status == TransportStatus.connected) {
        try {
          final result = await transport.sendBatch(entries);
          if (result.success) {
            _updateStatus(TransportStatus.connected);
            return result;
          }
        } catch (e) {
          // Continue to next transport
          debugPrint('Transport failed: $e');
        }
      }
    }

    _updateStatus(TransportStatus.error);
    return TransportResult.failure('All transports failed');
  }

  @override
  Future<void> dispose() async {
    await Future.wait(_transports.map((t) => t.dispose()));
    await _statusController.close();
  }
}
