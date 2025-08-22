import 'package:aico_frontend/core/utils/json_serializable.dart';
import 'package:equatable/equatable.dart';

/// Connection state for the AICO backend
/// Tracks connection status, server info, and error states
abstract class ConnectionState extends Equatable with JsonSerializable<ConnectionState> {
  const ConnectionState();

  @override
  List<Object?> get props => [];
}

/// Initial connection state
class ConnectionInitial extends ConnectionState {
  const ConnectionInitial();

  @override
  Map<String, dynamic> toJson() => {'type': 'initial'};

  @override
  ConnectionState fromJson(Map<String, dynamic> json) => const ConnectionInitial();

  @override
  ConnectionState copyWith() => const ConnectionInitial();
}

/// Connection in progress
class ConnectionConnecting extends ConnectionState {
  const ConnectionConnecting();

  @override
  Map<String, dynamic> toJson() => {'type': 'connecting'};

  @override
  ConnectionState fromJson(Map<String, dynamic> json) => const ConnectionConnecting();

  @override
  ConnectionState copyWith() => const ConnectionConnecting();
}

/// Successfully connected
class ConnectionConnected extends ConnectionState {
  final String serverUrl;
  final String serverVersion;
  final DateTime connectedAt;

  const ConnectionConnected({
    required this.serverUrl,
    required this.serverVersion,
    required this.connectedAt,
  });

  @override
  List<Object?> get props => [serverUrl, serverVersion, connectedAt];

  @override
  Map<String, dynamic> toJson() => {
    'type': 'connected',
    'serverUrl': serverUrl,
    'serverVersion': serverVersion,
    'connectedAt': connectedAt.toIso8601String(),
  };

  @override
  ConnectionState fromJson(Map<String, dynamic> json) {
    JsonSerializable.validateRequiredFields(json, ['serverUrl', 'serverVersion', 'connectedAt']);
    
    return ConnectionConnected(
      serverUrl: JsonSerializable.getField<String>(json, 'serverUrl'),
      serverVersion: JsonSerializable.getField<String>(json, 'serverVersion'),
      connectedAt: DateTime.parse(JsonSerializable.getField<String>(json, 'connectedAt')),
    );
  }

  @override
  ConnectionState copyWith({
    String? serverUrl,
    String? serverVersion,
    DateTime? connectedAt,
  }) {
    return ConnectionConnected(
      serverUrl: serverUrl ?? this.serverUrl,
      serverVersion: serverVersion ?? this.serverVersion,
      connectedAt: connectedAt ?? this.connectedAt,
    );
  }
}

/// Connection failed
class ConnectionError extends ConnectionState {
  final String message;
  final String? errorCode;
  final DateTime occurredAt;

  const ConnectionError({
    required this.message,
    this.errorCode,
    required this.occurredAt,
  });

  @override
  List<Object?> get props => [message, errorCode, occurredAt];

  @override
  Map<String, dynamic> toJson() => {
    'type': 'error',
    'message': message,
    'errorCode': errorCode,
    'occurredAt': occurredAt.toIso8601String(),
  };

  @override
  ConnectionState fromJson(Map<String, dynamic> json) {
    JsonSerializable.validateRequiredFields(json, ['message', 'occurredAt']);
    
    return ConnectionError(
      message: JsonSerializable.getField<String>(json, 'message'),
      errorCode: json['errorCode'] as String?,
      occurredAt: DateTime.parse(JsonSerializable.getField<String>(json, 'occurredAt')),
    );
  }

  @override
  ConnectionState copyWith({
    String? message,
    String? errorCode,
    DateTime? occurredAt,
  }) {
    return ConnectionError(
      message: message ?? this.message,
      errorCode: errorCode ?? this.errorCode,
      occurredAt: occurredAt ?? this.occurredAt,
    );
  }
}

/// Disconnected state
class ConnectionDisconnected extends ConnectionState {
  final String? reason;
  final DateTime? disconnectedAt;

  const ConnectionDisconnected({
    this.reason,
    this.disconnectedAt,
  });

  @override
  List<Object?> get props => [reason, disconnectedAt];

  @override
  Map<String, dynamic> toJson() => {
    'type': 'disconnected',
    'reason': reason,
    'disconnectedAt': disconnectedAt?.toIso8601String(),
  };

  @override
  ConnectionState fromJson(Map<String, dynamic> json) {
    return ConnectionDisconnected(
      reason: json['reason'] as String?,
      disconnectedAt: json['disconnectedAt'] != null 
          ? DateTime.parse(json['disconnectedAt'] as String)
          : null,
    );
  }

  @override
  ConnectionState copyWith({
    String? reason,
    DateTime? disconnectedAt,
  }) {
    return ConnectionDisconnected(
      reason: reason ?? this.reason,
      disconnectedAt: disconnectedAt ?? this.disconnectedAt,
    );
  }
}
