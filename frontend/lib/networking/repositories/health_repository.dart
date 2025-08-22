import '../clients/api_client.dart';
import '../models/health_models.dart';
import '../models/error_models.dart';

abstract class HealthRepository {
  Future<HealthResponse> getHealth();
  Future<DetailedHealthResponse> getDetailedHealth();
}

class ApiHealthRepository implements HealthRepository {
  final AicoApiClient _apiClient;

  ApiHealthRepository(this._apiClient);

  @override
  Future<HealthResponse> getHealth() async {
    try {
      return await _apiClient.getHealth();
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
      return await _apiClient.getDetailedHealth();
    } catch (e) {
      if (e is NetworkException) {
        rethrow;
      }
      throw ConnectionException('Failed to get detailed health status: $e');
    }
  }
}
