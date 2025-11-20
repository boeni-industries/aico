import 'package:aico_frontend/networking/clients/unified_api_client.dart';
import 'package:aico_frontend/data/models/emotion_model.dart';

/// Repository for emotion API operations
class EmotionRepository {
  final UnifiedApiClient _apiClient;

  EmotionRepository({
    required UnifiedApiClient apiClient,
  }) : _apiClient = apiClient;

  /// Get current emotional state from backend
  Future<EmotionModel?> getCurrentEmotion() async {
    try {
      print('[EMOTION_REPO] Fetching emotion from /emotion/current');
      final data = await _apiClient.get<Map<String, dynamic>>('/emotion/current');
      
      if (data != null) {
        print('[EMOTION_REPO] Got emotion data: $data');
        return EmotionModel.fromJson(data);
      } else {
        print('[EMOTION_REPO] No emotional state available (null response)');
        return null;
      }
    } catch (e) {
      print('[EMOTION_REPO] Error fetching emotion: $e');
      // Silently fail - emotion is non-critical
      return null;
    }
  }

  /// Get emotional state history
  Future<List<EmotionHistoryItem>> getEmotionHistory({int limit = 50}) async {
    try {
      print('[EMOTION_REPO] Fetching emotion history with limit=$limit');
      final data = await _apiClient.get<Map<String, dynamic>>('/emotion/history?limit=$limit');
      
      print('[EMOTION_REPO] History response: $data');
      
      if (data != null && data['history'] != null) {
        final history = (data['history'] as List)
            .map((item) => EmotionHistoryItem.fromJson(item as Map<String, dynamic>))
            .toList();
        print('[EMOTION_REPO] Parsed ${history.length} history items');
        return history;
      } else {
        print('[EMOTION_REPO] No history data in response');
        return [];
      }
    } catch (e) {
      print('[EMOTION_REPO] Error fetching history: $e');
      return [];
    }
  }
}
