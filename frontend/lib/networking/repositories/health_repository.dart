import 'package:aico_frontend/core/services/api_service.dart';
import 'package:aico_frontend/networking/models/error_models.dart';
import 'package:aico_frontend/networking/models/health_models.dart';

abstract class HealthRepository {
  Future<HealthResponse> getHealth();
  Future<DetailedHealthResponse> getDetailedHealth();
}

class ApiHealthRepository implements HealthRepository {
  final ApiService _apiService;

  ApiHealthRepository(this._apiService);

  @override
  Future<HealthResponse> getHealth() async {
    try {
      return await _apiService.getHealth();
    } catch (e) {
      if (e is NetworkException) {
        rethrow;
      }
      throw ConnectionException('Failed to get health status: $e');
    }
  }

  @override
  Future<DetailedHealthResponse> getDetailedHealth() async {
    try {
      return await _apiService.getDetailedHealth();
    } catch (e) {
      if (e is NetworkException) {
        rethrow;
      }
      throw ConnectionException('Failed to get detailed health status: $e');
    }
  }
}
