// Import the actual enums used by the connection system
import 'package:aico_frontend/networking/services/connection_manager.dart' show InternalConnectionStatus;
import 'package:equatable/equatable.dart';

/// Domain entity representing the connection state to the backend
class ConnectionState extends Equatable {
  final InternalConnectionStatus status;
  final String? errorMessage;
  final DateTime lastConnected;
  final DateTime? lastAttempt;
  final int retryCount;
  final Duration? nextRetryIn;
  final ConnectionMode mode;
  final bool encryptionActive;

  const ConnectionState({
    required this.status,
    this.errorMessage,
    required this.lastConnected,
    this.lastAttempt,
    this.retryCount = 0,
    this.nextRetryIn,
    this.mode = ConnectionMode.http,
    this.encryptionActive = false,
  });

  @override
  List<Object?> get props => [
        status,
        errorMessage,
        lastConnected,
        lastAttempt,
        retryCount,
        nextRetryIn,
        mode,
        encryptionActive,
      ];

  ConnectionState copyWith({
    InternalConnectionStatus? status,
    String? errorMessage,
    DateTime? lastConnected,
    DateTime? lastAttempt,
    int? retryCount,
    Duration? nextRetryIn,
    ConnectionMode? mode,
    bool? encryptionActive,
  }) {
    return ConnectionState(
      status: status ?? this.status,
      errorMessage: errorMessage ?? this.errorMessage,
      lastConnected: lastConnected ?? this.lastConnected,
      lastAttempt: lastAttempt ?? this.lastAttempt,
      retryCount: retryCount ?? this.retryCount,
      nextRetryIn: nextRetryIn ?? this.nextRetryIn,
      mode: mode ?? this.mode,
      encryptionActive: encryptionActive ?? this.encryptionActive,
    );
  }
}

enum ConnectionMode {
  http,
  httpFallback,
  websocket,
  ipc, // Future implementation
}

extension ConnectionModeExtension on ConnectionMode {
  String get displayName {
    switch (this) {
      case ConnectionMode.http:
        return 'HTTP';
      case ConnectionMode.httpFallback:
        return 'HTTP (Fallback)';
      case ConnectionMode.websocket:
        return 'WebSocket';
      case ConnectionMode.ipc:
        return 'IPC';
    }
  }
  
  bool get isRealTime => this == ConnectionMode.websocket || this == ConnectionMode.ipc;
  bool get isHighPerformance => this == ConnectionMode.ipc;
}
