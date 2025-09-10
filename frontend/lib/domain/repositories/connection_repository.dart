import 'package:aico_frontend/domain/entities/connection_state.dart';

/// Abstract repository interface for connection management
abstract class ConnectionRepository {
  /// Get current connection state
  Stream<ConnectionState> getConnectionState();
  
  /// Connect to backend
  Future<void> connect();
  
  /// Disconnect from backend
  Future<void> disconnect();
  
  /// Reconnect with retry logic
  Future<void> reconnect();
  
  /// Switch connection mode (HTTP, WebSocket, IPC)
  Future<void> switchMode(ConnectionMode mode);
  
  /// Test connection health
  Future<bool> testConnection();
  
  /// Get connection statistics
  Future<Map<String, dynamic>> getConnectionStats();
}
