import 'package:aico_frontend/data/models/proactive_model.dart';
import 'package:aico_frontend/networking/clients/unified_api_client.dart';

/// Remote data source for proactive conversation operations
class ProactiveRemoteDataSource {
  final UnifiedApiClient _apiClient;

  const ProactiveRemoteDataSource(this._apiClient);

  /// Get all pending proactive initiations for current user
  Future<List<InitiationModel>> getPendingInitiations() async {
    try {
      // Proactive conversation initiations are represented as pending interaction requests.
      // The legacy /conversation/proactive/* endpoints are intentionally not part of the
      // gateway HTTP surface.
      final response = await _apiClient.request<dynamic>(
        'GET',
        '/interactions',
        queryParameters: {
          'status': 'pending',
          // Most proactive initiations are delivered as dialogue interactions.
          'interaction_type': 'dialogue',
          'limit': '50',
          'offset': '0',
        },
      );

      if (response == null || response is! Map) {
        return [];
      }

      final items = response['items'];
      if (items == null || items is! List) {
        return [];
      }

      // Map InteractionResponse -> InitiationModel (UI expects this shape)
      return items
          .whereType<Map>()
          .map((raw) {
            final m = Map<String, dynamic>.from(raw);
            return InitiationModel.fromJson({
              'initiation_id': (m['interaction_id'] ?? '').toString(),
              'user_id': (m['user_id'] ?? '').toString(),
              'conversation_id': (m['correlation_id'] ?? '').toString(),
              'question': (m['prompt'] ?? '').toString(),
              'initiated_at': (m['created_at'] ?? '').toString(),
              'resolution_status': (m['status'] ?? '').toString(),
              'resolved_at': m['answered_at']?.toString(),
              'user_response_time': null,
              'engagement_score': null,
            });
          })
          .toList();
    } catch (e) {
      throw Exception('Failed to get pending initiations: $e');
    }
  }

  /// Get initiation history
  Future<List<InitiationModel>> getInitiationHistory({int limit = 20}) async {
    try {
      final response = await _apiClient.request<dynamic>(
        'GET',
        '/interactions',
        queryParameters: {
          'interaction_type': 'dialogue',
          'limit': limit.toString(),
          'offset': '0',
        },
      );

      if (response == null || response is! Map) {
        return [];
      }

      final items = response['items'];
      if (items == null || items is! List) {
        return [];
      }

      return items
          .whereType<Map>()
          .map((raw) {
            final m = Map<String, dynamic>.from(raw);
            return InitiationModel.fromJson({
              'initiation_id': (m['interaction_id'] ?? '').toString(),
              'user_id': (m['user_id'] ?? '').toString(),
              'conversation_id': (m['correlation_id'] ?? '').toString(),
              'question': (m['prompt'] ?? '').toString(),
              'initiated_at': (m['created_at'] ?? '').toString(),
              'resolution_status': (m['status'] ?? '').toString(),
              'resolved_at': m['answered_at']?.toString(),
              'user_response_time': null,
              'engagement_score': null,
            });
          })
          .toList();
    } catch (e) {
      throw Exception('Failed to get initiation history: $e');
    }
  }

  /// Respond to a proactive initiation
  Future<void> respondToInitiation(InitiationResponseRequest request) async {
    try {
      // Proactive responses are handled by answering the underlying interaction request.
      await _apiClient.request(
        'POST',
        '/interactions/${request.initiationId}/answer',
        data: {
          'answer_text': request.responseText ?? '',
          'answer_json': null,
        },
      );
    } catch (e) {
      throw Exception('Failed to respond to initiation: $e');
    }
  }
}
