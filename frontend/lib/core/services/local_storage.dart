import 'dart:convert';
import 'dart:io';

import 'package:aico_frontend/core/utils/aico_paths.dart';
import 'package:path/path.dart' as path;

/// Local file-based storage service for frontend persistence
/// Provides consistent local data storage patterns across the app
class LocalStorage {
  static const String _preferencesFileName = 'preferences.json';

  /// Save data to state persistence directory
  Future<void> saveState(String key, Map<String, dynamic> data) async {
    try {
      final statePath = await AICOPaths.getStatePath();
      await AICOPaths.ensureDirectory(statePath);
      
      final file = File(path.join(statePath, '${key}_state.json'));
      await file.writeAsString(jsonEncode(data));
    } catch (e) {
      throw LocalStorageException('Failed to save state for $key: $e');
    }
  }

  /// Load data from state persistence directory
  Future<Map<String, dynamic>?> loadState(String key) async {
    try {
      final statePath = await AICOPaths.getStatePath();
      final file = File(path.join(statePath, '${key}_state.json'));
      
      if (!await file.exists()) {
        return null;
      }
      
      final jsonString = await file.readAsString();
      return jsonDecode(jsonString) as Map<String, dynamic>;
    } catch (e) {
      throw LocalStorageException('Failed to load state for $key: $e');
    }
  }

  /// Save preferences data
  Future<void> savePreferences(Map<String, dynamic> preferences) async {
    try {
      final statePath = await AICOPaths.getStatePath();
      await AICOPaths.ensureDirectory(statePath);
      
      final file = File(path.join(statePath, _preferencesFileName));
      await file.writeAsString(jsonEncode(preferences));
    } catch (e) {
      throw LocalStorageException('Failed to save preferences: $e');
    }
  }

  /// Load preferences data
  Future<Map<String, dynamic>?> loadPreferences() async {
    try {
      final statePath = await AICOPaths.getStatePath();
      final file = File(path.join(statePath, _preferencesFileName));
      
      if (!await file.exists()) {
        return null;
      }
      
      final jsonString = await file.readAsString();
      return jsonDecode(jsonString) as Map<String, dynamic>;
    } catch (e) {
      throw LocalStorageException('Failed to load preferences: $e');
    }
  }

  /// Save data to cache directory
  Future<void> saveCache(String key, Map<String, dynamic> data) async {
    try {
      final cachePath = await AICOPaths.getCachePath();
      await AICOPaths.ensureDirectory(cachePath);
      
      final file = File(path.join(cachePath, '${key}_cache.json'));
      await file.writeAsString(jsonEncode(data));
    } catch (e) {
      throw LocalStorageException('Failed to save cache for $key: $e');
    }
  }

  /// Load data from cache directory
  Future<Map<String, dynamic>?> loadCache(String key) async {
    try {
      final cachePath = await AICOPaths.getCachePath();
      final file = File(path.join(cachePath, '${key}_cache.json'));
      
      if (!await file.exists()) {
        return null;
      }
      
      final jsonString = await file.readAsString();
      return jsonDecode(jsonString) as Map<String, dynamic>;
    } catch (e) {
      throw LocalStorageException('Failed to load cache for $key: $e');
    }
  }

  /// Save offline queue item
  Future<void> saveOfflineQueueItem(String id, Map<String, dynamic> item) async {
    try {
      final queuePath = await AICOPaths.getOfflineQueuePath();
      await AICOPaths.ensureDirectory(queuePath);
      
      final file = File(path.join(queuePath, '$id.json'));
      await file.writeAsString(jsonEncode(item));
    } catch (e) {
      throw LocalStorageException('Failed to save offline queue item $id: $e');
    }
  }

  /// Load all offline queue items
  Future<List<Map<String, dynamic>>> loadOfflineQueue() async {
    try {
      final queuePath = await AICOPaths.getOfflineQueuePath();
      final directory = Directory(queuePath);
      
      if (!await directory.exists()) {
        return [];
      }
      
      final files = await directory
          .list()
          .where((entity) => entity is File && entity.path.endsWith('.json'))
          .cast<File>()
          .toList();
      
      final items = <Map<String, dynamic>>[];
      for (final file in files) {
        try {
          final jsonString = await file.readAsString();
          final item = jsonDecode(jsonString) as Map<String, dynamic>;
          items.add(item);
        } catch (e) {
          // Skip corrupted files
          continue;
        }
      }
      
      return items;
    } catch (e) {
      throw LocalStorageException('Failed to load offline queue: $e');
    }
  }

  /// Remove offline queue item
  Future<void> removeOfflineQueueItem(String id) async {
    try {
      final queuePath = await AICOPaths.getOfflineQueuePath();
      final file = File(path.join(queuePath, '$id.json'));
      
      if (await file.exists()) {
        await file.delete();
      }
    } catch (e) {
      throw LocalStorageException('Failed to remove offline queue item $id: $e');
    }
  }

  /// Clear all cache data
  Future<void> clearCache() async {
    try {
      final cachePath = await AICOPaths.getCachePath();
      final directory = Directory(cachePath);
      
      if (await directory.exists()) {
        await directory.delete(recursive: true);
      }
    } catch (e) {
      throw LocalStorageException('Failed to clear cache: $e');
    }
  }

  /// Clear all state data (dangerous - use with caution)
  Future<void> clearAllState() async {
    try {
      final statePath = await AICOPaths.getStatePath();
      final directory = Directory(statePath);
      
      if (await directory.exists()) {
        await directory.delete(recursive: true);
      }
    } catch (e) {
      throw LocalStorageException('Failed to clear state: $e');
    }
  }

  /// Get storage statistics
  Future<StorageStats> getStorageStats() async {
    try {
      final statePath = await AICOPaths.getStatePath();
      final cachePath = await AICOPaths.getCachePath();
      final queuePath = await AICOPaths.getOfflineQueuePath();
      
      final stateSize = await _getDirectorySize(statePath);
      final cacheSize = await _getDirectorySize(cachePath);
      final queueSize = await _getDirectorySize(queuePath);
      
      return StorageStats(
        stateSize: stateSize,
        cacheSize: cacheSize,
        queueSize: queueSize,
        totalSize: stateSize + cacheSize + queueSize,
      );
    } catch (e) {
      throw LocalStorageException('Failed to get storage stats: $e');
    }
  }

  /// Calculate directory size in bytes
  Future<int> _getDirectorySize(String dirPath) async {
    final directory = Directory(dirPath);
    if (!await directory.exists()) {
      return 0;
    }
    
    int size = 0;
    await for (final entity in directory.list(recursive: true)) {
      if (entity is File) {
        size += await entity.length();
      }
    }
    return size;
  }
}

/// Storage statistics
class StorageStats {
  final int stateSize;
  final int cacheSize;
  final int queueSize;
  final int totalSize;

  const StorageStats({
    required this.stateSize,
    required this.cacheSize,
    required this.queueSize,
    required this.totalSize,
  });

  /// Format size in human-readable format
  String formatSize(int bytes) {
    if (bytes < 1024) return '${bytes}B';
    if (bytes < 1024 * 1024) return '${(bytes / 1024).toStringAsFixed(1)}KB';
    if (bytes < 1024 * 1024 * 1024) return '${(bytes / (1024 * 1024)).toStringAsFixed(1)}MB';
    return '${(bytes / (1024 * 1024 * 1024)).toStringAsFixed(1)}GB';
  }

  @override
  String toString() {
    return 'StorageStats(state: ${formatSize(stateSize)}, '
           'cache: ${formatSize(cacheSize)}, '
           'queue: ${formatSize(queueSize)}, '
           'total: ${formatSize(totalSize)})';
  }
}

/// Exception for local storage errors
class LocalStorageException implements Exception {
  final String message;
  const LocalStorageException(this.message);

  @override
  String toString() => 'LocalStorageException: $message';
}
