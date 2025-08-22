import 'package:flutter_test/flutter_test.dart';
import 'package:aico_ui/features/connection/repositories/connection_repository.dart';
import 'package:aico_ui/core/services/api_client.dart';
import 'package:aico_ui/core/services/local_storage.dart';

class FakeApiClient implements ApiClient {
  final bool shouldThrow;
  final Map<String, dynamic>? mockResponse;

  FakeApiClient({this.shouldThrow = false, this.mockResponse});

  @override
  Future<ApiResponse<T>> get<T>(
    String endpoint, {
    Map<String, String>? headers,
    Map<String, dynamic>? queryParams,
    T Function(Map<String, dynamic>)? fromJson,
  }) async {
    if (shouldThrow) throw Exception('API request failed');
    
    final data = mockResponse ?? {
      'status': 'healthy',
      'version': '1.0.0',
      'uptime': 3600,
    };
    
    return ApiResponse<T>(
      data: fromJson != null ? fromJson(data) : null,
      isSuccess: true,
      statusCode: 200,
      rawData: data,
    );
  }

  @override
  Future<ApiResponse<T>> post<T>(
    String endpoint, {
    Map<String, String>? headers,
    Map<String, dynamic>? body,
    T Function(Map<String, dynamic>)? fromJson,
  }) async {
    throw UnimplementedError();
  }

  @override
  Future<ApiResponse<T>> put<T>(
    String endpoint, {
    Map<String, String>? headers,
    Map<String, dynamic>? body,
    T Function(Map<String, dynamic>)? fromJson,
  }) async {
    throw UnimplementedError();
  }

  @override
  Future<ApiResponse<T>> delete<T>(
    String endpoint, {
    Map<String, String>? headers,
    T Function(Map<String, dynamic>)? fromJson,
  }) async {
    throw UnimplementedError();
  }

  @override
  Future<void> dispose() async {}
}

class FakeLocalStorage extends LocalStorage {
  final Map<String, Map<String, dynamic>> _storage = {};
  final bool shouldThrow;

  FakeLocalStorage({this.shouldThrow = false});

  @override
  Future<void> saveState(String key, Map<String, dynamic> data) async {
    if (shouldThrow) throw Exception('Storage save failed');
    _storage[key] = Map.from(data);
  }

  @override
  Future<Map<String, dynamic>?> loadState(String key) async {
    if (shouldThrow) throw Exception('Storage load failed');
    return _storage[key];
  }

  @override
  Future<void> savePreferences(Map<String, dynamic> preferences) async {
    if (shouldThrow) throw Exception('Storage save failed');
    _storage['preferences'] = Map.from(preferences);
  }

  @override
  Future<Map<String, dynamic>?> loadPreferences() async {
    if (shouldThrow) throw Exception('Storage load failed');
    return _storage['preferences'];
  }

  @override
  Future<void> saveCache(String key, Map<String, dynamic> data) async {
    if (shouldThrow) throw Exception('Storage save failed');
    _storage['cache_$key'] = Map.from(data);
  }

  @override
  Future<Map<String, dynamic>?> loadCache(String key) async {
    if (shouldThrow) throw Exception('Storage load failed');
    return _storage['cache_$key'];
  }

  @override
  Future<void> saveOfflineQueueItem(String id, Map<String, dynamic> item) async {
    if (shouldThrow) throw Exception('Storage save failed');
    _storage['queue_$id'] = Map.from(item);
  }

  @override
  Future<List<Map<String, dynamic>>> loadOfflineQueue() async {
    if (shouldThrow) throw Exception('Storage load failed');
    return _storage.entries
        .where((e) => e.key.startsWith('queue_'))
        .map((e) => e.value)
        .toList();
  }

  @override
  Future<void> removeOfflineQueueItem(String id) async {
    if (shouldThrow) throw Exception('Storage remove failed');
    _storage.remove('queue_$id');
  }

  @override
  Future<void> clearCache() async {
    if (shouldThrow) throw Exception('Storage clear failed');
    _storage.removeWhere((key, value) => key.startsWith('cache_'));
  }

  @override
  Future<void> clearAllState() async {
    if (shouldThrow) throw Exception('Storage clear all failed');
    _storage.clear();
  }

  @override
  Future<StorageStats> getStorageStats() async {
    if (shouldThrow) throw Exception('Storage stats failed');
    return const StorageStats(
      stateSize: 1024,
      cacheSize: 512,
      queueSize: 256,
      totalSize: 1792,
    );
  }
}

void main() {
  group('ConnectionRepository', () {
    late ConnectionRepository repository;
    late FakeApiClient apiClient;
    late FakeLocalStorage localStorage;

    setUp(() {
      apiClient = FakeApiClient();
      localStorage = FakeLocalStorage();
      repository = ConnectionRepository(
        apiClient: apiClient,
        localStorage: localStorage,
      );
    });

    group('testConnection', () {
      test('returns connection info on successful health check', () async {
        final connectionInfo = await repository.testConnection(
          serverUrl: 'http://test:8000',
        );

        expect(connectionInfo.serverUrl, 'http://test:8000');
        expect(connectionInfo.serverVersion, '1.0.0');
        expect(connectionInfo.isHealthy, isTrue);
        expect(connectionInfo.connectedAt, isA<DateTime>());
      });

      test('uses default URL when none provided', () async {
        final connectionInfo = await repository.testConnection();

        expect(connectionInfo.serverUrl, 'http://localhost:8000');
        expect(connectionInfo.serverVersion, '1.0.0');
        expect(connectionInfo.isHealthy, isTrue);
      });

      test('handles unknown version gracefully', () async {
        apiClient = FakeApiClient(mockResponse: {'status': 'healthy'});
        repository = ConnectionRepository(
          apiClient: apiClient,
          localStorage: localStorage,
        );

        final connectionInfo = await repository.testConnection();
        expect(connectionInfo.serverVersion, 'unknown');
      });

      test('throws ConnectionException when API fails', () async {
        apiClient = FakeApiClient(shouldThrow: true);
        repository = ConnectionRepository(
          apiClient: apiClient,
          localStorage: localStorage,
        );

        await expectLater(
          () => repository.testConnection(),
          throwsA(isA<ConnectionException>()),
        );
      });

      test('throws ConnectionException when health check fails', () async {
        apiClient = FakeApiClient(shouldThrow: true);
        repository = ConnectionRepository(
          apiClient: apiClient,
          localStorage: localStorage,
        );

        await expectLater(
          () => repository.testConnection(),
          throwsA(isA<ConnectionException>()),
        );
      });
    });

    group('getServerStatus', () {
      test('returns server status on successful request', () async {
        final status = await repository.getServerStatus();

        expect(status.status, 'healthy');
        expect(status.version, '1.0.0');
        expect(status.uptime, 3600);
        expect(status.timestamp, isA<DateTime>());
      });

      test('handles missing optional fields gracefully', () async {
        apiClient = FakeApiClient(mockResponse: {'status': 'healthy'});
        repository = ConnectionRepository(
          apiClient: apiClient,
          localStorage: localStorage,
        );

        final status = await repository.getServerStatus();
        expect(status.version, 'unknown');
        expect(status.uptime, 0);
      });

      test('throws ConnectionException when API fails', () async {
        apiClient = FakeApiClient(shouldThrow: true);
        repository = ConnectionRepository(
          apiClient: apiClient,
          localStorage: localStorage,
        );

        expect(
          () => repository.getServerStatus(),
          throwsA(isA<ConnectionException>()),
        );
      });
    });

    group('saveConnectionSettings', () {
      test('saves settings to local storage', () async {
        const settings = ConnectionSettings(
          defaultServerUrl: 'http://custom:8000',
          connectionTimeout: 60000,
          retryAttempts: 5,
          autoReconnect: false,
        );

        await repository.saveConnectionSettings(settings);

        final stored = await localStorage.loadState('connection_settings');
        expect(stored!['defaultServerUrl'], 'http://custom:8000');
        expect(stored['connectionTimeout'], 60000);
        expect(stored['retryAttempts'], 5);
        expect(stored['autoReconnect'], false);
      });

      test('throws ConnectionException when storage fails', () async {
        localStorage = FakeLocalStorage(shouldThrow: true);
        repository = ConnectionRepository(
          apiClient: apiClient,
          localStorage: localStorage,
        );

        const settings = ConnectionSettings(defaultServerUrl: 'http://test:8000');
        expect(
          () => repository.saveConnectionSettings(settings),
          throwsA(isA<ConnectionException>()),
        );
      });
    });

    group('loadConnectionSettings', () {
      test('returns settings when they exist', () async {
        await localStorage.saveState('connection_settings', {
          'defaultServerUrl': 'http://saved:8000',
          'connectionTimeout': 45000,
          'retryAttempts': 2,
          'autoReconnect': true,
        });

        final settings = await repository.loadConnectionSettings();
        expect(settings!.defaultServerUrl, 'http://saved:8000');
        expect(settings.connectionTimeout, 45000);
        expect(settings.retryAttempts, 2);
        expect(settings.autoReconnect, true);
      });

      test('returns null when no settings exist', () async {
        final settings = await repository.loadConnectionSettings();
        expect(settings, isNull);
      });

      test('throws ConnectionException when storage fails', () async {
        localStorage = FakeLocalStorage(shouldThrow: true);
        repository = ConnectionRepository(
          apiClient: apiClient,
          localStorage: localStorage,
        );

        expect(
          () => repository.loadConnectionSettings(),
          throwsA(isA<ConnectionException>()),
        );
      });
    });

    group('saveLastConnection', () {
      test('saves connection info to local storage', () async {
        final connectionInfo = ConnectionInfo(
          serverUrl: 'http://last:8000',
          serverVersion: '2.0.0',
          isHealthy: true,
          connectedAt: DateTime.now(),
        );

        await repository.saveLastConnection(connectionInfo);

        final stored = await localStorage.loadState('last_connection');
        expect(stored!['serverUrl'], 'http://last:8000');
        expect(stored['serverVersion'], '2.0.0');
        expect(stored['isHealthy'], true);
        expect(stored['connectedAt'], isA<String>());
      });

      test('throws ConnectionException when storage fails', () async {
        localStorage = FakeLocalStorage(shouldThrow: true);
        repository = ConnectionRepository(
          apiClient: apiClient,
          localStorage: localStorage,
        );

        final connectionInfo = ConnectionInfo(
          serverUrl: 'http://test:8000',
          serverVersion: '1.0.0',
          isHealthy: true,
          connectedAt: DateTime.now(),
        );

        expect(
          () => repository.saveLastConnection(connectionInfo),
          throwsA(isA<ConnectionException>()),
        );
      });
    });

    group('loadLastConnection', () {
      test('returns connection info when it exists', () async {
        final now = DateTime.now();
        await localStorage.saveState('last_connection', {
          'serverUrl': 'http://loaded:8000',
          'serverVersion': '1.5.0',
          'isHealthy': false,
          'connectedAt': now.toIso8601String(),
        });

        final connectionInfo = await repository.loadLastConnection();
        expect(connectionInfo!.serverUrl, 'http://loaded:8000');
        expect(connectionInfo.serverVersion, '1.5.0');
        expect(connectionInfo.isHealthy, false);
        expect(connectionInfo.connectedAt, now);
      });

      test('returns null when no connection info exists', () async {
        final connectionInfo = await repository.loadLastConnection();
        expect(connectionInfo, isNull);
      });

      test('throws ConnectionException when storage fails', () async {
        localStorage = FakeLocalStorage(shouldThrow: true);
        repository = ConnectionRepository(
          apiClient: apiClient,
          localStorage: localStorage,
        );

        expect(
          () => repository.loadLastConnection(),
          throwsA(isA<ConnectionException>()),
        );
      });
    });

    group('dispose', () {
      test('completes without error', () async {
        await expectLater(repository.dispose(), completes);
      });
    });
  });

  group('ConnectionInfo', () {
    test('toJson serializes correctly', () {
      final now = DateTime.now();
      final connectionInfo = ConnectionInfo(
        serverUrl: 'http://test:8000',
        serverVersion: '1.0.0',
        isHealthy: true,
        connectedAt: now,
      );

      final json = connectionInfo.toJson();
      expect(json['serverUrl'], 'http://test:8000');
      expect(json['serverVersion'], '1.0.0');
      expect(json['isHealthy'], true);
      expect(json['connectedAt'], now.toIso8601String());
    });

    test('fromJson deserializes correctly', () {
      final now = DateTime.now();
      final json = {
        'serverUrl': 'http://test:8000',
        'serverVersion': '1.0.0',
        'isHealthy': true,
        'connectedAt': now.toIso8601String(),
      };

      final connectionInfo = ConnectionInfo.fromJson(json);
      expect(connectionInfo.serverUrl, 'http://test:8000');
      expect(connectionInfo.serverVersion, '1.0.0');
      expect(connectionInfo.isHealthy, true);
      expect(connectionInfo.connectedAt, now);
    });
  });

  group('ServerStatus', () {
    test('toJson serializes correctly', () {
      final now = DateTime.now();
      final status = ServerStatus(
        status: 'healthy',
        version: '1.0.0',
        uptime: 3600,
        timestamp: now,
      );

      final json = status.toJson();
      expect(json['status'], 'healthy');
      expect(json['version'], '1.0.0');
      expect(json['uptime'], 3600);
      expect(json['timestamp'], now.toIso8601String());
    });

    test('fromJson deserializes correctly', () {
      final now = DateTime.now();
      final json = {
        'status': 'healthy',
        'version': '1.0.0',
        'uptime': 3600,
        'timestamp': now.toIso8601String(),
      };

      final status = ServerStatus.fromJson(json);
      expect(status.status, 'healthy');
      expect(status.version, '1.0.0');
      expect(status.uptime, 3600);
      expect(status.timestamp, now);
    });
  });

  group('ConnectionSettings', () {
    test('toJson serializes correctly', () {
      const settings = ConnectionSettings(
        defaultServerUrl: 'http://test:8000',
        connectionTimeout: 60000,
        retryAttempts: 5,
        autoReconnect: false,
      );

      final json = settings.toJson();
      expect(json['defaultServerUrl'], 'http://test:8000');
      expect(json['connectionTimeout'], 60000);
      expect(json['retryAttempts'], 5);
      expect(json['autoReconnect'], false);
    });

    test('fromJson deserializes correctly', () {
      final json = {
        'defaultServerUrl': 'http://test:8000',
        'connectionTimeout': 60000,
        'retryAttempts': 5,
        'autoReconnect': false,
      };

      final settings = ConnectionSettings.fromJson(json);
      expect(settings.defaultServerUrl, 'http://test:8000');
      expect(settings.connectionTimeout, 60000);
      expect(settings.retryAttempts, 5);
      expect(settings.autoReconnect, false);
    });

    test('fromJson uses defaults for missing fields', () {
      final json = {
        'defaultServerUrl': 'http://test:8000',
      };

      final settings = ConnectionSettings.fromJson(json);
      expect(settings.defaultServerUrl, 'http://test:8000');
      expect(settings.connectionTimeout, 30000);
      expect(settings.retryAttempts, 3);
      expect(settings.autoReconnect, true);
    });

    test('copyWith updates specified fields', () {
      const original = ConnectionSettings(
        defaultServerUrl: 'http://original:8000',
        connectionTimeout: 30000,
        retryAttempts: 3,
        autoReconnect: true,
      );

      final updated = original.copyWith(
        defaultServerUrl: 'http://updated:8000',
        retryAttempts: 5,
      );

      expect(updated.defaultServerUrl, 'http://updated:8000');
      expect(updated.connectionTimeout, 30000); // unchanged
      expect(updated.retryAttempts, 5);
      expect(updated.autoReconnect, true); // unchanged
    });
  });

  group('ConnectionException', () {
    test('toString returns formatted message', () {
      const exception = ConnectionException('Test error message');
      expect(exception.toString(), 'ConnectionException: Test error message');
    });
  });
}
