import 'package:equatable/equatable.dart';

/// Events for the Connection BLoC
/// Handles all connection-related actions and state transitions
abstract class ConnectionEvent extends Equatable {
  const ConnectionEvent();

  @override
  List<Object?> get props => [];
}

/// Connect to the AICO backend
class ConnectionConnect extends ConnectionEvent {
  final String? serverUrl;

  const ConnectionConnect({this.serverUrl});

  @override
  List<Object?> get props => [serverUrl];
}

/// Disconnect from the AICO backend
class ConnectionDisconnect extends ConnectionEvent {
  final String? reason;

  const ConnectionDisconnect({this.reason});

  @override
  List<Object?> get props => [reason];
}

/// Reconnect to the AICO backend
class ConnectionReconnect extends ConnectionEvent {
  const ConnectionReconnect();
}

/// Check connection status
class ConnectionCheckStatus extends ConnectionEvent {
  const ConnectionCheckStatus();
}

/// Update server URL
class ConnectionUpdateServerUrl extends ConnectionEvent {
  final String serverUrl;

  const ConnectionUpdateServerUrl(this.serverUrl);

  @override
  List<Object?> get props => [serverUrl];
}

/// Connection timeout occurred
class ConnectionTimeout extends ConnectionEvent {
  const ConnectionTimeout();
}

/// Connection restored after network issues
class ConnectionRestored extends ConnectionEvent {
  const ConnectionRestored();
}
