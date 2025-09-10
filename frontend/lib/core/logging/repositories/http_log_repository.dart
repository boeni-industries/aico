import 'dart:async';

import 'package:aico_frontend/core/logging/models/log_entry.dart';
import 'package:aico_frontend/core/logging/repositories/log_repository.dart';
import 'package:aico_frontend/networking/clients/unified_api_client.dart';
import 'package:flutter/foundation.dart';

/// HTTP-based log repository implementation
class HttpLogRepository implements LogRepository {
  final UnifiedApiClient _apiClient;
  final String _logEndpoint;
  final StreamController<LogEntry> _statusController = StreamController.broadcast();
  bool _isSending = false;

  HttpLogRepository({
    required UnifiedApiClient apiClient,
    String logEndpoint = '/logs/batch',
  })  : _apiClient = apiClient,
        _logEndpoint = logEndpoint;

  @override
  Stream<LogEntry> get logStatusStream => _statusController.stream;

  @override
  Future<bool> get isAvailable async {
    try {
      final response = await _apiClient.get('/health');
      return response.isSuccess;
    } catch (e) {
      return false;
    }
  }

  @override
  Future<void> sendLogs(List<LogEntry> logEntries) async {
    if (logEntries.isEmpty || _isSending) return;

    _isSending = true;
    debugPrint('📤 HttpLogRepository: Sending ${logEntries.length} log entries to $_logEndpoint');

    try {
      for (final entry in logEntries) {
        _statusController.add(entry.withStatus(LogStatus.sending));
      }

      final batchData = {
        'logs': logEntries.map((e) => e.toBackendJson()).toList(),
      };

      debugPrint('📤 HttpLogRepository: Batch data prepared, making API call...');
      await _apiClient.post<Map<String, dynamic>>(_logEndpoint, data: batchData);

      // If we reach here, the request was successful
      debugPrint('✅ HttpLogRepository: Successfully sent ${logEntries.length} log entries');
      for (final entry in logEntries) {
        _statusController.add(entry.withStatus(LogStatus.sent));
      }
    } catch (e) {
      debugPrint('❌ HttpLogRepository: Failed to send logs: $e');
      debugPrint('❌ HttpLogRepository: Error type: ${e.runtimeType}');
      for (final entry in logEntries) {
        _statusController.add(entry.withStatus(LogStatus.failed));
      }
    } finally {
      _isSending = false;
    }
  }

  @override
  Future<void> close() async {
    await _statusController.close();
  }
}
