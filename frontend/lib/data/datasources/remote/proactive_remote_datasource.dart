import 'package:aico_frontend/data/models/proactive_model.dart';
import 'package:aico_frontend/networking/clients/unified_api_client.dart';

/// Remote data source for proactive conversation operations
class ProactiveRemoteDataSource {
  final UnifiedApiClient _apiClient;

  const ProactiveRemoteDataSource(this._apiClient);

  /// Get all pending proactive initiations for current user
  Future<List<InitiationModel>> getPendingInitiations() async {
    try {
      final response = await _apiClient.request<dynamic>(
        'GET',
        '/conversation/proactive/pending',
      );
      
      if (response != null && response is List) {
        return response
            .map((item) => InitiationModel.fromJson(item as Map<String, dynamic>))
            .toList();
      }
      return [];
    } catch (e) {
      throw Exception('Failed to get pending initiations: $e');
    }
  }

  /// Get initiation history
  Future<List<InitiationModel>> getInitiationHistory({int limit = 20}) async {
    try {
      final response = await _apiClient.request<dynamic>(
        'GET',
        '/conversation/proactive/history',
        queryParameters: {'limit': limit.toString()},
      );
      
      if (response != null && response is List) {
        return response
            .map((item) => InitiationModel.fromJson(item as Map<String, dynamic>))
            .toList();
      }
      return [];
    } catch (e) {
      throw Exception('Failed to get initiation history: $e');
    }
  }

  /// Respond to a proactive initiation
  Future<void> respondToInitiation(InitiationResponseRequest request) async {
    try {
      await _apiClient.request(
        'POST',
        '/conversation/proactive/respond',
        data: request.toJson(),
      );
    } catch (e) {
      throw Exception('Failed to respond to initiation: $e');
    }
  }
}
