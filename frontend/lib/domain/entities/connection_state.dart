import 'package:equatable/equatable.dart';

/// Domain entity representing the connection state to the backend
class ConnectionState extends Equatable {
  final ConnectionStatus status;
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
    ConnectionStatus? status,
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

enum ConnectionStatus {
  disconnected,
  connecting,
  connected,
  reconnecting,
  failed,
}

enum ConnectionMode {
  http,
  httpFallback,
  websocket,
  ipc, // Future implementation
}

extension ConnectionStatusExtension on ConnectionStatus {
  bool get isConnected => this == ConnectionStatus.connected;
  bool get isConnecting => this == ConnectionStatus.connecting || 
                          this == ConnectionStatus.reconnecting;
  bool get hasError => this == ConnectionStatus.failed;
  
  String get displayName {
    switch (this) {
      case ConnectionStatus.disconnected:
        return 'Disconnected';
      case ConnectionStatus.connecting:
        return 'Connecting';
      case ConnectionStatus.connected:
        return 'Connected';
      case ConnectionStatus.reconnecting:
        return 'Reconnecting';
      case ConnectionStatus.failed:
        return 'Connection Failed';
    }
  }
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
