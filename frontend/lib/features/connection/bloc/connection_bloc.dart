import 'package:aico_frontend/features/connection/models/connection_event.dart';
import 'package:aico_frontend/features/connection/models/connection_state.dart';
import 'package:aico_frontend/features/connection/repositories/connection_repository.dart';
import 'package:hydrated_bloc/hydrated_bloc.dart';

/// BLoC for managing connection state with automatic persistence
/// Handles all connection-related business logic and state transitions
class ConnectionBloc extends HydratedBloc<ConnectionEvent, ConnectionState> {
  final ConnectionRepository _repository;

  ConnectionBloc({
    required ConnectionRepository repository,
  })  : _repository = repository,
        super(const ConnectionInitial()) {
    on<ConnectionConnect>(_onConnect);
    on<ConnectionDisconnect>(_onDisconnect);
    on<ConnectionReconnect>(_onReconnect);
    on<ConnectionCheckStatus>(_onCheckStatus);
    on<ConnectionUpdateServerUrl>(_onUpdateServerUrl);
    on<ConnectionTimeout>(_onTimeout);
    on<ConnectionRestored>(_onRestored);
  }

  /// Handle connection request
  Future<void> _onConnect(
    ConnectionConnect event,
    Emitter<ConnectionState> emit,
  ) async {
    emit(const ConnectionConnecting());

    try {
      // Load settings to get server URL if not provided
      final settings = await _repository.loadConnectionSettings();
      final serverUrl = event.serverUrl ?? settings?.defaultServerUrl ?? 'http://localhost:8000';

      // Test connection
      final connectionInfo = await _repository.testConnection(serverUrl: serverUrl);

      // Save successful connection
      await _repository.saveLastConnection(connectionInfo);

      emit(ConnectionConnected(
        serverUrl: connectionInfo.serverUrl,
        serverVersion: connectionInfo.serverVersion,
        connectedAt: connectionInfo.connectedAt,
      ));
    } catch (e) {
      emit(ConnectionError(
        message: e.toString(),
        occurredAt: DateTime.now(),
      ));
    }
  }

  /// Handle disconnection request
  Future<void> _onDisconnect(
    ConnectionDisconnect event,
    Emitter<ConnectionState> emit,
  ) async {
    emit(ConnectionDisconnected(
      reason: event.reason,
      disconnectedAt: DateTime.now(),
    ));
  }

  /// Handle reconnection request
  Future<void> _onReconnect(
    ConnectionReconnect event,
    Emitter<ConnectionState> emit,
  ) async {
    // Get last connection info
    final lastConnection = await _repository.loadLastConnection();
    if (lastConnection != null) {
      add(ConnectionConnect(serverUrl: lastConnection.serverUrl));
    } else {
      add(const ConnectionConnect());
    }
  }

  /// Handle status check request
  Future<void> _onCheckStatus(
    ConnectionCheckStatus event,
    Emitter<ConnectionState> emit,
  ) async {
    if (state is ConnectionConnected) {
      try {
        await _repository.getServerStatus();
        // Connection is still good, no state change needed
      } catch (e) {
        emit(ConnectionError(
          message: 'Connection lost: $e',
          occurredAt: DateTime.now(),
        ));
      }
    }
  }

  /// Handle server URL update
  Future<void> _onUpdateServerUrl(
    ConnectionUpdateServerUrl event,
    Emitter<ConnectionState> emit,
  ) async {
    try {
      // Load current settings
      final currentSettings = await _repository.loadConnectionSettings();
      
      // Update settings with new URL
      final newSettings = (currentSettings ?? const ConnectionSettings(
        defaultServerUrl: 'http://localhost:8000',
      )).copyWith(defaultServerUrl: event.serverUrl);
      
      // Save updated settings
      await _repository.saveConnectionSettings(newSettings);
      
      // If currently connected, reconnect with new URL
      if (state is ConnectionConnected) {
        add(ConnectionConnect(serverUrl: event.serverUrl));
      }
    } catch (e) {
      emit(ConnectionError(
        message: 'Failed to update server URL: $e',
        occurredAt: DateTime.now(),
      ));
    }
  }

  /// Handle connection timeout
  Future<void> _onTimeout(
    ConnectionTimeout event,
    Emitter<ConnectionState> emit,
  ) async {
    emit(ConnectionError(
      message: 'Connection timeout',
      occurredAt: DateTime.now(),
    ));
  }

  /// Handle connection restored
  Future<void> _onRestored(
    ConnectionRestored event,
    Emitter<ConnectionState> emit,
  ) async {
    add(const ConnectionReconnect());
  }

  @override
  ConnectionState? fromJson(Map<String, dynamic> json) {
    try {
      final type = json['type'] as String;
      switch (type) {
        case 'initial':
          return const ConnectionInitial();
        case 'connecting':
          return const ConnectionConnecting();
        case 'connected':
          return ConnectionConnected(
            serverUrl: json['serverUrl'] as String,
            serverVersion: json['serverVersion'] as String,
            connectedAt: DateTime.parse(json['connectedAt'] as String),
          );
        case 'error':
          return ConnectionError(
            message: json['message'] as String,
            errorCode: json['errorCode'] as String?,
            occurredAt: json['occurredAt'] != null 
                ? DateTime.parse(json['occurredAt'] as String)
                : DateTime.now(),
          );
        case 'disconnected':
          return ConnectionDisconnected(
            reason: json['reason'] as String?,
            disconnectedAt: json['disconnectedAt'] != null
                ? DateTime.parse(json['disconnectedAt'] as String)
                : null,
          );
        default:
          return null;
      }
    } catch (e) {
      return null; // Return null to use initial state
    }
  }

  @override
  Map<String, dynamic>? toJson(ConnectionState state) {
    return state.toJson();
  }
}
