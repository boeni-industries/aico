import 'package:aico_frontend/networking/clients/unified_api_client.dart';

/// Remote data source for behavioral learning feedback operations
/// 
/// Handles communication with the behavioral learning API endpoints
/// for submitting user feedback on AI responses.
class BehavioralRemoteDataSource {
  final UnifiedApiClient _apiClient;

  const BehavioralRemoteDataSource(this._apiClient);

  /// Submit feedback for an AI message
  /// 
  /// Args:
  ///   messageId: ID of the message being rated
  ///   reward: 1 for positive (thumbs up), -1 for negative (thumbs down)
  ///   reason: Optional quick tag category
  ///   freeText: Optional detailed feedback text
  /// 
  /// Returns:
  ///   Map containing the new confidence score and feedback event ID
  Future<Map<String, dynamic>> submitFeedback({
    required String messageId,
    required int reward,
    String? reason,
    String? freeText,
  }) async {
    try {
      final response = await _apiClient.request<Map<String, dynamic>>(
        'POST',
        '/behavioral/feedback',
        data: {
          'message_id': messageId,
          'reward': reward,
          if (reason != null) 'reason': reason,
          if (freeText != null) 'free_text': freeText,
        },
        fromJson: (json) => json,
      );
      
      if (response != null) {
        return response;
      }
      throw Exception('Invalid response from server');
    } catch (e) {
      throw Exception('Failed to submit feedback: $e');
    }
  }
}
