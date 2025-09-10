import 'dart:async';
import 'dart:convert';

import 'package:flutter/foundation.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'package:aico_frontend/core/logging/models/log_entry.dart';
import 'package:aico_frontend/core/providers/storage_providers.dart';

/// Local cache for log entries with persistent storage
class LogCache {
  final Ref _ref;
  final List<LogEntry> _memoryBuffer = [];
  final List<LogEntry> _uploadedBuffer = [];
  static const int _maxMemoryBuffer = 1000;
  static const int _maxUploadedBuffer = 500;

  LogCache(this._ref);

  /// Initialize the cache
  Future<void> initialize() async {
    try {
      // Try to load cached logs from storage
      final storageService = _ref.read(storageServiceProvider);
      final cachedData = storageService.getStringValue('pending_logs');
      if (cachedData != null) {
        final List<dynamic> jsonList = jsonDecode(cachedData);
        final cachedLogs = jsonList.map((json) => LogEntry.fromJson(json)).toList();
        _memoryBuffer.addAll(cachedLogs);
      }
    } catch (e) {
      debugPrint('Failed to load cached logs: $e');
    }
  }

  /// Add log entry to cache
  Future<void> addLog(LogEntry entry) async {
    // Add to memory buffer
    _memoryBuffer.add(entry);
    
    // Trim memory buffer if too large
    if (_memoryBuffer.length > _maxMemoryBuffer) {
      _memoryBuffer.removeRange(0, _memoryBuffer.length - _maxMemoryBuffer);
    }

    // Persist to storage
    await _persistToStorage();
  }

  /// Add multiple log entries to cache
  Future<void> addLogs(List<LogEntry> entries) async {
    _memoryBuffer.addAll(entries);
    
    // Trim memory buffer if too large
    if (_memoryBuffer.length > _maxMemoryBuffer) {
      final excess = _memoryBuffer.length - _maxMemoryBuffer;
      _memoryBuffer.removeRange(0, excess);
    }

    await _persistToStorage();
  }

  /// Get pending logs that haven't been uploaded
  Future<List<LogEntry>> getPendingLogs({int? limit}) async {
    final result = List<LogEntry>.from(_memoryBuffer);
    if (limit != null && result.length > limit) {
      return result.take(limit).toList();
    }
    return result;
  }

  /// Mark logs as uploaded
  Future<void> markAsUploaded(List<LogEntry> entries) async {
    // Remove from memory buffer and add to uploaded buffer
    for (final entry in entries) {
      _memoryBuffer.removeWhere((cached) => 
        cached.timestamp == entry.timestamp &&
        cached.module == entry.module &&
        cached.function == entry.function
      );
      
      _uploadedBuffer.add(entry);
    }
    
    // Trim uploaded buffer
    if (_uploadedBuffer.length > _maxUploadedBuffer) {
      final excess = _uploadedBuffer.length - _maxUploadedBuffer;
      _uploadedBuffer.removeRange(0, excess);
    }

    await _persistToStorage();
  }

  /// Get cache statistics
  Future<Map<String, int>> getStats() async {
    return {
      'memory_count': _memoryBuffer.length,
      'pending_count': _memoryBuffer.length,
      'uploaded_count': _uploadedBuffer.length,
      'total_count': _memoryBuffer.length + _uploadedBuffer.length,
    };
  }

  /// Clean up old entries
  Future<void> cleanup() async {
    // Clean up uploaded buffer
    if (_uploadedBuffer.length > _maxUploadedBuffer) {
      final excess = _uploadedBuffer.length - _maxUploadedBuffer;
      _uploadedBuffer.removeRange(0, excess);
    }
    
    await _persistToStorage();
  }

  /// Persist cache to storage
  Future<void> _persistToStorage() async {
    try {
      final storageService = _ref.read(storageServiceProvider);
      final jsonList = _memoryBuffer.map((entry) => entry.toJson()).toList();
      final jsonString = jsonEncode(jsonList);
      await storageService.setStringValue('pending_logs', jsonString);
    } catch (e) {
      debugPrint('Failed to persist logs to storage: $e');
    }
  }

  /// Close and cleanup
  Future<void> dispose() async {
    _memoryBuffer.clear();
    _uploadedBuffer.clear();
  }
}
