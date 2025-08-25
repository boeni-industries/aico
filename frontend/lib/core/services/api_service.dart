import 'package:aico_frontend/core/services/smart_api_client.dart';
import 'package:aico_frontend/networking/models/admin_models.dart';
import 'package:aico_frontend/networking/models/health_models.dart';
import 'package:aico_frontend/networking/models/user_models.dart';
import 'package:dio/dio.dart';

/// High-level API service that provides typed methods using SmartApiClient
/// Automatically handles encryption/unencryption based on endpoint requirements
class ApiService {
  final SmartApiClient _client;

  ApiService(Dio dio) : _client = SmartApiClient(dio);

  /// Initialize encryption (call once at app start)
  Future<void> initialize() async {
    await _client.initializeEncryption();
  }

  // Health endpoints (automatically unencrypted)
  Future<HealthResponse> getHealth() => 
    _client.get('/health', fromJson: HealthResponse.fromJson);

  Future<DetailedHealthResponse> getDetailedHealth() => 
    _client.get('/health/detailed', fromJson: DetailedHealthResponse.fromJson);

  // User endpoints (automatically encrypted)
  Future<UserListResponse> getUsers({String? userType, int limit = 100}) =>
    _client.get('/users', fromJson: UserListResponse.fromJson);

  Future<User> createUser(CreateUserRequest request) =>
    _client.post('/users', request.toJson(), fromJson: User.fromJson);

  Future<User> getUser(String uuid) =>
    _client.get('/users/$uuid', fromJson: User.fromJson);

  Future<User> updateUser(String uuid, UpdateUserRequest request) =>
    _client.put('/users/$uuid', request.toJson(), fromJson: User.fromJson);

  Future<void> deleteUser(String uuid) =>
    _client.delete('/users/$uuid');

  Future<AuthenticationResponse> authenticate(AuthenticateRequest request) =>
    _client.post('/users/authenticate', request.toJson(), fromJson: AuthenticationResponse.fromJson);

  // Admin endpoints (automatically encrypted)
  Future<AdminHealthResponse> getAdminHealth() =>
    _client.get('/admin/health', fromJson: AdminHealthResponse.fromJson);

  Future<GatewayStatusResponse> getGatewayStatus() =>
    _client.get('/admin/gateway/status', fromJson: GatewayStatusResponse.fromJson);

  Future<LogsListResponse> getLogs({
    int? limit,
    int? offset,
    String? level,
    String? subsystem,
  }) {
    final queryParams = <String, dynamic>{};
    if (limit != null) queryParams['limit'] = limit;
    if (offset != null) queryParams['offset'] = offset;
    if (level != null) queryParams['level'] = level;
    if (subsystem != null) queryParams['subsystem'] = subsystem;
    
    return _client.request('GET', '/admin/logs', 
      queryParameters: queryParams,
      fromJson: LogsListResponse.fromJson
    );
  }

  // Echo endpoints (automatically encrypted)
  Future<Map<String, dynamic>> echo(String message) =>
    _client.post('/echo', {'message': message});

  /// Access to underlying smart client for advanced usage
  SmartApiClient get client => _client;
  
  /// Encryption status
  bool get isEncryptionActive => _client.isEncryptionActive;
  String get encryptionStatus => _client.encryptionStatus;
}
