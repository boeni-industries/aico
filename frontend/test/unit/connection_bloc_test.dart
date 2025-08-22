import 'package:flutter_test/flutter_test.dart';
import 'package:bloc_test/bloc_test.dart';
import 'package:aico_frontend/features/connection/bloc/connection_bloc.dart';
import 'package:aico_frontend/features/connection/models/connection_event.dart';
import 'package:aico_frontend/features/connection/models/connection_state.dart';
import 'package:aico_frontend/features/connection/repositories/connection_repository.dart';
import 'package:hydrated_bloc/hydrated_bloc.dart';
import 'dart:io';

class FakeConnectionRepository implements ConnectionRepository {
  final bool shouldThrowOnConnect;
  final bool shouldThrowOnStatus;
  final bool shouldThrowOnSettings;
  final ConnectionInfo? mockConnectionInfo;
  final ConnectionSettings? mockSettings;

  FakeConnectionRepository({
    this.shouldThrowOnConnect = false,
    this.shouldThrowOnStatus = false,
    this.shouldThrowOnSettings = false,
    this.mockConnectionInfo,
    this.mockSettings,
  });

  @override
  Future<ConnectionInfo> testConnection({String? serverUrl}) async {
    if (shouldThrowOnConnect) throw ConnectionException('Connection failed');
    return mockConnectionInfo ?? ConnectionInfo(
      serverUrl: serverUrl ?? 'http://localhost:8000',
      serverVersion: '1.0.0',
      isHealthy: true,
      connectedAt: DateTime.now(),
    );
  }

  @override
  Future<ServerStatus> getServerStatus() async {
    if (shouldThrowOnStatus) throw ConnectionException('Status check failed');
    return ServerStatus(
      status: 'healthy',
      version: '1.0.0',
      uptime: 3600,
      timestamp: DateTime.now(),
    );
  }

  @override
  Future<ConnectionSettings?> loadConnectionSettings() async {
    if (shouldThrowOnSettings) throw ConnectionException('Settings load failed');
    return mockSettings;
  }

  @override
  Future<void> saveConnectionSettings(ConnectionSettings settings) async {
    if (shouldThrowOnSettings) throw ConnectionException('Settings save failed');
  }

  @override
  Future<ConnectionInfo?> loadLastConnection() async {
    return mockConnectionInfo;
  }

  @override
  Future<void> saveLastConnection(ConnectionInfo info) async {}

  @override
  Future<void> dispose() async {}
}

void main() {
  setUpAll(() async {
    TestWidgetsFlutterBinding.ensureInitialized();
    final storage = await HydratedStorage.build(
      storageDirectory: HydratedStorageDirectory((await Directory.systemTemp.createTemp('hydrated_bloc_test')).path),
    );
    HydratedBloc.storage = storage;
  });

  group('ConnectionBloc', () {
    blocTest<ConnectionBloc, ConnectionState>(
      'emits [connecting, connected] when ConnectionConnect succeeds',
      build: () => ConnectionBloc(repository: FakeConnectionRepository()),
      act: (bloc) => bloc.add(const ConnectionConnect()),
      expect: () => [
        isA<ConnectionConnecting>(),
        isA<ConnectionConnected>(),
      ],
    );

    blocTest<ConnectionBloc, ConnectionState>(
      'emits [connecting, error] when ConnectionConnect fails',
      build: () => ConnectionBloc(
        repository: FakeConnectionRepository(shouldThrowOnConnect: true),
      ),
      act: (bloc) => bloc.add(const ConnectionConnect()),
      expect: () => [
        isA<ConnectionConnecting>(),
        isA<ConnectionError>(),
      ],
    );

    blocTest<ConnectionBloc, ConnectionState>(
      'emits [disconnected] when ConnectionDisconnect is added',
      build: () => ConnectionBloc(repository: FakeConnectionRepository()),
      act: (bloc) => bloc.add(const ConnectionDisconnect(reason: 'User requested')),
      expect: () => [
        isA<ConnectionDisconnected>(),
      ],
    );

    blocTest<ConnectionBloc, ConnectionState>(
      'emits [connecting, connected] when ConnectionReconnect with last connection',
      build: () => ConnectionBloc(
        repository: FakeConnectionRepository(
          mockConnectionInfo: ConnectionInfo(
            serverUrl: 'http://test:8000',
            serverVersion: '1.0.0',
            isHealthy: true,
            connectedAt: DateTime.now(),
          ),
        ),
      ),
      act: (bloc) => bloc.add(const ConnectionReconnect()),
      expect: () => [
        isA<ConnectionConnecting>(),
        isA<ConnectionConnected>(),
      ],
    );

    blocTest<ConnectionBloc, ConnectionState>(
      'emits [error] when ConnectionCheckStatus fails on connected state',
      build: () => ConnectionBloc(
        repository: FakeConnectionRepository(shouldThrowOnStatus: true),
      ),
      seed: () => ConnectionConnected(
        serverUrl: 'http://localhost:8000',
        serverVersion: '1.0.0',
        connectedAt: DateTime.now(),
      ),
      act: (bloc) => bloc.add(const ConnectionCheckStatus()),
      expect: () => [
        isA<ConnectionError>(),
      ],
    );

    blocTest<ConnectionBloc, ConnectionState>(
      'emits [error] when ConnectionUpdateServerUrl fails',
      build: () => ConnectionBloc(
        repository: FakeConnectionRepository(shouldThrowOnSettings: true),
      ),
      act: (bloc) => bloc.add(const ConnectionUpdateServerUrl('http://new:8000')),
      expect: () => [
        isA<ConnectionError>(),
      ],
    );

    blocTest<ConnectionBloc, ConnectionState>(
      'emits [error] when ConnectionTimeout is added',
      build: () => ConnectionBloc(repository: FakeConnectionRepository()),
      act: (bloc) => bloc.add(const ConnectionTimeout()),
      expect: () => [
        isA<ConnectionError>(),
      ],
    );

    blocTest<ConnectionBloc, ConnectionState>(
      'emits [connecting, connected] when ConnectionRestored is added',
      build: () => ConnectionBloc(
        repository: FakeConnectionRepository(
          mockConnectionInfo: ConnectionInfo(
            serverUrl: 'http://restored:8000',
            serverVersion: '1.0.0',
            isHealthy: true,
            connectedAt: DateTime.now(),
          ),
        ),
      ),
      act: (bloc) => bloc.add(const ConnectionRestored()),
      expect: () => [
        isA<ConnectionConnecting>(),
        isA<ConnectionConnected>(),
      ],
    );
  });

  group('ConnectionBloc JSON serialization', () {
    late ConnectionBloc bloc;

    setUp(() {
      bloc = ConnectionBloc(repository: FakeConnectionRepository());
    });

    test('fromJson returns correct state for initial', () {
      final json = {'type': 'initial'};
      final state = bloc.fromJson(json);
      expect(state, isA<ConnectionInitial>());
    });

    test('fromJson returns correct state for connecting', () {
      final json = {'type': 'connecting'};
      final state = bloc.fromJson(json);
      expect(state, isA<ConnectionConnecting>());
    });

    test('fromJson returns correct state for connected', () {
      final json = {
        'type': 'connected',
        'serverUrl': 'http://test:8000',
        'serverVersion': '1.0.0',
        'connectedAt': '2023-01-01T00:00:00.000Z',
      };
      final state = bloc.fromJson(json);
      expect(state, isA<ConnectionConnected>());
      final connectedState = state as ConnectionConnected;
      expect(connectedState.serverUrl, 'http://test:8000');
      expect(connectedState.serverVersion, '1.0.0');
    });

    test('fromJson returns correct state for error', () {
      final json = {
        'type': 'error',
        'message': 'Test error',
        'errorCode': 'TEST_ERROR',
        'occurredAt': '2023-01-01T00:00:00.000Z',
      };
      final state = bloc.fromJson(json);
      expect(state, isA<ConnectionError>());
      final errorState = state as ConnectionError;
      expect(errorState.message, 'Test error');
      expect(errorState.errorCode, 'TEST_ERROR');
    });

    test('fromJson returns correct state for disconnected', () {
      final json = {
        'type': 'disconnected',
        'reason': 'User requested',
        'disconnectedAt': '2023-01-01T00:00:00.000Z',
      };
      final state = bloc.fromJson(json);
      expect(state, isA<ConnectionDisconnected>());
      final disconnectedState = state as ConnectionDisconnected;
      expect(disconnectedState.reason, 'User requested');
    });

    test('fromJson returns null for invalid JSON', () {
      final json = {'type': 'invalid'};
      final state = bloc.fromJson(json);
      expect(state, isNull);
    });

    test('fromJson returns null for malformed JSON', () {
      final json = {'invalid': 'data'};
      final state = bloc.fromJson(json);
      expect(state, isNull);
    });
  });
}
