import 'dart:async';

import 'package:aico_frontend/core/logging/models/log_entry.dart';
import 'package:aico_frontend/core/logging/repositories/log_repository.dart';
import 'package:dio/dio.dart';

/// HTTP-based log repository implementation
class HttpLogRepository implements LogRepository {
  final Dio _dio;
  final String _logEndpoint;
  final StreamController<LogEntry> _statusController = StreamController.broadcast();

  HttpLogRepository({
    required Dio dio,
    String logEndpoint = '/api/v1/logs',
  })  : _dio = dio,
        _logEndpoint = logEndpoint;

  @override
  Stream<LogEntry> get logStatusStream => _statusController.stream;

  @override
  Future<bool> get isAvailable async {
    try {
      final response = await _dio.get('/api/v1/health');
      return response.statusCode == 200;
    } catch (e) {
      return false;
    }
  }

  @override
  Future<void> sendLog(LogEntry logEntry) async {
    _statusController.add(logEntry.withStatus(LogStatus.sending));

    try {
      final response = await _dio.post(
        _logEndpoint,
        data: logEntry.toBackendJson(),
        options: Options(
          headers: {'Content-Type': 'application/json'},
          sendTimeout: const Duration(seconds: 10),
          receiveTimeout: const Duration(seconds: 10),
        ),
      );

      if (response.statusCode == 200 || response.statusCode == 204) {
        _statusController.add(logEntry.withStatus(LogStatus.sent));
      } else {
        throw DioException(
          requestOptions: response.requestOptions,
          response: response,
          message: 'Unexpected status code: ${response.statusCode}',
        );
      }
    } catch (_) {
      // Log failed - emit status update
      _statusController.add(logEntry.withStatus(LogStatus.failed));
    }
  }

  @override
  Future<void> sendLogs(List<LogEntry> logEntries) async {
    if (logEntries.isEmpty) return;

    // Update all to sending status
    for (final entry in logEntries) {
      _statusController.add(entry.withStatus(LogStatus.sending));
    }

    try {
      final batchData = {
        'logs': logEntries.map((e) => e.toBackendJson()).toList(),
      };

      final response = await _dio.post(
        '$_logEndpoint/batch',
        data: batchData,
        options: Options(
          headers: {'Content-Type': 'application/json'},
          sendTimeout: const Duration(seconds: 30),
          receiveTimeout: const Duration(seconds: 30),
        ),
      );

      if (response.statusCode == 200 || response.statusCode == 204) {
        // Mark all as sent
        for (final entry in logEntries) {
          _statusController.add(entry.withStatus(LogStatus.sent));
        }
      } else {
        throw DioException(
          requestOptions: response.requestOptions,
          response: response,
          message: 'Unexpected status code: ${response.statusCode}',
        );
      }
    } catch (_) {
      // Batch failed - emit status updates for all entries
      for (final entry in logEntries) {
        _statusController.add(entry.withStatus(LogStatus.failed));
      }
    }
  }

  @override
  Future<void> close() async {
    await _statusController.close();
  }
}
