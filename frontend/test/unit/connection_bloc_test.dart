import 'package:aico_frontend/presentation/blocs/connection/connection_bloc.dart';
import 'package:bloc_test/bloc_test.dart';
import 'package:flutter_test/flutter_test.dart';

// Tests for ConnectionBloc - simplified to match actual implementation

void main() {
  group('ConnectionBloc', () {
    blocTest<ConnectionBloc, ConnectionState>(
      'emits [connecting, connected] when ConnectionConnect succeeds',
      build: () => ConnectionBloc(),
      act: (bloc) => bloc.add(const ConnectionConnect()),
      expect: () => [
        isA<ConnectionConnecting>(),
        isA<ConnectionConnected>(),
      ],
    );

    blocTest<ConnectionBloc, ConnectionState>(
      'emits [disconnected] when ConnectionDisconnect is added',
      build: () => ConnectionBloc(),
      act: (bloc) => bloc.add(const ConnectionDisconnect()),
      expect: () => [
        isA<ConnectionDisconnected>(),
      ],
    );

    blocTest<ConnectionBloc, ConnectionState>(
      'emits [connecting, connected] when ConnectionInitialize is added',
      build: () => ConnectionBloc(),
      act: (bloc) => bloc.add(const ConnectionInitialize()),
      expect: () => [
        isA<ConnectionConnecting>(),
        isA<ConnectionConnected>(),
      ],
    );

    blocTest<ConnectionBloc, ConnectionState>(
      'emits correct state when ConnectionStatusChanged is added',
      build: () => ConnectionBloc(),
      act: (bloc) => bloc.add(const ConnectionStatusChanged(ConnectionStatus.connected)),
      expect: () => [
        isA<ConnectionConnected>(),
      ],
    );

    blocTest<ConnectionBloc, ConnectionState>(
      'emits error state when ConnectionStatusChanged with error',
      build: () => ConnectionBloc(),
      act: (bloc) => bloc.add(const ConnectionStatusChanged(ConnectionStatus.error)),
      expect: () => [
        isA<ConnectionError>(),
      ],
    );

    blocTest<ConnectionBloc, ConnectionState>(
      'emits offline state when ConnectionStatusChanged with offline',
      build: () => ConnectionBloc(),
      act: (bloc) => bloc.add(const ConnectionStatusChanged(ConnectionStatus.offline)),
      expect: () => [
        isA<ConnectionOffline>(),
      ],
    );
  });

  group('ConnectionBloc state management', () {
    test('initial state is ConnectionInitial', () {
      final bloc = ConnectionBloc();
      expect(bloc.state, isA<ConnectionInitial>());
      bloc.close();
    });

    test('ConnectionError contains message', () {
      const errorState = ConnectionError('Test error');
      expect(errorState.message, 'Test error');
      expect(errorState.props, ['Test error']);
    });

    test('ConnectionDisconnected can have optional reason', () {
      const disconnectedState = ConnectionDisconnected(reason: 'User requested');
      expect(disconnectedState.reason, 'User requested');
      expect(disconnectedState.props, ['User requested']);
    });

    test('ConnectionStatus enum has all expected values', () {
      expect(ConnectionStatus.values, contains(ConnectionStatus.initializing));
      expect(ConnectionStatus.values, contains(ConnectionStatus.connecting));
      expect(ConnectionStatus.values, contains(ConnectionStatus.connected));
      expect(ConnectionStatus.values, contains(ConnectionStatus.disconnected));
      expect(ConnectionStatus.values, contains(ConnectionStatus.offline));
      expect(ConnectionStatus.values, contains(ConnectionStatus.error));
    });
  });
}
