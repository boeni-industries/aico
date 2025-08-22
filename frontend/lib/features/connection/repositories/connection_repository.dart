import '../../../core/services/api_client.dart';
import '../../../core/services/local_storage.dart';
import '../../../core/utils/repository_factory.dart';

/// Repository for managing backend connection operations
/// Handles API communication and local connection state persistence
class ConnectionRepository implements Disposable {
  final ApiClient _apiClient;
  final LocalStorage _localStorage;

  ConnectionRepository({
    required ApiClient apiClient,
    required LocalStorage localStorage,
  })  : _apiClient = apiClient,
        _localStorage = localStorage;

  /// Test connection to the backend server
  Future<ConnectionInfo> testConnection({String? serverUrl}) async {
    try {
      final response = await _apiClient.get<Map<String, dynamic>>(
        '/api/v1/health',
        fromJson: (json) => json,
      );

      if (response.isSuccess && response.data != null) {
        return ConnectionInfo(
          serverUrl: serverUrl ?? 'http://localhost:8000',
          serverVersion: response.data!['version'] as String? ?? 'unknown',
          isHealthy: response.data!['status'] == 'healthy',
          connectedAt: DateTime.now(),
        );
      } else {
        throw ConnectionException('Health check failed');
      }
    } catch (e) {
      throw ConnectionException('Failed to connect to server: $e');
    }
  }

  /// Get server status information
  Future<ServerStatus> getServerStatus() async {
    try {
      final response = await _apiClient.get<Map<String, dynamic>>(
        '/api/v1/health',
        fromJson: (json) => json,
      );

      if (response.isSuccess && response.data != null) {
        return ServerStatus(
          status: response.data!['status'] as String,
          version: response.data!['version'] as String? ?? 'unknown',
          uptime: response.data!['uptime'] as int? ?? 0,
          timestamp: DateTime.now(),
        );
      } else {
        throw ConnectionException('Failed to get server status');
      }
    } catch (e) {
      throw ConnectionException('Failed to get server status: $e');
    }
  }

  /// Save connection settings locally
  Future<void> saveConnectionSettings(ConnectionSettings settings) async {
    try {
      await _localStorage.saveState('connection_settings', settings.toJson());
    } catch (e) {
      throw ConnectionException('Failed to save connection settings: $e');
    }
  }

  /// Load connection settings from local storage
  Future<ConnectionSettings?> loadConnectionSettings() async {
    try {
      final data = await _localStorage.loadState('connection_settings');
      if (data != null) {
        return ConnectionSettings.fromJson(data);
      }
      return null;
    } catch (e) {
      throw ConnectionException('Failed to load connection settings: $e');
    }
  }

  /// Save last successful connection info
  Future<void> saveLastConnection(ConnectionInfo info) async {
    try {
      await _localStorage.saveState('last_connection', info.toJson());
    } catch (e) {
      throw ConnectionException('Failed to save last connection: $e');
    }
  }

  /// Load last successful connection info
  Future<ConnectionInfo?> loadLastConnection() async {
    try {
      final data = await _localStorage.loadState('last_connection');
      if (data != null) {
        return ConnectionInfo.fromJson(data);
      }
      return null;
    } catch (e) {
      throw ConnectionException('Failed to load last connection: $e');
    }
  }

  @override
  Future<void> dispose() async {
    // Clean up any resources if needed
  }
}

/// Connection information model
class ConnectionInfo {
  final String serverUrl;
  final String serverVersion;
  final bool isHealthy;
  final DateTime connectedAt;

  const ConnectionInfo({
    required this.serverUrl,
    required this.serverVersion,
    required this.isHealthy,
    required this.connectedAt,
  });

  Map<String, dynamic> toJson() => {
    'serverUrl': serverUrl,
    'serverVersion': serverVersion,
    'isHealthy': isHealthy,
    'connectedAt': connectedAt.toIso8601String(),
  };

  factory ConnectionInfo.fromJson(Map<String, dynamic> json) {
    return ConnectionInfo(
      serverUrl: json['serverUrl'] as String,
      serverVersion: json['serverVersion'] as String,
      isHealthy: json['isHealthy'] as bool,
      connectedAt: DateTime.parse(json['connectedAt'] as String),
    );
  }
}

/// Server status model
class ServerStatus {
  final String status;
  final String version;
  final int uptime;
  final DateTime timestamp;

  const ServerStatus({
    required this.status,
    required this.version,
    required this.uptime,
    required this.timestamp,
  });

  Map<String, dynamic> toJson() => {
    'status': status,
    'version': version,
    'uptime': uptime,
    'timestamp': timestamp.toIso8601String(),
  };

  factory ServerStatus.fromJson(Map<String, dynamic> json) {
    return ServerStatus(
      status: json['status'] as String,
      version: json['version'] as String,
      uptime: json['uptime'] as int,
      timestamp: DateTime.parse(json['timestamp'] as String),
    );
  }
}

/// Connection settings model
class ConnectionSettings {
  final String defaultServerUrl;
  final int connectionTimeout;
  final int retryAttempts;
  final bool autoReconnect;

  const ConnectionSettings({
    required this.defaultServerUrl,
    this.connectionTimeout = 30000,
    this.retryAttempts = 3,
    this.autoReconnect = true,
  });

  Map<String, dynamic> toJson() => {
    'defaultServerUrl': defaultServerUrl,
    'connectionTimeout': connectionTimeout,
    'retryAttempts': retryAttempts,
    'autoReconnect': autoReconnect,
  };

  factory ConnectionSettings.fromJson(Map<String, dynamic> json) {
    return ConnectionSettings(
      defaultServerUrl: json['defaultServerUrl'] as String,
      connectionTimeout: json['connectionTimeout'] as int? ?? 30000,
      retryAttempts: json['retryAttempts'] as int? ?? 3,
      autoReconnect: json['autoReconnect'] as bool? ?? true,
    );
  }

  ConnectionSettings copyWith({
    String? defaultServerUrl,
    int? connectionTimeout,
    int? retryAttempts,
    bool? autoReconnect,
  }) {
    return ConnectionSettings(
      defaultServerUrl: defaultServerUrl ?? this.defaultServerUrl,
      connectionTimeout: connectionTimeout ?? this.connectionTimeout,
      retryAttempts: retryAttempts ?? this.retryAttempts,
      autoReconnect: autoReconnect ?? this.autoReconnect,
    );
  }
}

/// Exception for connection-related errors
class ConnectionException implements Exception {
  final String message;
  const ConnectionException(this.message);

  @override
  String toString() => 'ConnectionException: $message';
}
