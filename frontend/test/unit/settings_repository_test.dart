import 'package:aico_frontend/core/services/local_storage.dart';
import 'package:flutter_test/flutter_test.dart';

class MockLocalStorage extends LocalStorage {
  final Map<String, Map<String, dynamic>> _storage = {};
  final bool shouldThrow;

  MockLocalStorage({this.shouldThrow = false});

  @override
  Future<void> saveState(String key, Map<String, dynamic> data) async {
    if (shouldThrow) throw const LocalStorageException('Storage save failed');
    _storage[key] = Map.from(data);
  }

  @override
  Future<Map<String, dynamic>?> loadState(String key) async {
    if (shouldThrow) throw const LocalStorageException('Storage load failed');
    return _storage[key];
  }

  @override
  Future<void> savePreferences(Map<String, dynamic> preferences) async {
    if (shouldThrow) throw const LocalStorageException('Storage save failed');
    _storage['preferences'] = Map.from(preferences);
  }

  @override
  Future<Map<String, dynamic>?> loadPreferences() async {
    if (shouldThrow) throw const LocalStorageException('Storage load failed');
    return _storage['preferences'];
  }

  @override
  Future<void> saveCache(String key, Map<String, dynamic> data) async {
    if (shouldThrow) throw const LocalStorageException('Storage save failed');
    _storage['cache_$key'] = Map.from(data);
  }

  @override
  Future<Map<String, dynamic>?> loadCache(String key) async {
    if (shouldThrow) throw const LocalStorageException('Storage load failed');
    return _storage['cache_$key'];
  }

  @override
  Future<void> saveOfflineQueueItem(String id, Map<String, dynamic> item) async {
    if (shouldThrow) throw const LocalStorageException('Storage save failed');
    _storage['queue_$id'] = Map.from(item);
  }

  @override
  Future<List<Map<String, dynamic>>> loadOfflineQueue() async {
    if (shouldThrow) throw const LocalStorageException('Storage load failed');
    return _storage.entries
        .where((e) => e.key.startsWith('queue_'))
        .map((e) => e.value)
        .toList();
  }

  @override
  Future<void> removeOfflineQueueItem(String id) async {
    if (shouldThrow) throw const LocalStorageException('Storage remove failed');
    _storage.remove('queue_$id');
  }

  @override
  Future<void> clearCache() async {
    if (shouldThrow) throw const LocalStorageException('Storage clear failed');
    _storage.removeWhere((key, value) => key.startsWith('cache_'));
  }

  @override
  Future<void> clearAllState() async {
    if (shouldThrow) throw const LocalStorageException('Storage clear all failed');
    _storage.clear();
  }

  @override
  Future<StorageStats> getStorageStats() async {
    if (shouldThrow) throw const LocalStorageException('Storage stats failed');
    return const StorageStats(
      stateSize: 1024,
      cacheSize: 512,
      queueSize: 256,
      totalSize: 1792,
    );
  }
}

void main() {
  group('LocalStorage', () {
    late MockLocalStorage localStorage;

    setUp(() {
      localStorage = MockLocalStorage();
    });

    group('State Management', () {
      test('saves and loads state data', () async {
        const testData = {'theme': 'dark', 'locale': 'en'};
        
        await localStorage.saveState('settings', testData);
        final loaded = await localStorage.loadState('settings');
        
        expect(loaded, equals(testData));
      });

      test('returns null when state does not exist', () async {
        final loaded = await localStorage.loadState('nonexistent');
        expect(loaded, isNull);
      });

      test('throws LocalStorageException when save fails', () async {
        localStorage = MockLocalStorage(shouldThrow: true);
        
        expect(
          () => localStorage.saveState('test', {}),
          throwsA(isA<LocalStorageException>()),
        );
      });

      test('throws LocalStorageException when load fails', () async {
        localStorage = MockLocalStorage(shouldThrow: true);
        
        expect(
          () => localStorage.loadState('test'),
          throwsA(isA<LocalStorageException>()),
        );
      });
    });

    group('Preferences Management', () {
      test('saves and loads preferences', () async {
        const preferences = {'notifications': true, 'autoConnect': false};
        
        await localStorage.savePreferences(preferences);
        final loaded = await localStorage.loadPreferences();
        
        expect(loaded, equals(preferences));
      });

      test('returns null when preferences do not exist', () async {
        final loaded = await localStorage.loadPreferences();
        expect(loaded, isNull);
      });
    });

    group('Cache Management', () {
      test('saves and loads cache data', () async {
        const cacheData = {'apiResponse': 'cached_value'};
        
        await localStorage.saveCache('api_key', cacheData);
        final loaded = await localStorage.loadCache('api_key');
        
        expect(loaded, equals(cacheData));
      });

      test('clears cache data', () async {
        await localStorage.saveCache('key1', {'data': 'value1'});
        await localStorage.saveCache('key2', {'data': 'value2'});
        
        await localStorage.clearCache();
        
        final loaded1 = await localStorage.loadCache('key1');
        final loaded2 = await localStorage.loadCache('key2');
        
        expect(loaded1, isNull);
        expect(loaded2, isNull);
      });
    });

    group('Offline Queue Management', () {
      test('saves and loads offline queue items', () async {
        const item1 = {'action': 'sync', 'data': 'test1'};
        const item2 = {'action': 'upload', 'data': 'test2'};
        
        await localStorage.saveOfflineQueueItem('id1', item1);
        await localStorage.saveOfflineQueueItem('id2', item2);
        
        final queue = await localStorage.loadOfflineQueue();
        
        expect(queue.length, equals(2));
        expect(queue, containsAll([item1, item2]));
      });

      test('removes offline queue items', () async {
        const item = {'action': 'test'};
        
        await localStorage.saveOfflineQueueItem('test_id', item);
        await localStorage.removeOfflineQueueItem('test_id');
        
        final queue = await localStorage.loadOfflineQueue();
        expect(queue, isEmpty);
      });

      test('returns empty list when no queue items exist', () async {
        final queue = await localStorage.loadOfflineQueue();
        expect(queue, isEmpty);
      });
    });

    group('Storage Statistics', () {
      test('returns storage statistics', () async {
        final stats = await localStorage.getStorageStats();
        
        expect(stats.stateSize, equals(1024));
        expect(stats.cacheSize, equals(512));
        expect(stats.queueSize, equals(256));
        expect(stats.totalSize, equals(1792));
      });

      test('formats storage sizes correctly', () async {
        final stats = await localStorage.getStorageStats();
        
        expect(stats.formatSize(500), equals('500B'));
        expect(stats.formatSize(1536), equals('1.5KB'));
        expect(stats.formatSize(2097152), equals('2.0MB'));
      });
    });

    group('Error Handling', () {
      test('clears all state', () async {
        await localStorage.saveState('test1', {'data': 'value1'});
        await localStorage.saveState('test2', {'data': 'value2'});
        
        await localStorage.clearAllState();
        
        final loaded1 = await localStorage.loadState('test1');
        final loaded2 = await localStorage.loadState('test2');
        
        expect(loaded1, isNull);
        expect(loaded2, isNull);
      });

      test('handles storage exceptions properly', () async {
        localStorage = MockLocalStorage(shouldThrow: true);
        
        expect(
          () => localStorage.savePreferences({}),
          throwsA(isA<LocalStorageException>()),
        );
        
        expect(
          () => localStorage.loadPreferences(),
          throwsA(isA<LocalStorageException>()),
        );
        
        expect(
          () => localStorage.getStorageStats(),
          throwsA(isA<LocalStorageException>()),
        );
      });
    });
  });
}
