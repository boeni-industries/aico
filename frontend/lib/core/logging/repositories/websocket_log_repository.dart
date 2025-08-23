import 'dart:async';
import 'dart:convert';

import 'package:aico_frontend/core/logging/models/log_entry.dart';
import 'package:aico_frontend/core/logging/repositories/log_repository.dart';
import 'package:web_socket_channel/web_socket_channel.dart';

/// WebSocket-based log repository implementation
class WebSocketLogRepository implements LogRepository {
  final String _wsUrl;
  WebSocketChannel? _channel;
  final StreamController<LogEntry> _statusController = StreamController.broadcast();
  final Map<String, LogEntry> _pendingLogs = {};
  bool _isConnected = false;

  WebSocketLogRepository({
    required String wsUrl,
  }) : _wsUrl = wsUrl;

  @override
  Stream<LogEntry> get logStatusStream => _statusController.stream;

  @override
  Future<bool> get isAvailable async {
    if (_isConnected) return true;
    
    try {
      await _ensureConnection();
      return _isConnected;
    } catch (e) {
      return false;
    }
  }

  Future<void> _ensureConnection() async {
    if (_isConnected) return;

    try {
      _channel = WebSocketChannel.connect(Uri.parse(_wsUrl));
      
      // Listen for responses
      _channel!.stream.listen(
        _handleMessage,
        onError: _handleError,
        onDone: _handleDisconnection,
      );

      _isConnected = true;
    } catch (e) {
      _isConnected = false;
      rethrow;
    }
  }

  void _handleMessage(dynamic message) {
    try {
      final data = json.decode(message as String) as Map<String, dynamic>;
      final messageId = data['message_id'] as String?;
      final status = data['status'] as String?;

      if (messageId != null && status != null) {
        final pendingLog = _pendingLogs.remove(messageId);
        if (pendingLog != null) {
          final logStatus = status == 'success' ? LogStatus.sent : LogStatus.failed;
          _statusController.add(pendingLog.withStatus(logStatus));
        }
      }
    } catch (e) {
      // Ignore malformed messages
    }
  }

  void _handleError(dynamic error) {
    _isConnected = false;
    
    // Mark all pending logs as failed
    for (final entry in _pendingLogs.values) {
      _statusController.add(entry.withStatus(LogStatus.failed));
    }
    _pendingLogs.clear();
  }

  void _handleDisconnection() {
    _isConnected = false;
    
    // Mark all pending logs as failed
    for (final entry in _pendingLogs.values) {
      _statusController.add(entry.withStatus(LogStatus.failed));
    }
    _pendingLogs.clear();
  }

  @override
  Future<void> sendLog(LogEntry logEntry) async {
    await _ensureConnection();
    
    _statusController.add(logEntry.withStatus(LogStatus.sending));

    try {
      final messageId = DateTime.now().millisecondsSinceEpoch.toString();
      final message = {
        'type': 'log',
        'message_id': messageId,
        'data': logEntry.toBackendJson(),
      };

      _pendingLogs[messageId] = logEntry;
      _channel!.sink.add(json.encode(message));

      // Set timeout for response
      Timer(const Duration(seconds: 10), () {
        final pendingLog = _pendingLogs.remove(messageId);
        if (pendingLog != null) {
          _statusController.add(pendingLog.withStatus(LogStatus.failed));
        }
      });
    } catch (e) {
      _statusController.add(logEntry.withStatus(LogStatus.failed));
      rethrow;
    }
  }

  @override
  Future<void> sendLogs(List<LogEntry> logEntries) async {
    if (logEntries.isEmpty) return;

    await _ensureConnection();

    // Update all to sending status
    for (final entry in logEntries) {
      _statusController.add(entry.withStatus(LogStatus.sending));
    }

    try {
      final messageId = DateTime.now().millisecondsSinceEpoch.toString();
      final message = {
        'type': 'log_batch',
        'message_id': messageId,
        'data': {
          'logs': logEntries.map((e) => e.toBackendJson()).toList(),
        },
      };

      // Store all entries with same message ID
      for (final entry in logEntries) {
        _pendingLogs['${messageId}_${entry.hashCode}'] = entry;
      }

      _channel!.sink.add(json.encode(message));

      // Set timeout for response
      Timer(const Duration(seconds: 30), () {
        for (final entry in logEntries) {
          final key = '${messageId}_${entry.hashCode}';
          final pendingLog = _pendingLogs.remove(key);
          if (pendingLog != null) {
            _statusController.add(pendingLog.withStatus(LogStatus.failed));
          }
        }
      });
    } catch (e) {
      // Mark all as failed
      for (final entry in logEntries) {
        _statusController.add(entry.withStatus(LogStatus.failed));
      }
      rethrow;
    }
  }

  @override
  Future<void> close() async {
    _isConnected = false;
    await _channel?.sink.close();
    await _statusController.close();
    _pendingLogs.clear();
  }
}
