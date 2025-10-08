import 'package:aico_frontend/networking/clients/unified_api_client.dart';
import 'package:aico_frontend/networking/models/admin_models.dart';
import 'package:aico_frontend/networking/models/health_models.dart';
import 'package:aico_frontend/networking/models/user_models.dart';

/// High-level API service that provides typed methods using SmartApiClient
/// Automatically handles encryption/unencryption based on endpoint requirements
class ApiService {
  final UnifiedApiClient _client;

  ApiService(UnifiedApiClient client) : _client = client;

  /// Initialize encryption (call once at app start)
  Future<void> initialize() async {
    await _client.initialize();
  }

  // Health endpoints (automatically unencrypted)
  Future<HealthResponse> getHealth() async {
    final response = await _client.request<HealthResponse>('GET', '/health', fromJson: HealthResponse.fromJson);
    return response!;
  }

  Future<DetailedHealthResponse> getDetailedHealth() async {
    final response = await _client.request<DetailedHealthResponse>('GET', '/health/detailed', fromJson: DetailedHealthResponse.fromJson);
    return response!;
  }

  // User endpoints (automatically encrypted)
  Future<UserListResponse> getUsers({String? userType, int limit = 100}) async {
    final response = await _client.request<UserListResponse>('GET', '/users', fromJson: UserListResponse.fromJson);
    return response!;
  }

  Future<User> createUser(CreateUserRequest request) async {
    final response = await _client.request<User>('POST', '/users', data: request.toJson(), fromJson: User.fromJson);
    return response!;
  }

  Future<User> getUser(String uuid) async {
    final response = await _client.request<User>('GET', '/users/$uuid', fromJson: User.fromJson);
    return response!;
  }

  Future<User> updateUser(String uuid, UpdateUserRequest request) async {
    final response = await _client.request<User>('PUT', '/users/$uuid', data: request.toJson(), fromJson: User.fromJson);
    return response!;
  }

  Future<void> deleteUser(String uuid) async {
    await _client.request<Map<String, dynamic>>('DELETE', '/users/$uuid');
  }

  Future<AuthenticationResponse> authenticate(AuthenticateRequest request) async {
    final response = await _client.request<AuthenticationResponse>('POST', '/users/authenticate', data: request.toJson(), fromJson: AuthenticationResponse.fromJson);
    return response!;
  }

  // Admin endpoints (automatically encrypted)
  Future<AdminHealthResponse> getAdminHealth() async {
    final response = await _client.request<AdminHealthResponse>('GET', '/admin/health', fromJson: AdminHealthResponse.fromJson);
    return response!;
  }

  Future<GatewayStatusResponse> getGatewayStatus() async {
    final response = await _client.request<GatewayStatusResponse>('GET', '/admin/gateway/status', fromJson: GatewayStatusResponse.fromJson);
    return response!;
  }

  Future<LogsListResponse> getLogs({
    int? limit,
    int? offset,
    String? level,
    String? subsystem,
    String? component,
    DateTime? startTime,
    DateTime? endTime,
  }) async {
    final queryParameters = <String, String>{
      if (limit != null) 'limit': limit.toString(),
      if (offset != null) 'offset': offset.toString(),
      if (level != null) 'level': level,
      if (subsystem != null) 'subsystem': subsystem,
      if (component != null) 'component': component,
      if (startTime != null) 'start_time': startTime.toIso8601String(),
      if (endTime != null) 'end_time': endTime.toIso8601String(),
    };
    
    final response = await _client.request<LogsListResponse>('GET', '/admin/logs', queryParameters: queryParameters, fromJson: LogsListResponse.fromJson);
    return response!;
  }

  Future<void> clearLogs() async {
    await _client.request<Map<String, dynamic>>('POST', '/admin/logs/clear', data: {});
  }

  // Echo endpoints (automatically encrypted)
  Future<Map<String, dynamic>> echo(String message) async {
    final response = await _client.request<Map<String, dynamic>>('POST', '/echo', data: {'message': message});
    return response ?? {};
  }
}
