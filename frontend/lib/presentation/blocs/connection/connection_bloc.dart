import 'package:bloc/bloc.dart';
import 'package:equatable/equatable.dart';

// Events
abstract class ConnectionEvent extends Equatable {
  const ConnectionEvent();

  @override
  List<Object?> get props => [];
}

class ConnectionInitialize extends ConnectionEvent {
  const ConnectionInitialize();
}

class ConnectionConnect extends ConnectionEvent {
  const ConnectionConnect();
}

class ConnectionDisconnect extends ConnectionEvent {
  const ConnectionDisconnect();
}

class ConnectionStatusChanged extends ConnectionEvent {
  final ConnectionStatus status;

  const ConnectionStatusChanged(this.status);

  @override
  List<Object?> get props => [status];
}

// States
abstract class ConnectionState extends Equatable {
  const ConnectionState();

  @override
  List<Object?> get props => [];
}

class ConnectionInitial extends ConnectionState {
  const ConnectionInitial();
}

class ConnectionConnecting extends ConnectionState {
  const ConnectionConnecting();
}

class ConnectionConnected extends ConnectionState {
  const ConnectionConnected();
}

class ConnectionDisconnected extends ConnectionState {
  final String? reason;

  const ConnectionDisconnected({this.reason});

  @override
  List<Object?> get props => [reason];
}

class ConnectionOffline extends ConnectionState {
  const ConnectionOffline();
}

class ConnectionError extends ConnectionState {
  final String message;

  const ConnectionError(this.message);

  @override
  List<Object?> get props => [message];
}

// Connection Status Enum
enum ConnectionStatus {
  initializing,
  connecting,
  connected,
  disconnected,
  offline,
  error,
}

// BLoC
class ConnectionBloc extends Bloc<ConnectionEvent, ConnectionState> {
  ConnectionBloc() : super(const ConnectionInitial()) {
    on<ConnectionInitialize>(_onInitialize);
    on<ConnectionConnect>(_onConnect);
    on<ConnectionDisconnect>(_onDisconnect);
    on<ConnectionStatusChanged>(_onStatusChanged);
  }

  Future<void> _onInitialize(
    ConnectionInitialize event,
    Emitter<ConnectionState> emit,
  ) async {
    emit(const ConnectionConnecting());
    // TODO: Initialize connection logic
    emit(const ConnectionConnected());
  }

  Future<void> _onConnect(
    ConnectionConnect event,
    Emitter<ConnectionState> emit,
  ) async {
    emit(const ConnectionConnecting());
    // TODO: Connection logic
    emit(const ConnectionConnected());
  }

  Future<void> _onDisconnect(
    ConnectionDisconnect event,
    Emitter<ConnectionState> emit,
  ) async {
    emit(const ConnectionDisconnected());
  }

  Future<void> _onStatusChanged(
    ConnectionStatusChanged event,
    Emitter<ConnectionState> emit,
  ) async {
    switch (event.status) {
      case ConnectionStatus.connecting:
        emit(const ConnectionConnecting());
        break;
      case ConnectionStatus.connected:
        emit(const ConnectionConnected());
        break;
      case ConnectionStatus.disconnected:
        emit(const ConnectionDisconnected());
        break;
      case ConnectionStatus.offline:
        emit(const ConnectionOffline());
        break;
      case ConnectionStatus.error:
        emit(const ConnectionError('Connection error occurred'));
        break;
      case ConnectionStatus.initializing:
        emit(const ConnectionInitial());
        break;
    }
  }
}
