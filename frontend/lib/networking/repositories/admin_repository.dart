import 'package:aico_frontend/networking/models/admin_models.dart';
import 'package:aico_frontend/core/services/api_service.dart';
import 'package:aico_frontend/networking/models/error_models.dart';

abstract class AdminRepository {
  Future<AdminHealthResponse> getAdminHealth();
  Future<GatewayStatusResponse> getGatewayStatus();
  Future<LogsListResponse> getLogs({
    int? limit,
    int? offset,
    String? level,
    String? subsystem,
  });
}

class ApiAdminRepository implements AdminRepository {
  final ApiService _apiService;

  ApiAdminRepository(this._apiService);

  @override
  Future<AdminHealthResponse> getAdminHealth() async {
    try {
      return await _apiService.getAdminHealth();
    } catch (e) {
      if (e is NetworkException) {
        rethrow;
      }
      throw ConnectionException('Failed to get admin health: $e');
    }
  }

  @override
  Future<GatewayStatusResponse> getGatewayStatus() async {
    try {
      return await _apiService.getGatewayStatus();
    } catch (e) {
      if (e is NetworkException) {
        rethrow;
      }
      throw ConnectionException('Failed to get gateway status: $e');
    }
  }

  @override
  Future<LogsListResponse> getLogs({
    int? limit,
    int? offset,
    String? level,
    String? subsystem,
  }) async {
    try {
      return await _apiService.getLogs(
        limit: limit,
        offset: offset,
        level: level,
        subsystem: subsystem,
      );
    } catch (e) {
      if (e is NetworkException) {
        rethrow;
      }
      throw ConnectionException('Failed to get logs: $e');
    }
  }
}
